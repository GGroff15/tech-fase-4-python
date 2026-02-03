import logging
import threading
import time
from typing import Callable, Optional

from audio.emotion_buffer import AudioOverlapBuffer
from audio.google_stt import GoogleStreamingSttSession
from events.audio_events import TranscriptionEvent

logger = logging.getLogger("yolo_rest.audio.streaming_stt_orchestrator")


class StreamingSttOrchestrator:
    """
    Gerencia:
    - rotação de streams
    - overlap de áudio
    - envio contínuo
    """

    def __init__(
        self,
        overlap_ms: int = 1000,
        frame_ms: int = 20,
        on_transcript: Optional[Callable[[TranscriptionEvent], None]] = None,
    ):
        self.overlap_chunks = overlap_ms // frame_ms
        self.overlap_buffer = AudioOverlapBuffer(self.overlap_chunks)
        self.on_transcript = on_transcript

        self.current_session: Optional[GoogleStreamingSttSession] = None
        self.session_start_ts: Optional[float] = None

        self.max_stream_duration = 240  # segundos (antes do limite real)

    def _start_new_session(self):
        preload = self.overlap_buffer.get_overlap()

        self.current_session = GoogleStreamingSttSession(
            preload_chunks=preload,
            on_transcript=self.on_transcript,
        )
        self.session_start_ts = time.time()
        logger.debug("Starting new Google STT session")

        threading.Thread(
            target=self.current_session.start,
            daemon=True
        ).start()

    def push_audio(self, pcm_chunk: bytes, is_speech: bool = True):
        """Push audio chunk to the STT session.
        
        Args:
            pcm_chunk: Raw PCM audio bytes (16kHz, mono, 16-bit)
            is_speech: Whether VAD detected speech in this chunk.
                       Session only starts on first speech detection.
        """
        self.overlap_buffer.push(pcm_chunk)

        # Only start session when actual speech is detected
        if self.current_session is None:
            if is_speech:
                logger.info("Speech detected, starting Google STT session")
                self._start_new_session()
            else:
                # Buffer audio but don't start session yet
                return

        # Check for session rotation (before 5-minute limit)
        if self.session_start_ts and time.time() - self.session_start_ts > self.max_stream_duration:
            logger.info("Rotating Google STT session (duration limit)")
            self.current_session.close()
            self._start_new_session()

        self.current_session.push_audio(pcm_chunk)

    def close(self):
        if self.current_session:
            self.current_session.close()
