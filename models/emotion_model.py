import logging
import torch
import numpy as np
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification
from config.constants import EMOTION_MODEL_ID, HUGGING_FACE_API_KEY

logger = logging.getLogger("yolo_rest.models.emotion_model")


class SpeechEmotionModel:
    def __init__(self):
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing SpeechEmotionModel with device: {self._device}")

        try:
            logger.info(f"Loading emotion model: {EMOTION_MODEL_ID}")
            self._processor = Wav2Vec2FeatureExtractor.from_pretrained(
                EMOTION_MODEL_ID,
                token=HUGGING_FACE_API_KEY or None
            )
            self._model = Wav2Vec2ForSequenceClassification.from_pretrained(
                EMOTION_MODEL_ID,
                token=HUGGING_FACE_API_KEY or None
            ).to(self._device)

            self._model.eval()
            logger.info(f"SpeechEmotionModel loaded successfully: {EMOTION_MODEL_ID}")
        except Exception as e:
            logger.error(f"Failed to load SpeechEmotionModel: {e}")
            raise

    @torch.no_grad()
    def predict(self, pcm16: bytes) -> tuple[str, float]:
        try:
            logger.info(f"Running emotion prediction on audio buffer: size={len(pcm16)} bytes")
            
            waveform = (
                np.frombuffer(pcm16, dtype=np.int16)
                .astype(np.float32) / 32768.0
            )

            inputs = self._processor(
                waveform,
                sampling_rate=16_000,
                return_tensors="pt"
            )

            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            outputs = self._model(**inputs)
            logits = outputs.logits

            probs = torch.softmax(logits, dim=-1)[0]
            confidence, idx = torch.max(probs, dim=0)

            emotion = self._model.config.id2label[idx.item()]
            confidence_value = round(confidence.item(), 3)
            
            logger.info(f"Emotion prediction completed: emotion={emotion}, confidence={confidence_value}")

            return emotion, confidence_value
        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            raise
