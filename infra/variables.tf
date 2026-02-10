variable "project_id" {
  description = "GCP project id to provision resources into"
  type        = string
}

variable "region" {
  description = "Region for regional resources (Cloud Run location)"
  type        = string
  default     = "us-central1"
}

variable "sa_name" {
  description = "Service account short id to create"
  type        = string
  default     = "medical-assistent-processor"
}

variable "create_sa_key" {
  description = "Whether to create a long-lived service account key (not recommended)"
  type        = bool
  default     = false
}

variable "cloud_run_image" {
  description = "Container image for Cloud Run service"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated (public) access to Cloud Run"
  type        = bool
  default     = true
}

variable "roboflow_api_key" {
  description = "Roboflow API key to store in Secret Manager"
  type        = string
  default     = ""
  sensitive   = true
}

variable "api_key" {
  description = "Application API key to store in Secret Manager"
  type        = string
  default     = ""
  sensitive   = true
}
