"""
Database utility module for Biotech Catalyst Radar.

This module provides:
- PostgreSQL connection pooling
- Helper functions for common database operations
- Error handling and retry logic
- Type-safe query builders

Usage:
    from src.utils.db import get_db_connection, get_user, create_user

    # Get a connection from the pool
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
            users = cur.fetchall()

    # Or use helper functions
    user = get_user_by_email("user@example.com")
    subscription = get_user_subscription(user_id)
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor, execute_values
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONNECTION POOL
# ============================================================================

# Global connection pool (initialized on first use)
_connection_pool = None


def get_database_url() -> str:
    """
    Get database URL from environment variables.

    Supports two formats:
    1. DATABASE_URL (full connection string)
    2. Individual components (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

    Returns:
        str: PostgreSQL connection string

    Raises:
        ValueError: If database configuration is missing
    """
    # Check for full DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Handle Heroku/Render postgres:// -> postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # Build from individual components
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "biotech_radar")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    if not password:
        logger.warning("DB_PASSWORD not set - using empty password")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def init_connection_pool(minconn: int = 1, maxconn: int = 10) -> pool.ThreadedConnectionPool:
    """
    Initialize the PostgreSQL connection pool.

    Args:
        minconn: Minimum number of connections to maintain
        maxconn: Maximum number of connections allowed

    Returns:
        ThreadedConnectionPool instance

    Raises:
        psycopg2.Error: If connection fails
    """
    global _connection_pool

    if _connection_pool is not None:
        logger.info("Connection pool already initialized")
        return _connection_pool

    try:
        database_url = get_database_url()
        logger.info(f"Initializing connection pool (min={minconn}, max={maxconn})")

        _connection_pool = pool.ThreadedConnectionPool(
            minconn,
            maxconn,
            database_url,
            cursor_factory=RealDictCursor  # Return rows as dictionaries
        )

        logger.info("Connection pool initialized successfully")
        return _connection_pool

    except psycopg2.Error as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        raise


def close_connection_pool():
    """Close all connections in the pool."""
    global _connection_pool

    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Connection pool closed")


@contextmanager
def get_db_connection(retry_count: int = 3, retry_delay: int = 1):
    """
    Context manager to get a database connection from the pool.

    Automatically handles:
    - Connection pooling
    - Transaction management (commit/rollback)
    - Connection release back to pool
    - Retry logic on connection failures

    Args:
        retry_count: Number of times to retry on connection failure
        retry_delay: Delay in seconds between retries

    Yields:
        psycopg2.connection: Database connection

    Example:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users")
                users = cur.fetchall()
    """
    if _connection_pool is None:
        init_connection_pool()

    conn = None
    attempt = 0

    while attempt < retry_count:
        try:
            conn = _connection_pool.getconn()
            yield conn
            conn.commit()
            return

        except psycopg2.OperationalError as e:
            attempt += 1
            logger.warning(f"Connection attempt {attempt}/{retry_count} failed: {e}")

            if conn:
                conn.rollback()

            if attempt < retry_count:
                time.sleep(retry_delay)
            else:
                logger.error("All connection attempts failed")
                raise

        except Exception as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                _connection_pool.putconn(conn)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class User:
    """User account data structure."""
    id: str
    email: str
    created_at: datetime
    trial_start_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    stripe_customer_id: Optional[str]
    onboarding_completed: bool
    is_active: bool
    last_login_at: Optional[datetime]


@dataclass
class Subscription:
    """Subscription data structure."""
    id: str
    user_id: str
    stripe_subscription_id: str
    status: str
    plan_id: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool


@dataclass
class Catalyst:
    """Catalyst data structure."""
    id: str
    nct_id: str
    sponsor: str
    ticker: Optional[str]
    phase: str
    indication: str
    completion_date: Optional[datetime]
    market_cap: Optional[int]
    current_price: Optional[float]
    ticker_confidence_score: Optional[int]


# ============================================================================
# USER FUNCTIONS
# ============================================================================

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address.

    Args:
        email: User's email address

    Returns:
        User data as dictionary or None if not found
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email = %s AND is_active = TRUE",
                (email,)
            )
            return cur.fetchone()


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID.

    Args:
        user_id: User UUID

    Returns:
        User data as dictionary or None if not found
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE id = %s AND is_active = TRUE",
                (user_id,)
            )
            return cur.fetchone()


def create_user(
    email: str,
    password_hash: str,
    trial_days: int = 7,
    signup_source: str = "organic"
) -> Dict[str, Any]:
    """
    Create a new user with automatic trial setup.

    Args:
        email: User's email address
        password_hash: Bcrypt password hash
        trial_days: Number of days for free trial (default: 7)
        signup_source: How the user signed up (organic, referral, paid_ad)

    Returns:
        Created user data as dictionary

    Raises:
        psycopg2.IntegrityError: If email already exists
    """
    trial_start = datetime.now()
    trial_end = trial_start + timedelta(days=trial_days)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash, trial_start_date, trial_end_date, signup_source)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (email, password_hash, trial_start, trial_end, signup_source)
            )
            user = cur.fetchone()

            # Log signup event
            log_analytics_event(user['id'], 'signup', 'conversion', {'source': signup_source})
            log_analytics_event(user['id'], 'trial_start', 'conversion', {'trial_days': trial_days})

            logger.info(f"Created user: {email} (trial until {trial_end})")
            return user


def update_user(user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Update user fields.

    Args:
        user_id: User UUID
        **kwargs: Fields to update (e.g., last_login_at=datetime.now())

    Returns:
        Updated user data as dictionary

    Example:
        update_user(user_id, last_login_at=datetime.now(), onboarding_completed=True)
    """
    if not kwargs:
        raise ValueError("No fields to update")

    # Build dynamic UPDATE query
    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(sql.Identifier(key))
        values.append(value)

    values.append(user_id)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = sql.SQL("UPDATE users SET {} WHERE id = %s RETURNING *").format(
                sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(field) for field in fields
                )
            )
            cur.execute(query, values)
            return cur.fetchone()


