# Business Flows Index

This document provides a navigable index of all documented business flows in the **yolo-rest** system. Each flow represents a meaningful sequence of business actions, decisions, and state transitions expressed using terms from the [Ubiquitous Language](ubiquitous-language.md).

## Purpose

Business flows serve as:
- **Architectural documentation** describing how the system operates end-to-end
- **Onboarding resources** for developers joining the project
- **Requirements traceability** linking code to business capabilities
- **Communication artifacts** bridging technical and domain experts

## How to Use This Index

Flows are organized by **Bounded Context** (the subsystem or domain area they belong to). Each entry includes:
- **Flow Title**: Descriptive name of the business flow
- **Summary**: One-sentence description of what the flow accomplishes
- **Status**: `published` (stable), `reviewed` (validated), or `draft` (in progress)

Click any flow title to view its full documentation, including:
- Detailed step-by-step flow description
- Alternative paths and error handling
- Business rules and invariants
- Data structures and events
- Flow diagrams (sequence, state, flowchart)
- Acceptance criteria and test guidance
- Related domain terms and cross-flow references

---

## Streaming Infrastructure

Flows related to WebRTC connection management, session lifecycle, and resource cleanup.

- [WebRTC Session Establishment](flows/webrtc-session-establishment.md) — Establishes a WebRTC peer connection between client and server, initializes session, and prepares for media streaming. *(published)*
- [Session Closure and Reporting](flows/session-closure-and-reporting.md) — Handles graceful session termination when tracks end, stops processors, generates session summary metrics, and cleans up resources. *(published)*

---

## Media Processing

Flows describing how video and audio streams are ingested, validated, transformed, and analyzed.

- [Video Frame Processing Pipeline](flows/video-frame-processing-pipeline.md) — Processes incoming video frames through decode, validate, resize, and inference stages to detect wounds and emit real-time detection events. *(published)*
- [Audio Analysis Pipeline](flows/audio-analysis-pipeline.md) — Processes audio frames through windowing, WAV conversion, feature extraction, and emotion recognition to compute psychological risk scores. *(published)*

---

## Inference Infrastructure

Flows related to running machine learning models, handling inference failures, and ensuring detection reliability.

- [Inference Fallback Handling](flows/inference-fallback-handling.md) — Automatically switches from Roboflow hosted API to local YOLO model when primary inference fails, ensuring continuous detection capability. *(published)*

---

## Detection and Alerting

Flows that aggregate detection results, apply business rules, and generate actionable alerts.

- [Wound Detection and Alert Generation](flows/wound-detection-and-alert-generation.md) — Aggregates wound detections from video frames and generates alerts when wounds are found, potentially triggering downstream notifications. *(published)*

---

## Flow Relationships

### Core Flow Sequence

The typical end-to-end journey through the system follows this sequence:

1. **[WebRTC Session Establishment](flows/webrtc-session-establishment.md)** — Client connects and session begins
2. **Parallel Processing:**
   - **[Video Frame Processing Pipeline](flows/video-frame-processing-pipeline.md)** — Continuous video analysis
   - **[Audio Analysis Pipeline](flows/audio-analysis-pipeline.md)** — Concurrent audio risk scoring
3. **Detection Handling:**
   - **[Inference Fallback Handling](flows/inference-fallback-handling.md)** — Ensures inference reliability
   - **[Wound Detection and Alert Generation](flows/wound-detection-and-alert-generation.md)** — Escalates significant findings
4. **[Session Closure and Reporting](flows/session-closure-and-reporting.md)** — Session ends and metrics reported

### Cross-Cutting Concerns

Several flows interact with multiple bounded contexts:
- **Inference Fallback** is invoked by the Video Frame Processing Pipeline
- **Wound Detection and Alert Generation** consumes events from both video and audio pipelines
- **Session Closure** coordinates shutdown across all active processors

---

## Validation and Quality Checks

All flows in this index have been validated against the [Ubiquitous Language](ubiquitous-language.md). Each flow uses only terms defined in that document or explicitly flags missing terms for review.

### Known Missing Terms

The following terms are referenced in flows but not yet defined in the Ubiquitous Language:
- **ICE Candidate** (WebRTC networking)
- **Laplacian Variance** (blur detection algorithm)
- **MFCC**, **RMS Energy**, **Wav2Vec2** (audio analysis techniques)
- **Webhook**, **Dead-Letter Queue** (alerting infrastructure)
- **Model Loading**, **Weight Caching** (inference optimization)

These terms should be added to the Ubiquitous Language in a future update.

---

## Adding New Flows

When documenting a new business flow:

1. Create a markdown file under `docs/flows/<flow-slug>.md`
2. Use the [flow template structure](../.github/prompts/generate-flow-description.prompt.md) with YAML front-matter
3. Ensure all domain terms used are defined in [ubiquitous-language.md](ubiquitous-language.md)
4. Update this index file to include the new flow in the appropriate bounded context
5. Cross-link related flows in the "Related Flows" section of each document

---

## Changelog

| Date       | Author                      | Change                                      |
|------------|-----------------------------|---------------------------------------------|
| 2026-01-24 | flow-documentation-agent    | Initial flows index with 6 documented flows |

---

## Questions or Feedback?

If a flow is unclear, missing, or needs updating:
- Check the source code references in each flow document
- Review the [Ubiquitous Language](ubiquitous-language.md) for term definitions
- Open an issue or PR with suggested improvements
- Consult the [Copilot Instructions](../.github/copilot-instructions.md) for project conventions
