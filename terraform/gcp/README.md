# Google Cloud Platform Terraform Infrastructure

This directory contains Terraform configuration for deploying the Social Media Scraper on Google Cloud Platform.

## Architecture

- **Cloud Run** for containerized application (serverless)
- **Cloud SQL PostgreSQL** for database
- **Cloud Memorystore Redis** for caching and Celery
- **VPC** with private and public subnets
- **Secret Manager** for secrets management
- **Cloud Logging** for centralized logging

## Prerequisites

- Google Cloud SDK installed and configured
- Terraform >= 1.0
- Docker image pushed to GCR
- Appropriate GCP permissions

## Setup

### 1. Configure Variables

Create a `terraform.tfvars` file:

```hcl
gcp_project_id = "your-project-id"
gcp_region = "us-central1"
environment = "production"
project_name = "social-media-scraper"

gcr_repository_url = "gcr.io/your-project-id/social-media-scraper"
image_tag = "v1.0.0"

db_instance_tier = "db-f1-micro"
db_username = "admin"
db_password = "your-secure-password"

redis_tier = "BASIC"
redis_memory_size = 1
```

### 2. Initialize Terraform

```bash
cd terraform/gcp
terraform init
```

### 3. Plan Deployment

```bash
terraform plan -out=tfplan
```

### 4. Apply Configuration

```bash
terraform apply tfplan
```

## Outputs

After deployment, get outputs:

```bash
terraform output
```

Key outputs:
- `cloud_run_service_url` - Cloud Run service URL
- `cloud_sql_instance_connection_name` - Database connection name
- `redis_host` - Redis host address

## Secrets Management

Store secrets in Google Secret Manager:

```bash
gcloud secrets create social-media-scraper-secrets \
  --data-file=secrets.json \
  --replication-policy="automatic"
```

## Database Migrations

After deployment, run migrations:

```bash
# Connect to Cloud SQL
gcloud sql connect social-media-scraper-db --user=admin

# Or use Cloud Run job
gcloud run jobs create migrate \
  --image gcr.io/your-project/social-media-scraper \
  --command alembic \
  --args upgrade,head \
  --set-cloudsql-instances INSTANCE_CONNECTION_NAME
```

## Scaling

Cloud Run automatically scales based on traffic. Configure:

```bash
gcloud run services update social-media-scraper-app \
  --min-instances 3 \
  --max-instances 10 \
  --cpu 1 \
  --memory 512Mi
```

## Monitoring

- **Cloud Logging**: Automatic log collection
- **Cloud Monitoring**: Metrics and dashboards
- **Error Reporting**: Automatic error tracking

## Cost Optimization

- Use Cloud Run for serverless scaling
- Use appropriate instance tiers
- Enable Cloud SQL automated backups only in production
- Configure log retention policies
- Use Cloud CDN for static assets

## Cleanup

```bash
terraform destroy
```

**Warning:** This will delete all resources including databases. Ensure backups are taken.

## Troubleshooting

### Check Cloud Run Status

```bash
gcloud run services describe social-media-scraper-app --region us-central1
```

### View Logs

```bash
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

### Check Cloud SQL

```bash
gcloud sql instances describe social-media-scraper-db
```

