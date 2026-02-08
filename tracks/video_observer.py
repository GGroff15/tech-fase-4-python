import asyncio
from aiortc import MediaStreamTrack
from api.session import Session
from config.constants import ROBOFLOW_API_KEY, ROBOFLOW_MODEL_ID
from events.video_events import VisionEvent
from utils.emitter import DataChannelWrapper, http_post_event
from video.frame_sampler import FrameSampler
from inference_sdk import InferenceHTTPClient

class VideoObserverTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, source: MediaStreamTrack, session: Session):
        super().__init__()
        self._source = source
        self._sampler = FrameSampler(fps=3)
        self._yolo = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=ROBOFLOW_API_KEY)
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._frame_index = 0
        self._session = session

    async def recv(self):
        frame = await self._source.recv()
        self._frame_index += 1

        if self._sampler.should_process():
            img = frame.to_ndarray(format="bgr24")
            frame_index = self._frame_index

            self._loop.run_in_executor(
                None,
                self._run_yolo,
                img,
                frame_index
            )

        return frame


    def _run_yolo(self, img, frame_index: int):
        result = self._yolo.infer(img, model_id=ROBOFLOW_MODEL_ID)
        
        predictions = result.get("predictions")
        
        for prediction in predictions:
            event = VisionEvent(
                label=prediction["class"],
                confidence=prediction["confidence"],
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


