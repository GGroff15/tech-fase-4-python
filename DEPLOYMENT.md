# GCP Cloud Run Deployment Guide

## Prerequisites

Before deploying to GCP Cloud Run, ensure you have:

1. **GCP Project**: An active Google Cloud Platform project with billing enabled
2. **gcloud CLI**: Google Cloud SDK installed and configured
3. **APIs Enabled**: 
   - Cloud Run API
   - Cloud Build API
   - Container Registry API
   - Secret Manager API
   - Cloud Speech-to-Text API
4. **Permissions**: Project Editor or appropriate IAM roles

## Initial Setup

### 1. Configure gcloud CLI

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Configure Docker authentication for GCR
gcloud auth configure-docker
```

### 2. Create Service Account

Create a dedicated service account for the Cloud Run service with appropriate permissions:

```bash
# Create service account
gcloud iam service-accounts create yolo-rest \
    --display-name="YOLO REST Service" \
    --description="Service account for yolo-rest Cloud Run service"

# Grant Speech-to-Text permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Create Secrets in Secret Manager

Store sensitive configuration values in GCP Secret Manager:

```bash
# Create Roboflow API key secret
echo -n "YOUR_ROBOFLOW_API_KEY" | gcloud secrets create roboflow-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Create Event API key secret
echo -n "YOUR_EVENT_API_KEY" | gcloud secrets create event-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant service account access to secrets (already done with secretAccessor role above)
```

## Deployment Methods

### Method 1: Automated Deployment with Cloud Build (Recommended)

This method uses the `cloudbuild.yaml` file for automated CI/CD:

```bash
# Submit build to Cloud Build
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions _SERVICE_ACCOUNT=yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Check deployment status
gcloud run services describe yolo-rest --region=us-central1
```

### Method 2: Manual Docker Build and Deploy

For local development and testing:

```bash
# Build Docker image locally
docker build -t gcr.io/YOUR_PROJECT_ID/yolo-rest:latest .

# Test locally
docker run -p 8080:8080 \
    -e PORT=8080 \
    -e ROBOFLOW_API_KEY=your_key \
    -e LOG_LEVEL=DEBUG \
    gcr.io/YOUR_PROJECT_ID/yolo-rest:latest

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT_ID/yolo-rest:latest

# Deploy to Cloud Run
gcloud run deploy yolo-rest \
    --image gcr.io/YOUR_PROJECT_ID/yolo-rest:latest \
    --platform managed \
    --region us-central1 \
    --memory 4Gi \
    --cpu 4 \
    --concurrency 5 \
    --timeout 600 \
    --min-instances 0 \
    --max-instances 10 \
    --service-account yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --set-secrets ROBOFLOW_API_KEY=roboflow-api-key:latest,API_KEY=event-api-key:latest \
    --set-env-vars LOG_LEVEL=INFO,VIDEO_FPS=3,YOLO_CONFIDENCE=0.5 \
    --allow-unauthenticated
```

## Configuration

### Environment Variables

Set additional environment variables during deployment:

```bash
gcloud run services update yolo-rest \
    --region us-central1 \
    --set-env-vars \
        LOG_LEVEL=INFO,\
        VIDEO_FPS=3,\
        YOLO_CONFIDENCE=0.5,\
        YOLO_IMAGE_SIZE=640,\
        MAX_IMAGE_WIDTH=1280,\
        MAX_IMAGE_HEIGHT=720,\
        AUDIO_SAMPLE_RATE=16000,\
        STT_LANGUAGE=pt-BR,\
        EVENT_FORWARD_BASE_URL=https://your-backend-api.com
```

### Resource Configuration

Current deployment uses these resources (adjust based on your needs):

- **Memory**: 4GB (minimum for YOLO + Transformers models)
- **CPU**: 4 CPUs (balance between cost and performance)
- **Concurrency**: 5 (limit concurrent WebRTC streams)
- **Timeout**: 600s (10 minutes for long video sessions)
- **Min Instances**: 0 (dev/staging) or 1 (production for zero cold starts)
- **Max Instances**: 10 (cost control)

To adjust resources:

```bash
gcloud run services update yolo-rest \
    --region us-central1 \
    --memory 8Gi \
    --cpu 8 \
    --concurrency 10 \
    --min-instances 1
```

## Verification

### 1. Check Service Status

```bash
# Get service URL
gcloud run services describe yolo-rest \
    --region us-central1 \
    --format 'value(status.url)'

# View logs
gcloud logs read --service=yolo-rest --limit=50
```

### 2. Test Health Endpoints

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe yolo-rest \
    --region us-central1 \
    --format 'value(status.url)')

# Test liveness probe
curl $SERVICE_URL/health

# Expected response: {"status": "ok"}

# Test readiness probe
curl $SERVICE_URL/ready

# Expected response: {"ready": true, "checks": {...}}
```

### 3. Test WebRTC Connection

Use the provided test client or browser-based client to establish a WebRTC connection:

1. Open `$SERVICE_URL` in a browser
2. Allow camera/microphone access
3. Establish WebRTC connection
4. Verify detection events are received

## Monitoring

### Cloud Logging

View application logs in Cloud Console:

```bash
# Stream logs in real-time
gcloud logs tail --service=yolo-rest --format=json

# Filter errors only
gcloud logs read \
    --service=yolo-rest \
    --filter='severity>=ERROR' \
    --limit=20
```

### Cloud Monitoring

Set up alerts for:
- High error rates
- Memory/CPU usage
- Request latency
- Instance count

Example alert policy:

```bash
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_CHANNEL_ID \
    --display-name="YOLO REST High Error Rate" \
    --condition-display-name="Error rate > 5%" \
    --condition-threshold-value=5 \
    --condition-threshold-duration=60s
```

## Troubleshooting

### Common Issues

#### 1. Cold Start Timeouts

**Symptom**: First request times out or takes >30 seconds

**Solution**: 
- Use min-instances=1 for production
- Reduce YOLO model size (use yolov8n.pt instead of yolov8s.pt)
- Pre-download HuggingFace models during container build

#### 2. Out of Memory Errors

**Symptom**: Container crashes with OOM

**Solution**:
```bash
gcloud run services update yolo-rest \
    --region us-central1 \
    --memory 8Gi
```

#### 3. Google Speech-to-Text Permission Denied

**Symptom**: "PermissionDenied: 403 The caller does not have permission"

**Solution**: Verify service account has roles/speech.client:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"
```

#### 4. Roboflow API Errors

**Symptom**: "Roboflow inference failed" in logs

**Solution**:
- Verify ROBOFLOW_API_KEY secret is correctly set
- Check Roboflow API quota at roboflow.com
- Verify ROBOFLOW_MODEL_ID is correct

### Debug Deployment

Enable detailed logging to diagnose issues:

```bash
# Update service with DEBUG logging
gcloud run services update yolo-rest \
    --region us-central1 \
    --set-env-vars LOG_LEVEL=DEBUG

# View detailed logs
gcloud logs read \
    --service=yolo-rest \
    --limit=100 \
    --format=json
```

## Security Best Practices

### 1. Remove Exposed Credentials

**IMPORTANT**: The repository previously contained exposed credentials. Ensure:

```bash
# Verify no credential files are tracked
git log --all --full-history -- tech-fase-*.json
git log --all --full-history -- .env

# If credentials are in history, clean with BFG Repo-Cleaner
# https://rtyley.github.io/bfg-repo-cleaner/
```

### 2. Rotate Compromised Keys

If credentials were exposed:
1. Revoke Google service account keys in GCP Console
2. Rotate Roboflow API key at roboflow.com
3. Update secrets in Secret Manager
4. Redeploy with new secrets

### 3. Enable Authentication

For production, remove `--allow-unauthenticated` and require authentication:

```bash
gcloud run services update yolo-rest \
    --region us-central1 \
    --no-allow-unauthenticated

# Grant specific users/services access
gcloud run services add-iam-policy-binding yolo-rest \
    --region us-central1 \
    --member="user:developer@example.com" \
    --role="roles/run.invoker"
```

## Cost Optimization

### 1. Use Minimum Instances Wisely

- **Dev/Staging**: min-instances=0 (pay only for usage)
- **Production**: min-instances=1 (avoid cold starts, predictable cost)

### 2. Set Max Instances

Prevent runaway costs:

```bash
gcloud run services update yolo-rest \
    --region us-central1 \
    --max-instances 5  # Adjust based on expected load
```

### 3. Monitor Usage

Review Cloud Run metrics in GCP Console:
- Request count
- Billable instance time
- Container instance count

## Continuous Deployment

### GitHub Actions Integration

The project includes a complete GitHub Actions workflow at `.github/workflows/deploy.yml` that automatically:
1. Runs tests
2. Builds and pushes Docker image to Artifact Registry
3. Deploys to Cloud Run
4. Verifies deployment health

The workflow triggers on:
- Push to `main` or `develop` branches
- Manual workflow dispatch

#### Required GitHub Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

1. **`GCP_WORKLOAD_IDENTITY_PROVIDER`**: Workload Identity Provider resource name
   ```
   projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_NAME/providers/PROVIDER_NAME
   ```

2. **`GCP_SERVICE_ACCOUNT`**: Service account email for deployment
   ```
   yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

3. **`GCP_ARTIFACT_REGISTRY`**: Artifact Registry URL
   ```
   us-central1-docker.pkg.dev/YOUR_PROJECT_ID/yolo-rest
   ```

4. **`GCP_CLOUD_RUN_SERVICE_ACCOUNT`**: Cloud Run service account email
   ```
   yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

#### Setting Up Workload Identity Federation (Recommended)

Workload Identity Federation is more secure than service account keys:

```bash
# 1. Create Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location="global" \
    --description="GitHub Actions pool" \
    --display-name="GitHub Pool"

# 2. Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_ORG'"

# 3. Create service account for deployment
gcloud iam service-accounts create yolo-rest-deployer \
    --display-name="YOLO REST GitHub Deployer"

# 4. Grant permissions to deployment service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# 5. Allow GitHub Actions to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding \
    yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_ORG/yolo-rest" \
    --role="roles/iam.workloadIdentityUser"

# 6. Get the Workload Identity Provider resource name (add this to GitHub secrets)
gcloud iam workload-identity-pools providers describe github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --format="value(name)"
```

#### Manual Deployment via GitHub Actions

Trigger a manual deployment:

1. Go to your GitHub repository
2. Navigate to Actions → "Build and Deploy to Cloud Run"
3. Click "Run workflow"
4. Select environment (production/staging)
5. Click "Run workflow"

The workflow will show progress and create a deployment summary with service URLs and health check results

## Rollback

If deployment fails or causes issues:

```bash
# List revisions
gcloud run revisions list --service=yolo-rest --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic yolo-rest \
    --region us-central1 \
    --to-revisions=yolo-rest-00001-abc=100
```

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [Cloud Run Pricing Calculator](https://cloud.google.com/products/calculator)
- [aiortc WebRTC Library](https://github.com/aiortc/aiortc)

## Support

For issues specific to this deployment:
1. Check Cloud Run logs: `gcloud logs read --service=yolo-rest`
2. Verify health endpoints: `curl $SERVICE_URL/health`
3. Review environment variables: `gcloud run services describe yolo-rest --format=yaml`
4. Check Secret Manager access: Ensure service account has secretAccessor role
