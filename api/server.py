import asyncio
import logging
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from api.session import SessionRegistry
from tracks.audio_observer import AudioObserverTrack
from tracks.video_observer import VideoObserverTrack
from config.constants import DETECTIONS_CHANNEL_LABEL

logger = logging.getLogger("yolo_rest.api.server")

session_registry = SessionRegistry()
pcs: set[RTCPeerConnection] = set()

async def offer(request):
    params = await request.json()
    
    correlation_id = params["correlationId"]
    logger.info(f"[{correlation_id}] Received WebRTC offer request")
    
    offer = RTCSessionDescription(
        sdp=params["sdp"],
        type=params["type"]
    )

    pc = RTCPeerConnection()
    pcs.add(pc)
    
    session = session_registry.create(correlation_id)

    @pc.on("track")
    def on_track(track):
        logger.info(f"[{correlation_id}] Track received: kind={track.kind}")
        if track.kind == AudioObserverTrack.kind:
            observer = AudioObserverTrack(track, session)
            pc.addTrack(observer)
            logger.info(f"[{correlation_id}] AudioObserverTrack attached")

        elif track.kind == VideoObserverTrack.kind:
            observer = VideoObserverTrack(track, session)
            pc.addTrack(observer)
            logger.info(f"[{correlation_id}] VideoObserverTrack attached")

    @pc.on("datachannel")
    def on_datachannel(channel):
        logger.info(f"[{correlation_id}] Data channel received: label={channel.label}")
        if channel.label == DETECTIONS_CHANNEL_LABEL:
            session.attach_data_channel(channel)
            logger.info(f"[{correlation_id}] Data channel attached to session")
        else:
            logger.info(f"[{correlation_id}] Data channel label does not match expected: {DETECTIONS_CHANNEL_LABEL}")
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(
            f"Connection state change [{correlation_id}]: {pc.connectionState}"
        )

        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            pcs.discard(pc)
            session_registry.close(correlation_id)
            logger.info(f"Session closed: {correlation_id}")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    logger.info(f"[{correlation_id}] WebRTC answer created and local description set")

    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


async def on_shutdown(app):
    logger.info(f"Shutting down WebRTC server, closing {len(pcs)} peer connections")
    await asyncio.gather(*(pc.close() for pc in pcs))
    pcs.clear()
    
    session_count = len(session_registry.all())
    logger.info(f"Closing {session_count} active sessions")
    for session in session_registry.all():
        session.close()
    logger.info("WebRTC server shutdown complete")