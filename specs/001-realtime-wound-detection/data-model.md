# Data Model: Realtime Video Stream Wound Detection API

**Phase**: 1 (Design & Contracts)  
**Date**: 2026-01-16

## Domain Entities

### 1. VideoStream

Represents an active WebSocket streaming connection and its lifecycle.

**Attributes**:
- `session_id` (str): UUID identifying this stream session
- `websocket` (WebSocket): FastAPI WebSocket connection object
- `start_time` (float): Unix timestamp when stream started
- `frame_count` (int): Total frames received
- `processed_frame_count` (int): Frames successfully processed
- `dropped_frame_count` (int): Frames dropped due to processing lag
- `detection_count` (int): Total wounds detected across all frames
- `status` (StreamStatus enum): CONNECTING, ACTIVE, CLOSING, CLOSED
- `client_info` (dict): Optional client metadata (user agent, IP)

**Relationships**:
- Has many Frame objects during lifecycle
- Produces many WoundDetection results

**Validation Rules**:
- `session_id` must be valid UUID v4
- `frame_count` >= `processed_frame_count`
- `start_time` must be in the past

**State Transitions**:
```
CONNECTING → ACTIVE → CLOSING → CLOSED
     ↓                    ↓
   ERROR              ERROR
```

---

### 2. Frame

Individual video frame received over WebSocket connection.

**Attributes**:
- `frame_index` (int): Sequential number within stream (0-based)
- `timestamp_ms` (float): Milliseconds since stream start
- `raw_data` (bytes): JPEG or PNG encoded image data
- `decoded_image` (Optional[np.ndarray]): OpenCV image array after decoding
- `width` (int): Image width in pixels
- `height` (int): Image height in pixels
- `format` (ImageFormat enum): JPEG, PNG
- `size_bytes` (int): Raw data size
- `processing_status` (FrameStatus enum): RECEIVED, VALIDATED, PROCESSED, FAILED

**Relationships**:
- Belongs to one VideoStream
- Produces zero or more WoundDetection results

**Validation Rules**:
- `width` <= 1280 and `height` <= 720 (after preprocessing)
- `size_bytes` <= 10MB (protection against abuse)
- `format` must be JPEG or PNG
- `decoded_image` must be 3-channel BGR (OpenCV format)

**Lifecycle**:
1. Received from WebSocket (RECEIVED)
2. Decoded and validated (VALIDATED)
3. Sent to inference (PROCESSED)
4. Result returned or error (FAILED if exception)

---

### 3. WoundDetection

Result of analyzing a single frame for wounds.

**Attributes**:
- `frame_index` (int): Reference to source frame
- `timestamp_ms` (float): When detection was completed
- `processing_time_ms` (float): Inference latency
- `has_wounds` (bool): True if any wounds detected above threshold
- `wounds` (List[Wound]): Array of detected wound objects
- `frame_quality` (str): "good", "acceptable", "poor" (based on blur/resolution)
- `dropped_previous` (bool): True if frames were dropped before this one

**Relationships**:
- Belongs to one Frame
- Contains zero or more Wound objects

**Validation Rules**:
- `has_wounds` == True if `len(wounds) > 0`
- `processing_time_ms` > 0
- All wounds must have `detection_confidence` >= 0.5

**Business Logic**:
- If `frame_quality` == "poor", include warning in response
- If `dropped_previous` == True, include frame skip count in response

---

### 4. Wound

Individual wound identified within a frame.

**Attributes**:
- `wound_id` (int): Unique within frame (0-based index)
- `bbox_x` (float): Bounding box center X coordinate (normalized 0-1 or pixel coords)
- `bbox_y` (float): Bounding box center Y coordinate
- `bbox_width` (float): Bounding box width
- `bbox_height` (float): Bounding box height
- `wound_type` (str): Classification label (e.g., "cut", "bruise", "burn", "abrasion")
- `detection_confidence` (float): Confidence that this is a wound (0.0-1.0)
- `type_confidence` (float): Confidence in the specific wound type (0.0-1.0)

**Relationships**:
- Belongs to one WoundDetection

**Validation Rules**:
- `detection_confidence` >= 0.5 (minimum threshold)
- `type_confidence` >= 0.0 and <= 1.0
- Bounding box coordinates within frame bounds
- `wound_type` must be in allowed list (defined by model)

