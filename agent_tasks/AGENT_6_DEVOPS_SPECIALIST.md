# Agent 6: DEVOPS_SPECIALIST (Frankie)
## Production Enhancement: Configuration & Deployment

### 🎯 Mission
Create Docker setup, environment configuration management, database migrations, and deployment scripts to make the application production-ready and easily deployable.

---

## 📋 Detailed Tasks

### 1. Docker Setup

#### 1.1 Dockerfile
- **File:** `Dockerfile`
- Multi-stage build:
  - Stage 1: Build dependencies
  - Stage 2: Runtime image
- Optimize:
  - Use Python slim image
  - Install only production dependencies
  - Set non-root user
  - Expose port 5000

#### 1.2 Docker Compose
- **File:** `docker-compose.yml`
- Services:
  - `app` - Flask application
  - `redis` - Redis for Celery (if using)
  - `celery-worker` - Celery worker (if using)
  - `celery-beat` - Celery scheduler (if using)
- Networks and volumes
- Environment variables

#### 1.3 Docker Ignore
- **File:** `.dockerignore`
- Exclude:
  - `venv/`
  - `__pycache__/`
  - `.git/`
  - `*.db`
  - Test files
  - Development files

---

### 2. Environment Configuration

#### 2.1 Environment Template
- **File:** `.env.example`
- Include all required variables:
  - Database URL
  - Redis URL
  - API keys
  - JWT secret
  - Sentry DSN
  - Environment name
  - Log level

#### 2.2 Configuration Management
- **File:** `config/settings.py`
- Load from:
  - Environment variables
  - `.env` file (development)
  - Default values
- Validate required variables on startup
- Support multiple environments (dev, staging, prod)

#### 2.3 Configuration Validation
- Validate:
  - Required variables present
  - Variable formats (URLs, keys, etc.)
  - Database connectivity
  - External service connectivity

---

### 3. Database Migrations

#### 3.1 Alembic Setup
- **File:** `alembic.ini`
- Configure:
  - Database URL
  - Script location
  - Template directory

#### 3.2 Alembic Environment
- **File:** `alembic/env.py`
- Configure:
  - SQLAlchemy connection
  - Model imports
  - Migration context

#### 3.3 Initial Migration
- **File:** `alembic/versions/001_initial_schema.py`
- Create migration for existing schema:
  - DimAccount table
  - FactFollowersSnapshot table
  - FactSocialPost table
  - Indexes
  - Foreign keys

#### 3.4 Migration Scripts
- Create scripts for:
  - Running migrations
  - Rolling back migrations
  - Creating new migrations
  - Checking migration status

---

### 4. Deployment Scripts

#### 4.1 Deployment Script
- **File:** `scripts/deploy.sh`
- Steps:
  - Pull latest code
  - Install dependencies
  - Run database migrations
  - Restart services
  - Health check
  - Rollback on failure

#### 4.2 Database Backup Script
- **File:** `scripts/backup_db.sh`
- Backup:
  - SQLite database
  - Create timestamped backups
  - Compress backups
  - Clean old backups (keep last 30 days)

#### 4.3 Database Restore Script
- **File:** `scripts/restore_db.sh`
- Restore from backup
- Validate backup before restore
- Create backup of current DB before restore

#### 4.4 Startup Script
- **File:** `scripts/start.sh`
- Start all services:
  - Flask app
  - Celery worker (if using)
  - Celery beat (if using)
- Use process manager (supervisor, systemd)

---

### 5. Infrastructure as Code

#### 5.1 Kubernetes Manifests (Optional)
- **Files:** `k8s/`
- Create:
  - Deployment manifests
  - Service manifests
  - ConfigMap
  - Secrets
  - Ingress
  - PersistentVolumeClaims

#### 5.2 Cloud Deployment Guides
- **File:** `DEPLOYMENT.md`
- Guides for:
  - Docker deployment
  - AWS (ECS, EKS)
  - Google Cloud (GKE, Cloud Run)
  - Azure (AKS, Container Instances)
  - Heroku
  - DigitalOcean

#### 5.3 Terraform (Optional)
- Infrastructure as code for cloud deployment
- Define:
  - Compute resources
  - Database
  - Load balancer
  - Networking

---

## 📁 File Structure to Create

```
alembic/
├── versions/
│   └── 001_initial_schema.py
├── env.py
└── script.py.mako

scripts/
├── deploy.sh
├── backup_db.sh
├── restore_db.sh
└── start.sh

k8s/                    # Optional
├── deployment.yaml
├── service.yaml
├── configmap.yaml
└── ingress.yaml

Dockerfile
docker-compose.yml
.dockerignore
.env.example
DEPLOYMENT.md
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
alembic>=1.12.0
gunicorn>=21.2.0        # Production WSGI server
```

---

## ✅ Acceptance Criteria

- [ ] Dockerfile builds successfully
- [ ] Docker Compose starts all services
- [ ] Environment variables are properly managed
- [ ] Database migrations work
- [ ] Deployment scripts are functional
- [ ] Backup/restore scripts work
- [ ] Application runs in Docker
- [ ] Documentation is complete

---

## 🧪 Testing Requirements

- Test Docker build
- Test Docker Compose setup
- Test migrations (upgrade, downgrade)
- Test deployment script
- Test backup/restore
- Test in different environments

---

## 📝 Implementation Details

### Dockerfile Example:
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
USER nobody
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Docker Compose Example:
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=sqlite:///data/social_media.db
    volumes:
      - ./data:/app/data
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Alembic Migration Example:
```python
def upgrade():
    op.create_table('dim_account',
        sa.Column('account_key', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        # ... more columns
    )
    op.create_index('ix_dim_account_platform', 'dim_account', ['platform'])
```

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-6-devops`
2. Create Dockerfile
3. Create docker-compose.yml
4. Set up Alembic
5. Create initial migration
6. Create deployment scripts
7. Create .env.example
8. Test Docker setup
9. Write deployment documentation
10. Test in different environments

---

## 🔧 Environment Variables

### Required:
```
DATABASE_URL=sqlite:///data/social_media.db
ENVIRONMENT=production
SECRET_KEY=...
JWT_SECRET_KEY=...
```

### Optional:
```
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=...
LOG_LEVEL=INFO
```

---

## 📊 Deployment Checklist

- [ ] Docker image builds
- [ ] All services start correctly
- [ ] Database migrations run
- [ ] Environment variables set
- [ ] Health checks pass
- [ ] Logs are accessible
- [ ] Backups are configured
- [ ] Monitoring is set up
- [ ] SSL/TLS configured (if needed)
- [ ] Domain/DNS configured

---

## ⚠️ Important Considerations

- **Security:** Don't commit secrets to repository
- **Database:** Use proper database (PostgreSQL) for production
- **Scaling:** Design for horizontal scaling
- **Backups:** Automate database backups
- **Monitoring:** Set up monitoring before deployment
- **Rollback:** Have rollback plan ready
- **Documentation:** Keep deployment docs updated

---

## 🔐 Security Best Practices

- Use secrets management (AWS Secrets Manager, etc.)
- Don't hardcode credentials
- Use least privilege for containers
- Scan Docker images for vulnerabilities
- Use HTTPS in production
- Set up firewall rules

---

**Agent Frankie - Ready to deploy! 🚀**

