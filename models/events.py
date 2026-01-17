from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class WoundModel(BaseModel):
    id: int
    cls: str
    bbox: List[float]
    confidence: float
    type_confidence: float


class DetectionEvent(BaseModel):
    session_id: str
    timestamp_ms: int
    frame_index: int
    has_wounds: bool
    wounds: List[WoundModel]
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
