# Implementation Plan: Realtime Video Stream Wound Detection API

**Branch**: `001-realtime-wound-detection` | **Date**: 2026-01-16 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-realtime-wound-detection/spec.md`

## Summary

Create a WebSocket-based API endpoint that receives real-time video streams (JPEG/PNG frames up to 720p), analyzes each frame using a custom YOLOv8 wound detection model integrated via Roboflow, and streams detection results back to clients with sub-500ms latency. The system will support 5-10 concurrent streams, drop frames when processing capacity is exceeded, and report both detection confidence (≥0.5 threshold) and wound type classification confidence scores.

**Technical Approach**: FastAPI with WebSocket support, async frame processing pipeline, Roboflow inference API for wound detection, OpenCV for frame validation/preprocessing, and structured JSON streaming for detection events.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (WebSocket), Roboflow (model inference), OpenCV (frame handling), Ultralytics YOLOv8 (local fallback), websockets, python-multipart  
**Storage**: None (stateless, no persistence of video or results)  
**Testing**: pytest, pytest-asyncio, httpx (WebSocket testing)  
**Target Platform**: Linux/Windows server with optional GPU support  
**Project Type**: Single web API project  
**Performance Goals**: <500ms frame-to-detection latency, 30 FPS processing capability, 5-10 concurrent streams  
**Constraints**: 720p max resolution, 0.5 confidence threshold, frame dropping under load. Authentication required by default (API key or JWT) with a configurable dev-mode toggle to disable auth for local/trusted deployments.
**Scale/Scope**: Small to medium deployment (5-10 concurrent users), ~2000 LOC, single endpoint with streaming

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Real-Time First** | ✅ PASS | WebSocket streaming + async processing ensures <500ms latency; frame dropping strategy maintains real-time behavior under load |
| **II. Lightweight & Resource-Efficient** | ✅ PASS | Roboflow inference offloads heavy processing; frame dropping under load; 720p resolution limit; <500MB memory target per stream |
| **III. Modular Architecture** | ✅ PASS | Layered design: API → Frame Decoder → Roboflow Inference → Event Formatter → WebSocket Emitter |
| **IV. Fail-Safe & Observable** | ✅ PASS | Structured logging with session IDs; graceful frame skipping on errors; 30s idle timeout; health endpoints planned |
| **V. Secure by Design** | ✅ PASS | Authentication required by default (configurable). Input validation, rate limiting, and HTTPS recommended for production deployments. |

**Deviation Justification**: (none) Spec updated to require configurable authentication; dev-mode toggle allowed for local/trusted testing.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single project structure (existing codebase extension)
.
├── main.py                          # FastAPI app entry (extend with WebSocket endpoint)
├── requirements.txt                 # Python dependencies (add websockets, pytest-asyncio)
├── pytest.ini                       # Pytest configuration (new)
├── .env.example                     # Environment variables template (new)
│
├── api/                             # API layer (new directory)
│   ├── __init__.py
│   ├── websocket.py                 # WebSocket endpoint handler
│   ├── schemas.py                   # Pydantic models for messages
│   └── health.py                    # Health check endpoints
│
├── stream/                          # Stream processing layer (new directory)
│   ├── __init__.py
│   ├── session.py                   # StreamSession class (manages WebSocket lifecycle)
│   ├── frame_processor.py           # Async frame processing pipeline
│   ├── frame_buffer.py              # Frame dropping/prioritization logic
│   └── rate_limiter.py              # Concurrent stream limiting
│
├── inference/                       # Inference layer (new directory)
│   ├── __init__.py
│   ├── roboflow_client.py           # Roboflow API integration
│   ├── model_cache.py               # Model metadata caching
│   └── fallback.py                  # Local YOLOv8 fallback (optional)
│
├── preprocessing/                   # Preprocessing layer (new directory)
│   ├── __init__.py
│   ├── frame_decoder.py             # JPEG/PNG decoding with OpenCV
│   ├── validator.py                 # Resolution/format validation
│   └── resizer.py                   # 720p enforcement
│
├── models/                          # Data models (new directory)
│   ├── __init__.py
│   ├── detection.py                 # WoundDetection, Wound dataclasses
│   └── events.py                    # WebSocket event message schemas
│
├── utils/                           # Utilities (new directory)
│   ├── __init__.py
│   ├── logging_config.py            # Structured JSON logging setup
│   └── metrics.py                   # Performance metrics tracking
│
├── video/                           # Existing video analysis (keep for backward compat)
│   ├── __init__.py
│   └── video_analysis.py            # Legacy batch analysis endpoint
│
├── tests/                           # Test suite (new directory structure)
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_frame_decoder.py
│   │   ├── test_validator.py
│   │   └── test_frame_buffer.py
│   ├── integration/
│   │   ├── test_websocket_endpoint.py
│   │   ├── test_roboflow_client.py
│   │   └── test_session_lifecycle.py
│   └── fixtures/
│       ├── sample_frames/           # Test JPEG/PNG images
│       └── mock_responses.json      # Mock Roboflow API responses
│
└── docs/                            # Documentation (optional)
    └── websocket_protocol.md        # WebSocket message format reference
```

