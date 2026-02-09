# Use Python 3.11 slim base image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for aiortc (WebRTC) and OpenCV
# - libavformat-dev, libavcodec-dev, libavdevice-dev: FFmpeg libraries for video/audio codecs
# - libopus-dev: Opus audio codec
# - libvpx-dev: VP8/VP9 video codec
# - libsrtp2-dev: Secure Real-time Transport Protocol
# - build-essential: C/C++ compilers needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy model files (YOLO weights)
# These are already in the repo root, so they're copied with COPY . .
# Explicitly ensure they're present (this is a no-op but documents the requirement)
RUN test -f yolov8n.pt || echo "Warning: yolov8n.pt not found"

# Cloud Run expects the application to listen on the PORT environment variable
# Our application code uses config.constants.SERVER_PORT which reads from PORT env var
EXPOSE 8080

# Health check (optional, Cloud Run uses HTTP probes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run the application
# Cloud Run will inject PORT environment variable
CMD ["python", "main.py"]
