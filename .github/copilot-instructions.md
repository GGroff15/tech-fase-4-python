# Project purpose

This document describes the purpose and high-level design of the yolo-rest project.

Purpose
- Provide a simple API endpoint that accepts a video stream (or short video file/streaming chunks) and analyzes it in (near) real-time to detect facial wounds.
- When a wound is detected, the API should report results back to the client in real time so callers can react immediately.

High-level checklist (what this file describes)
- [x] API endpoint to analyze a video stream and detect face wounds
- [x] Architecture described as layers
- [x] Technologies called out (YOLOv8, OpenCV, plus recommendations for the API layer)
- [x] Requirements and expected behaviour (stream input, realtime analysis, realtime responses)

API endpoint (suggested)
- Endpoint: POST /api/v1/analyze/video-stream
  - Accepts: multipart/form-data uploads or chunked streaming (Content-Type: multipart/form-data OR application/octet-stream). Optionally accept a streaming source URL (rtsp/http) in JSON: { "source": "rtsp://..." }.
  - Real-time return options (pick one or support both):
    - Server-Sent Events (SSE) streaming JSON events with detection results as they are produced.
    - WebSocket that sends JSON messages with detection events.
    - Alternatively, return a single aggregated JSON result for short uploads.

Input contract (recommended)
- Either:
  - HTTP multipart upload containing a short video file (mp4, avi). Form field: `video`.
  - Chunked frames (application/octet-stream) where frames or chunks are appended and processed.
  - JSON with a `source` field pointing to a streaming URL (rtsp/http).

Output contract
- Real-time event message (SSE/WebSocket) JSON example:
  {
    "timestamp_ms": 1640995200000,
    "frame_index": 123,
    "has_wounds": true,
    "wounds": [
      { "id": 1, "class": "cut", "bbox": [x,y,w,h], "confidence": 0.92 }
    ]
  }
- Final summary response (optional): { "total_frames": 1200, "frames_with_wounds": 18, "first_detected_at_frame": 123 }

Architecture (layered)
- API / Presentation layer
  - Receives client connections (HTTP/SSE/WebSocket), handles auth/validation and backpressure. Suggested framework: FastAPI + Uvicorn (async), or Flask + gevent for simpler sync flows.
- Video IO layer
  - Responsible for reading raw video stream or file and extracting frames. Use OpenCV (cv2.VideoCapture) for file/stream ingestion and frame decoding.
- Preprocessing layer
  - Resize, normalize, and prepare frames as the YOLO model expects. Optionally do face ROI cropping to speed up inference.
- Inference layer
  - YOLOv8 model (Ultralytics or PyTorch implementation) loads the trained weights (yolov8n-pose.pt or a custom wound detection model) and runs detection on frames or ROIs.
- Postprocessing / Business logic layer
  - Filters detections (confidence threshold, NMS), translates model outputs to API event messages, aggregates results, and decides when to emit events.
- Streaming / Response layer
  - Emits real-time detection events back to the client via SSE or WebSocket, and returns final summaries when the stream ends.

Technologies (recommended)
- YOLOv8 (Ultralytics implementation) — model for wound detection (use a model trained specifically to detect face wounds). The project already contains local weights (e.g., `yolov8n.pt` / `yolov8n-pose.pt`).
- OpenCV (cv2) — reading video files/streams and extracting frames.
- FastAPI + Uvicorn (recommended) — build an async REST + SSE/WebSocket API quickly.
- PyTorch / Ultralytics package — runtime for YOLOv8. Consider torch.cuda if GPU is available.
- asyncio, websockets, sse-starlette (or FastAPI native support) — real-time message delivery.

Requirements (functional)
- Receive simple video streaming
  - The service must accept short video uploads and streaming sources (URL) or chunked frame uploads.
- Analyze video in real time
  - Frames should be processed as they arrive with low latency (target: process a frame within X ms — tune per hardware). Support model warm-up and batching if necessary.
- Return if wounds were detected in real time
  - Emit detection events immediately when a frame (or a short sequence) contains a wound.
  - Provide a final summary upon stream end.

Non-functional recommendations
- Latency: Aim for <200ms to <500ms per frame on a small/optimized model on GPU; on CPU expect higher latencies.
- Throughput & concurrency: Limit concurrent streams per instance. Use a queue to avoid overloading the model.
- Fault tolerance: Timeouts for slow streams, graceful shutdown, and drop/skip frames if processing backlog grows too large.
- Security: Validate uploaded content types, limit file size, optional authentication (API key/JWT), and run model code in an isolated environment.

Edge cases and behavior
- Low-quality frames: return lower confidence or skip. Consider sending a `quality` field in events.
- Long-running streams: periodically emit progress heartbeats to the client.
- No face/wound found: send events with `has_wounds:false` occasionally or only when first found/cleared.
- Partial/garbled uploads: return 4xx errors for bad requests and 5xx for internal errors.

Developer notes / next steps
- Implement a minimal FastAPI app with:
  - POST /api/v1/analyze/video-stream that supports multipart file upload and SSE responses.
  - A background worker that reads frames with OpenCV, runs the YOLOv8 model, and yields SSE messages.
- Add tests: unit test for frame extraction, integration test uploading a short sample video (included: `sample_video.mp4`), and an end-to-end smoke test that connects via SSE and asserts receipt of at least one detection or a clean summary.

Files in the repo that are relevant
- `video/video_analysis.py` — video handling utilities
- `audio/audio_analysis.py` — (unrelated to video) example of analysis pattern
- `alerts/alert_service.py` — streaming/alert patterns
- `yolo-training.py` — training scripts and hints about the model
- `yolov8n.pt`, `yolov8n-pose.pt` — example weights present in the repo

Requirements coverage mapping
- Create and expose an API endpoint to analyze a video and detect face wounds: Suggested endpoint and contract provided above. (Done — spec provided)
- Architecture: layers: Detailed layered architecture provided. (Done)
- Technologies: YOLOv8 and OpenCV called out, plus API framework recommendation. (Done)
- Requirements: receive video streaming, analyze in real time, return detections in real time: Functional and non-functional requirements described. (Done)

If you want, I can now:
- Implement the minimal FastAPI server stub and SSE/WebSocket streaming handler and run a smoke test using `sample_video.mp4`.
- Or generate a small example worker that uses OpenCV + a dummy YOLO runner (returns random detections) so you can iterate quickly without the real model.

