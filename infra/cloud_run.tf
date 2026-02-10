resource "google_cloud_run_service" "medical-agent-processor" {
  name     = "medical-agent-processor"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.medical-agent-processor.email

      containers {
        image = var.cloud_run_image

        // Mount secrets into env via secret value reference (Cloud Run will reference Secret Manager)
        dynamic "env" {
          for_each = length(var.roboflow_api_key) > 0 ? [1] : []
          content {
            name = "ROBOFLOW_API_KEY"
            value_from {
              secret_key_ref {
                // reference the secret resource name; Cloud Run expects the secret name
                name = google_secret_manager_secret.roboflow[0].secret_id
                key  = "latest"
              }
            }
          }
        }

        dynamic "env" {
          for_each = length(var.api_key) > 0 ? [1] : []
          content {
            name = "API_KEY"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.api_key[0].secret_id
                key  = "latest"
              }
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

// Allow unauthenticated access if requested
resource "google_cloud_run_service_iam_member" "invoker_all" {
  count = var.allow_unauthenticated ? 1 : 0
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_service.medical-agent-processor.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
