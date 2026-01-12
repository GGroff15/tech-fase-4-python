import tempfile

import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

async def analyze_video(video, frames_per_second: int):
    video_bytes = await video.read()
    temporary_file = tempfile.TemporaryFile(suffix=video.filename)
    temporary_file.write(video_bytes)

    video_cap = cv2.VideoCapture(temporary_file.name)

    if not video_cap.isOpened():
        temporary_file.close()
        return {"error": "Could not open video file."}

    video_fps = video_cap.get(cv2.CAP_PROP_FPS)

    if frames_per_second is None or frames_per_second <= 0:
        frames_per_second = 1

    if not video_fps or video_fps <= 0:
        frame_interval = 1
    else:
        frame_interval = max(1, int(round(video_fps / frames_per_second)))

    frame_index = 0
    detections = []

    while True:
        ret, frame = video_cap.read()
        if not ret:
            break

        if frame_index % frame_interval == 0:
            for r in model.predict(source=frame, stream=True):
                for box in r.boxes:
                    detections.append({
                        "label": r.names[int(box.cls)],
                        "confidence": float(box.conf),
                        "timestamp": video_cap.get(cv2.CAP_PROP_POS_MSEC)
                    })

        frame_index += 1

    video_cap.release()
    temporary_file.close()
    return detections
