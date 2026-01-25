"""Utilities for lazy-loading models and heavy objects.

Provides a small `LazyModelLoader` wrapper to centralize error handling,
device selection helpers and to make lazy initialization test-friendly.
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("yolo_rest.utils.loader")


class LazyModelLoader:
    """Lazy loader for expensive objects (models, pipelines).

    Example:
        loader = LazyModelLoader(lambda: SomeModel(path))
        model = loader.get()  # returns instance or None on failure
    """

    def __init__(self, factory: Callable[[], Any], name: Optional[str] = None):
        self._factory = factory
        self._name = name or getattr(factory, "__name__", "lazy_model")
        self._obj: Optional[Any] = None
        self._loaded: bool = False
        self._error: Optional[BaseException] = None

    def get(self) -> Optional[Any]:
        """Return the loaded object or None if loading failed.

        Loading is attempted once; subsequent calls return cached result.
        """
        if not self._loaded:
            try:
                self._obj = self._factory()
            except BaseException as e:
                self._error = e
                self._obj = None
                logger.debug("Lazy loader %s failed to initialize: %s", self._name, e)
            self._loaded = True
        return self._obj

    def is_available(self) -> bool:
        return self.get() is not None

    def get_error(self) -> Optional[BaseException]:
        return self._error


def get_torch_device() -> int:
    """Return device id for torch (0 for cuda, -1 for cpu) and handle ImportError.

    Use this helper when creating libraries that accept a `device` argument.
    """
    try:
        import torch

        return 0 if torch.cuda.is_available() else -1
    except Exception:
        return -1
