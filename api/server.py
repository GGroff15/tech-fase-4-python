import asyncio
import json
import logging
from time import time
from typing import Any, Optional
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay

from stream.frame_buffer import BaseBuffer, FrameBuffer, AudioBuffer
from stream.frame_processor import BaseProcessor, VideoProcessor
from stream.audio_processor import AudioProcessor
from stream.session import StreamSession

logger = logging.getLogger("yolo_rest.server")

# Constants
MAX_RESOLUTION = "1280x720"
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_IDLE_TIMEOUT_SEC = 30
DATA_CHANNEL_INIT_DELAY = 0.1
DETECTIONS_CHANNEL_LABEL = "detections"

relay = MediaRelay()
router = web.RouteTableDef()
peer_connections = set()  # Track active peer connections for cleanup

class WebRTCConnectionHandler:
    """Handles WebRTC peer connection lifecycle and track processing."""

    def __init__(self, peer_connection: RTCPeerConnection):
        self.peer_connection = peer_connection
        self.data_channel: Optional[Any] = None
        self.session: StreamSession = StreamSession()
        self.processor: Optional[BaseProcessor] = None

    def setup_data_channel_handler(self) -> None:
        """Configure data channel event handler."""
        @self.peer_connection.on("datachannel")
        def on_datachannel(channel: Any) -> None:
            if channel.label == DETECTIONS_CHANNEL_LABEL:
                self.data_channel = channel
                logger.info(f"DataChannel '{DETECTIONS_CHANNEL_LABEL}' connected")

    def setup_track_handler(self) -> None:
        """Configure track event handler."""
        @self.peer_connection.on("track")
        def on_track(track: MediaStreamTrack) -> None:
            logger.info(f"Track {track.kind} received")
            local_track = relay.subscribe(track)
            logger.info(f"Track connection established: {track.kind} track ready for processing")
            self._handle_track(track, local_track)

    def _handle_track(self, original_track: MediaStreamTrack, local_track: MediaStreamTrack) -> None:
        """Initialize session and start frame processing for a track."""
        # Route by track kind: use a specialized buffer/processor for audio
        if getattr(local_track, "kind", None) == "audio":
            logger.info("Starting audio processor for audio track")
            buffer = AudioBuffer()
            self.processor = AudioProcessor(buffer, self.session)
        else:
            buffer = FrameBuffer()
            self.processor = VideoProcessor(buffer, self.session)

        async def emitter(event: dict[str, Any]) -> None:
            await self._emit_event(event)

        self.processor.start(emitter)
        asyncio.ensure_future(self._send_session_init())
        asyncio.ensure_future(self._buffer_frames(local_track, buffer))

        @original_track.on("ended")
        async def on_ended() -> None:
            await self._handle_track_ended()

    async def _emit_event(self, event: dict[str, Any]) -> None:
        """Emit event through data channel if available and open."""
        logger.debug(f"Emitting event: {event}")
        if not self.data_channel:
            return
        if self.data_channel.readyState != "open":
            return
        self.data_channel.send(json.dumps(event))

    async def _send_session_init(self) -> None:
        """Send session initialization message to client."""
        await asyncio.sleep(DATA_CHANNEL_INIT_DELAY)
        if self.data_channel and self.data_channel.readyState == "open":
            init_event = {
                "event_type": "session_started",
                "session_id": self.session.session_id,
                "timestamp_ms": int(time() * 1000),
                "config": {
                    "max_resolution": MAX_RESOLUTION,
                    "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
                    "idle_timeout_sec": DEFAULT_IDLE_TIMEOUT_SEC
                }
            }
            self.data_channel.send(json.dumps(init_event))

    async def _buffer_frames(self, track: MediaStreamTrack, buffer: BaseBuffer) -> None:
        """Read frames from track and add to buffer."""
        try:
            while True:
                frame = await track.recv()
                await buffer.put(frame)
        except Exception as error:
            logger.info(f"Track ended or error: {error}")

    async def _handle_track_ended(self) -> None:
        """Handle track end by stopping processor and sending summary."""
        logger.info("Track ended")
        if self.processor:
            await self.processor.stop()
        
        summary = self.session.close()

        if self.data_channel and self.data_channel.readyState == "open":
            summary_event = {
                "event_type": "stream_closed",
                "session_id": self.session.session_id,
                "summary": {
                    "total_frames_received": summary.get("total_received", 0),
                    "total_frames_processed": summary.get("frame_count", 0),
                    "total_frames_dropped": self.session.dropped_count,
                    "total_detections": self.session.detection_count,
                    "duration_sec": summary.get("duration", 0)
                }
            }
            self.data_channel.send(json.dumps(summary_event))
        
        # Close peer connection and remove from tracking
        await self._cleanup()
    
    async def _cleanup(self) -> None:
        """Clean up peer connection resources."""
        try:
            if self.peer_connection in peer_connections:
                peer_connections.remove(self.peer_connection)
            await self.peer_connection.close()
            logger.info(f"Peer connection closed, session_id: {self.session.session_id}")
        except Exception as error:
            logger.error(f"Error during cleanup: {error}")


@router.get("/")
async def index(request):
    with open("api/index.html", "r") as f:
        return web.Response(content_type="text/html", text=f.read())


@router.get('/webrtc-client.js')
async def webrtc_client_js(request):
    """Serve the external WebRTC client JavaScript file."""
    try:
        with open("api/webrtc-client.js", "r", encoding="utf-8") as f:
            return web.Response(content_type="application/javascript", text=f.read())
    except FileNotFoundError:
        return web.Response(status=404, text="// webrtc-client.js not found")


@router.get('/styles.css')
async def styles_css(request):
    """Serve the page stylesheet."""
    try:
        with open("api/styles.css", "r", encoding="utf-8") as f:
            return web.Response(content_type="text/css", text=f.read())
    except FileNotFoundError:
        return web.Response(status=404, text="/* styles.css not found */")


@router.get('/favicon.ico')
async def favicon(request):
    """Serve favicon if present (returns 404 if missing)."""
    try:
        with open("api/favicon.ico", "rb") as f:
            data = f.read()
            return web.Response(body=data, content_type="image/x-icon")
    except FileNotFoundError:
        return web.Response(status=404, text="")

@router.post("/offer")
async def offer(request: web.Request) -> web.Response:
    """Handle WebRTC offer and create peer connection."""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    peer_connection = RTCPeerConnection()
    peer_connections.add(peer_connection)  # Track for cleanup
    
    handler = WebRTCConnectionHandler(peer_connection)
    handler.setup_data_channel_handler()
    handler.setup_track_handler()

    await peer_connection.setRemoteDescription(offer)
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)
    
    logger.info(f"WebRTC peer connection established, session_id: {handler.session.session_id}")

    return web.json_response({
        "sdp": peer_connection.localDescription.sdp,
        "type": peer_connection.localDescription.type
    })


async def on_shutdown(app: web.Application) -> None:
    """Clean up all peer connections on server shutdown."""
    logger.info("Shutting down, closing all peer connections...")
    close_tasks = [pc.close() for pc in peer_connections]
    await asyncio.gather(*close_tasks, return_exceptions=True)
    peer_connections.clear()
    logger.info("All peer connections closed")