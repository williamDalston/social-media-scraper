# Deployment Guide

This guide covers deploying the Social Media Scraper application to various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start with Docker](#quick-start-with-docker)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Deployment Methods](#deployment-methods)
  - [Docker Compose](#docker-compose)
  - [AWS (ECS/EKS)](#aws-ecseks)
  - [Google Cloud (GKE/Cloud Run)](#google-cloud-gkecloud-run)
  - [Azure (AKS)](#azure-aks)
  - [Heroku](#heroku)
  - [DigitalOcean](#digitalocean)
- [Database Migrations](#database-migrations)
- [Backup and Restore](#backup-and-restore)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL (recommended for production) or SQLite (for development)
- Redis (for Celery task queue)
- Git

---

## Quick Start with Docker

The fastest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone <repository-url>
cd social-media-scraper

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env file with your configuration
nano .env

# 4. Build and start services
docker-compose up -d

# 5. Run database migrations
docker-compose exec app alembic upgrade head

# 6. Check service status
docker-compose ps
```

The application will be available at `http://localhost:5000`

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

**Required variables:**
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Flask secret key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `JWT_SECRET_KEY` - JWT signing key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)

**Optional variables:**
- `ENVIRONMENT` - Environment name (development, staging, production)
- `REDIS_URL` - Redis connection URL
- `SENTRY_DSN` - Sentry error tracking DSN
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Configuration Validation

The application validates configuration on startup. To test your configuration:

```bash
python -c "from config.settings import config, validate_config_on_startup; validate_config_on_startup(); print('Configuration valid!')"
```

---

## Database Setup

### SQLite (Development)

SQLite is used by default for development. The database file is created automatically at `data/social_media.db`.

### PostgreSQL (Production)

For production, use PostgreSQL:

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE social_media;
CREATE USER scraper_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE social_media TO scraper_user;
\q

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://scraper_user:your_password@localhost:5432/social_media
```

### Database Migrations

Run migrations using Alembic:

```bash
# Upgrade to latest
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Downgrade one version
alembic downgrade -1

# Show current version
alembic current
```

---

## Deployment Methods

### Docker Compose

**Best for:** Local development, single-server deployments

1. **Build and start services:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f app
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

4. **Update and redeploy:**
   ```bash
   git pull
   docker-compose build
   docker-compose up -d
   alembic upgrade head
   ```

### AWS (ECS/EKS)

#### ECS Deployment

1. **Build and push Docker image:**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t social-media-scraper .
   docker tag social-media-scraper:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/social-media-scraper:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/social-media-scraper:latest
   ```

2. **Create ECS task definition** with environment variables from AWS Secrets Manager

3. **Create ECS service** with:
   - Application Load Balancer
   - Auto-scaling configuration
   - Health checks

#### EKS Deployment

1. **Create Kubernetes manifests** (see `k8s/` directory for examples)

2. **Deploy to EKS:**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Set up secrets:**
   ```bash
   kubectl create secret generic app-secrets --from-env-file=.env
   ```

### Google Cloud (GKE/Cloud Run)

#### Cloud Run Deployment

1. **Build and deploy:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/social-media-scraper
   gcloud run deploy social-media-scraper \
     --image gcr.io/PROJECT_ID/social-media-scraper \
     --platform managed \
     --region us-central1 \
     --set-env-vars DATABASE_URL=...,SECRET_KEY=...
   ```

#### GKE Deployment

1. **Build and push to GCR:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/social-media-scraper
   ```

2. **Deploy to GKE:**
   ```bash
   kubectl apply -f k8s/
   ```

### Azure (AKS)

1. **Build and push to Azure Container Registry:**
   ```bash
   az acr build --registry <registry-name> --image social-media-scraper:latest .
   ```

2. **Deploy to AKS:**
   ```bash
   kubectl apply -f k8s/
   ```

### Heroku

1. **Install Heroku CLI and login:**
   ```bash
   heroku login
   ```

2. **Create Heroku app:**
   ```bash
   heroku create social-media-scraper
   ```

3. **Add PostgreSQL addon:**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY=...
   heroku config:set JWT_SECRET_KEY=...
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   heroku run alembic upgrade head
   ```

### DigitalOcean

#### App Platform

1. **Connect GitHub repository** to DigitalOcean App Platform

2. **Configure build settings:**
   - Build command: `pip install -r requirements.txt`
   - Run command: `gunicorn -w 4 -b 0.0.0.0:8080 app:app`

3. **Add managed databases:**
   - PostgreSQL database
   - Redis database

4. **Set environment variables** in App Platform dashboard

#### Droplet Deployment

1. **Create Droplet** with Docker pre-installed

2. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd social-media-scraper
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   nano .env
   ```

4. **Deploy with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

---

## Database Migrations

### Running Migrations

**With Docker:**
```bash
docker-compose exec app alembic upgrade head
```

**Without Docker:**
```bash
alembic upgrade head
```

### Creating New Migrations

1. **Make changes to models** in `scraper/schema.py` or `models/`

2. **Generate migration:**
   ```bash
   alembic revision --autogenerate -m "description of changes"
   ```

3. **Review generated migration** in `alembic/versions/`

4. **Test migration:**
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

### Migration Best Practices

- Always test migrations on a copy of production data
- Review auto-generated migrations before committing
- Keep migrations small and focused
- Never edit existing migrations that have been applied to production

---

## Backup and Restore

### Automated Backups

Use the backup script to create database backups:

```bash
# Create backup
./scripts/backup_db.sh

# Backups are stored in backups/ directory
# Old backups (>30 days) are automatically cleaned up
```

### Manual Backup

**SQLite:**
```bash
cp data/social_media.db backups/db_backup_$(date +%Y%m%d_%H%M%S).db
```

**PostgreSQL:**
```bash
pg_dump $DATABASE_URL > backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

```bash
# List available backups
ls -lh backups/

# Restore from backup
./scripts/restore_db.sh backups/db_backup_20240101_120000.db
```

**Note:** The restore script automatically creates a backup of the current database before restoring.

---

## Monitoring and Health Checks

### Health Check Endpoint

The application provides a health check endpoint at `/health`:

```bash
curl http://localhost:5000/health
```

### Docker Health Checks

Docker Compose includes health checks for all services. Check status:

```bash
docker-compose ps
```

### Logs

**View application logs:**
```bash
# Docker Compose
docker-compose logs -f app

# Systemd
journalctl -u social-media-scraper -f

# Manual
tail -f logs/app.log
```

**View Celery logs:**
```bash
docker-compose logs -f celery-worker celery-beat
```

---

## Deployment Scripts

### Automated Deployment

Use the deployment script for automated deployments:

```bash
./scripts/deploy.sh
```

The script:
1. Backs up the database
2. Pulls latest code (if using git)
3. Installs dependencies
4. Runs database migrations
5. Builds Docker images (if using Docker)
6. Restarts services
7. Performs health checks
8. Cleans up old backups

### Service Management

**Start services:**
```bash
./scripts/start.sh start
```

**Stop services:**
```bash
./scripts/start.sh stop
```

**Restart services:**
```bash
./scripts/start.sh restart
```

**Check status:**
```bash
./scripts/start.sh status
```

---

## Troubleshooting

### Common Issues

#### Database Connection Errors

**Problem:** Cannot connect to database

**Solutions:**
- Verify `DATABASE_URL` is correct in `.env`
- Check database service is running
- Verify network connectivity
- Check firewall rules

#### Migration Errors

**Problem:** Migration fails

**Solutions:**
- Check database is accessible
- Verify migration file syntax
- Check for conflicting migrations
- Review migration history: `alembic history`

#### Docker Build Fails

**Problem:** Docker build errors

**Solutions:**
- Check Dockerfile syntax
- Verify all files are present
- Check `.dockerignore` isn't excluding needed files
- Review build logs: `docker-compose build --no-cache`

#### Services Won't Start

**Problem:** Services fail to start

**Solutions:**
- Check logs: `docker-compose logs`
- Verify environment variables are set
- Check port conflicts: `lsof -i :5000`
- Verify dependencies are installed

### Getting Help

1. Check application logs
2. Review Docker logs: `docker-compose logs`
3. Verify configuration: `python -c "from config.settings import config; print(config.get_summary())"`
4. Check health endpoint: `curl http://localhost:5000/health`

---

## Security Considerations

### Production Checklist

- [ ] Change all default secrets
- [ ] Use strong, unique passwords
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Enable database encryption
- [ ] Set up regular backups
- [ ] Configure rate limiting
- [ ] Enable monitoring and alerting
- [ ] Review and update dependencies regularly

### Secrets Management

**Never commit secrets to version control!**

Use environment variables or secrets management services:
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets
- Docker Secrets

---

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. **Load Balancer:** Use AWS ALB, GCP Load Balancer, or nginx
2. **Multiple App Instances:** Run multiple Gunicorn workers or containers
3. **Database Connection Pooling:** Configure SQLAlchemy connection pool
4. **Caching:** Use Redis for caching frequently accessed data
5. **CDN:** Use CloudFront or Cloudflare for static assets

### Vertical Scaling

Increase resources for single-instance deployments:
- More CPU cores
- More RAM
- Faster storage (SSD)

---

## Maintenance

### Regular Tasks

- **Daily:** Monitor logs and health checks
- **Weekly:** Review error logs and metrics
- **Monthly:** Update dependencies and security patches
- **Quarterly:** Review and optimize database performance

### Updates

1. **Test in staging environment first**
2. **Backup database before updates**
3. **Run migrations**
4. **Deploy new version**
5. **Verify health checks pass**
6. **Monitor for errors**

---

## Support

For issues or questions:
1. Check this documentation
2. Review application logs
3. Check GitHub issues
4. Contact the development team

---

**Last Updated:** 2024-01-01

