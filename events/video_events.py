class VisionEvent:
    
    def __init__(self, confidence: float, frameIndex, label) -> None:
        self.confidence = confidence
        self.frameIndex = frameIndex
        self.label = label
        
    def to_dict(self) -> dict:
        return {
            "confidence": self.confidence,
            "frameIndex": self.frameIndex,
            "label": self.label,
        }