def is_trial_active(user_id: str) -> bool:
    """
    Check if user's trial is still active.

    Args:
        user_id: User UUID

    Returns:
        True if trial is active, False otherwise
    """
    user = get_user_by_id(user_id)
    if not user or not user['trial_end_date']:
        return False

    return datetime.now() < user['trial_end_date']


# ============================================================================
# SUBSCRIPTION FUNCTIONS
# ============================================================================

def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user's active subscription.

    Args:
        user_id: User UUID

    Returns:
        Subscription data as dictionary or None if no active subscription
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM subscriptions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,)
            )
            return cur.fetchone()


def has_active_subscription(user_id: str) -> bool:
    """
    Check if user has an active paid subscription.

    Args:
        user_id: User UUID

    Returns:
        True if user has active subscription, False otherwise
    """
    subscription = get_user_subscription(user_id)
    return subscription is not None and subscription['status'] == 'active'


def create_subscription(
    user_id: str,
    stripe_subscription_id: str,
    stripe_product_id: str,
    status: str,
    plan_id: str,
    plan_amount: int,
    current_period_end: datetime
) -> Dict[str, Any]:
    """
    Create a new subscription (called from Stripe webhook).

    Args:
        user_id: User UUID
        stripe_subscription_id: Stripe subscription ID
        stripe_product_id: Stripe product ID
        status: Subscription status (active, canceled, etc.)
        plan_id: Plan identifier (monthly_29, annual_232)
        plan_amount: Amount in cents
        current_period_end: End of current billing period

    Returns:
        Created subscription data as dictionary
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subscriptions (
                    user_id, stripe_subscription_id, stripe_product_id,
                    status, plan_id, plan_amount, current_period_end
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, stripe_subscription_id, stripe_product_id,
                 status, plan_id, plan_amount, current_period_end)
            )
            subscription = cur.fetchone()

            # Log conversion event
            log_analytics_event(user_id, 'subscribe', 'conversion', {
                'plan': plan_id,
                'amount': plan_amount
            })

            logger.info(f"Created subscription for user {user_id}: {plan_id}")
            return subscription


def update_subscription_status(
    stripe_subscription_id: str,
    status: str,
    current_period_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Update subscription status (called from Stripe webhook).

    Args:
        stripe_subscription_id: Stripe subscription ID
        status: New status (active, canceled, past_due, etc.)
        current_period_end: New period end date (optional)

    Returns:
        Updated subscription data as dictionary
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if current_period_end:
                cur.execute(
                    """
                    UPDATE subscriptions
                    SET status = %s, current_period_end = %s, updated_at = NOW()
                    WHERE stripe_subscription_id = %s
                    RETURNING *
                    """,
                    (status, current_period_end, stripe_subscription_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE subscriptions
                    SET status = %s, updated_at = NOW()
                    WHERE stripe_subscription_id = %s
                    RETURNING *
                    """,
                    (status, stripe_subscription_id)
                )

            subscription = cur.fetchone()

            if subscription and status == 'canceled':
                log_analytics_event(subscription['user_id'], 'churn', 'retention', {
                    'plan': subscription['plan_id']
                })

            return subscription


# ============================================================================
# CATALYST FUNCTIONS
# ============================================================================

