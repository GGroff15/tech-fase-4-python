# Copilot instructions — yolo-rest

Real-time wound detection API using WebRTC, YOLOv8, and async Python. Accepts video/audio streams and emits detection events via WebRTC data channels.

## Quick start
```powershell
# Setup venv and dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run server (aiohttp + aiortc)
python main.py  # Listens on 0.0.0.0:8000

# Test
pytest -q  # asyncio_mode=auto in pytest.ini
```

## Architecture (WebRTC-based streaming)
- **Entry**: `main.py` → `api/server.py` (aiohttp web app)
- **WebRTC**: Client sends offer to `POST /offer`, server returns SDP answer. Video/audio tracks flow via `aiortc.RTCPeerConnection`
- **Processing pipeline**: `MediaStreamTrack` → `stream/frame_buffer.py` (single-slot async queue) → `stream/frame_processor.py` (BaseProcessor subclasses) → inference → emit detection events via WebRTC data channel
- **Inference**: `inference/roboflow_client.py` (HTTP to Roboflow) with local `inference/fallback.py` (Ultralytics YOLOv8) when Roboflow unavailable
- **Session lifecycle**: `stream/session.py` tracks frame counts, idle timeouts, and metrics per connection

### Key flow (video)
1. Client establishes WebRTC peer connection and sends video track
2. `api/server.py:WebRTCConnectionHandler._handle_track()` creates `FrameBuffer` + `VideoProcessor`
3. `VideoProcessor._run()` loop: decode JPEG frames, validate/resize, call `infer_image()`, emit `DetectionEvent` JSON via data channel
4. Audio tracks route to `AudioProcessor` (emotion detection via transformers)

## Project-specific patterns
- **Async buffer pattern**: All buffers inherit `stream/frame_buffer.py:BaseBuffer` (abstract `put`/`get`/`empty`). `FrameBuffer` uses size-1 queue; new frames drop old ones (backpressure handling)
- **Processor lifecycle**: `BaseProcessor.start(emitter)` spawns asyncio task running `_run()`. Always call `stop()` to cancel task
- **Logging**: Use `logger = logging.getLogger("yolo_rest.<module>")` namespace. Config in `utils/logging_config.py`
- **Constants**: All magic numbers in `config/constants.py` (MAX_IMAGE_WIDTH, DEFAULT_CONFIDENCE_THRESHOLD, etc.)
- **Env vars**: Load from `.env` via `os.getenv()`. See `.github/instructions/env-file.instructions.md`. Key vars: `ROBOFLOW_API_KEY`, `ROBOFLOW_MODEL_URL`, `USE_GPU`, `LOCAL_YOLO_MODEL_PATH`
- **Testing**: Use `conftest.py` fixtures (`jpeg_bytes`, `dummy_image`). Tests are async-friendly (`pytest.ini` sets `asyncio_mode=auto`)

## Critical files by layer
- **API/WebRTC**: `api/server.py` (WebRTCConnectionHandler, route handlers), `api/health.py` (health check)
- **Stream control**: `stream/frame_buffer.py` (BaseBuffer, FrameBuffer, AudioBuffer), `stream/frame_processor.py` (VideoProcessor, AudioProcessor), `stream/session.py` (StreamSession)
- **Preprocessing**: `preprocessing/frame_decoder.py` (decode_image), `preprocessing/resizer.py` (resize_to_720p), `preprocessing/validator.py` (blur detection)
- **Inference**: `inference/roboflow_client.py` (RoboflowConfig, infer_image), `inference/fallback.py` (LocalYoloFallback)
- **Models**: `models/detection.py` (Wound, WoundDetection dataclasses), `models/events.py` (for event schemas)
- **Utils**: `utils/emitter.py` (safe_emit, DataChannelWrapper), `utils/loader.py` (LazyModelLoader for deferred Ultralytics import)

## Common tasks
**Add a new processor**:
1. Subclass `stream/frame_processor.py:BaseProcessor`
2. Implement `async _run(self, emitter)` — loop over `self.frame_buffer.get()`, process, call `await safe_emit(emitter, event)`
3. Wire in `api/server.py:_handle_track()` by track kind

**Change inference backend**:
- Edit `inference/roboflow_client.py:infer_image()` or swap `LocalYoloFallback` in `fallback.py`
- Update `config/constants.py` for confidence thresholds

**Adjust buffer size**:
- Set `FRAME_BUFFER_MAX_SIZE` in `config/constants.py` (currently 1 = drop-replace strategy)

## Testing & validation
```powershell
# Unit tests (fast, no I/O)
pytest tests/unit/ -v

# Integration tests (require model files)
pytest tests/integration/ -v

# Run server and test WebRTC via browser
python main.py
# Open http://localhost:8000 (index.html serves webrtc-client.js)
```

**Key test examples**:
- `tests/unit/test_frame_buffer.py` — verify drop-replace behavior
- `tests/integration/test_local_fallback.py` — smoke test LocalYoloFallback with dummy image

## Dependencies & environment
- **Core**: `aiohttp` (web server), `aiortc` (WebRTC), `ultralytics` (YOLOv8), `opencv-python` (frame decoding)
- **ML**: `torch`, `transformers` (audio emotion detection)
- **Optional**: `roboflow` (cloud inference), `python-dotenv` (env loading)
- **Dev**: `pytest`, `pytest-asyncio`, `httpx` (test client)
- **Model weights**: `yolov8n.pt`, `yolov8s.pt` (repo root), custom weights in `runs/detect/train2/weights/best.pt`

## Common pitfalls
- **Blocking in async**: Never do sync I/O in `_run()` loops (VideoProcessor/AudioProcessor). Use `asyncio.to_thread()` for CPU-bound ops
- **Data channel timing**: DataChannelWrapper checks `readyState` before sending. Wait for `DATA_CHANNEL_INIT_DELAY` after track establishment
- **Inference failures**: `infer_image()` returns empty list on error/fallback failure. Handle gracefully
- **Model loading**: `LazyModelLoader` defers `ultralytics` import until first use (avoids startup cost). Don't construct YOLO directly

## Editing checklist
- [ ] Read related files in same module before editing (e.g., read `frame_buffer.py` before editing `frame_processor.py`)
- [ ] Update `config/constants.py` if adding configurable thresholds
- [ ] Add/update tests in `tests/unit/` or `tests/integration/`
- [ ] Verify `pytest -q` passes locally
- [ ] Check `ruff check .` (linting/formatting)
- [ ] Never commit `.env` or secrets — use `.env.example` for docs

## References
- **WebRTC flow**: `docs/flows/webrtc-session-establishment.md`, `docs/flows/video-frame-processing-pipeline.md`
- **Inference logic**: `docs/flows/inference-fallback-handling.md`, `docs/flows/wound-detection-and-alert-generation.md`
- **Quickstart**: `quickstart.md` (detailed setup with examples)
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

