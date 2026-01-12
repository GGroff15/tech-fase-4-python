import librosa
import numpy as np
import os

def analyze_audio(audio_path):
    if not os.path.exists(audio_path):
        return {
            "error": "Arquivo de áudio não encontrado",
            "risk_score": 0.0
        }

    y, sr = librosa.load(audio_path, sr=None)

    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfccs, axis=1)
    energy = np.mean(librosa.feature.rms(y=y))

    risk_score = float(np.mean(mfcc_mean) * energy)

    return {
        "mfcc_mean": mfcc_mean.tolist(),
        "energy": float(energy),
        "risk_score": risk_score
    }
