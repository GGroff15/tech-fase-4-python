class VisionEvent:
    def __init__(self, confidence: float, frameIndex: int, label: str, x: float, y: float, width: float, height: float) -> None:
        self.confidence = confidence
        self.frameIndex = frameIndex
        self.label = label
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def to_dict(self) -> dict:
        return {
            "confidence": self.confidence,
            "frameIndex": self.frameIndex,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }