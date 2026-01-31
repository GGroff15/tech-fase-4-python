import asyncio

import pytest

from stream.audio_processor import AudioEmotionProcessor
from stream.frame_buffer import AudioBuffer
from stream.session import StreamSession


@pytest.mark.asyncio
async def test_audio_processor_emits_emotion(monkeypatch):
    buf = AudioBuffer(maxsize=10)
    session = StreamSession(session_id="test-session")
    events = []

    async def emitter(ev):
        events.append(ev)

    # Create fake PCM that represents exactly 1.0 second of audio when sample_width=2
    sample_rate = 16000
    channels = 1
    pcm = b"\x00\x00" * sample_rate  # 2 bytes per sample * sample_rate -> 1 second
    wav_data = b"RIFFxxxxWAVEfmt " + b"data" + len(pcm).to_bytes(4, "little") + pcm

    def fake_decode(frame):
        # Return a fake temp path and 1.0s duration to match audioframe_to_wav_file signature
        return "fake.wav", 1.0

    def fake_predict_emotion(path):
        return {"label": "neutral", "score": 0.5}

    # Patch the module-level imports used by the processor
    monkeypatch.setattr("stream.audio_processor.audioframe_to_wav_file", fake_decode)
    monkeypatch.setattr("audio.ser.predict_emotion", fake_predict_emotion)

    # Put a single frame (the fake decoder will provide 1s of PCM)
    await buf.put("frame-1")

    proc = AudioEmotionProcessor(buf, session, window_seconds=1.0)
    proc.start(emitter)

    # Give the processor a short moment to process
    await asyncio.sleep(0.2)

    await proc.stop()

    assert len(events) >= 1
    ev = events[0]
    assert ev["event_type"] == "emotion_event"
    assert ev["audio_seconds"] == pytest.approx(1.0)
    # Ensure emotion payload is present and standardized
    assert "emotion" in ev
    assert isinstance(ev["emotion"], dict)
    assert ev["emotion"]["emotion"] == "neutral"
    assert ev["emotion"]["confidence"] == pytest.approx(0.5)
    assert isinstance(ev["emotion"]["timestamp"], str)
