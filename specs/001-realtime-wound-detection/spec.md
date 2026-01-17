# Feature Specification: Realtime Video Stream Wound Detection API

**Feature Branch**: `001-realtime-wound-detection`  
**Created**: January 16, 2026  
**Status**: Draft  
**Input**: User description: "Develop an endpoint that will receive a video stream in realtime and should return a information stream. The video stream will have frames extracted in realtime and each frame will be analyzed by a computational custom model to detect wounds. Wound detection must be returned in realtime too through a data stream."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Realtime Wound Detection (Priority: P1)

A client application (web, mobile, or desktop) needs to stream video to the server and receive immediate wound detection results as the video is being analyzed frame-by-frame.

**Why this priority**: This is the core functionality of the feature - without this, no wound detection capability exists. This delivers immediate value by enabling real-time analysis.

**Independent Test**: Can be fully tested by streaming a short 5-second video clip containing visible wounds and verifying that detection results are received during streaming (not after completion). Delivers standalone value as a functional wound detection system.

**Acceptance Scenarios**:

1. **Given** a client application with video stream capability, **When** the client starts streaming video frames to the endpoint, **Then** the server begins processing frames immediately and returns a data stream connection
2. **Given** an active video stream connection, **When** a frame containing a wound is analyzed, **Then** wound detection information (bounding box, confidence, frame timestamp) is sent to the client within 500ms of frame receipt
3. **Given** an active video stream connection, **When** a frame without wounds is analyzed, **Then** a "no wounds detected" status is sent to the client for that frame
4. **Given** a client streaming video, **When** the client closes the stream, **Then** the server gracefully terminates processing and closes the data stream with a completion message

---

### User Story 2 - Multiple Wounds Per Frame Detection (Priority: P2)

When a single video frame contains multiple wounds (e.g., multiple injuries on a patient), the system should identify and report all detected wounds with their individual characteristics.

**Why this priority**: Real-world scenarios often involve multiple wounds. This enhances the core functionality to handle realistic medical assessment situations.

**Independent Test**: Can be tested by streaming a frame containing 3+ distinct wounds and verifying that all wounds are detected and returned in the same detection event with unique identifiers and separate bounding boxes.

**Acceptance Scenarios**:

1. **Given** a video frame with multiple visible wounds, **When** the frame is analyzed, **Then** all wounds meeting the confidence threshold are detected and returned as an array of wound objects
2. **Given** multiple wound detections in a single frame, **When** results are returned, **Then** each wound has a unique identifier, bounding box coordinates, wound type classification, and confidence score
3. **Given** overlapping wounds in close proximity, **When** the frame is analyzed, **Then** the system distinguishes between separate wounds rather than merging them into a single detection

---

### User Story 3 - Stream Quality and Error Handling (Priority: P3)

When network conditions are poor or video quality is insufficient, the system should handle degraded input gracefully and inform the client about the issue without crashing or hanging.

**Why this priority**: Ensures system reliability and provides feedback to users when technical issues occur. Critical for production use but not core functionality.

**Independent Test**: Can be tested by intentionally sending corrupted frames, incomplete data, or extremely low-quality video and verifying the system responds with appropriate error messages rather than failing.

**Acceptance Scenarios**:

1. **Given** a low-quality or blurry frame, **When** wound detection confidence is below a minimum threshold for all detections, **Then** the system returns a quality warning message indicating analysis reliability is low
2. **Given** an active stream connection, **When** a frame cannot be decoded or is corrupted, **Then** the system skips that frame, logs the error, and continues processing subsequent frames
3. **Given** a client stream that stops sending frames mid-stream, **When** no frame is received for 30 seconds, **Then** the server times out the connection and releases resources
4. **Given** excessive concurrent stream requests, **When** server capacity is reached, **Then** new connection requests receive a "503 Service Unavailable" response with retry guidance

---

## Clarifications

### Session 2026-01-16

- Q: What is the minimum confidence threshold for reporting wound detections? → A: 0.5 (50%)
- Q: When incoming frame rate exceeds processing capacity, how should the system handle the backlog? → A: Drop intermediate frames
- Q: What is the maximum supported video frame resolution for realtime processing? → A: 1280x720 (720p)
- Q: Should the system report wound detections when type classification is uncertain, or only when a specific wound type can be identified? → A: Report with confidence per type
- Q: How should the system authenticate and authorize client connections to the WebSocket stream endpoint? → A: No need for authentication
 - Q: How should the system authenticate and authorize client connections to the WebSocket stream endpoint? → A: Require authentication by default (API key or JWT) with a configurable dev-mode toggle to disable auth for local/trusted environments

---

### Edge Cases