**Structure Decision**: Extending existing single-project FastAPI structure with modular directories for new streaming functionality. Preserving `video/` for backward compatibility with existing batch endpoint. New layered architecture (api → stream → inference → preprocessing) aligns with Constitution Principle III (Modular Architecture).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No authentication (Principle V deviation) | Explicit requirement for internal/trusted network deployment where network-level security is sufficient | API key/JWT authentication rejected because spec clarification stated "No need for authentication" for simplified internal use case |

---

## Phase 0: Research (Complete ✅)

**Output**: [research.md](research.md)

**Key Decisions**:
1. WebSocket protocol via FastAPI native support
2. Roboflow SDK for hosted model inference
3. Frame dropping with asyncio.Queue(maxsize=1)
4. OpenCV for frame validation and preprocessing
5. asyncio.Semaphore for concurrent stream limiting
6. Dual confidence thresholds (detection + type)
7. UUID-based session tracking with structured logging

**All NEEDS CLARIFICATION items resolved**: ✅

---

## Phase 1: Design & Contracts (Complete ✅)

**Outputs**:
- [data-model.md](data-model.md) - Entities: VideoStream, Frame, WoundDetection, Wound
- [contracts/websocket-api.md](contracts/websocket-api.md) - WebSocket protocol specification
- [quickstart.md](quickstart.md) - Setup and testing guide
- Agent context updated: ✅

**Architecture**: Modular layers with clear separation of concerns

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Application                     │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│           WebSocket Handler (api/)                   │
│  - Connection management                             │
│  - Session initialization                            │
│  - Message routing                                   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│       Stream Session Manager (stream/)               │
│  - Session lifecycle                                 │
│  - Frame buffer (drop strategy)                      │
│  - Rate limiting                                     │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│       Frame Processor Pipeline                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ 1. Decode (preprocessing/)                    │   │
│  │    - JPEG/PNG decode                          │   │
│  │    - Format validation                        │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ 2. Validate (preprocessing/)                  │   │
│  │    - Resolution check                         │   │
│  │    - Downscale to 720p                        │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ 3. Infer (inference/)                         │   │
│  │    - Roboflow API call                        │   │
│  │    - Confidence filtering                     │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │ 4. Format (models/)                           │   │
│  │    - Build DetectionEvent                     │   │
│  │    - JSON serialization                       │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│       WebSocket Emitter (api/)                       │
│  - Send detection results                            │
│  - Error handling                                    │
│  - Connection close                                  │
└─────────────────────────────────────────────────────┘
```

**Constitution Re-Check**: ✅ All principles satisfied (with documented deviation)

---

## Phase 2: Task Breakdown

**Status**: NOT STARTED (Use `/speckit.tasks` command)

**Expected Output**: `tasks.md` with:
- Granular development tasks
- Estimates and priorities
- Dependencies and ordering
- Test coverage requirements

---

## Implementation Notes

### Critical Path
1. **Foundation**: WebSocket endpoint skeleton + session management
2. **Core Pipeline**: Frame decode → Roboflow integration → Result emission
3. **Quality**: Frame dropping logic + error handling
4. **Polish**: Logging, metrics, health endpoints

### Risk Areas
- **Roboflow API latency**: May exceed 500ms under load
  - Mitigation: Monitor p95 latency, consider local fallback
- **Memory growth**: Long-running streams without GC
  - Mitigation: Explicit frame cleanup after processing
- **Concurrent stream limits**: May need tuning based on server capacity
  - Mitigation: Load testing with 10+ simulated clients

### Testing Strategy
- **Unit**: Frame validation, confidence filtering, message serialization
- **Integration**: WebSocket lifecycle, Roboflow client, end-to-end frame flow
- **Performance**: Latency benchmarks, concurrent stream stress tests
- **Contract**: API schema validation against contracts/websocket-api.md

### Deployment Considerations
- Use Gunicorn with Uvicorn workers for production
- Enable HTTPS/WSS via reverse proxy (nginx/Caddy)
- Set up log aggregation for structured JSON logs
- Monitor Roboflow API usage/costs
- Consider multi-region Roboflow deployment for redundancy

---

## Success Metrics (From Spec)

- ✅ **SC-001**: Clients receive first detection result within 500ms
- ✅ **SC-002**: System processes video streams up to 30 FPS
- ✅ **SC-003**: Detection accuracy matches standalone model (≥85% recall, ≥80% precision)
- ✅ **SC-004**: Processes 5-minute streams without failures
- ✅ **SC-005**: End-to-end latency <1 second for 95% of frames
- ✅ **SC-006**: Handles 5+ concurrent streams with <20% degradation
- ✅ **SC-007**: All detection results include required fields

**Validation**: Performance tests must verify these metrics before merge.

---

## Next Steps

1. Review this plan and related documents (research, data model, contracts)
2. Run `/speckit.tasks` to generate detailed implementation tasks
3. Begin implementation starting with foundation (WebSocket endpoint)
4. Set up Roboflow project and obtain API credentials
5. Create test fixtures (sample frames with known wounds)
6. Implement core pipeline with TDD approach
7. Performance testing and optimization
8. Documentation and deployment guide

---

**Plan Status**: ✅ COMPLETE (Phase 0 + Phase 1)  
**Ready for**: `/speckit.tasks` command to generate task breakdown