def get_catalysts(
    phase: Optional[str] = None,
    max_market_cap: Optional[int] = None,
    min_ticker_confidence: int = 80,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get catalysts with optional filters.

    Args:
        phase: Filter by phase (e.g., "Phase 3")
        max_market_cap: Maximum market cap in USD (e.g., 5000000000 for $5B)
        min_ticker_confidence: Minimum ticker confidence score (0-100)
        limit: Maximum number of results

    Returns:
        List of catalyst dictionaries
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT * FROM catalysts
                WHERE ticker IS NOT NULL
                AND completion_date IS NOT NULL
                AND ticker_confidence_score >= %s
            """
            params = [min_ticker_confidence]

            if phase:
                query += " AND phase = %s"
                params.append(phase)

            if max_market_cap:
                query += " AND market_cap < %s"
                params.append(max_market_cap)

            query += " ORDER BY completion_date ASC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            return cur.fetchall()


def upsert_catalyst(catalyst_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update catalyst data (used by scraper workflow).

    Args:
        catalyst_data: Dictionary with catalyst fields

    Returns:
        Upserted catalyst data as dictionary

    Required fields:
        - nct_id: ClinicalTrials.gov NCT ID

    Optional fields:
        - sponsor, phase, indication, completion_date, ticker, market_cap, etc.
    """
    required_field = 'nct_id'
    if required_field not in catalyst_data:
        raise ValueError(f"Missing required field: {required_field}")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Build dynamic UPSERT query
            columns = list(catalyst_data.keys())
            values = [catalyst_data[col] for col in columns]

            # Generate conflict resolution (update all fields except id and created_at)
            update_columns = [col for col in columns if col not in ['id', 'nct_id']]

            query = sql.SQL("""
                INSERT INTO catalysts ({columns})
                VALUES ({placeholders})
                ON CONFLICT (nct_id)
                DO UPDATE SET {updates}, updated_at = NOW()
                RETURNING *
            """).format(
                columns=sql.SQL(", ").join(map(sql.Identifier, columns)),
                placeholders=sql.SQL(", ").join(sql.Placeholder() * len(columns)),
                updates=sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                    for col in update_columns
                )
            )

            cur.execute(query, values)
            return cur.fetchone()


# ============================================================================
# ANALYTICS FUNCTIONS
# ============================================================================

def log_analytics_event(
    user_id: Optional[str],
    event_type: str,
    event_category: str,
    event_metadata: Optional[Dict[str, Any]] = None
):
    """
    Log an analytics event.

    Args:
        user_id: User UUID (None for anonymous events)
        event_type: Event type (signup, login, view_catalyst, etc.)
        event_category: Event category (engagement, conversion, retention)
        event_metadata: Additional event data as dictionary
    """
    import json

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_events (user_id, event_type, event_category, event_metadata)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, event_type, event_category, json.dumps(event_metadata) if event_metadata else None)
            )

    logger.debug(f"Logged event: {event_type} for user {user_id}")


def log_email_sent(
    user_id: str,
    email_type: str,
    email_campaign: str,
    subject: str,
    sendgrid_message_id: Optional[str] = None
):
    """
    Log an email sent to a user.

    Args:
        user_id: User UUID
        email_type: Email type (welcome, trial_day_3, etc.)
        email_campaign: Campaign name (trial_conversion, transactional, etc.)
        subject: Email subject line
        sendgrid_message_id: SendGrid message ID (optional)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO email_log (user_id, email_type, email_campaign, subject, sendgrid_message_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email_type, email_campaign, subject, sendgrid_message_id)
            )

    logger.info(f"Logged email sent: {email_type} to user {user_id}")


# ============================================================================
# WORKFLOW LOGGING
# ============================================================================

def log_workflow_start(workflow_id: str, workflow_name: str, execution_id: Optional[str] = None) -> str:
    """
    Log the start of a workflow run.

    Args:
        workflow_id: Workflow identifier
        workflow_name: Human-readable workflow name
        execution_id: n8n execution ID (optional)

    Returns:
        Workflow run UUID
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_runs (workflow_id, workflow_name, execution_id, status)
                VALUES (%s, %s, %s, 'running')
                RETURNING id
                """,
                (workflow_id, workflow_name, execution_id)
            )
            run_id = cur.fetchone()['id']
            logger.info(f"Started workflow: {workflow_name} (run_id={run_id})")
            return run_id


def log_workflow_complete(
    run_id: str,
    status: str,
    records_processed: int = 0,
    records_failed: int = 0,
    error_message: Optional[str] = None
):
    """
    Log the completion of a workflow run.

    Args:
        run_id: Workflow run UUID
        status: Final status (success, error, cancelled)
        records_processed: Number of records processed
        records_failed: Number of records that failed
        error_message: Error message if status is 'error'
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workflow_runs
                SET status = %s,
                    completed_at = NOW(),
                    duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
                    records_processed = %s,
                    records_failed = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (status, records_processed, records_failed, error_message, run_id)
            )

    logger.info(f"Completed workflow run {run_id}: {status} ({records_processed} processed, {records_failed} failed)")


# ============================================================================
# HEALTH CHECK
# ============================================================================

def check_database_health() -> Dict[str, Any]:
    """
    Check database connection and basic health metrics.

    Returns:
        Dictionary with health status and metrics
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check connection
                cur.execute("SELECT version()")
                version = cur.fetchone()['version']

                # Get table counts
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()['count']

                cur.execute("SELECT COUNT(*) FROM catalysts")
                catalyst_count = cur.fetchone()['count']

                return {
                    "status": "healthy",
                    "database_version": version,
                    "user_count": user_count,
                    "catalyst_count": catalyst_count,
                    "timestamp": datetime.now().isoformat()
                }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize connection pool when module is imported
# This can be disabled by setting LAZY_DB_INIT=true
if not os.getenv("LAZY_DB_INIT"):
    try:
        init_connection_pool()
    except Exception as e:
        logger.warning(f"Failed to initialize connection pool on import: {e}")
        logger.warning("Connection pool will be initialized on first use")
