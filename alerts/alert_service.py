def generate_alert(video_anomalies, audio_result):
    alerts = []

    if len(video_anomalies) > 0:
        alerts.append("Possível anomalia visual detectada")

    if audio_result["risk_score"] > 0.5:
        alerts.append("Possível risco psicológico detectado")

    return alerts
