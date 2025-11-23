# Quick Start Guide

Get the Social Media Scraper up and running in minutes!

## Prerequisites

- Docker and Docker Compose installed
- Git (for cloning)

## 1. Clone and Setup

```bash
git clone <repository-url>
cd social-media-scraper
cp .env.example .env
```

## 2. Configure Environment

Edit `.env` file and set at minimum:
- `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `JWT_SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

## 3. Start Services

**Option A: Using Makefile (Recommended)**
```bash
make build    # Build Docker images
make up       # Start services
make init-db  # Initialize database
```

**Option B: Using Docker Compose directly**
```bash
docker-compose up -d
./scripts/init_db.sh
```

## 4. Verify Installation

```bash
# Check service status
make status
# or
docker-compose ps

# Check health
make health
# or
curl http://localhost:5000/health

# View logs
make logs
# or
docker-compose logs -f
```

## 5. Access the Application

Open your browser to: `http://localhost:5000`

## Common Commands

```bash
# View all available commands
make help

# Service management
make start      # Start services
make stop       # Stop services
make restart    # Restart services

# Database
make migrate    # Run migrations
make backup     # Backup database

# Development
make dev        # Start with development settings
make test       # Run tests

# Logs
make logs       # All services
make logs-app   # App only
```

## Next Steps

1. **Create an admin user** (if not auto-created):
   ```bash
   docker-compose exec app python -c "from auth.utils import create_default_admin; create_default_admin()"
   ```

2. **Upload accounts** via the web interface or API

3. **Run your first scrape**:
   ```bash
   curl -X POST http://localhost:5000/api/run-scraper \
     -H "Content-Type: application/json" \
     -d '{"mode": "simulated"}'
   ```

## Troubleshooting

**Services won't start:**
```bash
make logs  # Check logs for errors
make config  # Validate configuration
```

**Database issues:**
```bash
make init-db  # Re-initialize database
```

**Port already in use:**
- Change `APP_PORT` in `.env` file
- Update `docker-compose.yml` port mapping

**Need help?**
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed documentation
- Review logs: `make logs`
- Check health: `make health`

## Development Mode

For development with auto-reload:

```bash
# Copy development override
cp docker-compose.override.yml.example docker-compose.override.yml

# Start in dev mode
make dev
```

This enables:
- Code auto-reload
- Debug logging
- Reduced worker concurrency

---

**That's it! You're ready to go! 🚀**

