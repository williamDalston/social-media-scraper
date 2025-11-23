# Getting Started - Complete Guide

Your step-by-step guide to getting the HHS Social Media Scraper running and getting the best possible results.

---

## 🎯 Goal

Get the system running and collecting high-quality social media data in under 30 minutes.

---

## 📋 Prerequisites Checklist

Before you start, ensure you have:

- [ ] **Docker Desktop** installed and running
- [ ] **Git** installed
- [ ] **Terminal/Command Prompt** access
- [ ] **Internet connection** for scraping
- [ ] **API keys** (optional, for YouTube scraping)

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone and Setup (1 min)

```bash
# Clone the repository
git clone <repository-url>
cd social-media-scraper

# Copy environment template
cp .env.example .env
```

### Step 2: Configure Environment (2 min)

```bash
# Generate secrets (run these commands)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Add to .env file (or edit manually)
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env
```

**Minimum `.env` configuration:**
```bash
SECRET_KEY=<generated-key>
JWT_SECRET_KEY=<generated-key>
DATABASE_PATH=social_media.db
```

### Step 3: Start Services (1 min)

```bash
# Using Makefile (recommended)
make build    # Build Docker images
make up       # Start all services
make init-db  # Initialize database
```

**Or using Docker Compose:**
```bash
docker-compose up -d
./scripts/init_db.sh
```

### Step 4: Verify Installation (1 min)

```bash
# Check services are running
make status

# Check health
make health

# View logs
make logs-app
```

**Expected output:**
- Services show "Up" status
- Health check returns 200 OK
- No error messages in logs

### Step 5: Access the Application

Open your browser: **http://localhost:5000**

You should see the dashboard!

---

## 👤 Setting Up Your First User

### Option 1: Auto-Create Admin (Recommended)

If enabled, the first user registered automatically becomes admin.

### Option 2: Manual Admin Creation

```bash
# Create admin user via command line
docker-compose exec app python -c "from auth.utils import create_default_admin; create_default_admin()"
```

### Option 3: Register via API

```bash
# Register via API
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "role": "Admin"
  }'
```

**Default credentials** (if auto-created):
- Username: `admin`
- Password: Check logs or reset manually

---

## 📊 Getting Your First Data

### Step 1: Add Accounts

**Option A: Upload CSV File**

Create `accounts.csv`:
```csv
Platform,Handle,Organization
X,@hhsgov,HHS
Instagram,hhsgov,HHS
Facebook,hhsgov,HHS
```

Upload via web interface or API:
```bash
# Get token first
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  | jq -r '.access_token')

# Upload accounts
curl -X POST http://localhost:5000/api/v1/accounts/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@accounts.csv"
```

**Option B: Use JSON File**

```bash
# Import from existing JSON
docker-compose exec app python -c "
from scraper.extract_accounts import populate_accounts
populate_accounts('hhs_accounts.json', 'social_media.db')
"
```

### Step 2: Run Your First Scrape

```bash
# Get your token
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  | jq -r '.access_token')

# Run scraper (simulated mode for testing)
curl -X POST http://localhost:5000/api/v1/jobs/run-scraper \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'
```

**What happens:**
- Scraper runs in background (or foreground in simulated mode)
- Collects metrics for all accounts
- Stores data in database
- Takes 1-5 minutes depending on account count

### Step 3: View Results

**Via Dashboard:**
1. Open http://localhost:5000
2. View summary metrics
3. Click on accounts to see history
4. Download data as CSV

**Via API:**
```bash
# Get summary
curl -X GET http://localhost:5000/api/v1/metrics/summary \
  -H "Authorization: Bearer $TOKEN"

# Get specific account history
curl -X GET http://localhost:5000/api/v1/metrics/history/X/@hhsgov \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🎯 Getting the Best Results

### 1. Configure Real Scraping (Not Simulated)

```bash
# In .env file
SCRAPER_MODE=real

# Add API keys for better results
YOUTUBE_API_KEY=your-youtube-api-key
TWITTER_BEARER_TOKEN=your-twitter-token  # Optional
```

### 2. Set Up Scheduled Scraping

Scraping runs automatically via Celery Beat:

```bash
# Check Celery Beat is running
make logs-beat

# View scheduled tasks
docker-compose exec app python -c "from celery_app import celery_app; print(celery_app.conf.beat_schedule)"
```

**Default schedule:**
- Daily scraping at 2 AM UTC
- Can be configured in `tasks/scheduled_tasks.py`

### 3. Optimize for Best Results

**Enable caching:**
```bash
REDIS_URL=redis://localhost:6379/0
CACHE_TYPE=redis
```

**Optimize scraper settings:**
```bash
SCRAPER_MAX_WORKERS=5        # Parallel workers
SCRAPER_TIMEOUT=30           # Request timeout
SCRAPER_RETRIES=3            # Retry attempts
```

### 4. Monitor Data Quality

```bash
# Check scraper health
curl http://localhost:5000/api/v1/jobs/status \
  -H "Authorization: Bearer $TOKEN"

