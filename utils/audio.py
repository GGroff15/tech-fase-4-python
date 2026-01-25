"""Audio helper utilities."""

import wave
from typing import Iterable


def write_wav_file(
    path: str,
    pcm_chunks: Iterable[bytes],
    sample_rate: int,
    channels: int,
    sampwidth: int = 2,
) -> None:
    """Write PCM chunks to a WAV file at `path`.

    `pcm_chunks` should be iterable of raw PCM byte strings (no RIFF header).
    """
    wf = wave.open(path, "wb")
    try:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        for chunk in pcm_chunks:
            wf.writeframes(chunk)
    finally:
        wf.close()
