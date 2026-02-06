import asyncio
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from api.session import SessionRegistry
from tracks.audio_observer import AudioObserverTrack
from tracks.video_observer import VideoObserverTrack
from config.constants import DETECTIONS_CHANNEL_LABEL


session_registry = SessionRegistry()
pcs: set[RTCPeerConnection] = set()

async def offer(request):
    params = await request.json()
    
    correlation_id = params["correlationId"]
    offer = RTCSessionDescription(
        sdp=params["sdp"],
        type=params["type"]
    )

    pc = RTCPeerConnection()
    pcs.add(pc)
    
    session = session_registry.create(correlation_id)

    @pc.on("track")
    def on_track(track):
        if track.kind == AudioObserverTrack.kind:
            pc.addTrack(AudioObserverTrack(track, session))

        elif track.kind == VideoObserverTrack.kind:
            pc.addTrack(VideoObserverTrack(track, session))

    @pc.on("datachannel")
    def on_datachannel(channel):
        if channel.label == DETECTIONS_CHANNEL_LABEL:
            session.attach_data_channel(channel)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(
            f"🔄 [{correlation_id}] state = {pc.connectionState}"
        )

        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            pcs.discard(pc)
            session_registry.close(correlation_id)
            print(f"🔴 Session closed: {correlation_id}")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


async def on_shutdown(app):
    await asyncio.gather(*(pc.close() for pc in pcs))
    pcs.clear()
    for session in session_registry.all():
        session.close()