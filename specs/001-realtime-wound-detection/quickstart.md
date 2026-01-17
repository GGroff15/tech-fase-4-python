# Quick Start: Realtime Wound Detection Stream

Get the wound detection WebSocket stream running in 5 minutes.

## Prerequisites

- Python 3.11+
- Roboflow account with trained wound detection model
- 4GB RAM minimum (8GB recommended)
- Optional: NVIDIA GPU with CUDA for local fallback

## 1. Environment Setup

```bash
# Clone repository (if not already)
git clone <repository-url>
cd yolo-rest

# Checkout feature branch
git checkout 001-realtime-wound-detection

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

Create `.env` file in project root:

```env
# Roboflow Configuration (REQUIRED)
ROBOFLOW_API_KEY=your_api_key_here
ROBOFLOW_WORKSPACE=your_workspace_name
ROBOFLOW_PROJECT=wound-detection
ROBOFLOW_VERSION=1

# Server Configuration (OPTIONAL - defaults shown)
MAX_CONCURRENT_STREAMS=10
CONFIDENCE_THRESHOLD=0.5
MAX_FRAME_WIDTH=1280
MAX_FRAME_HEIGHT=720
IDLE_TIMEOUT_SEC=30
MAX_FRAME_SIZE_MB=10

# Logging (OPTIONAL)
LOG_LEVEL=INFO
```

### Get Roboflow Credentials

1. Sign up at [roboflow.com](https://roboflow.com)
2. Upload and train wound detection model (or use existing project)
3. Get API key from Settings → API Keys
4. Find workspace name, project name, and version number in project URL:
   ```
   https://app.roboflow.com/{workspace}/{project}/{version}
   ```

## 3. Start Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 4. Test Connection

### Using Python

Create `test_client.py`:

```python
import asyncio
import websockets
import json

async def test_stream():
    uri = "ws://localhost:8000/ws/analyze-stream"
    
    async with websockets.connect(uri) as websocket:
        # Receive session started message
        session_msg = await websocket.recv()
        print("Session:", json.loads(session_msg))
        
        # Send test frame
        with open("sample_frame.jpg", "rb") as f:
            frame_data = f.read()
        
        await websocket.send(frame_data)
        print("Frame sent")
        
        # Receive detection result
        result_msg = await websocket.recv()
        result = json.loads(result_msg)
        print(f"Result: {result['has_wounds']} wounds detected")
        print(json.dumps(result, indent=2))
        
        # Close connection
        await websocket.close()

if __name__ == "__main__":
    asyncio.run(test_stream())
```

Run:
```bash
python test_client.py
```

### Using Browser Console

```javascript
// Open browser console at http://localhost:8000
const ws = new WebSocket('ws://localhost:8000/ws/analyze-stream');

ws.onopen = () => {
    console.log('Connected');
};

ws.onmessage = (event) => {
    console.log('Received:', JSON.parse(event.data));
};

// Send frame (from file input)
document.getElementById('fileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = () => {
        ws.send(reader.result);
    };
    reader.readAsArrayBuffer(file);
});
```

### Using wscat

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/ws/analyze-stream

# You'll see session_started message
# Send binary frame (not supported in wscat - use Python/browser)
```

## 5. Send Real Frames

### Continuous Webcam Stream

Create `webcam_stream.py`:

```python
import asyncio
import websockets
import cv2
import json

async def stream_webcam():
    uri = "ws://localhost:8000/ws/analyze-stream"
    
    async with websockets.connect(uri) as websocket:
        # Receive session info
        session_msg = await websocket.recv()
        session = json.loads(session_msg)
        print(f"Connected to session: {session['session_id']}")
        
        # Open webcam
        cap = cv2.VideoCapture(0)
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                
                # Send frame
                await websocket.send(frame_bytes)
                
                # Receive detection result (non-blocking)
                try:
                    result_msg = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=0.1
                    )
                    result = json.loads(result_msg)
                    
                    if result.get('has_wounds'):
                        print(f"⚠️  Frame {result['frame_index']}: "
                              f"{len(result['wounds'])} wound(s) detected!")
                    else:
                        print(f"✓ Frame {result['frame_index']}: No wounds")
                        
                except asyncio.TimeoutError:
                    pass  # No result yet, continue
                
                # Control frame rate (10 FPS)
                await asyncio.sleep(0.1)
                
        finally:
            cap.release()
            await websocket.close()

if __name__ == "__main__":
    asyncio.run(stream_webcam())
```

Run:
```bash
python webcam_stream.py
```

## 6. Verify Setup

### Check Health Endpoint

```bash
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

### Check Roboflow Connection

```bash
curl http://localhost:8000/health/roboflow

# Expected response:
# {"status": "connected", "model": "wound-detection", "version": 1}
```

## Expected Results

**Detection Response Example**:
```json
{
  "event_type": "detection_result",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "frame_index": 0,
  "timestamp_ms": 234.56,
  "has_wounds": true,
  "wounds": [
    {
      "wound_id": 0,
      "bbox": {"x": 0.45, "y": 0.32, "width": 0.12, "height": 0.08},
      "wound_type": "cut",
      "detection_confidence": 0.87,
      "type_confidence": 0.82
    }
  ],
  "metadata": {
    "processing_time_ms": 245.3,
    "quality_warning": null,
    "frames_dropped_since_last": 0
  }
}
```

## Troubleshooting

### Connection Refused
- Check server is running: `ps aux | grep uvicorn`
- Check port 8000 not in use: `netstat -an | grep 8000`
- Try: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`

### "503 Service Unavailable"
- Too many concurrent connections (>10)
- Wait for others to disconnect or increase `MAX_CONCURRENT_STREAMS`

### "INFERENCE_FAILED" Errors
- Check Roboflow API key is valid
- Check internet connection
- Verify project/version exists in Roboflow dashboard
- Check API usage limits not exceeded

### Slow Detection (<500ms target not met)
- Check `processing_time_ms` in response
- Roboflow API latency depends on network/server load
- Consider local YOLOv8 fallback for faster inference
- Reduce frame rate if sending too fast

### Invalid Frame Format Errors
- Ensure frames are valid JPEG or PNG
- Check frame size <10MB
- Verify JPEG quality not too low (recommend 80-95)

## Next Steps

- Review [WebSocket API Contract](contracts/websocket-api.md) for full protocol details
- See [Data Model](data-model.md) for entity structure
- Read [Research](research.md) for implementation decisions
- Check [Plan](plan.md) for architecture overview

## Production Deployment

```bash
# Install production ASGI server
pip install gunicorn

# Run with Gunicorn + Uvicorn workers
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

**Production Checklist**:
- [ ] Set strong `ROBOFLOW_API_KEY` via environment variable
- [ ] Enable HTTPS/WSS with reverse proxy (nginx/traefik)
- [ ] Set up log aggregation (ELK, Datadog, CloudWatch)
- [ ] Configure monitoring/alerts for health endpoints
- [ ] Adjust `MAX_CONCURRENT_STREAMS` based on server capacity
- [ ] Set up backup/fallback Roboflow workspace
- [ ] Document network security requirements (if internal deployment)
- [ ] Consider rate limiting per client IP
- [ ] Set up automated backups of configuration
