// Create Secret Manager secrets only when values provided
resource "google_secret_manager_secret" "roboflow" {
  count = length(var.roboflow_api_key) > 0 ? 1 : 0

  secret_id = "roboflow_api_key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "roboflow_version" {
  count  = length(var.roboflow_api_key) > 0 ? 1 : 0
  secret = google_secret_manager_secret.roboflow[0].id
  secret_data = var.roboflow_api_key
}

resource "google_secret_manager_secret" "api_key" {
  count = length(var.api_key) > 0 ? 1 : 0

  secret_id = "API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "api_key_version" {
  count  = length(var.api_key) > 0 ? 1 : 0
  secret = google_secret_manager_secret.api_key[0].id
  secret_data = var.api_key
}

// Grant SA access to secrets (if they exist)
resource "google_secret_manager_secret_iam_member" "roboflow_accessor" {
  count = length(var.roboflow_api_key) > 0 ? 1 : 0
  secret_id = google_secret_manager_secret.roboflow[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.medical-agent-processor.email}"
}

resource "google_secret_manager_secret_iam_member" "api_key_accessor" {
  count = length(var.api_key) > 0 ? 1 : 0
  secret_id = google_secret_manager_secret.api_key[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.medical-agent-processor.email}"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  count = length(var.gemini_api_key) > 0 ? 1 : 0

  secret_id = "API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "gemini_api_key_version" {
  count  = length(var.gemini_api_key) > 0 ? 1 : 0
  secret = google_secret_manager_secret.gemini_api_key[0].id
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret_iam_member" "gemini_api_key_accessor" {
  count = length(var.gemini_api_key) > 0 ? 1 : 0
  secret_id = google_secret_manager_secret.gemini_api_key[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.medical-agent-api.email}"
}
