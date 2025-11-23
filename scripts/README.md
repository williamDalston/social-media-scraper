# Deployment Scripts

This directory contains scripts for deploying and managing the Social Media Scraper application.

## Scripts

### `deploy.sh`
Automated deployment script that handles:
- Database backups
- Code updates
- Dependency installation
- Database migrations
- Docker image building
- Service restart
- Health checks
- Cleanup of old backups

**Usage:**
```bash
./scripts/deploy.sh
```

### `backup_db.sh`
Creates timestamped database backups with automatic compression and cleanup.

**Usage:**
```bash
./scripts/backup_db.sh
```

**Features:**
- Supports SQLite, PostgreSQL, and MySQL
- Automatic compression
- Retention policy (keeps last 30 days)
- Timestamped backup files

### `restore_db.sh`
Restores database from a backup file.

**Usage:**
```bash
./scripts/restore_db.sh <backup_file>
```

**Example:**
```bash
./scripts/restore_db.sh backups/db_backup_20240101_120000.db
```

**Safety Features:**
- Creates backup of current database before restore
- Requires confirmation before proceeding
- Validates backup file exists

### `start.sh`
Service management script for starting, stopping, restarting, and checking status of services.

**Usage:**
```bash
./scripts/start.sh {start|stop|restart|status}
```

**Examples:**
```bash
./scripts/start.sh start    # Start all services
./scripts/start.sh stop     # Stop all services
./scripts/start.sh restart  # Restart all services
./scripts/start.sh status   # Check service status
```

**Supported Methods:**
- Docker Compose (preferred)
- systemd services
- Manual process management

### `init_db.sh`
Database initialization script that creates the database, runs migrations, and optionally creates an initial admin user.

**Usage:**
```bash
./scripts/init_db.sh
```

**Features:**
- Creates database directory if needed
- Runs all pending migrations
- Optionally creates admin user (set CREATE_ADMIN=true in .env)

### `migrate.sh`
Convenient wrapper for Alembic migration commands.

**Usage:**
```bash
./scripts/migrate.sh {upgrade|downgrade|create|history|current|show|stamp} [args]
```

**Examples:**
```bash
./scripts/migrate.sh upgrade              # Upgrade to latest
./scripts/migrate.sh downgrade -1         # Downgrade by one
./scripts/migrate.sh create "add column" # Create new migration
./scripts/migrate.sh history              # Show migration history
./scripts/migrate.sh current              # Show current version
```

## Permissions

All scripts are executable. If you encounter permission errors:

```bash
chmod +x scripts/*.sh
```

## Requirements

- Bash shell
- Appropriate permissions for file operations
- Database client tools (for PostgreSQL/MySQL backups)
- Docker and Docker Compose (for Docker-based deployments)

## Notes

- Scripts automatically load environment variables from `.env` file
- Logs are written to `logs/` directory
- Backups are stored in `backups/` directory
- PID files are stored in `pids/` directory (for manual process management)

