import os
from typing import List, Dict, Any, Optional

import numpy as np

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


class LocalYoloFallback:
    """Local Ultralytics YOLOv8 fallback wrapper.

    Loads a model lazily from `LOCAL_YOLO_MODEL_PATH` env var or `yolov8n.pt` in repo.
    Use `USE_GPU` env var (true/false) to control device selection.
    """

    def __init__(self, model_path: Optional[str] = None, use_gpu: Optional[bool] = None, conf: float = 0.25):
        self.model_path = model_path or os.getenv("LOCAL_YOLO_MODEL_PATH") or "yolov8n.pt"
        self.use_gpu = (str(use_gpu).lower() == "true") if use_gpu is not None else (os.getenv("USE_GPU", "false").lower() == "true")
        self.conf = float(os.getenv("LOCAL_YOLO_CONF", str(conf)))
        self._model = None

    def _load(self):
        if YOLO is None:
            raise RuntimeError("ultralytics package not available in environment")
        if self._model is None:
            # model path may be relative to repo
            self._model = YOLO(self.model_path)
            if self.use_gpu:
                try:
                    self._model.to("cuda")
                except Exception:
                    # ignore gpu errors and use cpu
                    pass

    def predict(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Synchronous predict wrapper returning detections as dicts.

        Each dict: {id, cls, bbox: [x,y,w,h], confidence, type_confidence}
        bbox returned in absolute pixel coordinates (x,y top-left, w,h).
        """
        self._load()
        if self._model is None:
            return []

        # Ultralytics supports passing numpy images directly
        try:
            results = self._model.predict(source=image, conf=self.conf)
        except Exception:
            return []

        detections: List[Dict[str, Any]] = []
        idx = 0
        for r in results:
            # r.boxes may be empty
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

            # confs and clss may be torch tensors
            for i, b in enumerate(arr_xyxy):
                try:
                    x1, y1, x2, y2 = [float(v) for v in b]
                    w = x2 - x1
                    h = y2 - y1
                    conf = float(confs[i].cpu().numpy()) if confs is not None else 0.0
                    cls_idx = int(clss[i].cpu().numpy()) if clss is not None else 0
                    # map class index to string if model.names available
                    cls_name = (
                        getattr(self._model, "names", {}).get(cls_idx, str(cls_idx))
                        if hasattr(self._model, "names")
                        else str(cls_idx)
                    )
                    detections.append({
                        "id": idx,
                        "cls": cls_name,
                        "bbox": [x1, y1, w, h],
                        "confidence": conf,
                        "type_confidence": conf,
                    })
                    idx += 1
                except Exception:
                    continue

        return detections


__all__ = ["LocalYoloFallback"]
