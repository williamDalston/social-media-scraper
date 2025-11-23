# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying the Social Media Scraper application.

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured to access your cluster
- PersistentVolume support (for database and Redis data)
- Ingress controller (nginx recommended)
- cert-manager (optional, for TLS certificates)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Create Secrets

**Important:** Never commit actual secrets to git!

```bash
# Copy the example secrets file
cp k8s/secrets.yaml.example k8s/secrets.yaml

# Edit secrets.yaml with your actual values
nano k8s/secrets.yaml

# Apply secrets
kubectl apply -f k8s/secrets.yaml
```

**For Production:** Use a secrets management system:
- HashiCorp Vault
- AWS Secrets Manager
- Google Secret Manager
- Azure Key Vault

### 3. Create ConfigMap

```bash
kubectl apply -f k8s/configmap.yaml
```

### 4. Create Persistent Volume Claims

```bash
kubectl apply -f k8s/pvc-data.yaml
```

### 5. Deploy Redis

```bash
kubectl apply -f k8s/deployment-redis.yaml
kubectl apply -f k8s/service-redis.yaml
```

### 6. Deploy Application

```bash
kubectl apply -f k8s/deployment-app.yaml
kubectl apply -f k8s/deployment-celery-worker.yaml
kubectl apply -f k8s/deployment-celery-beat.yaml
kubectl apply -f k8s/service-app.yaml
```

### 7. Deploy Ingress (Optional)

Update `k8s/ingress.yaml` with your domain name, then:

```bash
kubectl apply -f k8s/ingress.yaml
```

### 8. Deploy Horizontal Pod Autoscaler (Optional)

```bash
kubectl apply -f k8s/hpa.yaml
```

## Complete Deployment

Deploy everything at once:

```bash
kubectl apply -f k8s/
```

## Verify Deployment

```bash
# Check all resources
kubectl get all -n social-media-scraper

# Check pod status
kubectl get pods -n social-media-scraper

# Check services
kubectl get svc -n social-media-scraper

# View logs
kubectl logs -f deployment/social-media-scraper-app -n social-media-scraper
```

## Run Database Migrations

```bash
# Get a pod name
POD_NAME=$(kubectl get pods -n social-media-scraper -l component=app -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $POD_NAME -n social-media-scraper -- alembic upgrade head
```

## Scaling

### Manual Scaling

```bash
# Scale app replicas
kubectl scale deployment social-media-scraper-app -n social-media-scraper --replicas=5

# Scale celery workers
kubectl scale deployment social-media-scraper-celery-worker -n social-media-scraper --replicas=4
```

### Automatic Scaling

The HPA (Horizontal Pod Autoscaler) will automatically scale based on CPU and memory usage.

## Rolling Updates

```bash
# Update image
kubectl set image deployment/social-media-scraper-app app=social-media-scraper:v2.0.0 -n social-media-scraper

# Check rollout status
kubectl rollout status deployment/social-media-scraper-app -n social-media-scraper

# Rollback if needed
kubectl rollout undo deployment/social-media-scraper-app -n social-media-scraper
```

## Troubleshooting

### Check Pod Logs

```bash
kubectl logs -f deployment/social-media-scraper-app -n social-media-scraper
kubectl logs -f deployment/social-media-scraper-celery-worker -n social-media-scraper
```

### Describe Resources

```bash
kubectl describe pod <pod-name> -n social-media-scraper
kubectl describe deployment social-media-scraper-app -n social-media-scraper
```

### Execute Commands in Pod

```bash
kubectl exec -it <pod-name> -n social-media-scraper -- /bin/bash
```

### Check Events

```bash
kubectl get events -n social-media-scraper --sort-by='.lastTimestamp'
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/

# Or delete namespace (removes everything)
kubectl delete namespace social-media-scraper
```

## Customization

### Resource Limits

Edit the `resources` section in deployment files to adjust CPU and memory limits.

### Replica Counts

Edit the `replicas` field in deployment files to change the number of instances.

### Storage

Edit `pvc-data.yaml` to change storage size and storage class.

### Ingress

Update `ingress.yaml` with your domain name and TLS configuration.

## Production Considerations

1. **Use managed databases** (RDS, Cloud SQL, etc.) instead of in-cluster PostgreSQL
2. **Use managed Redis** (ElastiCache, Cloud Memorystore, etc.) instead of in-cluster Redis
3. **Enable network policies** for pod-to-pod communication
4. **Use secrets management** instead of Kubernetes secrets for sensitive data
5. **Set up monitoring** (Prometheus, Grafana)
6. **Configure backup** for persistent volumes
7. **Use resource quotas** and limit ranges
8. **Enable pod security policies** or pod security standards

