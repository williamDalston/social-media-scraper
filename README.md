# HHS Social Media Scraper

A production-ready social media scraping and analytics platform for tracking HHS (Health and Human Services) social media accounts across multiple platforms.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.1+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🚀 Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone the repository
git clone <repository-url>
cd social-media-scraper

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your settings
nano .env

# 4. Start with Docker Compose
docker-compose up -d

# 5. Initialize database
./scripts/init_db.sh

# 6. Access the application
open http://localhost:5000
```

**Or use the Makefile:**
```bash
make build    # Build Docker images
make up       # Start services
make init-db  # Initialize database
make help     # See all commands
```

📖 **For detailed instructions, see [QUICK_START.md](./QUICK_START.md)**

---

## ✨ Features

### 🎯 Core Capabilities
- **Multi-Platform Scraping**: X (Twitter), Instagram, Facebook, LinkedIn, YouTube, Truth Social, TikTok, Reddit
- **Real-Time Metrics**: Follower counts, engagement metrics, post analytics
- **Historical Tracking**: Time-series data with historical trends
- **Background Processing**: Async job processing with Celery
- **RESTful API**: Complete API with OpenAPI/Swagger documentation
- **Dashboard**: Interactive web dashboard for data visualization

### 🔒 Security
- **JWT Authentication**: Secure token-based authentication
- **OAuth2 Support**: Google, Microsoft, GitHub OAuth integration
- **MFA/2FA**: Multi-factor authentication with TOTP
- **Role-Based Access Control**: Admin, Editor, Viewer roles
- **Rate Limiting**: API rate limiting to prevent abuse
- **Security Headers**: CSRF protection, CORS, security headers

### 📊 Observability
- **Structured Logging**: JSON and text format logging
- **Error Tracking**: Sentry integration for error monitoring
- **Health Checks**: Kubernetes-ready health endpoints
- **Metrics**: Prometheus metrics for monitoring
- **Distributed Tracing**: OpenTelemetry tracing support
- **Admin Dashboard**: Real-time system monitoring

### ⚡ Performance
- **Redis Caching**: Multi-level caching for fast responses
- **Database Optimization**: Indexed queries, connection pooling
- **Parallel Scraping**: Concurrent scraping for efficiency
- **Response Compression**: Gzip compression for API responses
- **Pagination**: Efficient data pagination

### 🧪 Quality Assurance
- **Comprehensive Testing**: Unit, integration, E2E, load tests
- **Test Coverage**: 80%+ code coverage
- **CI/CD**: GitHub Actions automation
- **Property-Based Testing**: Hypothesis testing
- **Security Testing**: OWASP compliance

### 🚀 Deployment
- **Docker**: Complete Docker setup with Docker Compose
- **Kubernetes**: K8s manifests and Helm charts
- **Infrastructure as Code**: Terraform templates for AWS, GCP, Azure
- **Database Migrations**: Alembic migration system
- **Zero-Downtime Deployments**: Blue-green and canary deployments

---

## 📁 Project Structure

```
social-media-scraper/
├── api/                    # API layer (Flask-RESTX, validation)
│   ├── v1/                # Versioned API endpoints
│   ├── schemas.py         # Marshmallow schemas
│   └── errors.py          # Custom exceptions
├── auth/                   # Authentication & authorization
│   ├── oauth.py           # OAuth2 implementation
│   ├── mfa.py             # MFA/TOTP implementation
│   └── decorators.py      # Auth decorators
├── scraper/                # Scraping engine
│   ├── platforms/         # Platform-specific scrapers
│   ├── utils/             # Scraper utilities
│   └── schema.py          # Database models
├── tasks/                  # Celery background tasks
├── cache/                  # Caching layer
├── config/                 # Configuration management
├── middleware/             # Request middleware
├── models/                 # Database models
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Deployment scripts
├── k8s/                    # Kubernetes manifests
├── helm/                   # Helm charts
└── terraform/              # Infrastructure as code
```

---

## 📚 Documentation

### Getting Started
- **[QUICK_START.md](./QUICK_START.md)** - Get started in 5 minutes
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Detailed deployment guide
- **[CONFIGURATION.md](./CONFIGURATION.md)** - Configuration reference
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Common issues and solutions

### API Documentation
- **[API Usage Guide](./docs/API_USAGE.md)** - Complete API documentation
- **[Swagger UI](http://localhost:5000/api/docs)** - Interactive API explorer (when running)
- **[Postman Collection](./docs/postman_collection.json)** - Import for API testing

### Development
- **[TESTING.md](./TESTING.md)** - Testing guide and best practices
- **[SECURITY.md](./SECURITY.md)** - Security documentation
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Contribution guidelines

### Infrastructure
- **[INFRASTRUCTURE.md](./INFRASTRUCTURE.md)** - Infrastructure overview
- **[DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md)** - Disaster recovery procedures
- **[k8s/README.md](./k8s/README.md)** - Kubernetes deployment guide

### Agent Tasks
- **[AGENT_ASSIGNMENTS.md](./AGENT_ASSIGNMENTS.md)** - Agent task overview
- **[PHASE_3_OVERVIEW.md](./PHASE_3_OVERVIEW.md)** - Phase 3 tasks overview
- **[agent_tasks/](./agent_tasks/)** - Detailed agent task files

---

## 🔧 Configuration

### Environment Variables

See **[CONFIGURATION.md](./CONFIGURATION.md)** for complete configuration reference.

**Required:**
```bash
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_PATH=social_media.db
```

**Optional:**
```bash
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=your-sentry-dsn
```

---

## 🏃 Running the Application

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Initialize database
python -c "from scraper.schema import init_db; init_db('social_media.db')"

# Run the application
python app.py
```

