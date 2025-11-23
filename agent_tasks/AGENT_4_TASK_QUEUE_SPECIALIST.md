# Agent 4: TASK_QUEUE_SPECIALIST (Dana)
## Production Enhancement: Background Jobs & Task Queue

### 🎯 Mission
Implement Celery-based task queue system for asynchronous scraping, scheduled tasks, and job status tracking to improve system scalability and user experience.

---

## 📋 Detailed Tasks

### 1. Celery Setup

#### 1.1 Celery Configuration
- **File:** `celery_app.py`
- Configure:
  - Redis broker URL (from environment)
  - Result backend (Redis)
  - Task serialization (JSON)
  - Timezone settings
  - Task routing
  - Task priorities

#### 1.2 Task Definitions
- **File:** `tasks/__init__.py`
- Initialize Celery app
- Import all task modules

#### 1.3 Scraper Tasks
- **File:** `tasks/scraper_tasks.py`
- Tasks:
  - `scrape_account(account_key)` - Scrape single account
  - `scrape_all_accounts()` - Scrape all accounts
  - `scrape_platform(platform)` - Scrape accounts for specific platform
  - `backfill_account(account_key, days)` - Backfill history for account

---

### 2. Background Job Processing

#### 2.1 Async Scraper Execution
- Move scraper execution to Celery tasks
- Make `/api/run-scraper` endpoint trigger async task
- Return job ID immediately
- Process scraping in background

#### 2.2 Task Status Tracking
- **File:** `models/job.py`
- Job model with:
  - `job_id` (Celery task ID)
  - `job_type` (scrape_all, scrape_account, etc.)
  - `status` (pending, running, completed, failed)
  - `progress` (percentage)
  - `result` (JSON)
  - `error_message`
  - `created_at`, `started_at`, `completed_at`
  - `account_key` (if applicable)

#### 2.3 Job Progress Updates
- Update job progress during execution
- Track accounts processed
- Report completion percentage
- Store intermediate results

---

### 3. Scheduled Tasks

#### 3.1 Celery Beat Configuration
- **File:** `celery_app.py` (add beat schedule)
- Scheduled tasks:
  - Daily scraping at 2 AM (configurable)
  - Weekly backfill check
  - Cleanup old jobs (monthly)

#### 3.2 Periodic Tasks
- **File:** `tasks/scheduled_tasks.py`
- Tasks:
  - `daily_scrape_all()` - Run daily metrics collection
  - `cleanup_old_jobs()` - Remove jobs older than 30 days
  - `health_check()` - Verify system health

#### 3.3 Timezone Configuration
- Use UTC for all scheduled tasks
- Convert to local timezone for display
- Handle daylight saving time

---

### 4. Job Management API

#### 4.1 Job Endpoints
- **File:** `app.py` (add routes)
- Endpoints:
  - `POST /api/jobs/scrape-all` - Start scrape all job
  - `POST /api/jobs/scrape-account/<account_key>` - Start single account job
  - `GET /api/jobs/<job_id>` - Get job status
  - `GET /api/jobs` - List all jobs (with pagination)
  - `POST /api/jobs/<job_id>/cancel` - Cancel running job
  - `DELETE /api/jobs/<job_id>` - Delete completed job

#### 4.2 Job Status Response
- Return:
  - Job ID
  - Status
  - Progress percentage
  - Result data
  - Error message (if failed)
  - Timestamps

#### 4.3 WebSocket Support (Optional)
- Real-time job progress updates
- Use Flask-SocketIO or similar
- Push updates to frontend

---

### 5. Error Handling & Retries

#### 5.1 Task Retry Logic
- Configure Celery retry:
  - Max retries: 3
  - Retry delay: exponential backoff
  - Retry on specific exceptions
  - Dead letter queue for failed tasks

#### 5.2 Error Logging
- Log all task failures
- Store error details in job record
- Send alerts for critical failures (optional)

#### 5.3 Task Timeouts
- Set task timeouts per task type
- Kill long-running tasks
- Handle timeout gracefully

---

## 📁 File Structure to Create

```
tasks/
├── __init__.py
├── scraper_tasks.py          # Scraper-related tasks
├── scheduled_tasks.py        # Periodic tasks
└── utils.py                  # Task utilities

models/
└── job.py                    # Job tracking model

celery_app.py                 # Celery configuration
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
celery>=5.3.0
redis>=5.0.0
flower>=2.0.0                 # Optional: Celery monitoring
```

---

## ✅ Acceptance Criteria

- [ ] Celery is configured and running
- [ ] Scraper tasks run asynchronously
- [ ] Job status is tracked in database
- [ ] Scheduled tasks run on schedule
- [ ] Job management API works
- [ ] Tasks can be cancelled
- [ ] Error handling and retries work
- [ ] Job history is maintained

---

## 🧪 Testing Requirements

- Test task execution
- Test job status tracking
- Test scheduled tasks
- Test job cancellation
- Test error handling
- Test retry logic
- Integration tests with Redis

---

## 📝 Implementation Details

### Celery Worker Command:
```bash
celery -A celery_app worker --loglevel=info
```

### Celery Beat Command:
```bash
celery -A celery_app beat --loglevel=info
```

### Example Task:
```python
@celery_app.task(bind=True, max_retries=3)
def scrape_account(self, account_key):
    try:
        # Scraping logic
        self.update_state(state='PROGRESS', meta={'progress': 50})
        # More scraping
        return {'status': 'completed', 'result': data}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-4-task-queue`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up Redis (local or Docker)
4. Create Celery app configuration
5. Create job model
6. Convert scraper to Celery tasks
7. Add job management API
8. Set up scheduled tasks
9. Test with workers
10. Update documentation

---

## 🔧 Redis Setup

### Docker (Recommended):
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Environment Variables:
```
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## 📊 Monitoring

### Flower (Optional):
- Web UI for monitoring Celery
- View task status, workers, queues
- Access at: `http://localhost:5555`

### Job Dashboard:
- Create admin page showing:
  - Active jobs
  - Job history
  - Queue status
  - Worker status

---

## ⚠️ Important Considerations

- **Redis Persistence:** Configure Redis persistence for production
- **Worker Scaling:** Can run multiple workers for parallel processing
- **Task Priorities:** Assign priorities to different task types
- **Resource Limits:** Set memory/CPU limits for workers
- **Monitoring:** Monitor queue length and worker health
- **Error Recovery:** Handle worker crashes gracefully

---

**Agent Dana - Ready to queue it up! ⚙️**

