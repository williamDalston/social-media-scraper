output "vpc_network_id" {
  description = "VPC network ID"
  value       = google_compute_network.main.id
}

output "cloud_sql_instance_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "cloud_sql_instance_ip" {
  description = "Cloud SQL instance IP"
  value       = google_sql_database_instance.main.private_ip_address
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.main.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.main.port
}

output "cloud_run_service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.app.status[0].url
}

output "secret_manager_secret_id" {
  description = "Secret Manager secret ID"
  value       = google_secret_manager_secret.app_secrets.secret_id
}

