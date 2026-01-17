# WebSocket API Contract: Realtime Wound Detection Stream

**Endpoint**: `ws://localhost:8000/ws/analyze-stream`  
**Protocol**: WebSocket (bidirectional)  
**Version**: 1.0

## Connection Lifecycle

### 1. Connection Handshake

**Client → Server**: WebSocket connection request

```
GET /ws/analyze-stream HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

**Server → Client**: Connection accepted

```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**Possible Errors**:
- `503 Service Unavailable`: Maximum concurrent streams reached (>10 connections)
- `400 Bad Request`: Invalid WebSocket handshake

---

### 2. Session Initialization

**Server → Client**: Session started message (immediately after connection)

```json
{
  "event_type": "session_started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp_ms": 0.0,
  "config": {
    "max_resolution": "1280x720",
    "confidence_threshold": 0.5,
    "idle_timeout_sec": 30
  }
}
```

---

## Client → Server Messages

### Frame Upload (Binary Message)

**Format**: Raw binary data (JPEG or PNG encoded image)

```
WebSocket Binary Frame:
[JPEG/PNG bytes]
```

**Constraints**:
- Maximum size: 10 MB per frame
- Supported formats: JPEG (.jpg, .jpeg), PNG (.png)
- Resolution: Will be downscaled to 1280x720 if larger
- No specific frame rate required (client controls timing)

**Behavior**:
- Server processes frames asynchronously
- If processing lags, intermediate frames are dropped
- Server always processes the most recent frame

**Error Conditions**:
- Invalid image format → Error event sent, frame skipped
- Oversized frame (>10MB) → Error event sent, connection may close
- Corrupted image data → Error event sent, frame skipped

---

### Ping/Keepalive (Text Message - Optional)

**Format**: JSON text message

```json
{
  "type": "ping"
}
```

**Response**:
```json
{
  "event_type": "pong",
  "timestamp_ms": 1234.56
}
```

**Purpose**: Keep connection alive during idle periods (if no frames sent for >30 seconds, connection may timeout)

---

## Server → Client Messages

### Detection Result Event (Text Message)

**Trigger**: After each frame is processed successfully

```json
{
  "event_type": "detection_result",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "frame_index": 42,
  "timestamp_ms": 1234.56,
  "has_wounds": true,
  "wounds": [
    {
      "wound_id": 0,
      "bbox": {
        "x": 0.45,
        "y": 0.32,
        "width": 0.12,
        "height": 0.08
      },
      "wound_type": "cut",
      "detection_confidence": 0.87,
      "type_confidence": 0.82
    },
    {
      "wound_id": 1,
      "bbox": {
        "x": 0.62,
        "y": 0.55,
        "width": 0.08,
        "height": 0.06
      },
      "wound_type": "bruise",
      "detection_confidence": 0.73,
      "type_confidence": 0.68
    }
  ],
  "metadata": {
    "processing_time_ms": 245.3,
    "quality_warning": null,
    "frames_dropped_since_last": 0
  }
}
```

**Field Descriptions**:
- `event_type`: Always "detection_result" for this message type
- `session_id`: UUID of the stream session
- `frame_index`: Sequential frame number (0-based, increments even if frames dropped)
- `timestamp_ms`: Milliseconds since stream start
- `has_wounds`: Boolean indicating if any wounds detected
- `wounds`: Array of wound objects (empty array if no wounds)
  - `wound_id`: Index within this frame (0-based)
  - `bbox`: Bounding box with normalized coordinates (0.0-1.0)
    - `x`, `y`: Center point
    - `width`, `height`: Dimensions
  - `wound_type`: Classification label
  - `detection_confidence`: Confidence that this is a wound (≥0.5)
  - `type_confidence`: Confidence in the specific type classification
- `metadata`:
  - `processing_time_ms`: Latency from frame receipt to result
  - `quality_warning`: String message if frame quality is poor, null otherwise
  - `frames_dropped_since_last`: Number of frames dropped between last result and this one

---

### No Wounds Detected Event

```json
{
  "event_type": "detection_result",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "frame_index": 43,
  "timestamp_ms": 1280.12,
  "has_wounds": false,
  "wounds": [],
  "metadata": {
    "processing_time_ms": 198.7,
    "quality_warning": null,
    "frames_dropped_since_last": 1
  }
}
```