### Makefile Commands

```bash
make help       # Show all available commands
make build      # Build Docker images
make up         # Start services
make down       # Stop services
make logs       # View logs
make test       # Run tests
make migrate    # Run database migrations
make backup     # Backup database
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scraper --cov=app --cov-report=html

# Run specific test category
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m e2e              # End-to-end tests only

# Run load tests
locust -f tests/load/locustfile.py
```

📖 **See [TESTING.md](./TESTING.md) for detailed testing guide**

---

## 📊 Project Status

### Phase 1: ✅ COMPLETE
- Security and authentication
- Testing infrastructure
- Scraper implementation
- Task queue integration
- Observability and monitoring
- DevOps setup
- API documentation
- Performance optimization

### Phase 2: ⏳ IN PROGRESS
- Advanced features (OAuth2, MFA)
- Enhanced testing (load, E2E)
- Advanced scrapers (sentiment, content)
- Kubernetes deployment
- Distributed tracing
- Advanced caching

### Phase 3: 🚀 READY TO START
- Production readiness
- Scraper optimization for best results
- Operational excellence
- Performance tuning

📖 **See [PHASE_3_OVERVIEW.md](./PHASE_3_OVERVIEW.md) for Phase 3 details**

---

## 🌐 Supported Platforms

- **X (Twitter)** - Follower counts, engagement metrics
- **Instagram** - Follower counts, post metrics
- **Facebook** - Page likes, engagement
- **LinkedIn** - Follower counts, engagement
- **YouTube** - Subscriber counts, view metrics
- **Truth Social** - Follower counts, engagement
- **TikTok** - Follower counts, video metrics
- **Reddit** - Subscriber counts, engagement

---

## 🛠️ Technology Stack

### Backend
- **Flask** - Web framework
- **SQLAlchemy** - ORM
- **Celery** - Background job processing
- **Redis** - Caching and message broker
- **Flask-RESTX** - API framework with Swagger

### Security
- **PyJWT** - JWT authentication
- **bcrypt** - Password hashing
- **Flask-Limiter** - Rate limiting
- **Flask-CORS** - CORS support

### Observability
- **Sentry** - Error tracking
- **Prometheus** - Metrics
- **OpenTelemetry** - Distributed tracing
- **Python JSON Logger** - Structured logging

### Testing
- **pytest** - Testing framework
- **Hypothesis** - Property-based testing
- **Locust** - Load testing
- **Playwright** - E2E testing

