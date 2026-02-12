import asyncio
import logging
from aiortc import MediaStreamTrack
from api.session import Session
from config import constants
from events.video_events import VisionEvent
from utils.emitter import DataChannelWrapper, http_post_event
from video.frame_sampler import FrameSampler
from inference_sdk import InferenceHTTPClient

logger = logging.getLogger("yolo_rest.tracks.video_observer")

class VideoObserverTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, source: MediaStreamTrack, session: Session):
        super().__init__()
        self._source = source
        self._sampler = FrameSampler(fps=constants.VIDEO_FPS)
        self._yolo = InferenceHTTPClient(
            api_url=constants.ROBOFLOW_API_URL,
            api_key=constants.ROBOFLOW_API_KEY)
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._frame_index = 0
        self._session = session
        logger.info(f"VideoObserverTrack initialized for session: {session.correlation_id}, fps={constants.VIDEO_FPS}")

    async def recv(self):
        frame = await self._source.recv()
        self._frame_index += 1

        if self._sampler.should_process():
            logger.info(f"[{self._session.correlation_id}] Processing video frame: {self._frame_index}")
            img = frame.to_ndarray(format="bgr24")
            frame_index = self._frame_index

            self._loop.run_in_executor(
                None,
                self._run_yolo,
                img,
                frame_index
            )
        else:
            logger.info(f"[{self._session.correlation_id}] Skipping video frame: {self._frame_index} (sampling rate)")

        return frame


    def _run_yolo(self, img, frame_index: int):
        try:
            logger.info(f"[{self._session.correlation_id}] Running YOLO inference on frame: {frame_index}")
            result = self._yolo.infer(img, model_id=constants.ROBOFLOW_MODEL_ID)
            
            predictions = result.get("predictions")
            logger.info(f"[{self._session.correlation_id}] YOLO inference completed: frame={frame_index}, detections={len(predictions)}")
            
            for prediction in predictions:
                confidence = prediction["confidence"]
                label = prediction["class"]
                logger.info(f"[{self._session.correlation_id}] Detection: frame={frame_index}, class={label}, confidence={confidence:.2f}")
                
                event = VisionEvent(
                    label=label,
                    confidence=confidence,
                    frameIndex=frame_index,
                    x=prediction["x"],
                    y=prediction["y"],
                    width=prediction["width"],
                    height=prediction["height"],
                )
                http_post_event("object", event, self._session)
                channel = self._session.data_channel
                if channel:
                    DataChannelWrapper(channel, self._loop).send_json(event)
        except Exception as e:
            logger.error(f"[{self._session.correlation_id}] YOLO inference failed: frame={frame_index}, error={e}")


