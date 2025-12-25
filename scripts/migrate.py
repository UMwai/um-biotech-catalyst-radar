#!/usr/bin/env python3
"""
Database migration runner for Biotech Catalyst Radar.

Usage:
    python scripts/migrate.py              # Run all migrations
    python scripts/migrate.py --seed       # Include seed data
    python scripts/migrate.py --rollback   # Drop all tables (DESTRUCTIVE!)
    python scripts/migrate.py --status     # Check migration status
"""

import os
import sys
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_migration(db_url, migration_file):
    """Run a single migration file."""
    import psycopg2

    print(f"Running {migration_file.name}...", end=" ")

    with open(migration_file) as f:
        sql = f.read()

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print("✓")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ FAILED")
        print(f"Error: {e}")
        return False
    finally:
        conn.close()


def check_migration_status(db_url):
    """Check which tables exist in the database."""
    import psycopg2

    print("\n" + "="*60)
    print("DATABASE MIGRATION STATUS")
    print("="*60)

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # Check if tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cur.fetchall()]

            expected_tables = [
                'users',
                'subscriptions',
                'catalysts',
                'catalyst_history',
                'analytics_events',
                'email_log',
                'workflow_runs'
            ]

            print("\nExpected tables:")
            for table in expected_tables:
                status = "✓" if table in tables else "✗"
                print(f"  {status} {table}")

            # Show table sizes
            if tables:
                print("\nTable sizes:")
                cur.execute("""
                    SELECT
                        tablename,
                        pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size('public.' || tablename) DESC;
                """)
                for table, size in cur.fetchall():
                    print(f"  {table}: {size}")

                # Show row counts
                print("\nRow counts:")
                for table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table};")
                    count = cur.fetchone()[0]
                    print(f"  {table}: {count:,} rows")

            print()

    except Exception as e:
        print(f"\nError checking status: {e}")
    finally:
        conn.close()


def rollback_migrations(db_url):
    """Drop all tables (DESTRUCTIVE!)."""
    import psycopg2

    print("\n" + "="*60)
    print("⚠️  WARNING: DESTRUCTIVE OPERATION")
    print("="*60)
    print("This will DROP ALL TABLES and DELETE ALL DATA!")
    confirm = input("Type 'yes' to confirm: ")

    if confirm.lower() != 'yes':
        print("Rollback cancelled.")
        return

    print("\nDropping all tables...", end=" ")

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE;")
            cur.execute("CREATE SCHEMA public;")
            cur.execute("GRANT ALL ON SCHEMA public TO postgres;")
            cur.execute("GRANT ALL ON SCHEMA public TO public;")
        conn.commit()
        print("✓")
        print("All tables dropped. Run migrations to recreate.")
    except Exception as e:
        conn.rollback()
        print(f"✗ FAILED")
        print(f"Error: {e}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--seed", action="store_true", help="Include seed data")
    parser.add_argument("--rollback", action="store_true", help="Drop all tables (DESTRUCTIVE!)")
    parser.add_argument("--status", action="store_true", help="Check migration status")
    args = parser.parse_args()

    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("\nSet it with:")
        print("  export DATABASE_URL='postgresql://user:password@host:5432/dbname'")
        print("\nOr configure individual variables in .env:")
        print("  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        sys.exit(1)

    # Handle special commands
    if args.status:
        check_migration_status(db_url)
        return

    if args.rollback:
        rollback_migrations(db_url)
        return

    # Run migrations
    migrations_dir = project_root / "migrations"
    if not migrations_dir.exists():
        print(f"ERROR: Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    migration_files = sorted(migrations_dir.glob("*.sql"))

    print("\n" + "="*60)
    print("RUNNING DATABASE MIGRATIONS")
    print("="*60)
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"Found {len(migration_files)} migration files\n")

    success_count = 0
    for migration_file in migration_files:
        # Skip seed data unless explicitly requested
        if "seed" in migration_file.name.lower() and not args.seed:
            print(f"Skipping {migration_file.name} (use --seed to include)")
            continue

        if run_migration(db_url, migration_file):
            success_count += 1
        else:
            print(f"\n✗ Migration failed: {migration_file.name}")
            print("Fix the error and run again.")
            sys.exit(1)

    print("\n" + "="*60)
    print(f"✓ Successfully ran {success_count} migrations")
    print("="*60)

    # Show status
    check_migration_status(db_url)


if __name__ == "__main__":
    main()
