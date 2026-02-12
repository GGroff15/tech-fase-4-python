// Enable required Google APIs
resource "google_project_service" "speech" {
  project = var.project_id
  service = "speech.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

// Service account for runtime
resource "google_service_account" "medical-agent-processor" {
  account_id   = var.medical-agent-processor_sa_name
  display_name = "Service account for yolo-rest runtime and STT access"
}

// IAM bindings for Speech and Secret Manager access
resource "google_project_iam_member" "speech_client" {
  project = var.project_id
  role    = "roles/speech.client"
  member  = "serviceAccount:${google_service_account.medical-agent-processor.email}"
}

resource "google_project_iam_member" "medical_agent_processor_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.medical-agent-processor.email}"
}

// Service account for runtime
resource "google_service_account" "medical-agent-api" {
  account_id   = var.medical-agent-api_sa_name
  display_name = "Service account for yolo-rest runtime and STT access"
}

resource "google_project_iam_member" "medical_agent_api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.medical-agent-api.email}"
}
