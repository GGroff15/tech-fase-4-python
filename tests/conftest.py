"""Shared pytest fixtures for tests.

Provides lightweight fixtures for JPEG bytes and a dummy image. These fixtures attempt
to use Pillow / numpy when available but degrade gracefully if those packages are
missing in the environment.
"""

import io

import pytest


@pytest.fixture
def jpeg_bytes():
    """Return JPEG-encoded bytes for a small gray image.

    Falls back to empty bytes if Pillow is not available.
    """
    try:
        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        return b""


@pytest.fixture
def dummy_image():
    """Return a simple numpy array image when numpy is available, else None."""
    try:
        import numpy as np

        return np.zeros((64, 64, 3), dtype="uint8")
    except Exception:
        return None
