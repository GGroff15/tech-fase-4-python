output "medical-agent-processor-medical-agent-processor-service_account_email" {
  value = google_service_account.medical-agent-processor.email
}

output "medical-agent-processor-cloud_run_url" {
  value = google_cloud_run_service.medical-agent-processor.status[0].url
  description = "Cloud Run service URL"
}

output "roboflow_secret_id" {
  value = length(var.roboflow_api_key) > 0 ? google_secret_manager_secret.roboflow[0].id : ""
  sensitive = true
}

output "api_key_secret_id" {
  value = length(var.api_key) > 0 ? google_secret_manager_secret.api_key[0].id : ""
  sensitive = true
}

output "medical-agent-api-service_account_email" {
  value = google_service_account.medical-agent-api.email
}

output "medical-agent-api-cloud_run_url" {
  value = google_cloud_run_service.medical-agent-api.status[0].url
  description = "Cloud Run service URL"
}

output "gemini_api_key_secret_id" {
  value = length(var.gemini_api_key) > 0 ? google_secret_manager_secret.gemini_api_key[0].id : ""
  sensitive = true
}
