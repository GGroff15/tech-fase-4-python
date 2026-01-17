# Tasks: Realtime Video Stream Wound Detection (001)

## Phase 1: Setup

- [ ] T001 Create dev environment and update requirements.txt — Create virtual environment and add `websockets`, `httpx`, `pytest-asyncio`, `python-dotenv`; add `.env.example` in project root

## Phase 2: Foundational

- [ ] T002 [P] Implement WebSocket endpoint in api/websocket.py — Add WebSocket handler, session start/close, binary frame receive
- [ ] T003 [P] Implement StreamSession in stream/session.py — Manage lifecycle, generate `session_id`, structured logging
- [ ] T004 [P] Implement frame buffer in stream/frame_buffer.py — Async queue maxsize=1 drop-replace strategy
- [ ] T005 [P] Implement frame processor in stream/frame_processor.py — Async pipeline: decode → validate → resize → infer
- [ ] T006 [P] Implement preprocessing utilities in preprocessing/ — `frame_decoder.py`, `validator.py`, `resizer.py` (OpenCV)
- [ ] T007 [P] Implement Roboflow client in inference/roboflow_client.py — Async calls & response parsing
- [ ] T008 [P] Implement local YOLOv8 fallback in inference/fallback.py — Optional Ultralytics inference
- [ ] T009 Implement data models in models/detection.py and models/events.py — Dataclasses and JSON schema
- [ ] T010 Implement logging and metrics in utils/ — `logging_config.py`, `metrics.py`
- [ ] T011 [P] Add health endpoints in api/health.py — readiness and Roboflow connectivity checks
- [ ] T012 Implement concurrent stream limiting in stream/rate_limiter.py — `MAX_CONCURRENT_STREAMS` semaphore
- [ ] T028 Implement configurable authentication (API key/JWT) — Middleware, config flag (`DEV_MODE_DISABLE_AUTH`), and docs (enable by default for prod)

- [X] T002 [P] Implement WebSocket endpoint in api/websocket.py — Add WebSocket handler, session start/close, binary frame receive
- [X] T003 [P] Implement StreamSession in stream/session.py — Manage lifecycle, generate `session_id`, structured logging
- [X] T004 [P] Implement frame buffer in stream/frame_buffer.py — Async queue maxsize=1 drop-replace strategy
- [X] T005 [P] Implement frame processor in stream/frame_processor.py — Async pipeline: decode → validate → resize → infer
- [X] T006 [P] Implement preprocessing utilities in preprocessing/ — `frame_decoder.py`, `validator.py`, `resizer.py` (OpenCV)
- [X] T007 [P] Implement Roboflow client in inference/roboflow_client.py — Async calls & response parsing
- [ ] T008 [P] Implement local YOLOv8 fallback in inference/fallback.py — Optional Ultralytics inference
- [X] T009 Implement data models in models/detection.py and models/events.py — Dataclasses and JSON schema
- [X] T010 Implement logging and metrics in utils/ — `logging_config.py`, `metrics.py`
- [X] T011 [P] Add health endpoints in api/health.py — readiness and Roboflow connectivity checks
- [X] T012 Implement concurrent stream limiting in stream/rate_limiter.py — `MAX_CONCURRENT_STREAMS` semaphore
- [X] T028 Implement configurable authentication (API key/JWT) — Middleware, config flag (`DEV_MODE_DISABLE_AUTH`), and docs (enable by default for prod)

## Phase 3: User Story Implementation

### [US1] Basic Realtime Wound Detection (P1)
- [ ] T013 [US1] Update main app in main.py — Register WebSocket route, health routes, initialize clients
- [ ] T014 [US1] Wire pipeline end-to-end — WebSocket → frame buffer → frame processor → Roboflow → emit detection events
- [ ] T015 [US1] Format DetectionEvent per contract — `contracts/websocket-api.md` message format

### [US2] Multiple Wounds Per Frame (P2)
- [ ] T016 [US2] Ensure inference parsing supports multiple detections — map Roboflow predictions to `Wound` objects
- [ ] T017 [US2] Add tests for multiple-wound frames in `tests/integration/` using mock responses

- [X] T013 [US1] Update main app in main.py — Register WebSocket route, health routes, initialize clients
- [X] T014 [US1] Wire pipeline end-to-end — WebSocket → frame buffer → frame processor → Roboflow → emit detection events
- [X] T015 [US1] Format DetectionEvent per contract — `contracts/websocket-api.md` message format

- [X] T016 [US2] Ensure inference parsing supports multiple detections — map Roboflow predictions to `Wound` objects
- [ ] T017 [US2] Add tests for multiple-wound frames in `tests/integration/` using mock responses

### [US3] Stream Quality & Error Handling (P3)
- [ ] T018 [US3] Implement error events and quality warnings — validation failures, low-quality frames
 - [X] T018 [US3] Implement error events and quality warnings — validation failures, low-quality frames
- [ ] T019 [US3] Implement idle timeout and graceful close — per-session idle timeout (`IDLE_TIMEOUT_SEC`)
- [ ] T020 [US3] Add session summary emission on close — `stream_closed` message per contract

## Phase 4: Tests & CI

- [ ] T021 [P] Unit tests in `tests/unit/` — `test_frame_decoder.py`, `test_validator.py`, `test_frame_buffer.py`
- [ ] T022 [P] Integration tests in `tests/integration/` — `test_websocket_endpoint.py`, `test_roboflow_client.py`
- [ ] T023 Performance tests in `tests/perf/` — `run_concurrent_streams.py` to validate latency & concurrency
- [ ] T024 CI configuration — `pytest.ini` and GitHub Actions workflow `/.github/workflows/ci.yml`

- [X] T021 [P] Unit tests in `tests/unit/` — `test_frame_decoder.py`, `test_validator.py`, `test_frame_buffer.py`
- [X] T022 [P] Integration tests in `tests/integration/` — `test_websocket_endpoint.py`, `test_roboflow_client.py`
- [ ] T023 Performance tests in `tests/perf/` — `run_concurrent_streams.py` to validate latency & concurrency
- [X] T024 CI configuration — `pytest.ini` and GitHub Actions workflow `/.github/workflows/ci.yml`

## Phase 5: Docs & Release

- [ ] T025 Update `.env.example` and `quickstart.md` — include ROBoflow env vars and run instructions
- [ ] T026 Update `requirements.txt` and lockfile — ensure reproducible environment
- [ ] T027 Create `README.md` section describing WebSocket contract and example client

- [ ] T025 Update `.env.example` and `quickstart.md` — include ROBoflow env vars and run instructions
- [X] T026 Update `requirements.txt` and lockfile — ensure reproducible environment
- [ ] T027 Create `README.md` section describing WebSocket contract and example client

---

**Notes**:
- Tasks labeled `[P]` are parallelizable across different files/components.
- Story-labeled tasks include the corresponding `[US1]`, `[US2]`, `[US3]` markers.
- Use `specs/001-realtime-wound-detection/plan.md` and `contracts/websocket-api.md` as references.
