import asyncio
import pytest

from stream.frame_buffer import AudioBuffer
from stream.session import StreamSession
from stream.audio_processor import AudioProcessor


@pytest.mark.asyncio
async def test_audio_processor_single_window(monkeypatch):
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
        return wav_data, sample_rate, channels

    def fake_analyze(path):
        return {"ok": True, "path": path}

    # Patch the module-level imports used by the processor
    monkeypatch.setattr("stream.audio_processor.audioframe_to_wav_bytes", fake_decode)
    monkeypatch.setattr("stream.audio_processor.analyze_audio", fake_analyze)

    # Put a single frame (the fake decoder will provide 1s of PCM)
    await buf.put("frame-1")

    proc = AudioProcessor(buf, session, window_seconds=1.0)
    proc.start(emitter)

    # Give the processor a short moment to process
    await asyncio.sleep(0.2)

    await proc.stop()

    assert len(events) >= 1
    ev = events[0]
    assert ev["event_type"] == "audio_event"
    assert ev["audio_seconds"] == pytest.approx(1.0)
    assert session.audio_seconds == pytest.approx(1.0)