# View admin dashboard
open http://localhost:5000/admin
```

---

## 📈 Optimizing for Production

### 1. Use PostgreSQL (Recommended)

```bash
# In .env
DATABASE_URL=postgresql://user:password@localhost:5432/social_media

# Update docker-compose.yml to include PostgreSQL service
```

### 2. Configure Redis Properly

```bash
# In .env
REDIS_URL=redis://:password@redis-host:6379/0

# Enable Redis persistence in docker-compose.yml
```

### 3. Set Up Monitoring

```bash
# Enable Sentry for error tracking
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
ENVIRONMENT=production

# Configure logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=/var/log/app.log
```

### 4. Configure Security

```bash
# Production security settings
SESSION_COOKIE_SECURE=True
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_STORAGE=redis://localhost:6379/0
```

---

## 🔄 Daily Workflow

### Morning Routine

1. **Check system health:**
   ```bash
   make health
   curl http://localhost:5000/health
   ```

2. **View overnight scraping results:**
   ```bash
   # Check dashboard or API
   open http://localhost:5000
   ```

3. **Review errors/alerts:**
   ```bash
   make logs-app
   # Check Sentry dashboard if configured
   ```

### Adding New Accounts

1. **Prepare CSV file** with new accounts
2. **Upload via web interface** or API
3. **Verify accounts** appear in dashboard
4. **Run scraper** manually or wait for scheduled run

### Monitoring

1. **Check scraper success rate:**
   - View admin dashboard
   - Check `/api/performance` endpoint

2. **Review data quality:**
   - Check for anomalies
   - Verify data completeness
   - Review data quality scores

3. **Monitor system resources:**
   - Check Docker stats: `docker stats`
   - Monitor database size
   - Check Redis memory usage

---

## 🎓 Learning Resources

### Understanding the System

1. **Read [README.md](./README.md)** - Project overview
2. **Review [CONFIGURATION.md](./CONFIGURATION.md)** - All configuration options
3. **Check [API_USAGE.md](./docs/API_USAGE.md)** - API documentation
4. **Explore Swagger UI** - http://localhost:5000/api/docs

### Troubleshooting

1. **Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Common issues
2. **View logs** - `make logs`
3. **Check health** - `make health`
4. **Review documentation** - See docs directory

---

## ✅ Success Checklist

You're ready for production when:

- [ ] All services running and healthy
- [ ] Database initialized with accounts
- [ ] Scraper successfully collecting data
- [ ] Dashboard showing metrics
- [ ] API endpoints working
- [ ] Authentication configured
- [ ] Monitoring in place
- [ ] Backups configured
- [ ] Documentation reviewed

---

## 🆘 Common First-Time Issues

### Issue: Can't access dashboard

**Solution:**
```bash
# Check if app is running
make status

# Check logs for errors
make logs-app

# Verify port is correct
curl http://localhost:5000/health
```

### Issue: No data after scraping

**Solution:**
```bash
# Check if scraper ran successfully
make logs-worker

# Verify accounts exist
docker-compose exec app python -c "
from scraper.schema import DimAccount
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
engine = init_db('social_media.db')
Session = sessionmaker(bind=engine)
session = Session()
accounts = session.query(DimAccount).all()
print(f'Found {len(accounts)} accounts')
"
```

### Issue: Authentication not working

**Solution:**
```bash
# Create admin user
docker-compose exec app python -c "from auth.utils import create_default_admin; create_default_admin()"

# Check JWT_SECRET_KEY is set
grep JWT_SECRET_KEY .env
```

---

## 📚 Next Steps

1. **Explore the Dashboard** - Familiarize yourself with the interface
2. **Try the API** - Use Swagger UI at `/api/docs`
3. **Upload Your Accounts** - Add your social media accounts
4. **Run a Scrape** - Test the scraper
5. **Review Data** - Check the results
6. **Configure Automation** - Set up scheduled scraping
7. **Optimize Settings** - Adjust for your needs
8. **Monitor Performance** - Use admin dashboard

---

## 🎯 Pro Tips for Best Results

1. **Use Real Scraping Mode** for actual data (not simulated)
2. **Configure API Keys** for platforms that require them (YouTube, Twitter)
3. **Enable Redis Caching** for faster performance
4. **Set Up Scheduled Scraping** for regular data collection
5. **Monitor Scraper Health** to catch issues early
6. **Review Data Quality** regularly
7. **Optimize Worker Count** based on your resources
8. **Use PostgreSQL** for production (better performance)

---

**You're all set! Happy scraping! 🚀**

For detailed information, see:
- [README.md](./README.md) - Project overview
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Troubleshooting help

