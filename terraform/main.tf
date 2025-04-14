terraform {
  required_version = ">= 1.11.4"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "=6.29.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region = var.region
  zone = var.zone
  credentials = file(var.service_account_credentials_path)
}

#　GoogleCloudのAPIを有効化するためのリソースを宣言

# Enable required APIs
resource "google_project_service" "required_services" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ])
  
  service            = each.key
  disable_on_destroy = false
}

# Secret Manager secrets
resource "google_secret_manager_secret" "app_secrets" {
  for_each  = var.secrets
  
  secret_id = each.key

  labels = {
    label = "fastapi-service"
  }
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_services]
}

resource "google_secret_manager_secret_version" "app_secret_versions" {
  for_each = var.secrets
  
  secret      = google_secret_manager_secret.app_secrets[each.key].id
  secret_data_wo = each.value # secret_dataよりもセキュリティ上の理由で推奨。secret_data属性は、Terraformの状態ファイル（tfstate）に平文で保存される可能性がある。
}

# Cloud Storage バケット
resource "google_storage_bucket" "app_storage" {
  name          = "${var.project_id}-${var.service_name}-bucket"
  location      = var.region
  force_destroy = true
  
  uniform_bucket_level_access = true
  
  depends_on = [google_project_service.required_services]
}

# Cloud Run用のサービスアカウント
resource "google_service_account" "cloud_run_service_account" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name} Cloud Run service"
  
  depends_on = [google_project_service.required_services]
}

# サービスアカウントに付与するIAMロール
# 1. Secret Managerへのアクセス権
resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_service_account.email}"
}

# 2. CLoud Storageへのアクセス権
resource "google_project_iam_member" "cloud_run_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run_service_account.email}"
}

# Artifact Registry のリポジトリ作成
resource "google_artifact_registry_repository" "fastapi-study" {
  repository_id = var.artifact_registry_repo
  location      = var.region
  format        = "DOCKER"
  description   = "Docker repository for ${var.artifact_registry_repo} container images"
  depends_on = [google_project_service.required_services]
}

# Cloud Run サービス
resource "google_cloud_run_service" "fastapi-service" {
  name     = var.service_name
  location = var.region
  
  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.service_name}:latest"
        
        # Example environment variables. You can reference secrets or set static values
        # Uncomment and configure as needed
        env {
           name  = "BUCKET_NAME"
           value = google_storage_bucket.app_storage.name
         }
        
        # Example of referencing a secret
        # env {
        #   name = "DATABASE_URL"
        #   value_from {
        #     secret_key_ref {
        #       name = google_secret_manager_secret.app_secrets["DATABASE_URL"].secret_id
        #       key  = "latest"
        #     }
        #   }
        # }
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
      
      service_account_name = google_service_account.cloud_run_service_account.email
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.required_services,
    google_secret_manager_secret.app_secrets,
    google_storage_bucket.app_storage
  ]
}

# Cloud Run 用パブリックアクセス設定
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.fastapi-service.name
  location = google_cloud_run_service.fastapi-service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Load Balancer configuration
# 外部 IP アドレスを予約
resource "google_compute_global_address" "lb_ip" {
  name        = "${var.service_name}-lb-ip"
  depends_on  = [google_project_service.required_services]
}

# Cloud Run用のサーバレスネットワークエンドポイントグループ
resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  name                  = "${var.service_name}-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.fastapi-service.name
  }
}

# Backend service for the load balancer
resource "google_compute_backend_service" "backend" {
  name        = "${var.service_name}-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30
  
  backend {
    group = google_compute_region_network_endpoint_group.serverless_neg.id
  }
}

# URL map
resource "google_compute_url_map" "url_map" {
  name            = "${var.service_name}-url-map"
  default_service = google_compute_backend_service.backend.id
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "https_proxy" {
  name    = "${var.service_name}-https-proxy"
  description      = "${var.service_name}のhttps-proxy"
  url_map          = google_compute_url_map.url_map.self_link
  ssl_certificates = [google_compute_managed_ssl_certificate.ssl.self_link]
}

# 転送ルール
resource "google_compute_global_forwarding_rule" "forwarding_rule_https" {
  name                  = "${var.service_name}-lb-rule"
  target                = google_compute_target_https_proxy.https_proxy.self_link
  port_range            = "80"
  ip_address            = google_compute_global_address.lb_ip.address
  load_balancing_scheme = "EXTERNAL"
}

# 証明書の作成
resource "google_compute_managed_ssl_certificate" "ssl" {
  provider = google
  name = "ssl"
  managed {
    domains = ["api.${var.service_name}.com"]
  }

  lifecycle {
    create_before_destroy = true
  }
}