# Social Media Scraper Helm Chart

This Helm chart deploys the Social Media Scraper application on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.0+
- PersistentVolume support
- Ingress controller (optional)

## Installation

### Add the chart repository (if using a repository)

```bash
helm repo add social-media-scraper https://charts.example.com
helm repo update
```

### Install from local chart

```bash
# Install with default values
helm install social-media-scraper ./helm/social-media-scraper

# Install with custom values
helm install social-media-scraper ./helm/social-media-scraper -f my-values.yaml

# Install with custom release name
helm install my-release ./helm/social-media-scraper
```

### Install with custom configuration

```bash
helm install social-media-scraper ./helm/social-media-scraper \
  --set image.tag=v1.0.0 \
  --set replicaCount.app=5 \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=api.example.com
```

## Configuration

The following table lists the configurable parameters and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount.app` | Number of app replicas | `3` |
| `replicaCount.celeryWorker` | Number of Celery worker replicas | `2` |
| `replicaCount.celeryBeat` | Number of Celery beat replicas | `1` |
| `image.repository` | Image repository | `social-media-scraper` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `3` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `10Gi` |
| `config.environment` | Environment name | `production` |
| `config.databaseUrl` | Database URL | (see values.yaml) |
| `config.redisUrl` | Redis URL | (see values.yaml) |
| `secrets.secretKey` | Flask secret key | (required) |
| `secrets.jwtSecretKey` | JWT secret key | (required) |

## Values Files

### Development

```yaml
# values-dev.yaml
replicaCount:
  app: 1
  celeryWorker: 1
  celeryBeat: 1

config:
  environment: development
  logLevel: DEBUG

autoscaling:
  enabled: false
```

### Production

```yaml
# values-prod.yaml
replicaCount:
  app: 5
  celeryWorker: 3
  celeryBeat: 1

config:
  environment: production
  logLevel: INFO

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20

ingress:
  enabled: true
  hosts:
    - host: api.production.example.com
```

## Upgrade

```bash
# Upgrade with new values
helm upgrade social-media-scraper ./helm/social-media-scraper -f values-prod.yaml

# Upgrade with new image tag
helm upgrade social-media-scraper ./helm/social-media-scraper --set image.tag=v2.0.0
```

## Rollback

```bash
# List releases
helm list

# Rollback to previous version
helm rollback social-media-scraper

# Rollback to specific revision
helm rollback social-media-scraper 2
```

## Uninstall

```bash
helm uninstall social-media-scraper
```

## Database Migrations

The chart includes a migration job that runs before the application starts:

```bash
# Run migrations manually
kubectl create job --from=cronjob/social-media-scraper-migrate migrate-$(date +%s)
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=social-media-scraper
```

### View logs

```bash
kubectl logs -l component=app -f
kubectl logs -l component=celery-worker -f
```

### Describe resources

```bash
helm status social-media-scraper
kubectl describe deployment social-media-scraper-app
```

### Test connectivity

```bash
# Port forward to service
kubectl port-forward svc/social-media-scraper-app 8080:80

# Test health endpoint
curl http://localhost:8080/health
```

## Production Considerations

1. **Use managed databases** instead of in-cluster PostgreSQL
2. **Use managed Redis** instead of in-cluster Redis
3. **Enable network policies** for security
4. **Use secrets management** (Vault, AWS Secrets Manager)
5. **Set resource quotas** and limit ranges
6. **Enable pod security standards**
7. **Configure backup** for persistent volumes
8. **Set up monitoring** (Prometheus, Grafana)

## Examples

See the `examples/` directory for example values files for different environments.

