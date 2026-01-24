import pytest

from stream.frame_buffer import AudioBuffer


@pytest.mark.asyncio
async def test_audio_buffer_get_many():
    buf = AudioBuffer(maxsize=10)
    # put 5 items
    for i in range(5):
        await buf.put(f"item-{i}")

    items = await buf.get_many(max_items=3, timeout=0.1)
    assert len(items) == 3
    assert items[0] == "item-0"

    # drain remaining
    rest = []
    while not buf.empty():
        rest.append(await buf.get())
    assert len(rest) == 2
