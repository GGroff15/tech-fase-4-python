# Code Analysis Report — yolo-rest

> **Generated**: January 24, 2026  
> **Scope**: Readability, Clean Code, Object Calisthenics, Project Structure, Duplications

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Structure Analysis](#project-structure-analysis)
3. [Duplicated Code](#duplicated-code)
4. [Object Calisthenics Violations](#object-calisthenics-violations)
5. [Clean Code Issues](#clean-code-issues)
6. [Readability Improvements](#readability-improvements)
7. [Recommendations Summary](#recommendations-summary)

---

## Executive Summary

The **yolo-rest** codebase is reasonably well-organized with clear separation of concerns across layers (API, stream processing, inference, preprocessing). However, several improvement opportunities exist:

| Category | Issues Found | Severity |
|----------|--------------|----------|
| Duplicated Code | 8 patterns | Medium |
| Object Calisthenics | 12 violations | Medium-High |
| Clean Code | 15 issues | Medium |
| Readability | 10 items | Low-Medium |

---

## Project Structure Analysis

### Current Structure — Strengths ✅

- **Layer separation**: Clear boundaries between `api/`, `stream/`, `inference/`, `preprocessing/`, `models/`
- **Test organization**: Separate `unit/` and `integration/` folders
- **Configuration centralization**: `config/constants.py` exists (partially used)
- **Documentation folder**: `docs/` and `specs/` present

### Current Structure — Issues ⚠️

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Orphan files in root** | `yolo_predict.py`, `teste.py` | Move to `scripts/` or delete if unused |
| **Mixed concerns in `api/`** | `index.html`, `styles.css`, `webrtc-client.js` | Move static assets to `api/static/` or `public/` |
| **Empty/unused folders** | `backend/`, `frontend/` | Remove or populate; causes confusion |
| **Model weights in root** | `yolov8n.pt`, `yolov8s.pt` | Move to `models/weights/` or `data/` |
| **Training artifacts scattered** | `runs/detect/` | Keep, but document in `.gitignore` rationale |

### Recommended Structure

```
yolo-rest/
├── api/
│   ├── handlers/           # Route handlers split by concern
│   ├── static/             # HTML, CSS, JS assets
│   └── server.py
├── config/
│   └── constants.py        # All magic numbers here
├── inference/
├── models/
│   ├── domain/             # Domain models (Wound, Detection)
│   └── weights/            # .pt files
├── preprocessing/
├── scripts/                # One-off scripts, training helpers
├── stream/
├── tests/
├── utils/
└── docs/
```

---

## Duplicated Code

### DUP-1: Buffer `put()` Method — Drop-Replace Logic

**Files**: 
- [stream/frame_buffer.py](../stream/frame_buffer.py#L41-L53) (`FrameBuffer.put`)
- [stream/frame_buffer.py](../stream/frame_buffer.py#L77-L89) (`AudioBuffer.put`)

**Pattern**: Identical 12-line `put()` implementation in both classes.

```python
# Repeated pattern:
async def put(self, frame) -> bool:
    was_dropped = False
    if self._queue.full():
        try:
            _ = self._queue.get_nowait()
            self.dropped_count += 1
            was_dropped = True
        except asyncio.QueueEmpty:
            pass
    await self._queue.put(frame)
    return was_dropped
```

**Recommendation**: Extract to `BaseBuffer` as a concrete implementation or use a mixin.

---

### DUP-2: Constants Redefined Across Files

**Pattern**: Same constants defined in multiple places instead of importing from `config/constants.py`.

| Constant | Defined In |
|----------|-----------|
| `DEFAULT_BLUR_THRESHOLD` | `preprocessing/validator.py`, `stream/frame_processor.py`, `config/constants.py` |
| `MAX_WIDTH/MAX_HEIGHT` | `preprocessing/validator.py`, `preprocessing/resizer.py`, `config/constants.py` |
| `IMAGE_ENCODING_FORMAT` | `inference/roboflow_client.py`, `config/constants.py` |
| `DEFAULT_CONFIDENCE_THRESHOLD` | `api/server.py`, `config/constants.py` |

**Recommendation**: Import ALL constants from `config/constants.py`. Remove local redefinitions.

---

### DUP-3: `make_jpeg_bytes()` Test Helper

**Files**:
- [tests/unit/test_frame_decoder.py](../tests/unit/test_frame_decoder.py#L7-L10)
- [tests/integration/test_websocket_endpoint.py](../tests/integration/test_websocket_endpoint.py#L8-L11)

**Pattern**: Identical helper function duplicated in two test files.

**Recommendation**: Move to `tests/conftest.py` as a pytest fixture.

---

### DUP-4: `make_image()` / `make_test_image()` Test Helpers

**Files**:
- [tests/unit/test_validator_resizer.py](../tests/unit/test_validator_resizer.py#L9-L10)
- [tests/integration/test_local_fallback.py](../tests/integration/test_local_fallback.py#L8-L10)

**Pattern**: Nearly identical image creation helpers.

**Recommendation**: Consolidate into `tests/conftest.py`.

---

### DUP-5: Lazy Model Loading Pattern

**Files**:
- [inference/fallback.py](../inference/fallback.py#L24-L35) (`LocalYoloFallback._load`)
- [audio/ser.py](../audio/ser.py#L9-L24) (`_get_pipeline`)
- [video/video_analysis.py](../video/video_analysis.py#L6) (module-level `model = YOLO(...)`)

**Pattern**: Each file implements its own lazy-loading pattern for ML models.

**Recommendation**: Create a generic `LazyModelLoader` utility in `utils/` with consistent initialization, device selection, and error handling.

---

### DUP-6: Event Emission Error Handling

**Files**:
- [stream/frame_processor.py](../stream/frame_processor.py#L150-L153) (`_emit_event`)
- [stream/frame_processor.py](../stream/frame_processor.py#L157-L163) (`_handle_processing_error`)

**Pattern**: Try-except blocks around emitter calls duplicated.

**Recommendation**: Create a single `safe_emit()` helper that wraps the emitter with consistent error handling and logging.

---

### DUP-7: Timestamp Generation

**Pattern**: `int(time.time() * 1000)` appears in multiple files for timestamp generation.

**Locations**:
- `api/server.py` (lines 90, 119)
- `stream/frame_processor.py` (line 137)
- `stream/audio_processor.py` (line 64)

**Recommendation**: Add to `utils/metrics.py`:
```python
def timestamp_ms() -> int:
    return int(time.time() * 1000)
```

---

### DUP-8: WAV File Writing Logic

**Files**:
- [preprocessing/audio_decoder.py](../preprocessing/audio_decoder.py#L44-L52)
- [stream/audio_processor.py](../stream/audio_processor.py#L104-L113)

**Pattern**: WAV file creation with `wave.open()`, `setnchannels()`, `setsampwidth()`, `setframerate()` duplicated.

**Recommendation**: Extract to a `write_wav_file(path, data, channels, sample_rate)` helper in `preprocessing/audio_decoder.py`.

---

## Object Calisthenics Violations

### Rule 1: One Level of Indentation Per Method

| File | Method | Indentation Levels | Recommendation |
|------|--------|-------------------|----------------|
| [inference/fallback.py](../inference/fallback.py#L49-L95) | `predict()` | 4 | Extract inner loops to helper methods |
| [stream/audio_processor.py](../stream/audio_processor.py#L79-L120) | `_process_window_sync()` | 4 | Extract WAV writing and chunk processing |
| [inference/roboflow_client.py](../inference/roboflow_client.py#L102-L125) | `MockDetectionGenerator.generate()` | 3 | Acceptable but could simplify |

---

### Rule 2: Don't Use the `else` Keyword

| File | Line | Issue |
|------|------|-------|
| [stream/audio_processor.py](../stream/audio_processor.py#L150-L154) | 150-154 | `else` block after try-except |
| [preprocessing/audio_decoder.py](../preprocessing/audio_decoder.py#L18-L21) | 18-21 | `else` fallback for channels |

**Recommendation**: Use early returns or guard clauses instead of else blocks.

---

### Rule 3: Wrap All Primitives and Strings

**Violations**: Many raw primitives passed around instead of domain objects.

| Primitive | Better Alternative |
|-----------|-------------------|
| `session_id: str` | `SessionId` value object |
| `confidence: float` | `Confidence` value object with validation |
| `bbox: List[float]` | `BoundingBox` dataclass |
| `timestamp_ms: int` | `Timestamp` value object |

---

### Rule 4: First-Class Collections

**Violations**:

| File | Issue |
|------|-------|
| [stream/frame_processor.py](../stream/frame_processor.py#L70-L77) | `List[WoundModel]` should be a `WoundCollection` class |
| [inference/fallback.py](../inference/fallback.py#L47) | `List[Dict[str, Any]]` for detections should be `DetectionResult` |

---

### Rule 5: One Dot Per Line (Law of Demeter)

**Violations**:

| File | Line | Code | Issue |
|------|------|------|-------|
| [api/server.py](../api/server.py#L80) | 80 | `self.data_channel.readyState` | Two dots — accessing internal state |
| [api/server.py](../api/server.py#L191) | 191 | `peer_connection.localDescription.sdp` | Two dots |
| [inference/fallback.py](../inference/fallback.py#L75) | 75 | `confs[i].cpu().numpy()` | Three chained calls |

---

### Rule 6: Keep All Entities Small

**Large Classes/Files**:

| File | Lines | Issue |
|------|-------|-------|
| [api/server.py](../api/server.py) | 213 | `WebRTCConnectionHandler` has 8 methods — consider splitting |
| [inference/roboflow_client.py](../inference/roboflow_client.py) | 221 | Too many classes in one file |
| [stream/audio_processor.py](../stream/audio_processor.py) | 164 | `_process_window_sync()` is 55+ lines |

**Recommendation**: Aim for <100 lines per class, <15 lines per method.

---

### Rule 7: No Classes With More Than Two Instance Variables

**Violations**:

| Class | Instance Variables | Recommendation |
|-------|-------------------|----------------|
| `StreamSession` | 11 variables | Split into `SessionMetrics`, `SessionConfig` |
| `WebRTCConnectionHandler` | 4 variables | Acceptable but could extract `TrackHandler` |
| `RoboflowClient` | 3 variables | Acceptable |

---

### Rule 8: No Getters/Setters

**Violations**: None significant — the codebase uses properties sparingly. ✅

---

### Rule 9: Classes Should Be Final or Abstract

**Issue**: `BaseBuffer` and `BaseProcessor` are correctly abstract, but concrete implementations like `FrameBuffer` could be marked `final` to prevent unintended inheritance.

---

## Clean Code Issues

### CC-1: Magic Numbers Not Extracted

| File | Line | Magic Number | Recommendation |
|------|------|--------------|----------------|
| [stream/audio_processor.py](../stream/audio_processor.py#L36) | 36 | `10` (frame batch size) | Extract to `AUDIO_BATCH_SIZE` |
| [stream/audio_processor.py](../stream/audio_processor.py#L82) | 82 | `48000` (sample rate) | Extract to `DEFAULT_SAMPLE_RATE` |
| [stream/frame_buffer.py](../stream/frame_buffer.py#L101) | 101 | `50`, `0.5` | Extract to constants |
| [inference/roboflow_client.py](../inference/roboflow_client.py#L115) | 115 | `50` (min width check) | Extract constant |

---

### CC-2: Functions Doing Too Much (Single Responsibility)

| Function | File | Issue |
|----------|------|-------|
| `_process_window_sync()` | audio_processor.py | Decodes, writes WAV, analyzes audio, predicts emotion — 4 responsibilities |
| `predict()` | fallback.py | Model loading + inference + result parsing |
| `analyze_video()` | video_analysis.py | File handling + video capture + inference + result building |

---

### CC-3: Inconsistent Error Handling

| Pattern | Files |
|---------|-------|
| Bare `except Exception` | audio_processor.py, fallback.py, audio_decoder.py |
| Silent exception swallowing | Multiple `except: pass` blocks |
| Inconsistent logging | Some errors logged, others silently ignored |

**Recommendation**: Define explicit exception types and handle consistently.

---

### CC-4: Mixed Abstraction Levels

| File | Issue |
|------|-------|
| [video/video_analysis.py](../video/video_analysis.py) | High-level `analyze_video()` directly uses low-level OpenCV and YOLO APIs |
| [stream/audio_processor.py](../stream/audio_processor.py) | Mixes async orchestration with sync WAV file manipulation |

---

### CC-5: Dead/Unused Code

| File | Item | Issue |
|------|------|-------|
| `models/detection.py` | `Wound`, `WoundDetection` | Duplicates `WoundModel` in `models/events.py` |
| `alerts/alert_service.py` | `generate_alert()` | Appears unused in main codebase |
| `preprocessing/validator.py` | `get_resolution()` | Not imported anywhere |
| `stream/rate_limiter.py` | `RateLimiter` | Not used in any processor |

---

### CC-6: Function/Variable Naming

| Current Name | Suggested Name | File |
|--------------|----------------|------|
| `_run()` | `_process_loop()` or `_consume_buffer()` | frame_processor.py |
| `r` | `result` or `yolo_result` | video_analysis.py |
| `ch` | `channel_count` | audio_decoder.py |
| `nparr` | `byte_array` | frame_decoder.py |
| `tmp` | `temp_file` | audio_decoder.py |

---

### CC-7: Comments Instead of Self-Documenting Code

| File | Line | Comment | Recommendation |
|------|------|---------|----------------|
| frame_buffer.py | 35-38 | Explains drop-replace | Method name should convey this: `put_with_drop_oldest()` |
| fallback.py | 69 | `# r.boxes may be empty` | Use guard clause with descriptive condition |

---

### CC-8: Inconsistent Import Organization

Some files use absolute imports, others relative. Some group stdlib/third-party/local, others don't.

**Recommendation**: Use `isort` with consistent configuration.

---

### CC-9: Missing Type Hints

| File | Function | Missing |
|------|----------|---------|
| `audio_analysis.py` | `analyze_audio()` | Return type |
| `alert_service.py` | `generate_alert()` | Parameter and return types |
| `video_analysis.py` | `analyze_video()` | Return type |

---

### CC-10: Hardcoded File Paths

| File | Line | Issue |
|------|------|-------|
| [api/server.py](../api/server.py#L142) | 142 | `"api/index.html"` hardcoded |
| [api/server.py](../api/server.py#L148) | 148 | `"api/webrtc-client.js"` hardcoded |
| [api/server.py](../api/server.py#L156) | 156 | `"api/styles.css"` hardcoded |

**Recommendation**: Use `pathlib.Path` relative to module or config.

---

## Readability Improvements

### READ-1: Long Methods Need Extraction

| Method | Lines | Max Recommended |
|--------|-------|-----------------|
| `_process_window_sync()` | 55 | 15-20 |
| `predict()` (fallback.py) | 50 | 15-20 |
| `offer()` | 25 | 15-20 |

---

### READ-2: Deep Nesting

```python
# inference/fallback.py lines 67-92 — 4 levels deep
for r in results:
    boxes = getattr(r, "boxes", None)
    if boxes is None:
        continue
    ...
    for i, b in enumerate(arr_xyxy):
        try:
            ...
        except Exception:
            continue
```

**Recommendation**: Extract to `_parse_yolo_results()` and `_parse_single_box()`.

---

### READ-3: Boolean Parameters (Flag Arguments)

| Function | Parameter | Issue |
|----------|-----------|-------|
| `BaseBuffer.put()` | Return `bool` | Returns whether dropped; consider returning a result object |

---

### READ-4: Inconsistent Docstrings

- Some methods have detailed docstrings (good)
- Some have single-line docstrings
- Some have none

**Recommendation**: Adopt consistent docstring format (Google or NumPy style) across all public methods.

---

### READ-5: Complex Conditionals

```python
# audio/ser.py line 11
device = 0 if (hasattr(__import__("torch"), "cuda") and __import__("torch").cuda.is_available()) else -1
```

**Recommendation**: Extract to helper:
```python
def get_torch_device() -> int:
    try:
        import torch
        return 0 if torch.cuda.is_available() else -1
    except ImportError:
        return -1
```

---

## Recommendations Summary

### Priority 1 — High Impact, Low Effort

| Item | Action |
|------|--------|
| Use `config/constants.py` | Update all files to import constants from central location |
| Create `tests/conftest.py` | Move shared test fixtures |
| Add `timestamp_ms()` utility | Reduce duplication across files |
| Extract `put()` to `BaseBuffer` | Remove duplication in buffer classes |

### Priority 2 — Medium Impact

| Item | Action |
|------|--------|
| Split `_process_window_sync()` | Extract WAV writing, emotion prediction |
| Create `LazyModelLoader` | Unify model loading pattern |
| Move static assets | `api/static/` for HTML/CSS/JS |
| Clean up unused code | Remove `models/detection.py` duplicates |

### Priority 3 — Architectural

| Item | Action |
|------|--------|
| Introduce value objects | `SessionId`, `Confidence`, `BoundingBox` |
| Create `WoundCollection` | First-class collection for wounds |
| Split large files | `roboflow_client.py` into multiple modules |
| Define custom exceptions | Replace bare `Exception` catches |

### Tooling Recommendations

| Tool | Purpose |
|------|---------|
| `ruff` | Already in use — enable more rules |
| `isort` | Consistent import ordering |
| `mypy --strict` | Catch type issues |
| `pytest-cov` | Measure test coverage |

---

## Appendix: Object Calisthenics Rules Reference

1. **One level of indentation per method**
2. **Don't use the ELSE keyword**
3. **Wrap all primitives and strings**
4. **First-class collections**
5. **One dot per line**
6. **Don't abbreviate**
7. **Keep all entities small**
8. **No classes with more than two instance variables**
9. **No getters/setters/properties**

---

*Report generated by code analysis. Review recommendations and prioritize based on team capacity.*
