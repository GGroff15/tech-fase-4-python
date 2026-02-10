# Use Python 3.11 slim base image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for aiortc (WebRTC) and OpenCV
# - libav* / codecs: FFmpeg libraries for video/audio
# - libopus/libvpx/libsrtp2: codecs / SRTP for WebRTC
# - build-essential: compilers for some Python wheels
# - libgl1-mesa-glx / libglib2.0-0 / libsm6 / libxrender1 / libxext6: runtime libs needed by OpenCV
ENV DEBIAN_FRONTEND=noninteractive

# Install small set first to surface any apt/CA issues early
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       apt-utils \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Then install heavier codec / OpenCV runtime packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libopus-dev \
    libvpx-dev \
    libsrtp2-dev \
    build-essential \
    libgl1 \
       libglib2.0-0 \
       libsm6 \
       libxrender1 \
       libxext6 \
       ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run expects the application to listen on the PORT environment variable
# Our application code uses config.constants.SERVER_PORT which reads from PORT env var
EXPOSE 8080

# Health check (optional, Cloud Run uses HTTP probes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run the application
# Cloud Run will inject PORT environment variable
CMD ["python", "main.py"]
