import tempfile
import wave
import logging
from typing import Tuple

logger = logging.getLogger("yolo_rest.audio_decoder")


def audioframe_to_wav_bytes(frame) -> Tuple[bytes, int, int]:
    """Convert a raw audio frame (aiortc/av.AudioFrame-like) to WAV bytes.

    Returns a tuple of (wav_bytes, sample_rate, channels).
    This is best-effort: it attempts to read common attributes from the frame.
    """
    # Attempt to extract common attributes
    sample_rate = getattr(frame, "sample_rate", getattr(frame, "rate", 48000))
    channels = getattr(frame, "channels", getattr(frame, "layout", None))
    if isinstance(channels, int):
        ch = channels
    else:
        # layout like "stereo" or an object — fall back to 1
        ch = 1

    # Try to get raw bytes
    raw = None
    try:
        # aiortc/av.AudioFrame: .planes is a list of memoryviews
        planes = getattr(frame, "planes", None)
        if planes and len(planes) > 0:
            raw = planes[0].to_bytes()
    except Exception:
        raw = None

    if raw is None:
        # aiortc AudioFrame may expose to_ndarray
        try:
            arr = frame.to_ndarray()
            # ndarray -> bytes (int16)
            raw = arr.tobytes()
            # shape -> channels inference
            if hasattr(arr, "shape") and len(arr.shape) > 1:
                ch = arr.shape[0]
        except Exception:
            logger.warning("Unable to decode audio frame to bytes")
            raise

    # Build WAV bytes in-memory
    with tempfile.TemporaryFile() as tmp:
        wf = wave.open(tmp, "wb")
        wf.setnchannels(ch)
        wf.setsampwidth(2)  # assume 16-bit PCM
        wf.setframerate(int(sample_rate))
        wf.writeframes(raw)
        wf.close()
        tmp.seek(0)
        data = tmp.read()

    return data, int(sample_rate), int(ch)
