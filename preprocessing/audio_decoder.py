import logging
import os
import tempfile
from turtle import st
import wave
from typing import Tuple

import numpy as np
from av import AudioFrame
from scipy.io import wavfile
from scipy.signal import resample

logger = logging.getLogger("yolo_rest.audio_decoder")

# Target sample rate for Vosk STT
TARGET_SAMPLE_RATE = 16000


def audioframe_to_pcm_bytes(frames: list[AudioFrame]) -> Tuple[bytes, float]:
    """Convert AudioFrames to WAV bytes (16kHz mono PCM)."""
    frame_bytes = []
    sample_rate = 0
    sample_width = 0
    duration_seconds = 0.0

    for frame in frames:
        frame_bytes.append(frame.to_ndarray().tobytes())
        sample_rate = frame.sample_rate
        sample_width = frame.format.bytes
        duration_seconds += frame.samples / frame.sample_rate

    with tempfile.NamedTemporaryFile(prefix="original_", suffix=".wav", delete=False) as tmp_original_wav:
        with wave.open(tmp_original_wav, "wb") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frame_bytes))

    sample_rate_original, data = wavfile.read(tmp_original_wav.name)

    # Cleanup original temp file
    try:
        os.unlink(tmp_original_wav.name)
    except OSError:
        pass

    if data.ndim > 1:
        data = data[:, 0]

    num_samples_16k = int(len(data) * TARGET_SAMPLE_RATE / sample_rate_original)
    data_16k = resample(data, num_samples_16k)

    with tempfile.NamedTemporaryFile(prefix="resampled_", suffix=".wav", delete=False) as tmp_resampled_wav:
        wavfile.write(tmp_resampled_wav.name, TARGET_SAMPLE_RATE, data_16k.astype(np.int16))

    with open(tmp_resampled_wav.name, "rb") as f:
        wav_data = f.read()

    # Cleanup resampled temp file
    try:
        os.unlink(tmp_resampled_wav.name)
    except OSError:
        pass

    return wav_data, duration_seconds


def audioframe_to_wav_file(frames: list[AudioFrame]) -> str:
    """Convert AudioFrames to a temporary WAV file (16kHz mono PCM).
    
    Returns:
        Path to the temporary WAV file.
        Note: Caller should clean up the temp file when done.
    """
    frame_bytes = []
    sample_rate = 0
    sample_width = 0
    duration_seconds = 0.0

    for frame in frames:
        frame_bytes.append(frame.to_ndarray().tobytes())
        sample_rate = frame.sample_rate
        sample_width = frame.format.bytes
        duration_seconds += frame.samples / frame.sample_rate

    with tempfile.NamedTemporaryFile(prefix="original_", suffix=".wav", delete=False) as tmp_original_wav:
        with wave.open(tmp_original_wav, "wb") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frame_bytes))

    sample_rate_original, data = wavfile.read(tmp_original_wav.name)

    # Cleanup original temp file
    try:
        os.unlink(tmp_original_wav.name)
    except OSError:
        pass

    if data.ndim > 1:
        data = data[:, 0]

    num_samples_16k = int(len(data) * TARGET_SAMPLE_RATE / sample_rate_original)
    data_16k = resample(data, num_samples_16k)

    with tempfile.NamedTemporaryFile(prefix="resampled_", suffix=".wav", delete=False) as tmp_resampled_wav:
        wavfile.write(tmp_resampled_wav.name, TARGET_SAMPLE_RATE, data_16k.astype(np.int16))

    return tmp_resampled_wav.name


def cleanup_temp_file(file_path: str) -> None:
    """Safely delete a temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except OSError as e:
        logger.debug("Failed to cleanup temp file %s: %s", file_path, e)