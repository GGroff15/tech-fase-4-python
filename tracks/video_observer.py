import asyncio
from aiortc import MediaStreamTrack
from api.session import Session
from events.video_events import VisionEvent
from utils.emitter import http_post_event
from video.frame_sampler import FrameSampler
from models.yolo_model import YoloV8Model


class VideoObserverTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, source: MediaStreamTrack, session: Session):
        super().__init__()
        self._source = source
        self._sampler = FrameSampler(fps=3)
        self._yolo = YoloV8Model()
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._frame_index = 0
        self._session = session

    async def recv(self):
        frame = await self._source.recv()
        self._frame_index += 1

        if self._sampler.should_process():
            img = frame.to_ndarray(format="bgr24")
            frame_index = self._frame_index  # captura o valor atual

            self._loop.run_in_executor(
                None,
                self._run_yolo,
                img,
                frame_index
            )

        return frame


    def _run_yolo(self, img, frame_index: int):
        labels, confidences = self._yolo.predict(img)

        for label, confidence in zip(labels, confidences):
            event = VisionEvent(
                label=label,
                confidence=round(confidence, 3),
                frameIndex=frame_index
            )
            http_post_event("object", event, self._session)


