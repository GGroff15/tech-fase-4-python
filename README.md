# YOLO-REST WebRTC Server

Real-time wound detection API using WebRTC, YOLOv8, and async Python. Accepts video/audio streams via WebRTC and emits detection events in real-time.

## Features

- 🎥 **Real-time Video Processing**: WebRTC-based streaming with YOLO wound detection
- 🎤 **Audio Analysis**: Google Speech-to-Text transcription + emotion detection
- 🚀 **Cloud-Ready**: Optimized for GCP Cloud Run deployment
- 🔧 **Highly Configurable**: 30+ environment variables for tuning
- 🔒 **Secure**: GCP Secret Manager integration, no hardcoded credentials
- 📊 **Production-Ready**: Health checks, structured logging, graceful shutdown

## Quick Start

### Local Development

```bash
# 1. Clone and setup
git clone <repository>
cd yolo-rest

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run server
python main.py
# Server starts on http://localhost:8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready
```

## Deployment

### Option 1: GitHub Actions (Recommended)

Automated CI/CD with testing, building, and deployment:

1. **Setup** (one-time):
   - Follow steps in [`.github/GITHUB_ACTIONS_SETUP.md`](.github/GITHUB_ACTIONS_SETUP.md)
   - Configure 4 GitHub secrets
   - Setup Workload Identity Federation

2. **Deploy**:
   ```bash
   # Automatic on push to main
   git push origin main
   
   # Or manual via GitHub UI
   # Actions → "Build and Deploy to Cloud Run" → Run workflow
   ```

**See [`.github/GITHUB_ACTIONS_SETUP.md`](.github/GITHUB_ACTIONS_SETUP.md) for detailed setup instructions.**

### Option 2: Cloud Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

### Option 3: Manual Deployment

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/yolo-rest:latest .

# Push to registry
docker push gcr.io/YOUR_PROJECT_ID/yolo-rest:latest

# Deploy to Cloud Run
gcloud run deploy yolo-rest \
  --image gcr.io/YOUR_PROJECT_ID/yolo-rest:latest \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4
```

**See [`DEPLOYMENT.md`](DEPLOYMENT.md) for comprehensive deployment guide.**

## Architecture

```
Client (Browser)
    ↓ WebRTC (video/audio)
[ Cloud Run / Local Server ]
    ├─→ Video Track → YOLOv8 Inference → Roboflow API
    │                      ↓
    │              Detection Events (WebRTC Data Channel)
    │
    └─→ Audio Track → Google STT → Transcription Events
                   └─→ Emotion Detection → Emotion Events
```

### Key Components

- **API Layer** ([`api/`](api/)): aiohttp server, WebRTC endpoint handlers
- **Video Processing** ([`tracks/video_observer.py`](tracks/video_observer.py)): Frame sampling, YOLO inference
- **Audio Processing** ([`audio/`](audio/)): VAD, Google STT, emotion detection
- **Models** ([`models/`](models/)): YOLOv8 and emotion classification models
- **Configuration** ([`config/constants.py`](config/constants.py)): Centralized environment variables

## Configuration

All configuration via environment variables. See [`.env.example`](.env.example) for complete list.

### Key Variables

```env
# Server
PORT=8080                              # Cloud Run injects this
LOG_LEVEL=INFO

# YOLO Model
YOLO_MODEL_PATH=yolov8n.pt
YOLO_CONFIDENCE=0.5
VIDEO_FPS=3

# Roboflow API
ROBOFLOW_API_KEY=your_key_here
ROBOFLOW_MODEL_ID=human-face-emotions/28

# Google Speech-to-Text
STT_LANGUAGE=pt-BR
STT_MAX_DURATION_SEC=240

# Event Forwarding
EVENT_FORWARD_BASE_URL=https://api.example.com
API_KEY=your_api_key
```

## Project Structure

```
yolo-rest/
├── api/                    # Web server and WebRTC handlers
├── audio/                  # Audio processing pipeline
├── config/                 # Configuration constants
├── events/                 # Event data models
├── models/                 # ML models (YOLO, emotion)
├── tracks/                 # WebRTC track observers
├── utils/                  # Logging, metrics, emitters
├── video/                  # Video processing utilities
├── .github/
│   ├── workflows/
│   │   └── deploy.yml     # GitHub Actions CI/CD
│   └── GITHUB_ACTIONS_SETUP.md  # Setup guide
├── Dockerfile             # Container definition
├── .dockerignore          # Build context exclusions
├── cloudbuild.yaml        # Cloud Build config
├── .env.example           # Configuration template
├── requirements.txt       # Python dependencies
├── main.py               # Application entry point
├── DEPLOYMENT.md         # Deployment guide
└── CLOUD_RUN_CHANGES.md  # Implementation summary
```

## Development

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/unit/test_frame_buffer.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Docker Development

```bash
# Build locally
docker build -t yolo-rest:dev .

