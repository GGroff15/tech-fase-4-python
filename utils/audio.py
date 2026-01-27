"""Audio helper utilities."""

import wave
from typing import Iterable
from typing import Tuple


def _ensure_numpy_and_librosa():
    try:
        import numpy as _np  # type: ignore
        import librosa as _librosa  # type: ignore
        return _np, _librosa
    except Exception as e:
        raise RuntimeError(
            "resample_pcm_chunks_to_mono requires numpy and librosa installed"
        ) from e


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


def resample_pcm_chunks_to_mono(
    pcm_chunks: Iterable[bytes],
    src_rate: int,
    src_channels: int,
    sampwidth: int = 2,
) -> Tuple[Iterable[bytes], int, int]:
    """Resample and mix PCM bytes to 16 kHz mono.

    - `pcm_chunks` should be iterable of raw PCM bytes (int16 expected when
      `sampwidth==2`).
    - Returns (pcm_chunks_resampled, target_rate, target_channels).

    Fast-path: if already 16000 Hz and mono, returns the original chunks.
    This function imports numpy and librosa lazily and raises a clear error
    if they are not available.
    """
    # Fast path
    TARGET_SR = 16000
    TARGET_CH = 1
    if src_rate == TARGET_SR and src_channels == TARGET_CH:
        return pcm_chunks, src_rate, src_channels

    np, librosa = _ensure_numpy_and_librosa()

    # Concatenate into single PCM buffer
    data = b"".join(pcm_chunks)
    if not data:
        return pcm_chunks, src_rate, src_channels

    if sampwidth != 2:
        raise NotImplementedError("Only 16-bit PCM (sampwidth=2) is supported")

    arr = np.frombuffer(data, dtype=np.int16)

    # If multi-channel, reshape and mix to mono by averaging channels
    if src_channels > 1:
        try:
            arr = arr.reshape(-1, src_channels)
            # mean across channels and convert to int16
            arr_mono = arr.mean(axis=1).astype(np.int16)
        except Exception:
            # fallback: simple downsample by taking first channel
            arr_mono = arr[::src_channels]
    else:
        arr_mono = arr

    # Convert to float32 in range [-1, 1] for librosa
    y = arr_mono.astype(np.float32) / 32768.0

    if src_rate != TARGET_SR:
        y_resampled = librosa.resample(y, orig_sr=src_rate, target_sr=TARGET_SR)
    else:
        y_resampled = y

    # Convert back to int16 PCM
    y_out = (y_resampled * 32767.0).astype(np.int16)
    out_bytes = y_out.tobytes()

    # Return as a single chunk iterable
    return [out_bytes], TARGET_SR, TARGET_CH
