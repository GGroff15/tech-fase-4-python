import asyncio
import logging
import os
import tempfile
import time
from typing import Any, Callable

import audio.ser as ser
from audio.audio_analysis import analyze_audio
from preprocessing.audio_decoder import audioframe_to_wav_bytes
from stream.frame_buffer import BaseBuffer
from stream.frame_processor import BaseProcessor
from stream.session import StreamSession

logger = logging.getLogger("yolo_rest.audio_processor")


class AudioProcessor(BaseProcessor):
    """Consume AudioFrames from a FrameBuffer, aggregate into time windows,
    run analysis and emit audio events via the emitter callable.
    """

    def __init__(
        self,
        frame_buffer: BaseBuffer,
        session: StreamSession,
        window_seconds: float = 1.0,
    ):
        super().__init__(frame_buffer, session)
        self.window_seconds = float(window_seconds)

    async def _run(self, emitter: Callable[[dict[str, Any]], Any]) -> None:
        """Main loop: collect frames for ~window_seconds and analyze each window."""
        # If the buffer supports `get_many`, use it to collect frames for up to
        # `window_seconds`. Otherwise process each frame as it arrives.
        while not self._stop:
            try:
                if hasattr(self.frame_buffer, "get_many"):
                    # collect for up to window_seconds (timeout)
                    try:
                        frames = await self.frame_buffer.get_many(
                            timeout=self.window_seconds
                        )
                    except TypeError:
                        # older signature may not support timeout kwarg
                        frames = await self.frame_buffer.get_many()

                    if frames:
                        await self._process_window(frames, emitter)
                    # otherwise loop again
                else:
                    frame = await self.frame_buffer.get()
                    # process single frame immediately when get_many isn't available
                    await self._process_window([frame], emitter)
            except Exception as error:
                logger.info(f"audio buffer get error: {error}")
                break

    async def _process_window(
        self, frames, emitter: Callable[[dict[str, Any]], Any]
    ) -> None:
        """Process a window of frames: decode, write WAV, run analysis off-loop, emit event."""
        try:
            # Run the blocking work in a thread to avoid blocking the event loop
            try:
                if len(frames) <= 1:
                    # small windows: run directly to avoid thread scheduling latency in tests
                    result, audio_seconds, frames_written = self._process_window_sync(
                        frames
                    )
                else:
                    result, audio_seconds, frames_written = await asyncio.to_thread(
                        self._process_window_sync, frames
                    )
            except Exception as e:
                logger.error(f"audio sync processing failed: {e}")
                return

            # Record audio metrics with computed seconds
            try:
                self.session.record_audio(frames=len(frames), seconds=audio_seconds)
            except Exception:
                logger.debug("session.record_audio failed, continuing")

            # Build and emit event
            event = {
                "event_type": "audio_event",
                "session_id": self.session.session_id,
                "timestamp_ms": int(time.time() * 1000),
                "analysis": result,
                "audio_seconds": float(audio_seconds),
                "frames": len(frames),
                "window_seconds": float(self.window_seconds),
            }

            try:
                await emitter(event)
            except Exception as e:
                logger.error(f"emit audio event failed: {e}")

        except Exception as error:
            logger.error(f"audio processing error: {error}")

    def _process_window_sync(self, frames):
        """Synchronous helper: decode frames, write tmp WAV, call analyze_audio.

        Returns (analysis_result, audio_seconds, frames_written).
        The temp file is removed before returning.
        """
        tmp_path = None
        try:
            wav_chunks = []
            sample_rate = 48000
            channels = 1
            total_bytes = 0
            for f in frames:
                try:
                    wav_data, sr, ch = audioframe_to_wav_bytes(f)
                except Exception as e:
                    logger.warning(f"skip frame decode: {e}")
                    continue
                idx = wav_data.find(b"data")
                if idx != -1:
                    raw = wav_data[idx + 8 :]
                else:
                    raw = wav_data
                wav_chunks.append(raw)
                total_bytes += len(raw)
                sample_rate = sr
                channels = ch

            if not wav_chunks:
                return {}, 0.0, 0

            # Write combined WAV file and call analyzer
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp_path = tmp.name
            # Use shared helper to write PCM chunks to WAV file
            from utils.audio import write_wav_file

            write_wav_file(tmp_path, wav_chunks, sample_rate, channels, sampwidth=2)

            # compute seconds: total PCM bytes / (sr * channels * bytes_per_sample)
            bytes_per_sample = 2
            audio_seconds = total_bytes / (sample_rate * channels * bytes_per_sample)

            result = analyze_audio(tmp_path)

            # Run speech-emotion recognition (SER) if available. This uses a
            # lazy-loaded HF pipeline in audio.ser and is safe to call here
            # because _process_window_sync runs in a thread via asyncio.to_thread.
            try:
                emotion = ser.predict_emotion(tmp_path)
            except Exception as e:
                logger.debug(f"predict_emotion failed: {e}")
                emotion = None

            if emotion:
                # merge into existing analysis dict to preserve contract
                try:
                    result["emotion"] = emotion
                except Exception:
                    # if result isn't a dict, wrap it
                    result = {"result": result, "emotion": emotion}
            else:
                # include a stable key even if model isn't available
                try:
                    result.setdefault("emotion", {"label": None, "score": 0.0})
                except Exception:
                    result = {
                        "result": result,
                        "emotion": {"label": None, "score": 0.0},
                    }

            return result, audio_seconds, len(wav_chunks)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # lifecycle methods start/stop inherited from BaseProcessor
