import numpy as np
from fastapi import FastAPI, UploadFile
from ultralytics import YOLO
import cv2

app = FastAPI()
model = YOLO("yolov8x-pose-p6.pt")

@app.post("/analyze-frame")
async def analyze_frame(frame: UploadFile):
    image_bytes = await frame.read()
    np_img = cv2.imdecode(
        np.frombuffer(image_bytes, np.uint8),
        cv2.IMREAD_COLOR
    )

    results = model(np_img)

    detections = []

    for r in results:
        for box in r.boxes:
            detections.append({
                "label": r.names[int(box.cls)],
                "confidence": float(box.conf),
                "bbox": {
                    "x": int(box.xyxy[0][0]),
                    "y": int(box.xyxy[0][1]),
                    "width": int(box.xyxy[0][2] - box.xyxy[0][0]),
                    "height": int(box.xyxy[0][3] - box.xyxy[0][1])
                }
            })

    return {"detections": detections}