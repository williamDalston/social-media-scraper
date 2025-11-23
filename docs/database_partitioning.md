# Database Partitioning Strategies

## Overview

This document describes partitioning strategies for improving database performance with large datasets.

## Partitioning Types

### 1. Date-Based Partitioning

Partition `fact_followers_snapshot` table by `snapshot_date`:

```sql
-- PostgreSQL example
CREATE TABLE fact_followers_snapshot (
    snapshot_id SERIAL,
    account_key INTEGER,
    snapshot_date DATE,
    followers_count INTEGER,
    -- ... other columns
    PRIMARY KEY (snapshot_id, snapshot_date)
) PARTITION BY RANGE (snapshot_date);

-- Create monthly partitions
CREATE TABLE fact_followers_snapshot_2024_01 
    PARTITION OF fact_followers_snapshot
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE fact_followers_snapshot_2024_02 
    PARTITION OF fact_followers_snapshot
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

### 2. Platform-Based Partitioning

Partition by platform for better query performance:

```sql
-- Hash partitioning by platform
CREATE TABLE dim_account (
    account_key SERIAL,
    platform VARCHAR,
    handle VARCHAR,
    -- ... other columns
    PRIMARY KEY (account_key, platform)
) PARTITION BY HASH (platform);

-- Create partitions for each platform
CREATE TABLE dim_account_x 
    PARTITION OF dim_account
    FOR VALUES WITH (MODULUS 5, REMAINDER 0);

CREATE TABLE dim_account_instagram 
    PARTITION OF dim_account
    FOR VALUES WITH (MODULUS 5, REMAINDER 1);
```

### 3. Account-Based Partitioning

For very large account datasets:

```sql
-- Range partitioning by account_key
CREATE TABLE fact_followers_snapshot (
    -- ... columns
) PARTITION BY RANGE (account_key);

CREATE TABLE fact_followers_snapshot_0_1000 
    PARTITION OF fact_followers_snapshot
    FOR VALUES FROM (0) TO (1000);
```

## Implementation Strategy

### Phase 1: Date Partitioning (Recommended First)

1. **Benefits:**
   - Most queries filter by date
   - Easy to archive old partitions
   - Improves query performance significantly

2. **Implementation:**
```python
# Migration script
def create_date_partitions():
    """Create monthly partitions for fact_followers_snapshot."""
    from datetime import datetime, timedelta
    from sqlalchemy import text
    
    current_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 1, 1)
    
    while current_date < end_date:
        next_month = current_date + timedelta(days=32)
        next_month = next_month.replace(day=1)
        
        partition_name = f"fact_followers_snapshot_{current_date.strftime('%Y_%m')}"
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name} 
        PARTITION OF fact_followers_snapshot
        FOR VALUES FROM ('{current_date.date()}') TO ('{next_month.date()}');
        """
        
        # Execute SQL
        # ...
        
        current_date = next_month
```

### Phase 2: Platform Partitioning

For platforms with high data volume (X, Instagram):

```python
def create_platform_partitions():
    """Create platform-specific partitions."""
    platforms = ['x', 'instagram', 'facebook', 'youtube', 'linkedin']
    
    for platform in platforms:
        partition_name = f"fact_followers_snapshot_{platform}"
        # Create partition for platform
        # ...
```

## Maintenance

### Automatic Partition Creation

```python
def create_future_partitions(months_ahead: int = 3):
    """Create partitions for future months."""
    from datetime import datetime, timedelta
    
    current = datetime.now().replace(day=1)
    for i in range(months_ahead):
        month = current + timedelta(days=32 * i)
        month = month.replace(day=1)
        create_partition_for_month(month)
```

### Partition Archival

```python
def archive_old_partitions(months_to_keep: int = 12):
    """Archive partitions older than N months."""
    cutoff_date = datetime.now() - timedelta(days=30 * months_to_keep)
    
    # Detach old partitions
    # Move to archive storage
    # Update indexes
```

## Query Optimization

### Partition Pruning

Queries automatically benefit from partition pruning:

```python
# This query only scans relevant partitions
session.query(FactFollowersSnapshot).filter(
    FactFollowersSnapshot.snapshot_date >= date(2024, 1, 1),
    FactFollowersSnapshot.snapshot_date < date(2024, 2, 1)
).all()
```

### Index Strategy

Create indexes on partition key columns:

```sql
-- Index on partition key
CREATE INDEX idx_snapshot_date ON fact_followers_snapshot(snapshot_date);

-- Composite index for common queries
CREATE INDEX idx_account_date ON fact_followers_snapshot(account_key, snapshot_date);
```

## Performance Benefits

- **Query Performance**: 10-100x faster for date-range queries
- **Maintenance**: Easier to manage large datasets
- **Archival**: Simple to archive old data
- **Parallel Processing**: Partitions can be processed in parallel

## Considerations

### SQLite Limitations

SQLite doesn't support native partitioning. For SQLite:
- Use separate tables per time period
- Implement application-level partitioning
- Consider migrating to PostgreSQL for production

### Migration Path

1. Start with date partitioning (biggest impact)
2. Monitor query performance
3. Add platform partitioning if needed
4. Consider account-based partitioning for very large datasets

## Monitoring

Track partition usage and performance:

```python
def get_partition_stats():
    """Get statistics for each partition."""
    return {
        'partition_sizes': {...},
        'query_performance': {...},
        'oldest_partition': ...,
        'newest_partition': ...
    }
```

