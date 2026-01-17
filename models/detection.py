from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class Wound:
    id: int
    cls: str
    bbox: List[float]  # [x, y, w, h]
    confidence: float
    type_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WoundDetection:
    frame_index: int
    timestamp_ms: int
    wounds: List[Wound]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_ms": self.timestamp_ms,
            "wounds": [w.to_dict() for w in self.wounds],
        }