### Deployment
- **Docker** - Containerization
- **Kubernetes** - Orchestration
- **Helm** - Package management
- **Terraform** - Infrastructure as code

---

## 📖 Usage Examples

### Upload Accounts

```bash
# Upload CSV file with accounts
curl -X POST http://localhost:5000/api/v1/accounts/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@accounts.csv"
```

### Run Scraper

```bash
# Run scraper in simulated mode
curl -X POST http://localhost:5000/api/v1/jobs/run-scraper \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'
```

### Get Metrics

```bash
# Get summary metrics
curl -X GET http://localhost:5000/api/v1/metrics/summary \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get account history
curl -X GET http://localhost:5000/api/v1/metrics/history/X/@hhsgov \
  -H "Authorization: Bearer YOUR_TOKEN"
```

📖 **See [docs/API_USAGE.md](./docs/API_USAGE.md) for complete API examples**

---

## 🔐 Security

The application implements comprehensive security features:

- ✅ JWT authentication with refresh tokens
- ✅ OAuth2/OpenID Connect support
- ✅ Multi-factor authentication (MFA/TOTP)
- ✅ Role-based access control (RBAC)
- ✅ API rate limiting
- ✅ CSRF protection
- ✅ Security headers
- ✅ Input validation and sanitization
- ✅ Security audit logging

📖 **See [SECURITY.md](./SECURITY.md) for detailed security documentation**

---

## 🚨 Troubleshooting

Common issues and solutions:

**Services won't start:**
```bash
make logs        # Check logs
make config      # Validate configuration
```

**Database issues:**
```bash
make init-db     # Re-initialize database
make migrate     # Run migrations
```

**Port conflicts:**
- Change `APP_PORT` in `.env` file

📖 **See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for complete troubleshooting guide**

---

## 📈 Performance

Current performance targets:
- ✅ API response time < 2s (p95)
- ✅ Scraper success rate > 95%
- ✅ Data accuracy > 98%
- ✅ Cache hit rate > 80%
- ✅ Uptime target: 99.9%+

📖 **See [docs/PERFORMANCE_OPTIMIZATION_GUIDE.md](./docs/PERFORMANCE_OPTIMIZATION_GUIDE.md) for optimization tips**

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd social-media-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If exists

# Run tests
pytest

# Run in development mode
export FLASK_ENV=development
python app.py
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Documentation**: See the [docs/](./docs/) directory
- **Issues**: Report issues in the issue tracker
- **Questions**: Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## 🔗 Quick Links

### Getting Started
- 📖 [Getting Started Guide](./GETTING_STARTED.md) - Complete step-by-step guide
- ⚡ [Quick Start](./QUICK_START.md) - 5-minute quick start
- 🔧 [Configuration Reference](./CONFIGURATION.md) - All configuration options
- 🆘 [Troubleshooting Guide](./TROUBLESHOOTING.md) - Common issues and solutions

### Documentation
- 🚀 [Deployment Guide](./DEPLOYMENT.md) - Production deployment
- 📚 [API Documentation](./docs/API_USAGE.md) - Complete API reference
- 🧪 [Testing Guide](./TESTING.md) - Testing documentation
- 🔒 [Security Guide](./SECURITY.md) - Security documentation
- 📊 [Project Status](./PROJECT_STATUS.md) - Current project status

### Development
- 🤝 [Contributing Guide](./CONTRIBUTING.md) - How to contribute
- 📊 [Phase 3 Overview](./PHASE_3_OVERVIEW.md) - Phase 3 tasks
- 🎯 [Agent Assignments](./AGENT_ASSIGNMENTS.md) - Agent task overview

---

## 🎯 Next Steps

1. **Read [QUICK_START.md](./QUICK_START.md)** to get started
2. **Configure your environment** - See [CONFIGURATION.md](./CONFIGURATION.md)
3. **Upload accounts** - Use the web interface or API
4. **Run your first scrape** - See usage examples above
5. **Explore the dashboard** - Access at `http://localhost:5000`
6. **Check API docs** - Visit `http://localhost:5000/api/docs`

---

**Ready to get started? Jump to [QUICK_START.md](./QUICK_START.md) 🚀**

