import pytest

from stream.frame_buffer import VideoBuffer


@pytest.mark.asyncio
async def test_frame_buffer_drop_replace():
    buf = VideoBuffer()
    await buf.put(b"first")
    # put second, should replace first
    await buf.put(b"second")
    data = await buf.get()
    assert data == b"second"
