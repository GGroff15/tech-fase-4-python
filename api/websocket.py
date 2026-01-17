import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from stream.session import StreamSession
from stream.frame_buffer import FrameBuffer
from stream.frame_processor import FrameProcessor

router = APIRouter()
logger = logging.getLogger("yolo_rest.websocket")


@router.websocket("/ws/analyze")
async def analyze_ws(websocket: WebSocket):
    """Accept binary frames from client and emit JSON detection events.

    This is a minimal handler (placeholder inference). Real pipeline will
    connect to frame buffer and inference components.
    """

    logger.info("client_connected", extra={"session_id": None})
    await websocket.accept()

    # Create session, buffer and processor
    session = StreamSession()
    buffer = FrameBuffer()
    processor = FrameProcessor(buffer, session)

    async def emitter(event: dict):
        await websocket.send_json(event)

    # start processor
    processor.start(emitter)

    try:
        while True:
            logger.info("awaiting_frame", extra={"session_id": session.session_id})
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("type") == "websocket.receive":
                logger.info("frame_received", extra={"session_id": session.session_id})
                if "bytes" in msg:
                    data = msg.get("bytes")
                    # record received and push latest frame into buffer
                    try:
                        session.record_received()
                    except Exception:
                        pass
                    dropped = await buffer.put(data)
                    if dropped:
                        try:
                            session.record_dropped(1)
                        except Exception:
                            pass
                else:
                    # ignore text messages for now
                    continue

    except WebSocketDisconnect:
        logger.info("client_disconnected", extra={"session_id": session.session_id})
    except Exception as e:
        logger.exception("websocket_error", extra={"session_id": session.session_id, "error": str(e)})
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:

        # stop processor and close session
        await processor.stop()
        summary = session.close()
        # enhance summary format per contract
        summary_payload = {
            "total_frames_received": summary.get("total_received", session.total_received),
            "total_frames_processed": summary.get("frame_count", session.frame_count),
            "total_frames_dropped": session.dropped_count,
            "total_detections": session.detection_count,
            "duration_sec": round((session.end_time - session.start_time) if session.end_time and session.start_time else 0, 2),
        }
        try:
            await websocket.send_json({"event": "stream_closed", "summary": summary_payload})
        except Exception:
            pass
