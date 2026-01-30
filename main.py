import aiohttp
import aiohttp_cors
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from utils.logging_config import configure_logging

configure_logging()

from aiohttp import web
from api import health, server



app = web.Application()
app.add_routes(health.router)
app.add_routes(server.router)
app.on_shutdown.append(server.on_shutdown)  # Register shutdown handler
# Configure CORS to allow requests from the Angular dev origin only
cors = aiohttp_cors.setup(app, defaults={
	"http://localhost:4200": aiohttp_cors.ResourceOptions(
		allow_credentials=False,
		expose_headers="*",
		allow_headers="*",
	)
})
# Attach CORS settings to all existing routes/resources
for route in list(app.router.routes()):
	try:
		cors.add(route.resource)
	except Exception:
		# Some internal routes/resources may not accept CORS attachment; ignore them
		pass
web.run_app(app, host="0.0.0.0", port=8000)
