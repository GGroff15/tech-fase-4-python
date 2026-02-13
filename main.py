import aiohttp_cors
import logging
from dotenv import load_dotenv

load_dotenv()

from config import constants
from utils.logging_config import configure_logging

configure_logging(level=constants.LOG_LEVEL)

logger = logging.getLogger("yolo_rest.main")

from aiohttp import web
from api import health, server


app = web.Application()
app.add_routes(health.router)
app.router.add_post("/offer", server.offer)
app.on_shutdown.append(server.on_shutdown)

cors = aiohttp_cors.setup(app, defaults={
	"*": aiohttp_cors.ResourceOptions(
		allow_credentials=False,
		expose_headers="*",
		allow_headers="*",
		allow_methods=["GET", "POST", "OPTIONS"],
	)
})
for route in list(app.router.routes()):
	try:
		cors.add(route.resource)
	except Exception:
		pass

# Log startup configuration
logger.info("=" * 60)
logger.info("🚀 YOLO-REST WebRTC Server Starting")
logger.info("=" * 60)
logger.info(f"Host: {constants.DEFAULT_SERVER_HOST}")
logger.info(f"Port: {constants.SERVER_PORT}")
logger.info(f"Log Level: {constants.LOG_LEVEL}")
logger.info(f"Video FPS: {constants.VIDEO_FPS}")
logger.info(f"Roboflow API: {'Configured' if constants.ROBOFLOW_API_KEY else 'Not configured'}")
logger.info("=" * 60)

web.run_app(app, host=constants.DEFAULT_SERVER_HOST, port=constants.SERVER_PORT)
