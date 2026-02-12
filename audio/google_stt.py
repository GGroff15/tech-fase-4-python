import logging
import queue
import time
from typing import Callable, Optional
from google.cloud import speech_v1 as speech

from config import constants
from events.audio_events import TranscriptionEvent
from utils.time_converter import epoch_to_iso_utc

logger = logging.getLogger("yolo_rest.audio.google_stt")


class GoogleStreamingSttSession:

    def __init__(
        self,
        preload_chunks: Optional[list[bytes]] = None,
        on_transcript: Optional[Callable[[TranscriptionEvent], None]] = None,
    ):
        """
        Args:
            preload_chunks: Audio chunks to send at stream start (for overlap).
            on_transcript: Callback(event: TranscriptionEvent) for final results.
        """
        self.client = speech.SpeechClient()
        self.audio_queue: queue.Queue[Optional[bytes]] = queue.Queue()
        self.closed = False
        self.preload_chunks = preload_chunks or []
        self.on_transcript = on_transcript

        self.recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=constants.STT_SAMPLE_RATE,
            language_code=constants.STT_LANGUAGE,
            enable_automatic_punctuation=constants.STT_ENABLE_PUNCTUATION,
            model=constants.STT_MODEL,
        )

        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.recognition_config,
            interim_results=True,
            single_utterance=constants.STT_SINGLE_UTTERANCE,
        )

        logger.info(
            "GoogleStreamingSttSession initialized: language=%s, model=%s, "
            "sample_rate=%dHz, preload_chunks=%d",
            constants.STT_LANGUAGE,
            constants.STT_MODEL,
            constants.STT_SAMPLE_RATE,
            len(self.preload_chunks),
        )

    def _audio_generator(self):
        if self.preload_chunks:
            logger.debug("Sending %d preload chunks", len(self.preload_chunks))
        for chunk in self.preload_chunks:
            yield speech.StreamingRecognizeRequest(audio_content=chunk)
        if self.preload_chunks:
            logger.debug("Preload complete, switching to queue mode")

        while not self.closed:
            chunk = self.audio_queue.get()
            if chunk is None:
                logger.info("Queue sentinel received, generator exiting")
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def start(self):
        """
        Blocking call that processes streaming responses.
        Run this in a separate thread.
        """
        logger.info("GoogleStreamingSttSession.start() initiated, calling streaming_recognize (blocking)")
        try:
            responses = self.client.streaming_recognize(
                config=self.streaming_config,
                requests=self._audio_generator()
            )
            logger.info("Google STT streaming connection established, awaiting responses")

            for response in responses:
                if logger.isEnabledFor(logging.DEBUG) and response.results:
                    logger.debug("Received %d result(s) from Google STT", len(response.results))
                for result in response.results:
                    if not result.alternatives:
                        continue
                    
                    alternative = result.alternatives[0]
                    transcript = alternative.transcript
                    confidence = alternative.confidence if hasattr(alternative, 'confidence') else 1.0
                    is_final = result.is_final

                    if is_final and self.on_transcript:
                        current_time = epoch_to_iso_utc(time.time())
                        event = TranscriptionEvent(
                            text=transcript,
                            confidence=confidence,
                            start_time=current_time,
                            end_time=current_time,
                        )
                        self.on_transcript(event)
                        logger.info(
                            "FINAL transcript: text='%s', confidence=%.2f, length=%d chars",
                            transcript,
                            confidence,
                            len(transcript),
                        )
                    elif logger.isEnabledFor(logging.DEBUG):
                        truncated = transcript[:50] + "..." if len(transcript) > 50 else transcript
                        logger.debug("PARTIAL transcript: text='%s'", truncated)
        except Exception as e:
            logger.error(
                "Google STT streaming error: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
                extra={"preload_count": len(self.preload_chunks), "closed": self.closed},
            )

    def push_audio(self, pcm_chunk: bytes):
        if not self.closed:
            self.audio_queue.put(pcm_chunk)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Audio pushed: size=%d bytes, queue_depth=%d",
                    len(pcm_chunk),
                    self.audio_queue.qsize(),
                )

    def close(self):
        logger.info("GoogleStreamingSttSession.close() called, queue sentinel sent")
        self.closed = True
        self.audio_queue.put(None)
