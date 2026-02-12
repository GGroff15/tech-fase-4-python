import asyncio
import logging
import time
from aiortc import MediaStreamTrack
from api import session
from audio.resampler import AudioResampler16kMono
from audio.transcription_pipeline import RealtimeTranscriptionPipeline
from audio.emotion_buffer import EmotionAudioBuffer
from events.audio_events import EmotionEvent, TranscriptionEvent
from models.emotion_model import SpeechEmotionModel
from utils.emitter import http_post_event
from utils.time_converter import epoch_to_iso_utc

logger = logging.getLogger("yolo_rest.tracks.audio_observer")


class AudioObserverTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, source: MediaStreamTrack, session: session.Session):
        super().__init__()
        self._source = source
        self._resampler = AudioResampler16kMono()
        self._emotion_buffer = EmotionAudioBuffer()
        self._loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._emotion_model = SpeechEmotionModel()
        self._stream_start_monotonic: float | None = None
        self._epoch_offset = time.time() - time.monotonic()
        self._session = session
        self._pipeline = RealtimeTranscriptionPipeline(
            on_transcript=self._handle_transcript
        )
        logger.info(f"AudioObserverTrack initialized for session: {session.correlation_id}")

    def _handle_transcript(self, event: TranscriptionEvent):
        """Callback invoked from Google STT thread with transcription results."""
        logger.info(f"[{self._session.correlation_id}] Transcript received: text={event.text}, confidence={event.confidence:.2f}")
        http_post_event("transcript", event, self._session)

    async def recv(self):
        frame = await self._source.recv()
        
        for resampled in self._resampler.resample(frame):
            pcm = resampled.to_ndarray().tobytes()

            result = self._emotion_buffer.push(pcm)
            if result is not None:
                window_pcm, offset = result
                
                self._loop.run_in_executor(
                    None,
                    self._detect_emotion,
                    window_pcm,
                    offset
                )

        await self._pipeline.on_audio_frame(frame)

        return frame

    def stop(self):
        """Call this when the track ends to cleanup resources."""
        super().stop()
        self._pipeline.close()
        logger.info(f"AudioObserverTrack stopped for session: {self._session.correlation_id}")

    def _detect_emotion(self, window_pcm: bytes, offset_sec: float):
        if self._stream_start_monotonic is None:
            self._stream_start_monotonic = time.monotonic()
        
        logger.info(f"[{self._session.correlation_id}] Running emotion detection on audio window")
        emotion, confidence = self._emotion_model.predict(window_pcm)
        logger.info(f"[{self._session.correlation_id}] Emotion detected: emotion={emotion}, confidence={confidence:.2f}")

        absolute_epoch = (
            self._stream_start_monotonic
            + offset_sec
            + self._epoch_offset
        )

        event = EmotionEvent(
            emotion=emotion,
            confidence=confidence,
            timestamp=epoch_to_iso_utc(absolute_epoch)
        )
        
        http_post_event("emotion", event, self._session)