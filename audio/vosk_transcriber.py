import json
import time
from vosk import Model, KaldiRecognizer

from events.audio_events import TranscriptionEvent
from utils.time_converter import epoch_to_iso_utc


class VoskTranscriber:
    def __init__(self, model_path: str):
        self._model = Model(model_path)
        self._recognizer = KaldiRecognizer(self._model, 16_000)
        self._recognizer.SetWords(True)
        self._stream_start_monotonic: float | None = None
        self._epoch_offset = time.time() - time.monotonic()

    def accept(self, pcm16: bytes) -> TranscriptionEvent | None:
        if self._stream_start_monotonic is None:
            self._stream_start_monotonic = time.monotonic()

        if not self._recognizer.AcceptWaveform(bytes(pcm16)):
            return None

        result = json.loads(self._recognizer.Result())
        words = result.get("result", [])
        text = result.get("text", "").strip()

        if not text or not words:
            return None

        start_offset = words[0]["start"]
        end_offset = words[-1]["end"]

        start_iso = self._offset_to_iso(start_offset)
        end_iso = self._offset_to_iso(end_offset)

        confidence = self._aggregate_confidence(words)

        return TranscriptionEvent(
            text=text,
            confidence=confidence,
            start=start_iso,
            end=end_iso,
        )

    def _offset_to_iso(self, offset_sec: float) -> str:
        absolute_epoch = (
            self._stream_start_monotonic + offset_sec + self._epoch_offset
        )
        return epoch_to_iso_utc(absolute_epoch)

    @staticmethod
    def _aggregate_confidence(words: list[dict]) -> float:
        confidences = [w["conf"] for w in words if "conf" in w]
        return round(sum(confidences) / len(confidences), 3) if confidences else 0.0
