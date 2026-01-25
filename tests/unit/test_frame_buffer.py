import pytest

from stream.frame_buffer import FrameBuffer


@pytest.mark.asyncio
async def test_frame_buffer_drop_replace():
    buf = FrameBuffer()
    await buf.put(b"first")
    # put second, should replace first
    await buf.put(b"second")
    data = await buf.get()
    assert data == b"second"
