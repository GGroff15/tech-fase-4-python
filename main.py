from video.video_analysis import analyze_video
from audio.audio_analysis import analyze_audio
from alerts.alert_service import generate_alert

VIDEO_PATH = "sample_video.mp4"
AUDIO_PATH = "sample_audio.wav"

video_result = analyze_video(VIDEO_PATH)
audio_result = analyze_audio(AUDIO_PATH)

alerts = generate_alert(video_result, audio_result)

print(f"Total de eventos visuais detectados: {len(video_result)}")

print("ALERTAS GERADOS:")
for alert in alerts:
    print("-", alert)



