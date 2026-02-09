import torch
from ultralytics import YOLO
from config import constants


class YoloV8Model:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = constants.YOLO_MODEL_PATH
        self._model = YOLO(model_path)
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def predict(self, image_bgr):
        results = self._model(
            image_bgr,
            imgsz=constants.YOLO_IMAGE_SIZE,
            conf=constants.YOLO_CONFIDENCE,
            device=self._device,
            verbose=False
        )

        detections = results[0]
        labels = []
        confidences = []

        for box in detections.boxes:
            cls_id = int(box.cls[0])
            labels.append(self._model.names[cls_id])
            confidences.append(float(box.conf[0]))

        return labels, confidences
