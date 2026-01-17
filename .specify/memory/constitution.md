<!--
  SYNC IMPACT REPORT
  ==================
  Version Change: N/A → 1.0.0 (Initial ratification)
  
  Modified Principles: N/A (Initial creation)
  
  Added Sections:
  - Core Principles (5 principles)
  - Performance & Reliability Standards
  - Security & Safety Requirements
  - Governance
  
  Removed Sections: N/A
  
  Templates Status:
  ✅ plan-template.md - Constitution Check gate references ready
  ✅ spec-template.md - User story requirements align with Real-time First principle
  ✅ tasks-template.md - Task categorization aligns with modular principles
  
  Follow-up TODOs: None
-->

# YOLO-REST Real-Time Wound Detection Constitution

## Core Principles

### I. Real-Time First (NON-NEGOTIABLE)
**Principle**: All video processing and wound detection MUST operate in real-time with minimal latency.

**Requirements**:
- Stream processing with <500ms frame-to-detection latency target (GPU) or <1000ms (CPU)
- Immediate emission of detection events as wounds are identified
- No batch processing that delays feedback to clients
- Asynchronous architecture to prevent blocking operations
- Backpressure handling to gracefully degrade under load rather than fail

**Rationale**: Real-time feedback is the core value proposition. Delayed detection undermines medical use cases and user trust.

### II. Lightweight & Resource-Efficient
**Principle**: The system MUST minimize resource consumption to enable deployment on constrained hardware and reduce operational costs.

**Requirements**:
- YOLOv8 nano/small models preferred over larger variants unless accuracy mandates otherwise
- Frame skipping/sampling strategies when processing capacity is exceeded
- Memory footprint <500MB per concurrent stream under normal operation
- CPU-only fallback mode for environments without GPU access
- Efficient frame decoding and preprocessing (OpenCV optimizations)

**Rationale**: Lightweight operation enables broader deployment scenarios (edge devices, cost-sensitive cloud instances) and better scalability.

### III. Modular Architecture
**Principle**: The system MUST be decomposed into independent, testable layers with clear contracts.

**Required Layers**:
1. **API/Presentation**: HTTP/WebSocket/SSE handling, authentication, validation
2. **Video I/O**: Stream ingestion, frame extraction (OpenCV)
3. **Preprocessing**: Frame normalization, resizing, ROI extraction
4. **Inference**: YOLO model execution, detection
5. **Postprocessing**: Confidence filtering, NMS, event generation
6. **Response**: Real-time event emission and final summaries

**Requirements**:
- Each layer independently testable with mocked dependencies
- Clear input/output contracts documented
- No cross-layer coupling (e.g., API layer never directly calls YOLO)

**Rationale**: Modularity enables isolated testing, easier debugging, and component reuse/replacement.

### IV. Fail-Safe & Observable
**Principle**: The system MUST handle failures gracefully and provide visibility into operation.

**Requirements**:
- Structured logging (JSON) with contextual metadata (stream_id, frame_index, timestamp)
- Graceful degradation: frame drops preferred over crashes
- Timeout enforcement on slow streams (configurable, default 30s idle timeout)
- Health check endpoints (`/health`, `/metrics`) for monitoring
- Error responses with clear status codes (4xx for client errors, 5xx for server errors)
- No silent failures - log all anomalies (low quality frames, inference errors)

**Rationale**: Medical applications demand reliability. Observable systems are debuggable and maintainable.

### V. Secure by Design
**Principle**: The system MUST protect sensitive medical data and prevent abuse.

**Requirements**:
- Input validation: Content-Type verification, file size limits (default 100MB)
- Authentication via API keys or JWT tokens (configurable)
- No logging of video frame content or PII
- Rate limiting per client to prevent DoS (configurable)
- HTTPS enforcement in production deployments
- Model inference isolated from API layer (e.g., separate process/container)

**Rationale**: Medical data is sensitive. Security breaches erode trust and violate regulations (HIPAA, GDPR).

## Performance & Reliability Standards

**Latency Targets**:
- Frame-to-detection: <500ms p95 (GPU), <1000ms p95 (CPU)
- API response time: <100ms for non-streaming endpoints

**Throughput Targets**:
- Minimum 10 FPS processing rate per stream on modest hardware (4-core CPU or entry-level GPU)
- Concurrent stream limit: Configurable per instance (default 5)

**Availability**:
- Graceful shutdown handling (finish in-flight streams before termination)
- No single point of failure in stateless API design

**Quality Gates**:
- Frame quality assessment: Flag low-quality frames (blur, low resolution) without blocking processing
- Model confidence thresholds: Configurable per deployment (default 0.5)

## Security & Safety Requirements

**Data Handling**:
- Video streams MUST NOT be persisted to disk unless explicitly configured
- Detection results MUST NOT include raw frame data in responses
- Temporary files (if any) MUST be securely deleted after processing

**Access Control**:
- API endpoints MUST require authentication (disabled only for development/testing)
- Role-based access if multiple client types exist

**Compliance**:
- Follow OWASP Top 10 guidelines for web API security
- Medical data handling aligns with relevant regulations (HIPAA/GDPR where applicable)

**Safety**:
- Model predictions are advisory only - not diagnostic
- Clear disclaimers in API documentation

## Governance

**Amendment Process**:
1. Proposed changes documented with rationale
2. Impact assessment on existing code and templates
3. Version bump (MAJOR for principle removal/redefinition, MINOR for additions, PATCH for clarifications)
4. Update propagation to all templates and guidance documents
5. Team review and approval (if team exists)

**Versioning Policy**:
- Constitution version follows semantic versioning (MAJOR.MINOR.PATCH)
- All code artifacts reference constitution version in comments/docs

**Compliance Verification**:
- All feature specs MUST include a "Constitution Check" section
- Code reviews MUST verify adherence to principles
- Automated tests MUST validate performance/reliability standards where measurable

**Authority**:
- This constitution supersedes all other development practices
- Deviations require explicit justification and amendment process
- Runtime guidance in `.github/copilot-instructions.md` complements but does not override principles

**Version**: 1.0.0 | **Ratified**: 2026-01-16 | **Last Amended**: 2026-01-16
