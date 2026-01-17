from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    # Basic readiness check: ensure required env vars are present (placeholder)
    missing = []
    if not os.getenv("ROBOFLOW_API_KEY"):
        missing.append("ROBOFLOW_API_KEY")
    return {"ready": len(missing) == 0, "missing": missing}
