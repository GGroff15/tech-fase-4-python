import asyncio

import pytest

from stream.audio_processor import AudioEmotionProcessor
from stream.frame_buffer import AudioEmotionBuffer
from stream.session import StreamSession


@pytest.mark.asyncio
async def test_audio_processor_single_window(monkeypatch):
    buf = AudioEmotionBuffer(maxsize=10)
    session = StreamSession(session_id="test-session")
    events = []

    async def emitter(ev):
        events.append(ev)

    def fake_decode(frame):
        # Return a fake temp path and 1.0s duration to match audioframe_to_wav_file signature
        return "fake.wav", 1.0

    def fake_predict_emotion(path):
        return {"label": None, "score": 0.0}

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
    assert session.audio_seconds == pytest.approx(1.0)
