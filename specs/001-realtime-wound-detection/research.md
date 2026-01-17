# Research: Realtime Video Stream Wound Detection API

**Phase**: 0 (Outline & Research)  
**Date**: 2026-01-16

## Research Questions & Findings

### 1. WebSocket Implementation in FastAPI

**Question**: What is the best approach for implementing WebSocket streaming in FastAPI for bidirectional video/detection communication?

**Decision**: Use FastAPI's native WebSocket support with async/await patterns.

**Rationale**:
- FastAPI has built-in WebSocket support via Starlette
- Async/await enables non-blocking frame processing
- Native integration with existing FastAPI app structure
- Well-documented and widely used in production

**Implementation Pattern**:
```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/analyze-stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive frame
            data = await websocket.receive_bytes()
            # Process frame asynchronously
            result = await process_frame(data)
            # Send detection result
            await websocket.send_json(result)
    except WebSocketDisconnect:
        # Cleanup
        pass
```

**Alternatives Considered**:
- Socket.io: More features but adds complexity and dependencies
- Raw websockets library: Lower level, more control but loses FastAPI integration

---

### 2. Roboflow Integration for Wound Detection

**Question**: How to integrate Roboflow-hosted custom wound detection models for real-time inference?

**Decision**: Use Roboflow Python SDK with async HTTP client for model inference.

**Rationale**:
- Roboflow hosts trained models, eliminating need for local GPU
- REST API provides simple integration
- Supports custom YOLOv8 models trained on wound datasets
- Pay-per-prediction pricing scales with usage

**Implementation Pattern**:
```python
from roboflow import Roboflow
import httpx

class RoboflowClient:
    def __init__(self, api_key: str, workspace: str, project: str, version: int):
        rf = Roboflow(api_key=api_key)
        self.model = rf.workspace(workspace).project(project).version(version).model
        self.async_client = httpx.AsyncClient()
    
    async def predict_async(self, image_bytes: bytes) -> dict:
        # Use Roboflow's infer endpoint
        response = await self.async_client.post(
            self.model.api_url,
            files={"file": image_bytes},
            data={"confidence": 50}  # 0.5 threshold
        )
        return response.json()
```

**Configuration Requirements**:
- `ROBOFLOW_API_KEY`: Authentication token
- `ROBOFLOW_WORKSPACE`: Workspace name
- `ROBOFLOW_PROJECT`: Project name (wound detection model)
- `ROBOFLOW_VERSION`: Model version number

**Alternatives Considered**:
- Local YOLOv8 with Ultralytics: Requires GPU, more setup but no API costs
- TensorFlow Serving: More complex deployment, better for high-throughput scenarios

---

### 3. Frame Dropping Strategy Under Load

**Question**: How to implement frame dropping when processing lags behind incoming frame rate?

**Decision**: Use asyncio.Queue with maxsize=1 and get_nowait() to always process most recent frame.

**Rationale**:
- Queue size of 1 ensures only latest frame is queued
- Older frames automatically dropped when new frame arrives
- Simple to implement and reason about
- Aligns with constitution principle I (Real-Time First)

**Implementation Pattern**:
```python
import asyncio

class FrameBuffer:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1)
        self.dropped_count = 0
    
    async def add_frame(self, frame_data: bytes):
        try:
            self.queue.put_nowait(frame_data)
        except asyncio.QueueFull:
            # Drop oldest, replace with newest
            try:
                self.queue.get_nowait()
                self.dropped_count += 1
            except asyncio.QueueEmpty:
                pass
            await self.queue.put(frame_data)
    
    async def get_frame(self) -> bytes:
        return await self.queue.get()
```

**Alternatives Considered**:
- Adaptive sampling: More complex, requires frame rate calculation
- Priority queue: Unnecessary complexity for this use case
- Buffering multiple frames: Violates real-time requirement

---

### 4. Frame Validation and Preprocessing

**Question**: How to validate incoming frames (format, resolution) and enforce 720p limit efficiently?

**Decision**: Use OpenCV (cv2.imdecode) for decoding with resolution validation and downscaling if needed.

**Rationale**:
- OpenCV already in dependencies for existing video analysis
- Fast JPEG/PNG decoding
- Built-in image resizing with quality preservation
- Widely used and battle-tested

**Implementation Pattern**:
```python
import cv2
import numpy as np

def validate_and_preprocess(frame_bytes: bytes, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
    # Decode image
    nparr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Invalid image format")
    
    h, w = img.shape[:2]
    
    # Check if downscaling needed
    if w > max_width or h > max_height:
        scale = min(max_width / w, max_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return img
```

**Performance**: cv2.imdecode is fast (<5ms for typical images), meeting latency budget.

