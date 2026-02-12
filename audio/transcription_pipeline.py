import logging
from typing import Callable, Optional

from audio.audio_frame_adapter import AudioFrameAdapter, PcmChunker
from audio.streaming_stt_orchestrator import StreamingSttOrchestrator
from audio.vad_detector import VadDetector
from events.audio_events import TranscriptionEvent

logger = logging.getLogger("yolo_rest.audio.transcription_pipeline")


class RealtimeTranscriptionPipeline:

    def __init__(
        self,
        on_transcript: Optional[Callable[[TranscriptionEvent], None]] = None,
    ):
        """
        Args:
            on_transcript: Callback(event: TranscriptionEvent) for final results.
        """
        self.adapter = AudioFrameAdapter()
        self.chuncker = PcmChunker()
        self.vad = VadDetector()
        self.orchestrator = StreamingSttOrchestrator(on_transcript=on_transcript)

        self._session_active = False  # Track if STT session is running

    async def on_audio_frame(self, frame):
        pcm = self.adapter.to_pcm16(frame)
        chunks = self.chuncker.push(pcm)

        for pcm_chunk in chunks:
            is_speech = self.vad.is_speech(pcm_chunk)

            if not self._session_active:
                # Before session starts: only send when speech detected
                if is_speech:
                    self._session_active = True
                    logger.debug("First speech detected, activating STT session")
                    self.orchestrator.push_audio(pcm_chunk, is_speech=True)
            else:
                # Session active: send ALL audio continuously (Google needs real-time flow)
                self.orchestrator.push_audio(pcm_chunk, is_speech=is_speech)

    def close(self):
        self.orchestrator.close()
