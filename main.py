from api import health, server
from aiohttp import web

from utils.logging_config import configure_logging

configure_logging()

app = web.Application()
app.add_routes(health.router)
app.add_routes(server.router)
app.on_shutdown.append(server.on_shutdown)  # Register shutdown handler
web.run_app(app, host="0.0.0.0", port=8000)