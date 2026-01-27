import logging
import tempfile
import wave
from typing import Tuple

import numpy as np
from av import AudioFrame
from scipy.io import wavfile
from scipy.signal import resample

logger = logging.getLogger("yolo_rest.audio_decoder")

def audioframe_to_pcm_bytes(frames: list[AudioFrame]) -> Tuple[bytes, float]:
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
        with wave.open(tmp_original_wav, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(b"".join(frame_bytes))
        
    sample_rate_original, data = wavfile.read(tmp_original_wav.name)
    
    if data.ndim > 1:
        data = data[:, 0]
        
    num_samples_16k = int(len(data) * 16000 / sample_rate_original)
    
    data_16k = resample(data, num_samples_16k)
    
    with tempfile.NamedTemporaryFile(prefix="resampled_", suffix=".wav", delete=False) as temporary_resampled_wav:
        wavfile.write(temporary_resampled_wav.name, 16000, data_16k.astype(np.int16))
    
    with open(temporary_resampled_wav.name, "rb") as f:
            data = f.read()
    
    return data, duration_seconds

def audioframe_to_wav_file(frames: list[AudioFrame]) -> Tuple[str, float]:
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
        with wave.open(tmp_original_wav, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(b"".join(frame_bytes))
        
    sample_rate_original, data = wavfile.read(tmp_original_wav.name)
    
    if data.ndim > 1:
        data = data[:, 0]
        
    num_samples_16k = int(len(data) * 16000 / sample_rate_original)
    
    data_16k = resample(data, num_samples_16k)
    
    with tempfile.NamedTemporaryFile(prefix="resampled_", suffix=".wav", delete=False) as temporary_resampled_wav:
        wavfile.write(temporary_resampled_wav.name, 16000, data_16k.astype(np.int16))
        
    return temporary_resampled_wav.name, duration_seconds