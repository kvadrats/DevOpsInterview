output "artifact_registry_repo" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}"
  description = "Full Artifact Registry hostname/repo"
}

output "gke_cluster_name" {
  value = google_container_cluster.autopilot.name
}

output "gke_location" {
  value = google_container_cluster.autopilot.location
}

output "workload_identity_provider" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Use in GitHub Actions: this is the WIF provider resource name"
}

output "deployer_service_account_email" {
  value = google_service_account.github_deployer.email
}
