# AWS Terraform Infrastructure

This directory contains Terraform configuration for deploying the Social Media Scraper on AWS using ECS Fargate.

## Architecture

- **ECS Fargate** for containerized application
- **Application Load Balancer** for traffic distribution
- **RDS PostgreSQL** for database
- **ElastiCache Redis** for caching and Celery
- **VPC** with public and private subnets
- **Secrets Manager** for secrets management
- **CloudWatch** for logging

## Prerequisites

- AWS CLI configured
- Terraform >= 1.0
- Docker image pushed to ECR
- Appropriate AWS permissions

## Setup

### 1. Configure Variables

Create a `terraform.tfvars` file:

```hcl
aws_region = "us-east-1"
environment = "production"
project_name = "social-media-scraper"

ecr_repository_url = "123456789012.dkr.ecr.us-east-1.amazonaws.com/social-media-scraper"
image_tag = "v1.0.0"

app_desired_count = 3
app_cpu = 512
app_memory = 1024

db_instance_class = "db.t3.small"
db_allocated_storage = 100
db_username = "admin"
db_password = "your-secure-password"

redis_node_type = "cache.t3.small"
redis_num_cache_nodes = 1
```

### 2. Initialize Terraform

```bash
cd terraform/aws
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
- `alb_dns_name` - Application Load Balancer DNS name
- `db_endpoint` - RDS database endpoint
- `redis_endpoint` - ElastiCache Redis endpoint

## Secrets Management

Secrets should be stored in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name social-media-scraper-secrets \
  --secret-string file://secrets.json
```

Example `secrets.json`:
```json
{
  "SECRET_KEY": "your-secret-key",
  "JWT_SECRET_KEY": "your-jwt-secret-key",
  "DATABASE_URL": "postgresql://user:pass@db-endpoint:5432/social_media",
  "REDIS_URL": "redis://redis-endpoint:6379/0"
}
```

## Database Migrations

After deployment, run migrations:

```bash
# Get ECS task
TASK_ARN=$(aws ecs list-tasks --cluster social-media-scraper-cluster --service-name social-media-scraper-app --query 'taskArns[0]' --output text)

# Run migrations
aws ecs execute-command \
  --cluster social-media-scraper-cluster \
  --task $TASK_ARN \
  --container app \
  --command "alembic upgrade head" \
  --interactive
```

## Scaling

### Manual Scaling

```bash
aws ecs update-service \
  --cluster social-media-scraper-cluster \
  --service social-media-scraper-app \
  --desired-count 5
```

### Auto Scaling

Configure ECS Service Auto Scaling:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/social-media-scraper-cluster/social-media-scraper-app \
  --min-capacity 3 \
  --max-capacity 10
```

## Backup

RDS automated backups are configured with:
- Backup retention: 7 days (configurable)
- Backup window: 03:00-04:00 UTC
- Point-in-time recovery enabled

## Monitoring

- CloudWatch Logs: `/ecs/social-media-scraper-app`
- CloudWatch Metrics: ECS, RDS, ElastiCache metrics
- Container Insights: Enabled on ECS cluster

## Cost Optimization

- Use Spot instances for non-production
- Enable RDS automated backups only in production
- Use smaller instance types for dev/staging
- Configure auto-scaling to scale down during low traffic

## Cleanup

```bash
terraform destroy
```

**Warning:** This will delete all resources including databases. Ensure backups are taken.

## Troubleshooting

### Check ECS Service Status

```bash
aws ecs describe-services \
  --cluster social-media-scraper-cluster \
  --services social-media-scraper-app
```

### View Logs

```bash
aws logs tail /ecs/social-media-scraper-app --follow
```

### Check Security Groups

```bash
aws ec2 describe-security-groups --filters "Name=tag:Name,Values=social-media-scraper-*"
```

