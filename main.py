from fastapi import FastAPI, UploadFile, File, Form
from ultralytics import YOLO
from video.video_analysis import analyze_video

app = FastAPI()
model = YOLO("yolov8n-pose.pt")

@app.post("/analyze-video")
async def analyze_video_endpoint(video: UploadFile = File(...), frames_per_second: int = Form(1)):

    detections = await analyze_video(video, frames_per_second)

    return {"detections": detections}