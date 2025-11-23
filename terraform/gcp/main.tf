terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "social-media-scraper-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = false
  
  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "google_compute_subnetwork" "private" {
  count = length(var.availability_zones)
  
  name          = "${var.project_name}-private-${count.index + 1}"
  ip_cidr_range = var.private_subnet_cidrs[count.index]
  region        = var.gcp_region
  network       = google_compute_network.main.id
  
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "public" {
  count = length(var.availability_zones)
  
  name          = "${var.project_name}-public-${count.index + 1}"
  ip_cidr_range = var.public_subnet_cidrs[count.index]
  region        = var.gcp_region
  network       = google_compute_network.main.id
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "main" {
  name             = "${var.project_name}-db"
  database_version = "POSTGRES_15"
  region           = var.gcp_region
  
  settings {
    tier              = var.db_instance_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }
  
  deletion_protection = var.environment == "production"
  
  tags = {
    Name        = "${var.project_name}-db"
    Environment = var.environment
  }
}

resource "google_sql_database" "main" {
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "main" {
  name     = var.db_username
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# Cloud Memorystore Redis
resource "google_redis_instance" "main" {
  name           = "${var.project_name}-redis"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size
  region         = var.gcp_region
  
  authorized_network = google_compute_network.main.id
  
  redis_version     = "REDIS_7_0"
  display_name      = "Redis for Social Media Scraper"
  
  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "TWELVE_HOURS"
  }
  
  tags = {
    Name        = "${var.project_name}-redis"
    Environment = var.environment
  }
}

# Cloud Run Service (or GKE)
resource "google_cloud_run_service" "app" {
  name     = "${var.project_name}-app"
  location = var.gcp_region
  
  template {
    spec {
      containers {
        image = "${var.gcr_repository_url}:${var.image_tag}"
        
        ports {
          container_port = 5000
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_username}:${var.db_password}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}"
        }
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
      
      service_account_name = google_service_account.app.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "3"
        "autoscaling.knative.dev/maxScale" = "10"
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.main.connection_name
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  tags = {
    Name        = "${var.project_name}-app"
    Environment = var.environment
  }
}

# Service Account
resource "google_service_account" "app" {
  account_id   = "${var.project_name}-app"
  display_name = "Social Media Scraper Application"
}

# IAM
resource "google_project_iam_member" "app" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Secret Manager
resource "google_secret_manager_secret" "app_secrets" {
  secret_id = "${var.project_name}-secrets"
  
  replication {
    automatic = true
  }
  
  labels = {
    Environment = var.environment
  }
}

# Load Balancer
resource "google_compute_backend_service" "app" {
  name                  = "${var.project_name}-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 30
  enable_cdn            = false
  load_balancing_scheme = "EXTERNAL"
  
  backend {
    group = google_compute_instance_group.app.id
  }
  
  health_checks = [google_compute_health_check.app.id]
}

resource "google_compute_health_check" "app" {
  name               = "${var.project_name}-health-check"
  check_interval_sec = 10
  timeout_sec        = 5
  
  http_health_check {
    port         = 5000
    request_path = "/health"
  }
}

# Cloud Logging
resource "google_logging_project_sink" "app" {
  name        = "${var.project_name}-logs"
  destination = "storage.googleapis.com/${google_storage_bucket.logs.name}"
  
  filter = "resource.type=cloud_run_revision AND resource.labels.service_name=${google_cloud_run_service.app.name}"
}

resource "google_storage_bucket" "logs" {
  name     = "${var.project_name}-logs-${var.gcp_project_id}"
  location = var.gcp_region
  
  lifecycle_rule {
    condition {
      age = var.log_retention_days
    }
    action {
      type = "Delete"
    }
  }
}

