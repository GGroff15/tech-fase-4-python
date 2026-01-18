from aiohttp import web
import os

router = web.RouteTableDef()


@router.get("/health")
async def health(request):
    return web.json_response({"status": "ok"})

@router.get("/ready")
async def ready(request):
    # Basic readiness check: ensure required env vars are present (placeholder)
    missing = []
    if not os.getenv("ROBOFLOW_API_KEY"):
        missing.append("ROBOFLOW_API_KEY")
    return web.json_response({"ready": len(missing) == 0, "missing": missing})
