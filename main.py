from utils.logging_config import configure_logging

configure_logging()

from aiohttp import web
from api import health, server

app = web.Application()
app.add_routes(health.router)
app.add_routes(server.router)
app.on_shutdown.append(server.on_shutdown)  # Register shutdown handler
web.run_app(app, host="0.0.0.0", port=8000)
