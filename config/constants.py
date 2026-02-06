"""Application-wide constants and configuration values.

This module centralizes all magic numbers and configuration constants
to improve maintainability and follow clean code principles.
"""
import os

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
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "human-face-emotions/28")

# Image Quality
QUALITY_WARNING_BLUR_FORMAT = "blurry:score={:.1f}"

# HTTP Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8000

# Default base for event HTTP forwarding. Typically the OpenAPI server
# serving `/v3/api-docs` runs on port 8080 in this project; override via env.
EVENT_FORWARD_BASE_URL = os.getenv("EVENT_FORWARD_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "")
