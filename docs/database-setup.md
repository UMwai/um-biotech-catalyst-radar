# PostgreSQL Database Setup Guide

This guide walks you through setting up the PostgreSQL database for Biotech Catalyst Radar.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Running Migrations](#running-migrations)
5. [Database Schema](#database-schema)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- PostgreSQL 13+ installed
- Python 3.9+ with `psycopg2-binary` package
- Environment variables configured (see `.env.example`)

### 1-Minute Setup (Local Development)

```bash
# Install PostgreSQL (macOS)
brew install postgresql@14
brew services start postgresql@14

# Create database
createdb biotech_radar

# Set environment variable
export DATABASE_URL="postgresql://localhost:5432/biotech_radar"

# Run migrations
psql $DATABASE_URL < migrations/001_initial_schema.sql
psql $DATABASE_URL < migrations/002_indexes.sql

# (Optional) Load seed data for testing
psql $DATABASE_URL < migrations/003_seed_data.sql

# Verify setup
python -c "from src.utils.db import check_database_health; print(check_database_health())"
```

---

## Local Development

### Option 1: PostgreSQL via Homebrew (macOS)

```bash
# Install
brew install postgresql@14

# Start service
brew services start postgresql@14

# Create database and user
createdb biotech_radar
createuser -s postgres  # If postgres user doesn't exist

# Set password (optional)
psql -d biotech_radar -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

### Option 2: PostgreSQL via Docker

```bash
# Run PostgreSQL container
docker run -d \
  --name biotech-postgres \
  -e POSTGRES_DB=biotech_radar \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:14

# Verify connection
docker exec -it biotech-postgres psql -U postgres -d biotech_radar -c "SELECT version();"
```

**Docker Compose** (recommended):

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:14
    container_name: biotech-postgres
    environment:
      POSTGRES_DB: biotech_radar
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d  # Auto-run migrations

volumes:
  pgdata:
```

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop
docker-compose down
```

### Option 3: PostgreSQL via Ubuntu/Linux

```bash
# Install
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb biotech_radar
sudo -u postgres createuser -s $USER

# Set password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

---

## Production Deployment

### Recommended Hosting Providers

| Provider | Free Tier | Pros | Cons |
|----------|-----------|------|------|
| **Supabase** | 500 MB, 2 projects | Generous free tier, managed backups, dashboard | Limited storage |
| **Render** | 90 days free, then $7/mo | Easy setup, auto-sleep disabled | Paid only after trial |
| **Railway** | $5/mo free credit | Fast, git-based deploys | Requires credit card |
| **Neon** | 10 GB free | Serverless, branching | Beta product |
| **Heroku Postgres** | 10k rows free | Rock solid, mature | Row limit restrictive |

### Setup: Supabase (Recommended)

1. **Create project**: https://app.supabase.com/
2. **Get connection string**:
   - Go to Settings → Database
   - Copy **Connection String** (URI format)
   - Replace `[YOUR-PASSWORD]` with your database password
3. **Run migrations**:
   ```bash
   # Using psql
   export DATABASE_URL="postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres"
   psql $DATABASE_URL < migrations/001_initial_schema.sql
   psql $DATABASE_URL < migrations/002_indexes.sql
   ```
4. **Set environment variable** in your deployment platform:
   ```
   DATABASE_URL=postgresql://postgres:[password]@db.[project-id].supabase.co:5432/postgres
   ```

### Setup: Render

1. **Create PostgreSQL instance**: https://dashboard.render.com/
   - Click **New** → **PostgreSQL**
   - Choose **Free** plan (or Starter at $7/mo)
   - Database name: `biotech_radar`
2. **Get internal connection string**:
   - Copy **Internal Database URL**
3. **Run migrations** via Render Shell:
   ```bash
   # Open Shell from Render dashboard
   psql $DATABASE_URL < migrations/001_initial_schema.sql
   psql $DATABASE_URL < migrations/002_indexes.sql
   ```
4. **Set environment variable** in your web service.

### Setup: Railway

1. **Create project**: https://railway.app/
2. **Add PostgreSQL**:
   - Click **+ New** → **Database** → **Add PostgreSQL**
3. **Get connection string**:
   - Click on PostgreSQL service
   - Copy **Database URL** from Variables tab
4. **Run migrations** via Railway CLI:
   ```bash
   railway run psql $DATABASE_URL < migrations/001_initial_schema.sql
   railway run psql $DATABASE_URL < migrations/002_indexes.sql
   ```

---

## Running Migrations

### Manual Migration (via psql)

```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:5432/dbname"

# Run migrations in order
psql $DATABASE_URL < migrations/001_initial_schema.sql
psql $DATABASE_URL < migrations/002_indexes.sql

# Optional: Load seed data (DEVELOPMENT ONLY!)
psql $DATABASE_URL < migrations/003_seed_data.sql
```

### Python Migration Script

Create `scripts/migrate.py`:

```python
#!/usr/bin/env python3
"""Run database migrations."""

import os
import sys
from pathlib import Path
import psycopg2

def run_migration(db_url, migration_file):
    """Run a single migration file."""
    print(f"Running {migration_file.name}...")

    with open(migration_file) as f:
        sql = f.read()

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"✓ {migration_file.name} completed")
    except Exception as e:
        conn.rollback()
        print(f"✗ {migration_file.name} failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    migrations_dir = Path(__file__).parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    print(f"Found {len(migration_files)} migrations")

    for migration_file in migration_files:
        # Skip seed data unless explicitly requested
        if "seed" in migration_file.name and "--seed" not in sys.argv:
            print(f"Skipping {migration_file.name} (use --seed to include)")
            continue

        run_migration(db_url, migration_file)

    print("\n✓ All migrations completed successfully!")

if __name__ == "__main__":
    main()
```

Run migrations:

```bash
# Basic migrations
python scripts/migrate.py

# Include seed data
python scripts/migrate.py --seed
```

### Verify Migration Success

```python
# Python script
from src.utils.db import check_database_health

health = check_database_health()
print(health)
# Output: {'status': 'healthy', 'user_count': 0, 'catalyst_count': 0, ...}
```

Or via psql:

```sql
-- Check tables exist
\dt

-- Check table counts
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Database Schema

### Tables Overview

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **users** | User accounts, trials, Stripe integration | `email`, `trial_end_date`, `stripe_customer_id` |
| **subscriptions** | Stripe subscriptions | `user_id`, `status`, `plan_id` |
| **catalysts** | Clinical trial data | `nct_id`, `ticker`, `completion_date`, `market_cap` |
| **catalyst_history** | Daily market snapshots | `catalyst_id`, `snapshot_date`, `current_price` |
| **analytics_events** | User behavior tracking | `user_id`, `event_type`, `created_at` |
| **email_log** | Email delivery tracking | `user_id`, `email_type`, `sent_at`, `opened_at` |
| **workflow_runs** | n8n workflow logs | `workflow_id`, `status`, `records_processed` |

### Entity-Relationship Diagram

```
┌─────────────────┐
│     users       │
│─────────────────│
│ id (PK)         │◄─────┐
│ email           │      │
│ trial_end_date  │      │
│ stripe_cust_id  │      │
└─────────────────┘      │
                         │
                    ┌────┴──────────────┐
                    │                   │
              ┌─────┴──────────┐  ┌────┴──────────────┐
              │ subscriptions  │  │ analytics_events  │
              │────────────────│  │───────────────────│
              │ id (PK)        │  │ id (PK)           │
              │ user_id (FK)   │  │ user_id (FK)      │
              │ status         │  │ event_type        │
              │ plan_id        │  │ event_metadata    │
              └────────────────┘  └───────────────────┘

┌─────────────────┐
│   catalysts     │
│─────────────────│
│ id (PK)         │◄─────┐
│ nct_id (UNIQUE) │      │
│ ticker          │      │
│ completion_date │      │
│ market_cap      │      │
└─────────────────┘      │
                         │
                ┌────────┴────────────┐
                │ catalyst_history    │
                │─────────────────────│
                │ id (PK)             │
                │ catalyst_id (FK)    │
                │ snapshot_date       │
                │ current_price       │
                └─────────────────────┘
```

### Key Indexes

- `idx_users_email` - Fast login lookups
- `idx_catalysts_completion_date` - Sort by upcoming catalysts
- `idx_catalysts_ticker` - Filter by ticker symbol
- `idx_subscriptions_status` - Find active subscribers
- `idx_analytics_events_user_id` - User activity queries

See `migrations/002_indexes.sql` for full index list.

---

## Environment Variables

### Required Variables

```bash
# Option 1: Full connection string (recommended)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Option 2: Individual components
DB_HOST=localhost
DB_PORT=5432
DB_NAME=biotech_radar
DB_USER=postgres
DB_PASSWORD=your_password
```

### Optional Variables

```bash
# Connection pool settings
DB_POOL_MIN=1          # Minimum connections (default: 1)
DB_POOL_MAX=10         # Maximum connections (default: 10)

# Lazy initialization (delay pool init until first use)
LAZY_DB_INIT=false
```

### Connection String Formats

```bash
# Local PostgreSQL
DATABASE_URL=postgresql://localhost:5432/biotech_radar

# With username/password
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/biotech_radar

# Remote host
DATABASE_URL=postgresql://user:pass@db.example.com:5432/biotech_radar

# Supabase
DATABASE_URL=postgresql://postgres:password@db.abcdefgh.supabase.co:5432/postgres

# Render
DATABASE_URL=postgresql://biotech_radar_user:xyz@dpg-abc123.oregon-postgres.render.com/biotech_radar

# Railway
DATABASE_URL=postgresql://postgres:xyz@containers-us-west-123.railway.app:5432/railway
```

---

## Troubleshooting

### Connection Refused

```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solution**:
- Check PostgreSQL is running: `brew services list` (macOS) or `sudo systemctl status postgresql` (Linux)
- Verify port 5432 is not blocked: `lsof -i :5432`
- Check `pg_hba.conf` allows local connections

### Authentication Failed

```
psycopg2.OperationalError: FATAL: password authentication failed for user "postgres"
```

**Solution**:
- Verify password in `DATABASE_URL` is correct
- Check `pg_hba.conf` authentication method (`md5` or `trust`)
- Reset password: `ALTER USER postgres WITH PASSWORD 'newpassword';`

### Permission Denied

```
psycopg2.errors.InsufficientPrivilege: permission denied for table users
```

**Solution**:
```sql
-- Grant privileges to user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
```

### Table Already Exists

```
psycopg2.errors.DuplicateTable: relation "users" already exists
```

**Solution**:
- Migrations were already run
- To reset: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` (⚠️ DELETES ALL DATA)
- Or skip the error if tables are correct

### Pool Exhausted

```
psycopg2.pool.PoolError: connection pool exhausted
```

**Solution**:
- Increase `DB_POOL_MAX` environment variable
- Check for connection leaks (missing `conn.close()`)
- Use context managers: `with get_db_connection() as conn:`

### Slow Queries

**Solution**:
```sql
-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM catalysts WHERE ticker = 'ACMT';

-- Rebuild indexes
REINDEX TABLE catalysts;

-- Update statistics
ANALYZE catalysts;
```

---

## Database Maintenance

### Backups

```bash
# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore database
psql $DATABASE_URL < backup_20251224.sql

# Backup to compressed file
pg_dump $DATABASE_URL | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Monitoring

```sql
-- Table sizes
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT
  schemaname, tablename, indexname,
  idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Long-running queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
```

### Vacuum & Analyze

```sql
-- Full vacuum (run weekly)
VACUUM ANALYZE;

-- Per-table vacuum
VACUUM ANALYZE users;
VACUUM ANALYZE catalysts;

-- Auto-vacuum status
SELECT schemaname, relname, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
ORDER BY last_vacuum DESC;
```

---

## Testing

### Test Database Connection

```python
from src.utils.db import check_database_health

health = check_database_health()
assert health['status'] == 'healthy'
print(f"✓ Database connected: {health['database_version']}")
```

### Test CRUD Operations

```python
from src.utils.db import create_user, get_user_by_email

# Create user
user = create_user('test@example.com', 'hashed_password', trial_days=7)
assert user['email'] == 'test@example.com'

# Retrieve user
retrieved = get_user_by_email('test@example.com')
assert retrieved['id'] == user['id']

# Update user
from src.utils.db import update_user
from datetime import datetime

updated = update_user(user['id'], last_login_at=datetime.now())
assert updated['last_login_at'] is not None

print("✓ All CRUD tests passed")
```

---

## Next Steps

1. **Run migrations** (see [Running Migrations](#running-migrations))
2. **Update `.env`** with your `DATABASE_URL`
3. **Test connection**: `python -c "from src.utils.db import check_database_health; print(check_database_health())"`
4. **Implement user authentication** in Streamlit app
5. **Set up Stripe webhooks** to update subscriptions table
6. **Configure n8n workflows** to write to database

---

## Additional Resources

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **psycopg2 Documentation**: https://www.psycopg.org/docs/
- **Database Schema**: See `migrations/001_initial_schema.sql`
- **Index Reference**: See `migrations/002_indexes.sql`
- **Supabase Docs**: https://supabase.com/docs/guides/database
- **Render PostgreSQL**: https://render.com/docs/databases

---

**Last Updated**: 2025-12-24
**Maintained By**: Biotech Radar Team
