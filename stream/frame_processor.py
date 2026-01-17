import asyncio
import logging
import time
from typing import Callable, Any, List

from preprocessing.frame_decoder import decode_image
from preprocessing.validator import validate_resolution, is_blurry, estimate_blur_score
from preprocessing.resizer import resize_to_720p
from inference.roboflow_client import infer_image
from models.events import DetectionEvent, WoundModel

logger = logging.getLogger("yolo_rest.frame_processor")


class FrameProcessor:
    """Processes frames from a FrameBuffer and emits detection events via an emitter.

    Emitter must be an async callable that accepts a single dict (the event JSON).
    """

    def __init__(self, frame_buffer, session):
        self.frame_buffer = frame_buffer
        self.session = session
        self._task = None
        self._stop = False

    def _convert_detections(self, detections: List[dict]) -> List[WoundModel]:
        wounds: List[WoundModel] = []
        for d in detections:
            try:
                w = WoundModel(
                    id=int(d.get("id", 0)),
                    cls=str(d.get("cls", "unknown")),
                    bbox=[float(x) for x in d.get("bbox", [0, 0, 0, 0])],
                    confidence=float(d.get("confidence", 0.0)),
                    type_confidence=float(d.get("type_confidence", 0.0)),
                )
                wounds.append(w)
            except Exception:
                logger.exception("invalid_detection_format")
        return wounds

    async def _run(self, emitter: Callable[[dict], Any]):
        while not self._stop:
            frame = await self.frame_buffer.get()
            try:
                img = decode_image(frame)
                quality_warning = None
                if not validate_resolution(img):
                    img = resize_to_720p(img)

                # Quality checks
                blur_score = estimate_blur_score(img)
                if is_blurry(img):
                    quality_warning = f"blurry:score={blur_score:.1f}"

                # Call inference
                detections = await infer_image(img)

                wounds = self._convert_detections(detections)

                # record detections count
                if len(wounds) > 0:
                    try:
                        self.session.record_detection(len(wounds))
                    except Exception:
                        pass

                event_model = DetectionEvent(
                    session_id=self.session.session_id,
                    timestamp_ms=int(time.time() * 1000),
                    frame_index=self.session.frame_count,
                    has_wounds=len(wounds) > 0,
                    wounds=wounds,
                    metadata={"quality_warning": quality_warning, "processing_time_ms": None},
                )

                # record and emit (include processing_time)
                self.session.record_frame()
                try:
                    # fill processing time metadata
                    event = event_model.model_dump()
                    event.setdefault("metadata", {})["processing_time_ms"] = 0
                    await emitter(event)
                except Exception:
                    logger.exception("emit_failed")

            except Exception as e:
                logger.exception("frame_processing_error")
                # send a minimal error event
                try:
                    await emitter({
                        "session_id": self.session.session_id,
                        "error": str(e),
                    })
                except Exception:
                    logger.exception("emitter_failed")

    def start(self, emitter: Callable[[dict], Any]):
        if self._task is None:
            self._task = asyncio.create_task(self._run(emitter))

    async def stop(self):
        self._stop = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
