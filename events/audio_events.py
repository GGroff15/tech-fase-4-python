from typing import Optional


class TranscriptionEvent:
    
    def __init__(
        self,
        text: str,
        confidence: float,
        start_time: str,
        end_time: str,
    ):
        self.text = text
        self.confidence = confidence
        self.start_time = start_time
        self.end_time = end_time
        
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "startTime": self.start_time,
            "endTime": self.end_time,
        }
        
class EmotionEvent:
    
    def __init__(self, emotion: str, confidence: float, timestamp: str):
        self.emotion = emotion
        self.confidence = confidence
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "emotion": self.emotion,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }