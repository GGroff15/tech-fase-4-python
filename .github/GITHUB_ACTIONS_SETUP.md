# GitHub Actions Setup Guide

Quick reference for setting up GitHub Actions deployment for yolo-rest.

## Required GitHub Secrets

Add these secrets in your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider resource name | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | Service account email for deployment | `yolo-rest-deployer@your-project-id.iam.gserviceaccount.com` |
| `GCP_ARTIFACT_REGISTRY` | Artifact Registry repository URL | `us-central1-docker.pkg.dev/your-project-id/yolo-rest` |
| `GCP_CLOUD_RUN_SERVICE_ACCOUNT` | Cloud Run service account email | `yolo-rest@your-project-id.iam.gserviceaccount.com` |

## Quick Setup Commands

Replace `YOUR_PROJECT_ID`, `YOUR_GITHUB_ORG`, and `PROJECT_NUMBER` with your actual values.

### 1. Create Workload Identity Pool and Provider

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

# Create workload identity pool
gcloud iam workload-identity-pools create github-pool \
    --location="global" \
    --description="GitHub Actions pool" \
    --display-name="GitHub Pool"

# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_ORG'"
```

### 2. Create and Configure Deployment Service Account

```bash
# Create service account for GitHub Actions
gcloud iam service-accounts create yolo-rest-deployer \
    --display-name="YOLO REST GitHub Deployer" \
    --description="Service account for GitHub Actions to deploy yolo-rest"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

# Allow GitHub to impersonate this service account
gcloud iam service-accounts add-iam-policy-binding \
    yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_ORG/yolo-rest" \
    --role="roles/iam.workloadIdentityUser"
```

### 3. Create Artifact Registry Repository

```bash
# Create Docker repository in Artifact Registry
gcloud artifacts repositories create yolo-rest \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for yolo-rest"
```

### 4. Get Secret Values

```bash
# Get Workload Identity Provider resource name (GCP_WORKLOAD_IDENTITY_PROVIDER)
gcloud iam workload-identity-pools providers describe github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --format="value(name)"

# Output will be like:
# projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider

# GCP_SERVICE_ACCOUNT value
echo "yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com"

# GCP_ARTIFACT_REGISTRY value
echo "us-central1-docker.pkg.dev/YOUR_PROJECT_ID/yolo-rest"

# GCP_CLOUD_RUN_SERVICE_ACCOUNT value (created earlier in DEPLOYMENT.md)
echo "yolo-rest@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

### 5. Add Secrets to GitHub

1. Go to your GitHub repository
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Add each secret from the table above with the values from step 4

## Testing the Workflow

### Automatic Trigger (Push)

The workflow automatically runs when you push to `main` or `develop` branches:

```bash
git add .
git commit -m "Deploy to Cloud Run"
git push origin main
```

### Manual Trigger (Workflow Dispatch)

1. Go to GitHub repository
2. Click **Actions** tab
3. Select **"Build and Deploy to Cloud Run"** workflow
4. Click **"Run workflow"** button
5. Select environment (production/staging)
6. Click **"Run workflow"**

## Workflow Steps

The workflow performs these steps:

1. **Test Job**: 
   - Checks out code
   - Sets up Python 3.11
   - Installs dependencies
   - Runs pytest tests

2. **Build and Push Job**:
   - Authenticates to GCP using Workload Identity
   - Builds Docker image
   - Pushes to Artifact Registry with multiple tags (SHA, timestamp, latest)
   - Creates build summary

3. **Deploy Job**:
   - Deploys to Cloud Run with configured resources (4GB RAM, 4 CPU)
   - Sets secrets from Secret Manager
   - Verifies deployment (health and readiness checks)
   - Creates deployment summary with service URL

## Viewing Workflow Results

After the workflow completes:

1. **Build Summary**: Shows Docker image details and tags
2. **Deployment Summary**: Shows service URL, endpoints, and configuration
3. **Logs**: Click on any step to see detailed logs

## Troubleshooting

### "Error: google-github-actions/auth failed with: retry function failed after 3 attempts"

**Cause**: Workload Identity Federation not properly configured

**Fix**: Verify step 2 - ensure service account can be impersonated by GitHub

```bash
# Check bindings
gcloud iam service-accounts get-iam-policy \
    yolo-rest-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### "Error: Permission denied on resource project"

**Cause**: Deployment service account lacks necessary permissions

**Fix**: Re-run step 2 to grant all required roles

### "Error: UNAUTHENTICATED: Request had invalid authentication credentials"

**Cause**: Secret values are incorrect or expired

**Fix**: Re-run step 4 to get current values and update GitHub secrets

### Tests Fail But Build Continues

The workflow allows test failures to prevent blocking deployments during development. To make tests blocking:

Edit `.github/workflows/deploy.yml` line 35:
```yaml
# Change this:
pytest -v --tb=short || echo "Warning: Tests failed but continuing build"

# To this:
pytest -v --tb=short
```

## Monitoring Deployments

### View All Workflow Runs

GitHub → Actions → "Build and Deploy to Cloud Run"

### View Cloud Run Deployments

```bash
# List all revisions
gcloud run revisions list --service=yolo-rest --region=us-central1

# View service details
gcloud run services describe yolo-rest --region=us-central1
```

### View Deployment Logs

```bash
# GitHub Actions logs: Click on workflow run → Select job → View logs

# Cloud Run logs
gcloud logs tail --service=yolo-rest
```

## Next Steps

After setup:
1. ✅ Test manual workflow dispatch
2. ✅ Verify deployment at service URL
3. ✅ Test health endpoints
4. ✅ Set up monitoring alerts
5. ✅ Configure branch protection rules (require passing tests)

## Additional Resources

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions for GCP](https://github.com/google-github-actions)
- [Cloud Run Deployment Best Practices](https://cloud.google.com/run/docs/tips)
