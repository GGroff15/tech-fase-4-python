import sys
from ultralytics import YOLO

model = YOLO("")

# Realiza a predição
results = model(input_path, conf=conf)
# Exibe os resultados
for result in results:
    print(f"Frame: {getattr(result, 'frame', 'N/A')}")
    for box in result.boxes:
        print({
            "class": int(box.cls[0]),
            "confidence": float(box.conf[0]),
            "bbox": box.xyxy[0].tolist()
        })
