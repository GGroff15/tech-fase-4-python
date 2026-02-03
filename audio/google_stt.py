import logging
import queue
import time
from typing import Callable, Optional
from google.cloud import speech_v1 as speech

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
            sample_rate_hertz=16000,
            language_code="pt-BR",
            enable_automatic_punctuation=True,
            model="latest_long",
        )

        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.recognition_config,
            interim_results=True,
            single_utterance=False,
        )

    def _audio_generator(self):
        for chunk in self.preload_chunks:
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

        while not self.closed:
            chunk = self.audio_queue.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def start(self):
        """
        Blocking call that processes streaming responses.
        Run this in a separate thread.
        """
        try:
            responses = self.client.streaming_recognize(
                config=self.streaming_config,
                requests=self._audio_generator()
            )

            for response in responses:
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
                        logger.info("FINAL: %s (confidence: %.2f)", transcript, confidence)
                    else:
                        logger.debug("PARTIAL: %s", transcript)
        except Exception as e:
            logger.error("Google STT streaming error: %s", e)

    def push_audio(self, pcm_chunk: bytes):
        if not self.closed:
            self.audio_queue.put(pcm_chunk)

    def close(self):
        self.closed = True
        self.audio_queue.put(None)
