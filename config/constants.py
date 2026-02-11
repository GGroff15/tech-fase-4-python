"""Application-wide constants and configuration values.

This module centralizes all magic numbers and configuration constants
to improve maintainability and follow clean code principles.
"""
import os

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================
DEFAULT_SERVER_HOST = "0.0.0.0"
# Cloud Run injects PORT env var; use it if available, otherwise default to 8000
SERVER_PORT = int(os.getenv("PORT", "8000"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================================
# IMAGE PROCESSING
# ============================================================================
MAX_IMAGE_WIDTH = int(os.getenv("MAX_IMAGE_WIDTH", "1280"))
MAX_IMAGE_HEIGHT = int(os.getenv("MAX_IMAGE_HEIGHT", "720"))
MIN_IMAGE_DIMENSION = 1
DEFAULT_BLUR_THRESHOLD = float(os.getenv("BLUR_THRESHOLD", "100.0"))
IMAGE_ENCODING_FORMAT = ".jpg"

# ============================================================================
# YOLO MODEL CONFIGURATION
# ============================================================================
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.5"))

# ============================================================================
# VIDEO PROCESSING
# ============================================================================
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "3"))  # Frame sampling rate

# Frame Buffer
FRAME_BUFFER_MAX_SIZE = 1

# ============================================================================
# AUDIO PROCESSING
# ============================================================================
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_FRAME_MS = int(os.getenv("AUDIO_FRAME_MS", "20"))
AUDIO_WINDOW_SEC = float(os.getenv("AUDIO_WINDOW_SEC", "1.0"))
AUDIO_OVERLAP_MS = int(os.getenv("AUDIO_OVERLAP_MS", "1000"))

# Voice Activity Detection
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", "1"))  # 0-3, higher = more aggressive

# ============================================================================
# GOOGLE SPEECH-TO-TEXT
# ============================================================================
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "pt-BR")
STT_SAMPLE_RATE = int(os.getenv("STT_SAMPLE_RATE", "16000"))
STT_MODEL = os.getenv("STT_MODEL", "latest_long")
STT_ENABLE_PUNCTUATION = os.getenv("STT_ENABLE_PUNCTUATION", "true").lower() == "true"
STT_SINGLE_UTTERANCE = os.getenv("STT_SINGLE_UTTERANCE", "false").lower() == "true"
STT_MAX_DURATION_SEC = int(os.getenv("STT_MAX_DURATION_SEC", "240"))  # Google STT stream rotation

# ============================================================================
# EMOTION DETECTION MODEL
# ============================================================================
EMOTION_MODEL_ID = os.getenv("EMOTION_MODEL_ID", "prithivMLmods/Speech-Emotion-Classification")
HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY", "")  # Optional: HuggingFace Hub authentication token for private models and rate limits

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================
DEFAULT_IDLE_TIMEOUT_SEC = int(os.getenv("IDLE_TIMEOUT_SEC", "30"))
DEFAULT_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

# ============================================================================
# WEBRTC CONFIGURATION
# ============================================================================
DATA_CHANNEL_INIT_DELAY_SEC = 0.1
DETECTIONS_CHANNEL_LABEL = "detections"

# ============================================================================
# ROBOFLOW API
# ============================================================================
ROBOFLOW_API_URL = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "human-face-emotions/28")
DEFAULT_ROBOFLOW_CONFIDENCE = float(os.getenv("ROBOFLOW_CONFIDENCE", "0.5"))
ROBOFLOW_HTTP_TIMEOUT_SEC = float(os.getenv("ROBOFLOW_HTTP_TIMEOUT_SEC", "10.0"))

# ============================================================================
# IMAGE QUALITY
# ============================================================================
QUALITY_WARNING_BLUR_FORMAT = "blurry:score={:.1f}"

# ============================================================================
# HTTP/EVENT FORWARDING
# ============================================================================
# Default base for event HTTP forwarding. Typically the OpenAPI server
# serving `/v3/api-docs` runs on port 8080 in this project; override via env.
EVENT_FORWARD_BASE_URL = os.getenv("EVENT_FORWARD_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "")
HTTP_REQUEST_TIMEOUT_SEC = float(os.getenv("HTTP_REQUEST_TIMEOUT_SEC", "10.0"))
DEFAULT_SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))