import asyncio
from contextlib import asynccontextmanager


class RateLimiter:
    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def acquire(self):
        await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()
