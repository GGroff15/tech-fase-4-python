import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from utils.loader import LazyModelLoader

logger = logging.getLogger("yolo_rest.fallback")


class LocalYoloFallback:
    """Local Ultralytics YOLOv8 fallback wrapper.

    Loads a model lazily from `LOCAL_YOLO_MODEL_PATH` env var or `yolov8n.pt` in repo.
    Use `USE_GPU` env var (true/false) to control device selection.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_gpu: Optional[bool] = None,
        conf: float = 0.25,
    ):
        self.model_path = (
            model_path or os.getenv("LOCAL_YOLO_MODEL_PATH") or "yolov8n.pt"
        )
        self.use_gpu = (
            (str(use_gpu).lower() == "true")
            if use_gpu is not None
            else (os.getenv("USE_GPU", "false").lower() == "true")
        )
        self.conf = float(os.getenv("LOCAL_YOLO_CONF", str(conf)))

        def _factory():
            try:
                from ultralytics import YOLO

                m = YOLO(self.model_path)
                if self.use_gpu:
                    try:
                        m.to("cuda")
                    except Exception:
                        logger.warning("Failed to move YOLO model to GPU, using CPU instead", exc_info=True)
                return m
            except Exception:
                logger.warning("Failed to load YOLO model", exc_info=True)
                return None

        self._loader = LazyModelLoader(_factory, name="ultralytics_yolo")

    def _load(self):
        model = self._loader.get()
        if model is None:
            raise RuntimeError(
                "ultralytics package or model not available in environment"
            )
        return model

    def predict(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Synchronous predict wrapper returning detections as dicts.

        Each dict: {id, cls, bbox: [x,y,w,h], confidence, type_confidence}
        bbox returned in absolute pixel coordinates (x,y top-left, w,h).
        """
        try:
            model = self._load()
        except RuntimeError:
            logger.warning("Local YOLO model not available for fallback")
            return []

        # Ultralytics supports passing numpy images directly
        try:
            results = model.predict(source=image, conf=self.conf)
        except Exception:
            logger.warning("Local YOLO inference failed", exc_info=True)
            return []

        # parse results into standardized detection dicts
        return self._parse_yolo_results(results)

    def _parse_yolo_results(self, results) -> List[Dict[str, Any]]:
        detections: List[Dict[str, Any]] = []
        idx = 0
        for r in results:
            boxes = getattr(r, "boxes", None)
            if boxes is None:
                continue
            xyxy = getattr(boxes, "xyxy", None)
            confs = getattr(boxes, "conf", None)
            clss = getattr(boxes, "cls", None)
            if xyxy is None:
                continue
            try:
                arr_xyxy = xyxy.cpu().numpy()
            except Exception:
                try:
                    arr_xyxy = np.array(xyxy)
                except Exception:
                    continue

            for i, b in enumerate(arr_xyxy):
                parsed = self._parse_single_box(b, i, confs, clss, idx)
                if parsed:
                    detections.append(parsed)
                    idx += 1

        return detections

    def _parse_single_box(self, b, i, confs, clss, idx) -> Optional[Dict[str, Any]]:
        try:
            x1, y1, x2, y2 = [float(v) for v in b]
            w = x2 - x1
            h = y2 - y1
            conf = float(confs[i].cpu().numpy()) if confs is not None else 0.0
            cls_idx = int(clss[i].cpu().numpy()) if clss is not None else 0
            
            model = self._loader.get()
            cls_name = (
                model.names.get(cls_idx, str(cls_idx))
                if model and hasattr(model, "names")
                else str(cls_idx)
            )
            return {
                "id": idx,
                "cls": cls_name,
                "bbox": [x1, y1, w, h],
                "confidence": conf,
                "type_confidence": conf,
            }
        except Exception as e:
            logger.warning(f"Failed to parse detection box: {e}")
            return None


__all__ = ["LocalYoloFallback"]
