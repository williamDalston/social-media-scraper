# Microsoft Azure Terraform Infrastructure

This directory contains Terraform configuration for deploying the Social Media Scraper on Microsoft Azure.

## Architecture

- **Container Instances** (or AKS) for containerized application
- **Azure Database for PostgreSQL** for database
- **Azure Cache for Redis** for caching and Celery
- **Virtual Network** with subnets
- **Key Vault** for secrets management
- **Application Insights** for monitoring
- **Log Analytics** for centralized logging

## Prerequisites

- Azure CLI installed and configured
- Terraform >= 1.0
- Docker image pushed to ACR
- Appropriate Azure permissions

## Setup

### 1. Login to Azure

```bash
az login
az account set --subscription "your-subscription-id"
```

### 2. Configure Variables

Create a `terraform.tfvars` file:

```hcl
azure_region = "eastus"
environment = "production"
project_name = "social-media-scraper"

acr_repository_url = "yourregistry.azurecr.io/social-media-scraper"
image_tag = "v1.0.0"

db_sku_name = "B_Standard_B1ms"
db_username = "admin"
db_password = "your-secure-password"

redis_sku_name = "Basic"
redis_capacity = 1
```

### 3. Initialize Terraform

```bash
cd terraform/azure
terraform init
```

### 4. Plan Deployment

```bash
terraform plan -out=tfplan
```

### 5. Apply Configuration

```bash
terraform apply tfplan
```

## Outputs

After deployment, get outputs:

```bash
terraform output
```

Key outputs:
- `container_group_fqdn` - Container group FQDN
- `postgresql_fqdn` - Database FQDN
- `redis_hostname` - Redis hostname
- `key_vault_uri` - Key Vault URI

## Secrets Management

Store secrets in Azure Key Vault:

```bash
az keyvault secret set \
  --vault-name social-media-scraper-kv \
  --name SECRET-KEY \
  --value "your-secret-key"
```

## Database Migrations

After deployment, run migrations:

```bash
# Connect to database
az postgres flexible-server connect \
  --name social-media-scraper-db \
  --admin-user admin \
  --admin-password your-password

# Or use container instance
az container exec \
  --resource-group social-media-scraper-rg \
  --name social-media-scraper-app \
  --exec-command "alembic upgrade head"
```

## Scaling

Scale container instances:

```bash
az container create \
  --resource-group social-media-scraper-rg \
  --name social-media-scraper-app-2 \
  --image yourregistry.azurecr.io/social-media-scraper:v1.0.0 \
  --cpu 1 \
  --memory 1.5
```

## Monitoring

- **Application Insights**: Application performance monitoring
- **Log Analytics**: Centralized logging
- **Azure Monitor**: Infrastructure metrics

## Cost Optimization

- Use appropriate SKU sizes
- Enable auto-shutdown for non-production
- Use reserved instances for predictable workloads
- Configure log retention policies
- Use Azure CDN for static assets

## Cleanup

```bash
terraform destroy
```

**Warning:** This will delete all resources including databases. Ensure backups are taken.

## Troubleshooting

### Check Container Status

```bash
az container show \
  --resource-group social-media-scraper-rg \
  --name social-media-scraper-app
```

### View Logs

```bash
az container logs \
  --resource-group social-media-scraper-rg \
  --name social-media-scraper-app
```

### Check Database

```bash
az postgres flexible-server show \
  --resource-group social-media-scraper-rg \
  --name social-media-scraper-db
```