- What happens when the video stream frame rate exceeds the model's processing capacity (e.g., 60fps video but model can only process 10fps)? System drops intermediate frames to maintain realtime operation.
- How does the system handle extremely large video frames (e.g., 4K resolution) that may slow down processing? Maximum supported resolution is 1280x720 (720p); frames exceeding this should be rejected or downscaled by the client.
- What happens if the same wound appears across consecutive frames - is it tracked as the same wound or reported as new detections?
- How does the system behave when the video contains faces with wounds vs wounds on other body parts?
- What happens if network latency causes frames to arrive out of order?
- How are frames prioritized if a backlog develops (drop frames, queue, or adaptive sampling)? System drops frames, always processing the most recent available frame.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept incoming video streams through a dedicated API endpoint that supports continuous data transmission (not batch file upload)
- **FR-002**: System MUST extract individual frames from the incoming video stream in realtime as data arrives
- **FR-003**: System MUST analyze each extracted frame using a custom-trained wound detection model capable of identifying wound characteristics
- **FR-004**: System MUST return wound detection results as a continuous data stream (not as a single response at stream end)
- **FR-005**: System MUST include in each detection result: frame timestamp/index, wound presence indicator (boolean), wound location (bounding box coordinates), detection confidence score, wound type classification, and type classification confidence score
- **FR-006**: System MUST use WebSocket protocol for bidirectional stream communication, where the client sends video frames and simultaneously receives detection results in real time
- **FR-007**: System MUST process frames in the order they are received to maintain temporal consistency
- **FR-008**: System MUST handle graceful connection termination from either client or server side without data loss for already-processed frames
- **FR-009**: System MUST provide frame-level detection results within 500ms of frame receipt under normal processing conditions
- **FR-010**: System MUST support at least 5-10 concurrent stream connections from multiple clients simultaneously
- **FR-011**: System MUST classify detected wounds by type (e.g., cut, bruise, burn, abrasion) and include a separate type classification confidence score for each detection, allowing users to assess both detection and classification certainty independently
- **FR-011a**: System MUST only report wound detections with confidence scores of 0.5 (50%) or higher to balance sensitivity with false positive reduction
- **FR-012**: System MUST handle variable frame rates from client streams (common video frame rates: 15, 24, 30, 60 fps)
- **FR-012a**: System MUST drop intermediate frames when processing capacity is exceeded, always prioritizing the most recent frame to maintain realtime operation and low latency
- **FR-013**: System MUST accept raw frames as individual JPEG or PNG images transmitted over the stream
- **FR-013a**: System MUST support video frames up to 1280x720 (720p) resolution to balance image detail with realtime processing performance
- **FR-014**: System MUST log all stream sessions with session ID, start/end times, frame count, and detection summary for audit purposes

- **FR-015**: System MUST require authenticated clients for the WebSocket API (API key or JWT). Authentication MAY be disabled via a configurable "dev-mode" flag for local or trusted deployments; production deployments MUST enable authentication.

### Key Entities

- **VideoStream**: Represents an active streaming connection from a client, containing stream metadata (session ID, start time, frame rate, resolution), connection status, and associated detection results
- **Frame**: Individual video frame extracted from stream, containing raw image data, frame sequence number, timestamp relative to stream start, and processing status
- **WoundDetection**: Result of analyzing a single frame, containing frame reference, detection timestamp, array of detected wounds (if any), and overall frame quality assessment
- **Wound**: Individual wound identified in a frame, containing bounding box coordinates (x, y, width, height), wound type classification, detection confidence score (0.0-1.0), type classification confidence score (0.0-1.0), and unique identifier within the frame

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clients receive first wound detection result within 500ms of sending the first frame containing a wound
- **SC-002**: System maintains realtime processing for video streams up to 30 frames per second without frame dropping or buffering delays exceeding 1 second
- **SC-003**: Detection accuracy matches or exceeds the standalone model's performance (wound detection recall rate ≥ 85% and precision ≥ 80% on test dataset)
- **SC-004**: System successfully processes video streams lasting up to 5 minutes continuously without connection failures or memory leaks
- **SC-005**: End-to-end latency (time from client sending frame to client receiving detection result) remains under 1 second for 95% of frames under normal network conditions
- **SC-006**: System handles at least 5 concurrent video streams simultaneously without degrading per-stream processing time by more than 20%
- **SC-007**: Detection results include all required data fields (timestamp, bounding box, detection confidence, wound type, type confidence) for 100% of positive detections

## Assumptions

- The custom wound detection model is already trained and available as a loadable model file (e.g., YOLOv8 weights)
- Client applications are responsible for video capture and encoding; the server focuses on analysis
- WebSocket protocol will be used for bidirectional streaming of video frames and detection results
- Server has sufficient computational resources (GPU preferred) to run the wound detection model in realtime
- Frames are analyzed independently; no temporal tracking of wounds across frames is required in v1
- A confidence threshold of 0.5 (50%) will be used to filter wound detections, balancing sensitivity with precision
- Authentication is required by default: the system MUST require authenticated clients (API key or JWT). A configurable "dev-mode" toggle may disable authentication for local or trusted deployments; production deployments MUST enable authentication.
- Video streams are expected to be relatively short (under 10 minutes) for typical use cases; long-running surveillance scenarios are out of scope
- Default behavior when processing falls behind: drop frames to maintain realtime behavior rather than queuing all frames

## Out of Scope

- Video recording/storage of incoming streams (analysis only, not archival)
- Historical analysis of pre-recorded video files (focus is on realtime streaming)
- Wound tracking across frames (identifying same wound in multiple frames)
- Integration with electronic health records (EHR) or medical databases
- User interface for initiating or viewing streams (API-only feature)
- Video preprocessing like stabilization, enhancement, or color correction
- Multi-angle or 3D wound reconstruction from multiple video streams
- Automatic wound measurement (size, depth) beyond detection and classification
