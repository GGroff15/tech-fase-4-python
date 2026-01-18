"""Application-wide constants and configuration values.

This module centralizes all magic numbers and configuration constants
to improve maintainability and follow clean code principles.
"""

# Image Processing
MAX_IMAGE_WIDTH = 1280
MAX_IMAGE_HEIGHT = 720
MIN_IMAGE_DIMENSION = 1
DEFAULT_BLUR_THRESHOLD = 100.0
IMAGE_ENCODING_FORMAT = ".jpg"

# Frame Buffer
FRAME_BUFFER_MAX_SIZE = 1

# Session Configuration
DEFAULT_IDLE_TIMEOUT_SEC = 30
DEFAULT_CONFIDENCE_THRESHOLD = 0.5

# WebRTC Configuration
DATA_CHANNEL_INIT_DELAY_SEC = 0.1
DETECTIONS_CHANNEL_LABEL = "detections"

# Roboflow API
DEFAULT_ROBOFLOW_CONFIDENCE = 0.5
ROBOFLOW_HTTP_TIMEOUT_SEC = 10.0
DEFAULT_USE_LOCAL_FALLBACK = True

# Image Quality
QUALITY_WARNING_BLUR_FORMAT = "blurry:score={:.1f}"

# HTTP Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8000