---

### Error Event (Text Message)

**Trigger**: Processing error, validation failure, or server issue

```json
{
  "event_type": "error",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "frame_index": 44,
  "timestamp_ms": 1340.23,
  "error_code": "INVALID_IMAGE_FORMAT",
  "error_message": "Frame could not be decoded as JPEG or PNG",
  "severity": "warning"
}
```

**Error Codes**:
- `INVALID_IMAGE_FORMAT`: Frame is not valid JPEG/PNG
- `FRAME_TOO_LARGE`: Frame exceeds 10MB size limit
- `INFERENCE_FAILED`: Roboflow API error or timeout
- `INTERNAL_ERROR`: Unexpected server error

**Severity Levels**:
- `warning`: Frame skipped, stream continues
- `error`: Stream terminating due to critical error

---

### Stream Summary Event (Text Message)

**Trigger**: When client closes connection gracefully

```json
{
  "event_type": "stream_closed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp_ms": 5432.10,
  "summary": {
    "total_frames_received": 156,
    "total_frames_processed": 148,
    "total_frames_dropped": 8,
    "total_detections": 23,
    "duration_sec": 5.43
  }
}
```

---

## Connection Termination

### Graceful Close

**Client → Server**: WebSocket close frame

```
Close Code: 1000 (Normal Closure)
Reason: "Stream ended"
```

**Server → Client**: Sends stream summary, then close acknowledgment

---

### Error Close

**Server → Client**: WebSocket close frame

```
Close Code: 1008 (Policy Violation) - Max streams reached
Close Code: 1002 (Protocol Error) - Invalid message format
Close Code: 1011 (Internal Error) - Server error
```

---

### Idle Timeout Close

**Server → Client**: After 30 seconds of no frames received

```
Close Code: 1000 (Normal Closure)
Reason: "Idle timeout - no frames received for 30 seconds"
```

---

## Message Flow Examples

### Successful Stream

```
Client                          Server
  |                               |
  |--- WebSocket Connect -------->|
  |<-- 101 Switching Protocols ---|
  |                               |
  |<-- session_started ----------|
  |                               |
  |--- Frame 0 (binary) --------->|
  |                               |-- Process frame
  |<-- detection_result (frame 0)|
  |                               |
  |--- Frame 1 (binary) --------->|
  |--- Frame 2 (binary) --------->|  (Frame 1 dropped due to lag)
  |                               |-- Process frame 2
  |<-- detection_result (frame 2)|
  |    (frames_dropped: 1)        |
  |                               |
  |--- Close (1000) ------------->|
  |<-- stream_closed -------------|
  |<-- Close ACK -----------------|
```

### Stream with Error

```
Client                          Server
  |                               |
  |--- Frame N (invalid) -------->|
  |                               |-- Validation fails
  |<-- error (INVALID_FORMAT) ----|
  |                               |
  |--- Frame N+1 (valid) -------->|  (Stream continues)
  |<-- detection_result ----------|
```

---

## Performance Expectations

- **Latency Target**: <500ms from frame upload to detection result
- **Throughput**: Server processes up to 30 FPS per stream
- **Concurrency**: Maximum 10 concurrent WebSocket connections
- **Frame Dropping**: Transparent to client; indicated in `frames_dropped_since_last`

---

## Testing

### Connection Test

```bash
# Using wscat
wscat -c ws://localhost:8000/ws/analyze-stream
```

### Send Frame Test

```python
import asyncio
import websockets
import json

async def test_stream():
    uri = "ws://localhost:8000/ws/analyze-stream"
    async with websockets.connect(uri) as websocket:
        # Receive session started
        message = await websocket.recv()
        print(json.loads(message))
        
        # Send frame
        with open("test_frame.jpg", "rb") as f:
            frame_bytes = f.read()
        await websocket.send(frame_bytes)
        
        # Receive detection result
        result = await websocket.recv()
        print(json.loads(result))
        
        # Close gracefully
        await websocket.close()

asyncio.run(test_stream())
```

---

## Versioning

**Current Version**: 1.0

**Backward Compatibility**: Breaking changes will increment major version. Clients should check `session_started` message for compatibility.
