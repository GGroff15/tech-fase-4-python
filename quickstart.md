# Quickstart — yolo-rest (Realtime Wound Detection)

Prerequisites
- Python 3.11+ (recommended)
- Git
- Optional: GPU drivers + CUDA for local YOLO fallback

Install and run (local dev)

1. Create a virtual environment and activate it:

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set any values (optional):

```powershell
copy .env.example .env
# Edit .env to set ROBOFLOW_MODEL_URL / ROBOFLOW_API_KEY if using Roboflow
```

4. Run the app with Uvicorn:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Testing the WebSocket endpoint (example client)

Python example (send a JPEG file):

```python
import asyncio
import websockets

async def send_frame(path):
    uri = "ws://localhost:8000/ws/analyze"
    async with websockets.connect(uri) as ws:
        # receive session_started (if implemented)
        msg = await ws.recv()
        print(msg)
        with open(path, 'rb') as f:
            await ws.send(f.read())
        # receive detection
        resp = await ws.recv()
        print(resp)

asyncio.run(send_frame('sample_video.mp4'))
```

Quick notes
- By default the service will use a local Ultralytics model fallback if `ROBOFLOW_*` vars are not configured.
- For production, set `DEV_MODE_DISABLE_AUTH=false` and provide an API key or JWT middleware.
- See `specs/001-realtime-wound-detection/contracts/websocket-api.md` for the WebSocket contract.