**Coordinate System**:
- Option A (Roboflow default): Normalized [0.0, 1.0] relative to image dimensions
- Option B: Absolute pixel coordinates

Decision: Use **normalized coordinates** [0.0, 1.0] for consistency with Roboflow and resolution independence.

---

## Supporting Entities

### 5. StreamConfig

Configuration for stream processing behavior.

**Attributes**:
- `max_concurrent_streams` (int): Global limit (default: 10)
- `confidence_threshold` (float): Minimum detection confidence (default: 0.5)
- `max_resolution_width` (int): Maximum frame width (default: 1280)
- `max_resolution_height` (int): Maximum frame height (default: 720)
- `idle_timeout_sec` (int): Seconds before closing inactive stream (default: 30)
- `max_frame_size_bytes` (int): Maximum frame upload size (default: 10MB)

**Source**: Environment variables with fallback to defaults

---

### 6. DetectionEvent (WebSocket Message)

JSON message sent to client for each processed frame.

**Attributes**:
- `event_type` (str): "detection_result", "error", "stream_closed"
- `session_id` (str): Stream session identifier
- `frame_index` (int): Frame this event relates to
- `timestamp_ms` (float): When event was generated
- `has_wounds` (bool): Detection result
- `wounds` (List[dict]): Array of wound objects (serialized Wound entities)
- `metadata` (dict): Additional info (processing_time, quality_warning, frames_dropped)

**Example JSON**:
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
      "bbox": {"x": 0.45, "y": 0.32, "width": 0.12, "height": 0.08},
      "wound_type": "cut",
      "detection_confidence": 0.87,
      "type_confidence": 0.82
    }
  ],
  "metadata": {
    "processing_time_ms": 245.3,
    "quality_warning": null,
    "frames_dropped_since_last": 2
  }
}
```

---

## Enums

### StreamStatus
- `CONNECTING`: Initial state, WebSocket handshake in progress
- `ACTIVE`: Accepting and processing frames
- `CLOSING`: Graceful shutdown initiated
- `CLOSED`: Connection terminated
- `ERROR`: Unexpected termination

### FrameStatus
- `RECEIVED`: Frame data received from client
- `VALIDATED`: Decoded and validated successfully
- `PROCESSED`: Inference completed
- `FAILED`: Error during processing

### ImageFormat
- `JPEG`: JPEG/JPG image
- `PNG`: PNG image

---

## Data Flow

```
Client                WebSocket              FrameProcessor           Roboflow API
  |                       |                        |                        |
  |-- frame (bytes) ----->|                        |                        |
  |                       |-- Frame object ------->|                        |
  |                       |                        |-- validate/decode      |
  |                       |                        |-- infer request ------>|
  |                       |                        |<-- predictions --------|
  |                       |<-- DetectionEvent -----|                        |
  |<-- JSON event --------|                        |                        |
```

---

## Persistence

**Note**: This system is **stateless** with no persistent storage.

- VideoStream: Exists only in memory during WebSocket connection
- Frame: Exists only during processing (garbage collected after)
- WoundDetection: Returned to client immediately, not stored
- Audit Logs: Written to stdout/files as structured JSON (external log aggregation recommended)

**Future Consideration**: If analytics/reporting needed, DetectionEvent messages could be published to message queue (Redis, Kafka) for separate storage service.

---

## Validation Summary

| Entity | Key Validations |
|--------|----------------|
| VideoStream | Valid UUID, state transitions |
| Frame | Format (JPEG/PNG), resolution (≤720p), size (≤10MB) |
| WoundDetection | Confidence thresholds, timestamp consistency |
| Wound | Confidence ≥0.5, bbox within bounds, normalized coords |
| DetectionEvent | Required fields present, valid JSON schema |

---

## Error Handling

**Invalid Frame Format**:
- Log error with session_id and frame_index
- Send error event to client
- Continue processing next frame

**Roboflow API Failure**:
- Log error with retry attempt count
- Send error event to client
- Exponential backoff for retries (max 3 attempts)
- Fall back to local model if configured

**Memory/Resource Exhaustion**:
- Drop frames gracefully
- Log warning with metrics
- Include frame_dropped count in next detection event
