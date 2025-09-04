# file: terraform/main.tf
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset([
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "compute.googleapis.com",
    "serviceusage.googleapis.com",
  ])
  service = each.key
  disable_on_destroy = false
}

# Artifact Registry (Docker)
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repo_name
  format        = "DOCKER"
  depends_on    = [google_project_service.services]
}

# GKE Autopilot cluster (keeps node mgmt minimal)
resource "google_container_cluster" "autopilot" {
  name              = var.cluster_name
  location          = var.region
  enable_autopilot  = true
  deletion_protection = false
  depends_on        = [google_project_service.services]
}

# Service Account used by GitHub Actions (deployer)
resource "google_service_account" "github_deployer" {
  account_id   = "github-deployer"
  display_name = "GitHub Actions GKE/AR Deployer"
}

# Grant minimal roles to push images and deploy to the cluster
resource "google_project_iam_member" "github_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/container.admin",            # apply manifests/rollouts
    "roles/iam.serviceAccountTokenCreator"
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_deployer.email}"
}

# Workload Identity Federation for GitHub OIDC
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub OIDC Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  attribute_condition                = "attribute.repository == \"${var.github_repo}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
  attribute_mapping = {
    "google.subject"     = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.actor"    = "assertion.actor"
    "attribute.ref"      = "assertion.ref"
  }
}

# Allow identities from the pool (limited to your repo) to impersonate the SA
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}
