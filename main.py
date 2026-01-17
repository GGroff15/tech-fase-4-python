from fastapi import FastAPI
from api import websocket as ws_router, health

app = FastAPI()

app.include_router(ws_router.router)
app.include_router(health.router)