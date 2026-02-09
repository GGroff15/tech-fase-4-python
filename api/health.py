import os
from pathlib import Path

from aiohttp import web
from config import constants

router = web.RouteTableDef()


@router.get("/health")
async def health(request):
    """Basic liveness probe - always returns ok if the server is running."""
    return web.json_response({"status": "ok"})


@router.get("/ready")
async def ready(request):
    """Readiness probe - validates critical dependencies are available."""
    checks = {}
    ready = True
    
    # Check Roboflow API key is configured
    if not constants.ROBOFLOW_API_KEY:
        checks["roboflow_api_key"] = "missing"
        ready = False
    else:
        checks["roboflow_api_key"] = "ok"
    
    # Check YOLO model file exists
    model_path = Path(constants.YOLO_MODEL_PATH)
    if model_path.exists():
        checks["yolo_model"] = "ok"
    else:
        checks["yolo_model"] = f"missing: {constants.YOLO_MODEL_PATH}"
        ready = False
    
    # Check event forwarding is configured (if API_KEY is set)
    if constants.API_KEY:
        checks["event_forwarding"] = "configured"
    else:
        checks["event_forwarding"] = "not_configured"
        # Not marking as not ready since event forwarding might be optional
    
    status_code = 200 if ready else 503
    return web.json_response(
        {"ready": ready, "checks": checks},
        status=status_code
    )