**Alternatives Considered**:
- PIL/Pillow: Slower for JPEG decoding
- Direct JPEG header parsing: Complex, only provides metadata not decoded image

---

### 5. Concurrent Stream Limiting

**Question**: How to enforce 5-10 concurrent stream limit to prevent resource exhaustion?

**Decision**: Use asyncio.Semaphore with configurable limit in WebSocket connection handler.

**Rationale**:
- Built-in Python concurrency primitive
- Automatic blocking and queuing of excess connections
- Clean error handling for rejected connections
- Easy to configure via environment variable

**Implementation Pattern**:
```python
import asyncio
from fastapi import WebSocket, status

MAX_CONCURRENT_STREAMS = 10
stream_semaphore = asyncio.Semaphore(MAX_CONCURRENT_STREAMS)

@app.websocket("/ws/analyze-stream")
async def websocket_endpoint(websocket: WebSocket):
    if stream_semaphore.locked() and stream_semaphore._value == 0:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Max concurrent streams reached")
        return
    
    async with stream_semaphore:
        await websocket.accept()
        # Handle stream...
```

**Configuration**: `MAX_CONCURRENT_STREAMS` environment variable (default: 10)

**Alternatives Considered**:
- Manual counter with locks: More error-prone
- Redis-based distributed limiting: Overkill for single-instance deployment

---

### 6. Detection Result Confidence Thresholding

**Question**: How to apply dual confidence thresholds (detection ≥0.5, type classification) in Roboflow responses?

**Decision**: Filter Roboflow predictions at 0.5 detection confidence, include type confidence in response.

**Rationale**:
- Roboflow API supports confidence parameter in request
- Server-side filtering ensures consistency
- Type classification confidence typically provided separately in YOLO outputs

**Implementation Pattern**:
```python
async def process_roboflow_response(predictions: dict) -> list[dict]:
    detections = []
    for pred in predictions.get("predictions", []):
        detection_conf = pred.get("confidence", 0.0)
        if detection_conf >= 0.5:
            detections.append({
                "bbox": [pred["x"], pred["y"], pred["width"], pred["height"]],
                "wound_type": pred["class"],
                "detection_confidence": detection_conf,
                "type_confidence": pred.get("class_confidence", detection_conf)  # Use detection conf as fallback
            })
    return detections
```

**Roboflow Request**: Set `confidence=50` (percentage) in API call.

---

### 7. Session Management and Logging

**Question**: How to track stream sessions for audit logging and debugging?

**Decision**: Generate UUID for each WebSocket connection, use structured logging with session context.

**Rationale**:
- UUIDs are unique and traceable
- Structured logging (JSON) enables log aggregation and analysis
- Session ID in every log message provides request tracing

**Implementation Pattern**:
```python
import uuid
import logging
import json

logger = logging.getLogger(__name__)

class StreamSession:
    def __init__(self, websocket: WebSocket):
        self.session_id = str(uuid.uuid4())
        self.websocket = websocket
        self.start_time = time.time()
        self.frame_count = 0
        self.detection_count = 0
    
    def log(self, level: str, message: str, **kwargs):
        log_data = {
            "session_id": self.session_id,
            "timestamp": time.time(),
            "message": message,
            **kwargs
        }
        logger.log(getattr(logging, level.upper()), json.dumps(log_data))
```

**Log Fields**: session_id, timestamp, event_type, frame_index, processing_time_ms, detections_count

---

## Technology Summary

| Technology | Purpose | Version/Package |
|------------|---------|-----------------|
| FastAPI | Web framework, WebSocket support | fastapi>=0.104.0 |
| Roboflow | Hosted wound detection inference | roboflow>=1.1.0 |
| OpenCV | Frame decoding, validation, preprocessing | opencv-python>=4.8.0 |
| websockets | WebSocket protocol (FastAPI dependency) | websockets>=12.0 |
| httpx | Async HTTP client for Roboflow API | httpx>=0.25.0 |
| pytest-asyncio | Async test support | pytest-asyncio>=0.21.0 |
| uvicorn | ASGI server | uvicorn>=0.24.0 |
| python-dotenv | Environment variable management | python-dotenv>=1.0.0 |

## Best Practices Applied

1. **Async/Await Throughout**: All I/O operations (WebSocket, HTTP, file) use async patterns
2. **Graceful Degradation**: Frame dropping preferred over queuing/blocking
3. **Resource Limits**: Semaphore for concurrent streams, memory bounds on frame buffers
4. **Observability**: Structured logging with session IDs, performance metrics
5. **Input Validation**: Frame format/resolution validation before processing
6. **Error Handling**: Try/except blocks with specific error types, WebSocket close codes
7. **Configuration**: Environment variables for all tunable parameters
8. **Testing**: Pytest with async fixtures, mock Roboflow API responses
