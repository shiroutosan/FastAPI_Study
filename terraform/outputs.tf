# Outputs
output "cloud_run_url" {
  description = "The URL of the deployed Cloud Run service."
  value = google_cloud_run_service.fastapi-service.status[0].url
}

output "storage_bucket" {
  description = "The name of the Google Cloud Storage bucket created for the application."
  value = google_storage_bucket.app_storage.name
}

output "load_balancer_ip" {
  description = "The external IP address of the load balancer."
  value = google_compute_global_address.lb_ip.address
}

output "ssl_certificate_domains" {
  description = "The domain(s) associated with the managed SSL certificate."
  value       = google_compute_managed_ssl_certificate.ssl.managed[0].domains
}