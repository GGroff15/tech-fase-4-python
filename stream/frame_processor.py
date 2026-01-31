import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List

from config.constants import (QUALITY_WARNING_BLUR_FORMAT)
from inference.roboflow_client import infer_image
from models.events import DetectionEvent, WoundModel
from preprocessing.frame_decoder import decode_image
from preprocessing.resizer import resize_to_720p
from preprocessing.validator import (estimate_blur_score, is_blurry,
                                     validate_resolution)
from stream.frame_buffer import VideoBuffer
from stream.session import StreamSession
from utils.emitter import safe_emit

logger = logging.getLogger("yolo_rest.frame_processor")

# NOTE: thresholds and formats are centralized in config.constants


class BaseProcessor(ABC):
    """Abstract base class for processors handling media buffers.

    Subclasses must implement `_run(self, emitter)` as the main async loop.
    This base provides `start` and `stop` lifecycle management to keep
    implementations consistent between video and audio processors.
    """

    def __init__(self, session: StreamSession):
        self.session: StreamSession = session
        self._task = None
        self._stop = False

    @abstractmethod
    async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
        raise NotImplementedError()

    def start(self, emitter: Callable[[Dict[str, Any]], Any]):
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


class VideoProcessor(BaseProcessor):
    """Processes frames from a FrameBuffer and emits detection events via an emitter.

    Emitter must be an async callable that accepts a single dict (the event JSON).
    """

    def __init__(self, session: StreamSession, frame_buffer: VideoBuffer):
        self.frame_buffer = frame_buffer
        self.session = session
        self._task = None
        self._stop = False

    def _convert_detections(self, detections: List[Dict[str, Any]]) -> List[WoundModel]:
        """Convert raw detection dictionaries to WoundModel objects."""
        wounds: List[WoundModel] = []
        for detection in detections:
            wound = self._create_wound_from_detection(detection)
            if wound:
                wounds.append(wound)
        return wounds

    def _create_wound_from_detection(
        self, detection: Dict[str, Any]
    ) -> WoundModel | None:
        """Create a single WoundModel from a detection dictionary."""
        try:
            return WoundModel(
                id=int(detection.get("id", 0)),
                cls=str(detection.get("cls", "unknown")),
                bbox=[float(x) for x in detection.get("bbox", [0, 0, 0, 0])],
                confidence=float(detection.get("confidence", 0.0)),
                type_confidence=float(detection.get("type_confidence", 0.0)),
            )
        except (ValueError, TypeError) as error:
            logger.warning(
                f"invalid_detection_format: {error}", extra={"detection": detection}
            )
            return None

    async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
        """Main processing loop that handles frames from the buffer."""
        while not self._stop:
            frame = await self.frame_buffer.get()
            await self._process_single_frame(frame, emitter)

    async def _process_single_frame(
        self, frame: Any, emitter: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Process a single frame through the detection pipeline."""
        try:
            image = decode_image(frame)
            prepared_image = self._prepare_image(image)
            quality_warning = self._check_image_quality(prepared_image)
            detections = await infer_image(prepared_image)
            await self._emit_detection_event(detections, quality_warning, emitter)
        except Exception as error:
            await self._handle_processing_error(error, emitter)

    def _prepare_image(self, image: Any) -> Any:
        """Prepare image by validating and resizing if necessary."""
        if not validate_resolution(image):
            return resize_to_720p(image)
        return image

    def _check_image_quality(self, image: Any) -> str | None:
        """Check image quality and return warning message if needed."""
        blur_score = estimate_blur_score(image)
        if is_blurry(image):
            return QUALITY_WARNING_BLUR_FORMAT.format(blur_score)
        return None

    async def _emit_detection_event(
        self,
        detections: List[Dict[str, Any]],
        quality_warning: str | None,
        emitter: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Convert detections to event and emit to client."""
        wounds = self._convert_detections(detections)

        # Record metrics (total wounds for this frame) and capture frame index
        self._record_detections(wounds)
        frame_index = self.session.frame_count
        self.session.record_frame()

        # Emit one event per detected object with required schema:
        # { "label": "person", "confidence": 0.76, "frameIndex": 1234 }
        for wound in wounds:
            try:
                per_obj = {
                    "event_type": "object",
                    "label": wound.cls,
                    "confidence": round(float(wound.confidence), 2),
                    "frameIndex": frame_index,
                }
            except Exception:
                # Fallback in case wound fields are malformed
                per_obj = {"label": "unknown", "confidence": 0.0, "frameIndex": frame_index}

            await self._emit_event(per_obj, emitter)

    def _record_detections(self, wounds: List[WoundModel]) -> None:
        """Record detection count in session."""
        if wounds:
            self.session.record_detection(len(wounds))

    def _create_detection_event(
        self, wounds: List[WoundModel], quality_warning: str | None
    ) -> Dict[str, Any]:
        """Create a detection event from wounds and metadata."""
        event_model = DetectionEvent(
            session_id=self.session.session_id,
            timestamp_ms=int(time.time() * 1000),
            frame_index=self.session.frame_count,
            has_wounds=len(wounds) > 0,
            wounds=wounds,
            metadata={"quality_warning": quality_warning, "processing_time_ms": 0},
        )
        return event_model.model_dump()

    async def _emit_event(
        self, event: Dict[str, Any], emitter: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Emit event to client with error handling."""
        await safe_emit(emitter, event, logger, self.session.session_id)

    async def _handle_processing_error(
        self, error: Exception, emitter: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Handle frame processing errors by logging and emitting error event."""
        logger.error(
            f"frame_processing_error: {error}",
            extra={"session_id": self.session.session_id},
        )
        error_event = {
            "session_id": self.session.session_id,
            "error": str(error),
        }
        await safe_emit(emitter, error_event, logger, self.session.session_id)

    # lifecycle (start/stop) inherited from BaseProcessor
