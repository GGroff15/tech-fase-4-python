# Infra: Terraform for Speech-to-Text + Cloud Run

This folder contains a minimal Terraform module to:

- Enable Speech-to-Text, Secret Manager and Cloud Run APIs
- Create a service account for runtime and grant `roles/speech.client` and secret access
- Create Secret Manager secrets for `roboflow_api_key` and `API_KEY` (optional)
- Deploy a Cloud Run service and optionally allow public invocations

Usage

1. Ensure you have a deployer account locally with sufficient privileges to enable APIs and manage IAM.
2. From repo root run:

```bash
cd infra
terraform init
terraform plan -var="project_id=YOUR_PROJECT_ID" \
  -var="roboflow_api_key=..." -var="api_key=..."
terraform apply -var="project_id=YOUR_PROJECT_ID" \
  -var="roboflow_api_key=..." -var="api_key=..." -auto-approve
```

Notes & Security

- This module defaults to not creating long-lived service account keys (`create_sa_key = false`). Workload Identity is recommended for Cloud Run.
- Do not commit secret values to source control. Use CI secret injection or pass via `-var` in your pipeline.
- Verify Cloud Run secret mounting details for your provider version — adjust `cloud_run.tf` if necessary.
