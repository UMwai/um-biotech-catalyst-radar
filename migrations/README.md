# Database Migrations

This directory contains SQL migration files for the Biotech Catalyst Radar database.

## Migration Files

| File | Description |
|------|-------------|
| `001_initial_schema.sql` | Creates all tables (users, subscriptions, catalysts, etc.) |
| `002_indexes.sql` | Adds performance indexes |
| `003_seed_data.sql` | Sample data for testing (DEVELOPMENT ONLY) |

## Running Migrations

### Quick Start

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@host:5432/biotech_radar"

# Run migrations
python scripts/migrate.py

# Include seed data (development only)
python scripts/migrate.py --seed
```

### Using psql Directly

```bash
psql $DATABASE_URL < migrations/001_initial_schema.sql
psql $DATABASE_URL < migrations/002_indexes.sql

# Optional: seed data
psql $DATABASE_URL < migrations/003_seed_data.sql
```

### Check Migration Status

```bash
python scripts/migrate.py --status
```

Output:
```
============================================================
DATABASE MIGRATION STATUS
============================================================

Expected tables:
  ✓ users
  ✓ subscriptions
  ✓ catalysts
  ✓ catalyst_history
  ✓ analytics_events
  ✓ email_log
  ✓ workflow_runs

Table sizes:
  users: 16 kB
  catalysts: 24 kB
  ...

Row counts:
  users: 3 rows
  catalysts: 8 rows
  ...
```

## Migration Order

Migrations must be run in order:

1. **001_initial_schema.sql** - Creates tables and triggers
2. **002_indexes.sql** - Adds indexes (depends on tables)
3. **003_seed_data.sql** - Inserts test data (optional)

## Rollback

To drop all tables and reset the database:

```bash
python scripts/migrate.py --rollback
```

**WARNING**: This is DESTRUCTIVE and will delete all data!

## Creating New Migrations

When adding new tables or columns:

1. Create a new file: `004_your_migration_name.sql`
2. Use sequential numbering (001, 002, 003, ...)
3. Include comments explaining the changes
4. Test locally before deploying to production

Example migration:

```sql
-- ============================================================================
-- Migration 004: Add user preferences table
-- ============================================================================
-- Author: Your Name
-- Created: 2025-12-24
-- ============================================================================

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE,
    weekly_digest BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Add trigger for updated_at
CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment
COMMENT ON TABLE user_preferences IS 'User notification and email preferences';
```

## Best Practices

1. **Always test migrations locally first**
2. **Backup production database before running migrations**
3. **Never edit existing migration files** (create new ones instead)
4. **Use transactions** (migrations should be atomic)
5. **Include rollback instructions** in comments
6. **Document breaking changes** clearly

## Production Deployment

### Supabase

```bash
# Get connection string from Supabase dashboard
export DATABASE_URL="postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"

# Run migrations
python scripts/migrate.py
```

### Render

```bash
# Get internal database URL from Render dashboard
export DATABASE_URL="postgresql://user:pass@dpg-xxx.oregon-postgres.render.com/biotech_radar"

# Run via Render Shell or Railway CLI
python scripts/migrate.py
```

### Railway

```bash
# Use Railway CLI
railway run python scripts/migrate.py
```

## Troubleshooting

### Migration Failed: Table Already Exists

The tables were already created. Check status:

```bash
python scripts/migrate.py --status
```

### Permission Denied

Grant privileges:

```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
```

### Connection Refused

Check that PostgreSQL is running and `DATABASE_URL` is correct.

## Additional Resources

- [Database Setup Guide](../docs/database-setup.md)
- [Target Architecture Spec](../specs/architecture/02-target-architecture.md)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Last Updated**: 2025-12-24
