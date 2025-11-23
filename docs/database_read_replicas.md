# Database Read Replica Configuration

## Overview

This document describes how to configure and use read replicas for scaling database read operations.

## Architecture

### Primary Database
- Handles all write operations
- Single source of truth
- Located at: `DATABASE_URL`

### Read Replicas
- Handle read-only queries
- Improve read performance
- Reduce load on primary database
- Located at: `DATABASE_READ_REPLICA_URL`

## Configuration

### Environment Variables

```bash
# Primary database (writes)
DATABASE_URL=postgresql://user:pass@primary-db:5432/social_media

# Read replica (reads)
DATABASE_READ_REPLICA_URL=postgresql://user:pass@replica-db:5432/social_media

# Enable read replica routing
ENABLE_READ_REPLICA=true
```

### Implementation

The application automatically routes read queries to read replicas when configured:

```python
from scraper.schema import get_read_session, get_write_session

# For read operations (uses replica)
session = get_read_session()
accounts = session.query(DimAccount).all()

# For write operations (uses primary)
session = get_write_session()
session.add(new_account)
session.commit()
```

## Setup Instructions

### PostgreSQL

1. **Set up replication:**
```sql
-- On primary database
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET max_replication_slots = 3;

-- Create replication user
CREATE USER replicator WITH REPLICATION PASSWORD 'password';
GRANT CONNECTION ON DATABASE social_media TO replicator;
```

2. **Configure replica:**
```bash
# On replica server
pg_basebackup -h primary-db -D /var/lib/postgresql/data -U replicator -P -W -R
```

3. **Start replica:**
```bash
systemctl start postgresql
```

### MySQL

1. **Configure primary:**
```ini
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
```

2. **Create replication user:**
```sql
CREATE USER 'replicator'@'%' IDENTIFIED BY 'password';
GRANT REPLICATION SLAVE ON *.* TO 'replicator'@'%';
FLUSH PRIVILEGES;
```

3. **Configure replica:**
```sql
CHANGE MASTER TO
  MASTER_HOST='primary-db',
  MASTER_USER='replicator',
  MASTER_PASSWORD='password',
  MASTER_LOG_FILE='mysql-bin.000001',
  MASTER_LOG_POS=0;

START SLAVE;
```

## Usage in Code

### Automatic Routing

The application automatically uses read replicas for:
- `GET` requests (read operations)
- Query operations that don't modify data

### Manual Routing

For explicit control:

```python
from scraper.schema import get_read_engine, get_write_engine

# Read from replica
read_engine = get_read_engine()
read_session = sessionmaker(bind=read_engine)()

# Write to primary
write_engine = get_write_engine()
write_session = sessionmaker(bind=write_engine)()
```

## Monitoring

### Replication Lag

Monitor replication lag to ensure data freshness:

```sql
-- PostgreSQL
SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;

-- MySQL
SHOW SLAVE STATUS\G
-- Check Seconds_Behind_Master
```

### Health Checks

The application includes health checks for replica status:

```python
from scraper.schema import check_replica_health

health = check_replica_health()
# Returns: {'status': 'healthy', 'lag_seconds': 0.5}
```

## Best Practices

1. **Use read replicas for:**
   - Dashboard queries
   - Reporting queries
   - Analytics queries
   - Read-heavy endpoints

2. **Use primary for:**
   - All write operations
   - Transactions
   - Critical reads requiring latest data

3. **Monitor replication lag:**
   - Alert if lag > 5 seconds
   - Route to primary if lag too high

4. **Load balancing:**
   - Use multiple read replicas
   - Distribute read load evenly
   - Implement health checks

## Troubleshooting

### Replica Not Available

If replica is unavailable, the application automatically falls back to primary database.

### High Replication Lag

1. Check network connectivity
2. Verify replica server resources
3. Review primary database load
4. Consider adding more replicas

### Data Inconsistency

1. Verify replication is working
2. Check for replication errors
3. Monitor replication lag
4. Consider using primary for critical reads

## Performance Benefits

- **Reduced primary load**: 30-50% reduction in read queries
- **Improved response times**: Lower latency for read operations
- **Better scalability**: Add replicas as needed
- **High availability**: Continue serving reads if primary fails

## Limitations

- **Eventual consistency**: Replicas may lag behind primary
- **Write operations**: Must always use primary
- **Transactions**: Cannot span primary and replica
- **Complexity**: Additional infrastructure to manage

