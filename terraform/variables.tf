# file: terraform/variables.tf
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region (for GKE + Artifact Registry)"
  type        = string
  default     = "europe-north1"
}

variable "cluster_name" {
  description = "GKE Autopilot cluster name"
  type        = string
  default     = "joke-autopilot"
}

variable "repo_name" {
  description = "Artifact Registry repository id"
  type        = string
  default     = "apps"
}

variable "github_repo" {
  description = "GitHub owner/repo used by Actions OIDC (e.g., your-org/your-repo)"
  type        = string
}
