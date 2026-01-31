import asyncio
import logging
import datetime
from typing import Any, Callable, Dict, Optional
from av import AudioFrame

import audio.ser as ser
import audio.stt as stt
from preprocessing.audio_decoder import audioframe_to_wav_file, cleanup_temp_file
from stream.frame_buffer import AudioEmotionBuffer, SpeechToTextBuffer
from stream.frame_processor import BaseProcessor
from stream.session import StreamSession

logger = logging.getLogger("yolo_rest.audio_processor")


class AudioProcessor(BaseProcessor):
    """Base class for audio processors consuming AudioFrames from a FrameBuffer."""

    def __init__(
        self,
        session: StreamSession,
        audio_emotion_buffer: AudioEmotionBuffer,
        speech_to_text_buffer: SpeechToTextBuffer,
    ):
        super().__init__(session)
        self.audio_emotion_buffer = audio_emotion_buffer
        self.speech_to_text_buffer = speech_to_text_buffer

    async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
        AudioSpeechToTextProcessor(self.speech_to_text_buffer, self.session).start(emitter)
        AudioEmotionProcessor(self.audio_emotion_buffer, self.session).start(emitter)


class AudioSpeechToTextProcessor(BaseProcessor):
    """Consume AudioFrames from a FrameBuffer, run speech-to-text transcription,
    and emit transcription events via the emitter callable.
    """

    def __init__(
        self, 
        buffer: SpeechToTextBuffer, 
        session: StreamSession,
        window_seconds: float = 2.5,  # 2.5s for responsive real-time STT
    ):
        super().__init__(session)
        self.buffer = buffer
        self.window_seconds = float(window_seconds)

    async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
        self.emitter = emitter
        """Main loop: collect frames for ~window_seconds and transcribe each window."""
        
        while not self._stop:
            try:
                # Retrieve up to 3s of audio, timeout matches window size
                frames: list[AudioFrame] = await self.buffer.get_many(
                    retrive_duration=3,  # Reduced from 10s for faster processing
                    timeout=self.window_seconds
                )

                if not frames:
                    continue
                
                await self._process_window(frames)
                
            except asyncio.CancelledError:
                logger.info("Speech-to-text processor cancelled")
                break
            except Exception as error:
                logger.error(f"audio buffer get error: {error}")
                continue
            
    async def _process_window(
        self, frames: list[AudioFrame]
    ) -> None:
        """Process a window of frames: decode, write WAV, run transcription off-loop, emit event.

        The audio is converted to 16 kHz mono before being written so downstream
        speech-to-text consumers can expect that sample rate and channel layout.
        """
        try:
            try:
                if len(frames) <= 1:
                    stt_result: Optional[dict] = self._process_window_sync(frames)
                else:
                    stt_result: Optional[dict] = await asyncio.to_thread(
                        self._process_window_sync, frames
                    )
            except Exception as e:
                logger.error(f"audio sync processing failed: {e}")
                return

            try:
                self.session.record_audio(frames=len(frames), seconds=0.0)
            except Exception:
                logger.debug("session.record_audio failed, continuing")

            # stt_result expected to be a dict: {text, confidence, start, end}
            text = stt_result.get("text") if stt_result else None
            confidence = float(stt_result.get("confidence", 0.0) or 0.0) if stt_result else 0.0
            start_offset = stt_result.get("start") if stt_result else None
            end_offset = stt_result.get("end") if stt_result else None

            event = {
                "event_type": "transcript",
                "text": text,
                "confidence": float(confidence),
                "startTime": start_offset,
                "endTime": end_offset,
            }

            try:
                await self.emitter(event)
            except Exception as e:
                logger.error(f"emit transcription event failed: {e}")

        except Exception as error:
            logger.error(f"audio processing error: {error}")

    def _process_window_sync(self, frames: list[AudioFrame]) -> Optional[dict]:
        """Synchronous helper for STT: decode frames, write tmp WAV (16k mono),
        and return (transcript, audio_seconds)."""
        tmp_path = None
        try:
            tmp_path = audioframe_to_wav_file(frames=frames)
            return stt.transcribe_with_metadata(tmp_path)
        finally:
            if tmp_path:
                cleanup_temp_file(tmp_path)
        

class AudioEmotionProcessor(BaseProcessor):
    """Consume AudioFrames from a FrameBuffer, aggregate into time windows,
    run analysis and emit audio events via the emitter callable.
    """

    def __init__(
        self,
        buffer: AudioEmotionBuffer,
        session: StreamSession,
        window_seconds: float = 10.0,
    ):
        super().__init__(session)
        self.buffer = buffer
        self.window_seconds = float(window_seconds)

    async def _run(self, emitter: Callable[[dict[str, Any]], Any]) -> None:
        self.emitter = emitter
        """Main loop: collect frames for ~window_seconds and analyze each window."""
        while not self._stop:
            try:
                frames = await self.buffer.get_many(
                    retrive_duration=5, 
                    timeout=self.window_seconds
                )

                if not frames:
                    continue
                
                await self._process_window(frames)
                
            except asyncio.CancelledError:
                logger.info("Audio emotion processor cancelled")
                break
            except Exception as error:
                logger.error(f"audio buffer get error: {error}")
                continue

    async def _process_window(
        self, frames: list[AudioFrame]
    ) -> None:
        """Process a window of frames: decode, write WAV, run analysis off-loop, emit event."""
        try:
            # Run the blocking work in a thread to avoid blocking the event loop
            try:
                if len(frames) <= 1:
                    # small windows: run directly to avoid thread scheduling latency in tests
                    result = self._process_window_sync(
                        frames
                    )
                else:
                    result = await asyncio.to_thread(
                        self._process_window_sync, frames
                    )
            except Exception as e:
                logger.error(f"audio sync processing failed: {e}")
                return

            try:
                self.session.record_audio(frames=len(frames), seconds=0.0)
            except Exception:
                logger.debug("session.record_audio failed, continuing")

            
            try:
                await self.emitter(result)
            except Exception as e:
                logger.error(f"emit audio event failed: {e}")

        except Exception as error:
            logger.error(f"audio processing error: {error}")

    def _process_window_sync(self, frames: list[AudioFrame]):
        """Synchronous helper: decode frames, write tmp WAV, call analyze_audio.

        Returns (analysis_result, audio_seconds).
        The temp file is removed before returning.
        """
        tmp_path = None
        try:
            tmp_path = audioframe_to_wav_file(frames=frames)

            try:
                ser_out = ser.predict_emotion(tmp_path)
            except Exception as e:
                logger.debug(f"predict_emotion failed: {e}")
                ser_out = None

            emotion_payload = {
                "event_type": "emotion",
                "emotion": ser_out.get("label") if ser_out else None,
                "confidence": float(ser_out.get("score", 0.0)) if ser_out else 0.0,
                "timestamp": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }

            return emotion_payload
        finally:
            if tmp_path:
                cleanup_temp_file(tmp_path)