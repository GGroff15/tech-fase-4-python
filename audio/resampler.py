from av.audio.resampler import AudioResampler
from av import AudioFrame


class AudioResampler16kMono:
    def __init__(self):
        self._resampler = AudioResampler(
            format="s16",
            layout="mono",
            rate=16_000,
        )

    def resample(self, frame: AudioFrame) -> list[AudioFrame]:
        return self._resampler.resample(frame)