import asyncio
import logging
import os
import time
from typing import Any, Callable, Dict
from av import AudioFrame

import audio.ser as ser
import audio.stt as stt
from audio.audio_analysis import analyze_audio
from preprocessing.audio_decoder import audioframe_to_pcm_bytes, audioframe_to_wav_file
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
        window_seconds: float = 5.0,
    ):
        super().__init__(session)
        self.buffer = buffer
        self.window_seconds = float(window_seconds)

    async def _run(self, emitter: Callable[[Dict[str, Any]], Any]) -> None:
        self.emitter = emitter
        """Main loop: collect frames for ~window_seconds and transcribe each window."""
        
        while not self._stop:
            try:
                frames: list[AudioFrame] = await self.buffer.get_many(
                    retrive_duration=10, 
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
                    transcript, audio_seconds = self._process_window_sync(
                        frames
                    )
                else:
                    transcript, audio_seconds = await asyncio.to_thread(
                        self._process_window_sync, frames
                    )
            except Exception as e:
                logger.error(f"audio sync processing failed: {e}")
                return

            try:
                self.session.record_audio(frames=len(frames), seconds=audio_seconds)
            except Exception:
                logger.debug("session.record_audio failed, continuing")

            # Build and emit event
            event = {
                "event_type": "transcription_event",
                "session_id": self.session.session_id,
                "timestamp_ms": int(time.time() * 1000),
                "transcript": transcript,
                "audio_seconds": float(audio_seconds),
                "frames": len(frames),
            }

            try:
                await self.emitter(event)
            except Exception as e:
                logger.error(f"emit transcription event failed: {e}")

        except Exception as error:
            logger.error(f"audio processing error: {error}")

    def _process_window_sync(self, frames: list[AudioFrame]):
        """Synchronous helper for STT: decode frames, write tmp WAV (16k mono),
        and return (transcript, audio_seconds)."""
        
        pcm_bytes, duration_seconds = audioframe_to_wav_file(frames=frames)
        
        transcription = stt.transcribe_bytes(pcm_bytes)
        
        return transcription, duration_seconds
        

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
                    result, duration_seconds = self._process_window_sync(
                        frames
                    )
                else:
                    result, duration_seconds = await asyncio.to_thread(
                        self._process_window_sync, frames
                    )
            except Exception as e:
                logger.error(f"audio sync processing failed: {e}")
                return

            try:
                self.session.record_audio(frames=len(frames), seconds=duration_seconds)
            except Exception:
                logger.debug("session.record_audio failed, continuing")

            event = {
                "event_type": "audio_event",
                "session_id": self.session.session_id,
                "timestamp_ms": int(time.time() * 1000),
                "analysis": result,
                "audio_seconds": float(duration_seconds),
                "frames": len(frames),
                "window_seconds": float(self.window_seconds),
            }

            try:
                await self.emitter(event)
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
            tmp_path, duration_seconds = audioframe_to_wav_file(frames=frames)

            result = analyze_audio(tmp_path)

            try:
                emotion = ser.predict_emotion(tmp_path)
            except Exception as e:
                logger.debug(f"predict_emotion failed: {e}")
                emotion = None

            if emotion:
                try:
                    result["emotion"] = emotion
                except Exception:
                    result = {"result": result, "emotion": emotion}
            else:
                try:
                    result.setdefault("emotion", {"label": None, "score": 0.0})
                except Exception:
                    result = {
                        "result": result,
                        "emotion": {"label": None, "score": 0.0},
                    }

            return result, duration_seconds
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