# Run locally
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e ROBOFLOW_API_KEY=your_key \
  -e LOG_LEVEL=DEBUG \
  yolo-rest:dev

# Test
curl http://localhost:8080/health
```

### Code Style

```bash
# Format with ruff
ruff check .

# Auto-fix issues
ruff check --fix .
```

## Resource Requirements

### Local Development
- Python 3.11+
- 2GB RAM minimum
- Model files: `yolov8n.pt` (included)

### Cloud Run Production
- **Memory**: 4GB (YOLO + Transformers)
- **CPU**: 4 cores
- **Concurrency**: 5 (recommended)
- **Timeout**: 600s (10 minutes)
- **Cold Start**: ~15-30s first request

## Environment-Specific Configuration

### Development
```env
LOG_LEVEL=DEBUG
MIN_INSTANCES=0
YOLO_CONFIDENCE=0.6
VIDEO_FPS=5
```

### Staging
```env
LOG_LEVEL=INFO
MIN_INSTANCES=0
YOLO_CONFIDENCE=0.5
VIDEO_FPS=3
```

### Production
```env
LOG_LEVEL=WARNING
MIN_INSTANCES=1
YOLO_CONFIDENCE=0.5
VIDEO_FPS=3
MAX_INSTANCES=10
```

## Monitoring

### Health Endpoints

- **`GET /health`**: Liveness probe (always returns 200)
- **`GET /ready`**: Readiness probe (checks dependencies)

### Cloud Logging

```bash
# View logs
gcloud logs tail --service=yolo-rest

# Filter errors
gcloud logs read \
  --service=yolo-rest \
  --filter='severity>=ERROR' \
  --limit=50
```

### Metrics

Key metrics to monitor:
- Request latency (target: <500ms per frame)
- Error rate (target: <1%)
- Memory usage (alert: >80%)
- Instance count
- Cold start frequency

## Troubleshooting

### Common Issues

**Container fails to start**
- Check: Model files exist (`yolov8n.pt`)
- Check: Required secrets configured
- View logs: `gcloud logs read --service=yolo-rest --limit=100`

**Out of memory**
- Increase memory: `--memory=8Gi`
- Reduce concurrency: `--concurrency=3`

**Slow inference**
- Cloud Run uses CPU (no GPU)
- Use smaller model: `yolov8n.pt` instead of `yolov8s.pt`
- Reduce image size: `YOLO_IMAGE_SIZE=320`

**Cold starts**
- Set min-instances: `--min-instances=1` (costs more)
- Optimize container size (current: ~2-3GB)

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for comprehensive troubleshooting.

## Security

### Best Practices Implemented

✅ No credentials in code or git history  
✅ GCP Secret Manager for sensitive values  
✅ Workload Identity Federation (no service account keys)  
✅ Environment-based configuration  
✅ Request timeouts to prevent hangs  
✅ Cloud Run IAM for access control  

### Security Checklist

- [ ] Rotate all API keys before first deploy
- [ ] Delete `tech-fase-*.json` from filesystem
- [ ] Enable Cloud Run authentication (remove `--allow-unauthenticated`)
- [ ] Configure VPC connector for private APIs
- [ ] Set up Cloud Armor for DDoS protection
- [ ] Enable audit logs

## Cost Optimization

**Typical Costs (us-central1)**:
- Idle (min-instances=0): $0/month
- Always-on (min-instances=1, 4GB/4CPU): ~$50-100/month
- Per request: ~$0.01-0.05 per minute of video

**Optimization Tips**:
1. Use min-instances=0 for dev/staging
2. Set max-instances cap (e.g., 10)
3. Monitor and tune concurrency setting
4. Use Committed Use Discounts for production

## Documentation

- [**DEPLOYMENT.md**](DEPLOYMENT.md) - Comprehensive deployment guide
- [**CLOUD_RUN_CHANGES.md**](CLOUD_RUN_CHANGES.md) - Implementation summary
- [**.github/GITHUB_ACTIONS_SETUP.md**](.github/GITHUB_ACTIONS_SETUP.md) - CI/CD setup
- [**.env.example**](.env.example) - Complete configuration reference
- [**quickstart.md**](quickstart.md) - Detailed local setup

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

[Specify your license here]

## Support

For issues and questions:
- Check [`DEPLOYMENT.md`](DEPLOYMENT.md) troubleshooting section
- Review [`.github/GITHUB_ACTIONS_SETUP.md`](.github/GITHUB_ACTIONS_SETUP.md) for CI/CD issues
- Open GitHub issue

## Acknowledgments

- YOLOv8 by Ultralytics
- Google Cloud Speech-to-Text
- aiortc WebRTC library
- Roboflow inference platform
