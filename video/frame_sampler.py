import time


class FrameSampler:
    def __init__(self, fps=5):
        self._interval = 1 / fps
        self._last = 0.0

    def should_process(self) -> bool:
        now = time.time()
        if now - self._last >= self._interval:
            self._last = now
            return True
        return False
