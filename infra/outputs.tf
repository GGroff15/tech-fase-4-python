output "service_account_email" {
  value = google_service_account.medical-agent-processor.email
}

output "cloud_run_url" {
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
