import aiohttp_cors
from dotenv import load_dotenv

load_dotenv()

from utils.logging_config import configure_logging

configure_logging()

from aiohttp import web
from api import health, server


app = web.Application()
app.add_routes(health.router)
app.router.add_post("/offer", server.offer)
app.on_shutdown.append(server.on_shutdown)

cors = aiohttp_cors.setup(app, defaults={
	"*": aiohttp_cors.ResourceOptions(
		allow_credentials=True,
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

web.run_app(app, host="0.0.0.0", port=8000)
