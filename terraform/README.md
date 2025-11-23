# Terraform Infrastructure as Code

This directory contains Terraform configurations for deploying the Social Media Scraper to various cloud providers.

## Directory Structure

```
terraform/
├── aws/          # AWS ECS deployment
├── gcp/          # Google Cloud Platform deployment
├── azure/        # Microsoft Azure deployment
└── README.md     # This file
```

## Supported Providers

### AWS
- **Service**: ECS Fargate
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Load Balancer**: Application Load Balancer
- **See**: [aws/README.md](./aws/README.md)

### Google Cloud Platform
- **Service**: Cloud Run / GKE
- **Database**: Cloud SQL PostgreSQL
- **Cache**: Cloud Memorystore Redis
- **Load Balancer**: Cloud Load Balancing
- **See**: [gcp/README.md](./gcp/README.md) (to be created)

### Microsoft Azure
- **Service**: Container Instances / AKS
- **Database**: Azure Database for PostgreSQL
- **Cache**: Azure Cache for Redis
- **Load Balancer**: Azure Load Balancer
- **See**: [azure/README.md](./azure/README.md) (to be created)

## Common Workflow

1. **Choose your provider** (AWS, GCP, or Azure)
2. **Configure variables** in `terraform.tfvars`
3. **Initialize Terraform**: `terraform init`
4. **Plan deployment**: `terraform plan`
5. **Apply configuration**: `terraform apply`
6. **Run migrations**: See provider-specific README
7. **Verify deployment**: Check health endpoints

## Best Practices

1. **Use remote state** (S3, GCS, or Azure Storage)
2. **Version control** your Terraform files
3. **Use workspaces** for multiple environments
4. **Tag resources** appropriately
5. **Enable deletion protection** in production
6. **Use secrets management** (not hardcoded values)
7. **Review plans** before applying
8. **Backup state files** regularly

## State Management

### Remote Backend

Configure remote backend in `main.tf`:

**AWS (S3):**
```hcl
backend "s3" {
  bucket = "your-terraform-state-bucket"
  key    = "terraform.tfstate"
  region = "us-east-1"
}
```

**GCP (GCS):**
```hcl
backend "gcs" {
  bucket = "your-terraform-state-bucket"
  prefix = "terraform/state"
}
```

**Azure (Storage):**
```hcl
backend "azurerm" {
  resource_group_name  = "terraform-state"
  storage_account_name = "terraformstate"
  container_name       = "tfstate"
  key                  = "terraform.tfstate"
}
```

## Workspaces

Use workspaces for multiple environments:

```bash
# Create workspace
terraform workspace new production
terraform workspace new staging
terraform workspace new development

# Switch workspace
terraform workspace select production

# List workspaces
terraform workspace list
```

## Variables

Create `terraform.tfvars` files for each environment:

```hcl
# terraform.tfvars.production
environment = "production"
app_desired_count = 5
db_instance_class = "db.t3.large"

# terraform.tfvars.staging
environment = "staging"
app_desired_count = 2
db_instance_class = "db.t3.small"
```

Apply with:
```bash
terraform apply -var-file=terraform.tfvars.production
```

## Security

1. **Never commit secrets** to version control
2. **Use secrets management** services
3. **Enable encryption** at rest and in transit
4. **Use least privilege** IAM roles
5. **Enable VPC** for network isolation
6. **Use security groups** / firewall rules
7. **Enable audit logging**

## Cost Management

1. **Use appropriate instance sizes**
2. **Enable auto-scaling**
3. **Use reserved instances** for predictable workloads
4. **Monitor costs** with cloud provider tools
5. **Tag resources** for cost allocation
6. **Clean up unused resources**

## Migration Between Providers

To migrate between cloud providers:

1. **Export data** from current provider
2. **Set up infrastructure** in new provider
3. **Import data** to new provider
4. **Update DNS** and routing
5. **Verify functionality**
6. **Decommission** old infrastructure

## Troubleshooting

### Common Issues

**State Lock:**
```bash
# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

**State Mismatch:**
```bash
# Refresh state
terraform refresh
```

**Import Existing Resources:**
```bash
terraform import aws_instance.example i-1234567890abcdef0
```

## Additional Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

