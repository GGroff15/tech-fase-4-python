import cv2
from ultralytics import YOLO # type: ignore

# modelo YOLOv8 (pode ser treinado depois)
model = YOLO("yolov8n.pt")

def analyze_video(video_path):
    cap = cv2.VideoCapture(video_path)
    anomalies = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)

        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                # EXEMPLO DE REGRA SIMPLES DE ANOMALIA
                if conf > 0.6:
                    anomalies.append({
                        "confidence": conf,
                        "class": cls
                    })

    cap.release()
    return anomalies
