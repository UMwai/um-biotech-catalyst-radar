"""
SQLite Database Manager for local development.

This module provides SQLite database operations for the Phase 2 MVP.
In production, swap to Supabase (Postgres) using the same interface.

Usage:
    from src.utils.sqlite_db import SQLiteDB

    db = SQLiteDB()
    db.init_schema()

    # Insert company
    company_id = db.upsert_company("ACAD", "Acadia Pharmaceuticals")

    # Insert catalyst
    db.insert_catalyst(company_id, catalyst_type="Phase3_Readout", ...)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


def _to_date_str(val: Any) -> Optional[str]:
    """Convert various date types to ISO date string for SQLite.

    Handles: datetime, date, pandas Timestamp, pandas NaT, strings
    Returns: ISO date string (YYYY-MM-DD) or None
    """
    if val is None:
        return None
    if pd.isna(val):  # Handles NaT and numpy NaN
        return None
    if isinstance(val, str):
        return val if val else None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    if hasattr(val, "strftime"):  # pandas Timestamp
        return val.strftime("%Y-%m-%d")
    return None


class SQLiteDB:
    """SQLite database manager for local development."""

    def __init__(self, db_path: str = "data/radar.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_done = False

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initialize database schema from migration file."""
        if self._init_done:
            return

        migration_path = Path(__file__).parent.parent.parent / "migrations" / "004_phase2_sqlite_schema.sql"

        if not migration_path.exists():
            logger.error(f"Migration file not found: {migration_path}")
            raise FileNotFoundError(f"Migration file not found: {migration_path}")

        with open(migration_path, "r") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            logger.info("Database schema initialized")

        self._init_done = True

    # =========================================================================
    # COMPANIES
    # =========================================================================

    def upsert_company(
        self,
        ticker: str,
        name: str,
        market_cap_usd: Optional[float] = None,
        enterprise_value_usd: Optional[float] = None,
        sector: str = "Biotech",
    ) -> int:
        """Insert or update a company.

        Returns:
            Company ID.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO companies (ticker, name, market_cap_usd, enterprise_value_usd, sector)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    name = excluded.name,
                    market_cap_usd = excluded.market_cap_usd,
                    enterprise_value_usd = excluded.enterprise_value_usd,
                    sector = excluded.sector,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (ticker, name, market_cap_usd, enterprise_value_usd, sector),
            )
            return cursor.fetchone()[0]

    def get_company_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company by ticker."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM companies WHERE ticker = ?",
                (ticker,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Get all companies."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM companies ORDER BY ticker")
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # FDA EVENTS
    # =========================================================================

    def insert_fda_event(
        self,
        company_id: int,
        event_type: str,
        event_date: Optional[date],
        drug_name: str,
        indication: Optional[str] = None,
        source_url: Optional[str] = None,
        raw_text: Optional[str] = None,
    ) -> int:
        """Insert an FDA event."""
        # Convert date to ISO string for SQLite compatibility
        event_date_str = _to_date_str(event_date)

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO fda_events
                (company_id, event_type, event_date, drug_name, indication, source_url, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (company_id, event_type, event_date_str, drug_name, indication, source_url, raw_text),
            )
            return cursor.fetchone()[0]

    def get_upcoming_fda_events(self, days_ahead: int = 90) -> List[Dict[str, Any]]:
        """Get FDA events within N days."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT fe.*, c.ticker, c.name as company_name
                FROM fda_events fe
                JOIN companies c ON fe.company_id = c.id
                WHERE fe.event_date >= date('now')
                AND fe.event_date <= date('now', '+' || ? || ' days')
                ORDER BY fe.event_date ASC
                """,
                (days_ahead,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # SEC FILINGS
    # =========================================================================

    def upsert_sec_filing(
        self,
        company_id: int,
        filing_type: str,
        filing_date: date,
        accession_number: str,
        file_path: Optional[str] = None,
        cash_runway_months: Optional[float] = None,
        monthly_burn_rate_usd: Optional[float] = None,
        cash_position_usd: Optional[float] = None,
        extraction_model: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
        raw_text: Optional[str] = None,
    ) -> int:
        """Insert or update an SEC filing."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sec_filings
                (company_id, filing_type, filing_date, accession_number, file_path,
                 cash_runway_months, monthly_burn_rate_usd, cash_position_usd,
                 extraction_model, extraction_confidence, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(accession_number) DO UPDATE SET
                    cash_runway_months = excluded.cash_runway_months,
                    monthly_burn_rate_usd = excluded.monthly_burn_rate_usd,
                    cash_position_usd = excluded.cash_position_usd,
                    extraction_model = excluded.extraction_model,
                    extraction_confidence = excluded.extraction_confidence,
                    extracted_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (company_id, filing_type, filing_date, accession_number, file_path,
                 cash_runway_months, monthly_burn_rate_usd, cash_position_usd,
                 extraction_model, extraction_confidence, raw_text),
            )
            return cursor.fetchone()[0]

    def get_latest_sec_filing(
        self, ticker: str, filing_type: str = "10-K"
    ) -> Optional[Dict[str, Any]]:
        """Get most recent SEC filing for a ticker."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT sf.*, c.ticker, c.name as company_name
                FROM sec_filings sf
                JOIN companies c ON sf.company_id = c.id
                WHERE c.ticker = ? AND sf.filing_type = ?
                ORDER BY sf.filing_date DESC
                LIMIT 1
                """,
                (ticker, filing_type),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # CLINICAL TRIALS
    # =========================================================================

    def upsert_clinical_trial(
        self,
        nct_id: str,
        title: str,
        phase: str,
        status: str,
        conditions: List[str],
        interventions: List[str],
        primary_completion_date: Optional[date],
        study_completion_date: Optional[date],
        enrollment_count: Optional[int],
        sponsor_name: str,
        sponsor_ticker: Optional[str] = None,
        ticker_confidence: Optional[float] = None,
        trial_design_score: Optional[float] = None,
        trial_design_notes: Optional[str] = None,
        design_scoring_model: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> int:
        """Insert or update a clinical trial."""
        # Convert dates to ISO strings for SQLite compatibility
        primary_date_str = _to_date_str(primary_completion_date)
        study_date_str = _to_date_str(study_completion_date)

        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clinical_trials
                (nct_id, title, phase, status, conditions, interventions,
                 primary_completion_date, study_completion_date, enrollment_count,
                 sponsor_name, sponsor_ticker, ticker_confidence,
                 trial_design_score, trial_design_notes, design_scoring_model, company_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(nct_id) DO UPDATE SET
                    title = excluded.title,
                    phase = excluded.phase,
                    status = excluded.status,
                    conditions = excluded.conditions,
                    interventions = excluded.interventions,
                    primary_completion_date = excluded.primary_completion_date,
                    study_completion_date = excluded.study_completion_date,
                    enrollment_count = excluded.enrollment_count,
                    sponsor_ticker = excluded.sponsor_ticker,
                    ticker_confidence = excluded.ticker_confidence,
                    trial_design_score = excluded.trial_design_score,
                    trial_design_notes = excluded.trial_design_notes,
                    design_scoring_model = excluded.design_scoring_model,
                    company_id = excluded.company_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (nct_id, title, phase, status, json.dumps(conditions), json.dumps(interventions),
                 primary_date_str, study_date_str, enrollment_count,
                 sponsor_name, sponsor_ticker, ticker_confidence,
                 trial_design_score, trial_design_notes, design_scoring_model, company_id),
            )
            return cursor.fetchone()[0]

    def get_upcoming_trials(
        self, days_ahead: int = 90, phase_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get trials with completion dates within N days."""
        query = """
            SELECT ct.*, c.ticker, c.name as company_name, c.market_cap_usd
            FROM clinical_trials ct
            LEFT JOIN companies c ON ct.company_id = c.id
            WHERE ct.primary_completion_date >= date('now')
            AND ct.primary_completion_date <= date('now', '+' || ? || ' days')
        """
        params = [days_ahead]

        if phase_filter:
            placeholders = ",".join("?" * len(phase_filter))
            query += f" AND ct.phase IN ({placeholders})"
            params.extend(phase_filter)

        query += " ORDER BY ct.primary_completion_date ASC"

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                # Parse JSON fields
                if item.get("conditions"):
                    item["conditions"] = json.loads(item["conditions"])
                if item.get("interventions"):
                    item["interventions"] = json.loads(item["interventions"])
                results.append(item)
            return results

    # =========================================================================
    # CATALYSTS (unified view)
    # =========================================================================

    def insert_catalyst(
        self,
        company_id: int,
        catalyst_type: str,
        catalyst_date: Optional[date],
        source: str,
        indication: Optional[str] = None,
        drug_name: Optional[str] = None,
        trial_phase: Optional[str] = None,
        trial_nct_id: Optional[str] = None,
        source_reference: Optional[str] = None,
        confidence_score: Optional[float] = None,
        catalyst_date_precision: str = "exact",
    ) -> int:
        """Insert a catalyst event."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO catalysts_v2
                (company_id, catalyst_type, catalyst_date, catalyst_date_precision,
                 indication, drug_name, trial_phase, trial_nct_id, source,
                 source_reference, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (company_id, catalyst_type, catalyst_date, catalyst_date_precision,
                 indication, drug_name, trial_phase, trial_nct_id, source,
                 source_reference, confidence_score),
            )
            return cursor.fetchone()[0]

    def get_all_catalysts(
        self, days_ahead: int = 90, include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all catalysts with company info."""
        query = """
            SELECT cv.*, c.ticker, c.name as company_name, c.market_cap_usd
            FROM catalysts_v2 cv
            JOIN companies c ON cv.company_id = c.id
        """

        if not include_expired:
            query += " WHERE cv.catalyst_date >= date('now')"
            query += f" AND cv.catalyst_date <= date('now', '+{days_ahead} days')"

        query += " ORDER BY cv.catalyst_date ASC"

        with self.get_connection() as conn:
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def aggregate_catalysts(self) -> int:
        """Aggregate catalysts from clinical_trials and fda_events into catalysts_v2.

        This creates a unified view of all upcoming catalysts for the proactive feed.
        Returns the number of catalysts created.
        """
        count = 0

        with self.get_connection() as conn:
            # Clear existing catalysts to avoid duplicates
            conn.execute("DELETE FROM catalysts_v2")

            # 1. Add clinical trial readouts
            trials = conn.execute("""
                SELECT ct.*, c.id as comp_id, c.ticker
                FROM clinical_trials ct
                LEFT JOIN companies c ON ct.sponsor_ticker = c.ticker
                WHERE ct.primary_completion_date >= date('now')
            """).fetchall()

            for trial in trials:
                trial = dict(trial)
                company_id = trial.get("comp_id") or trial.get("company_id")
                if not company_id:
                    continue

                # Determine catalyst type based on phase
                phase = trial.get("phase", "")
                if "3" in phase:
                    catalyst_type = "Phase3_Readout"
                elif "2" in phase:
                    catalyst_type = "Phase2_Readout"
                else:
                    catalyst_type = "Trial_Readout"

                # Parse conditions
                conditions = trial.get("conditions", "[]")
                if isinstance(conditions, str):
                    try:
                        import json
                        conditions = json.loads(conditions)
                    except:
                        conditions = [conditions]
                indication = conditions[0] if conditions else None

                conn.execute("""
                    INSERT INTO catalysts_v2
                    (company_id, catalyst_type, catalyst_date, catalyst_date_precision,
                     indication, trial_phase, trial_nct_id, source, source_reference, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id,
                    catalyst_type,
                    trial.get("primary_completion_date"),
                    "exact",
                    indication,
                    trial.get("phase"),
                    trial.get("nct_id"),
                    "CTgov",
                    f"[NCT: {trial.get('nct_id')}]",
                    trial.get("ticker_confidence", 80),
                ))
                count += 1

            # 2. Add FDA events
            fda_events = conn.execute("""
                SELECT fe.*, c.ticker
                FROM fda_events fe
                JOIN companies c ON fe.company_id = c.id
                WHERE fe.event_date >= date('now')
            """).fetchall()

            for event in fda_events:
                event = dict(event)
                conn.execute("""
                    INSERT INTO catalysts_v2
                    (company_id, catalyst_type, catalyst_date, catalyst_date_precision,
                     indication, drug_name, source, source_reference, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.get("company_id"),
                    event.get("event_type", "FDA_Event"),
                    event.get("event_date"),
                    "exact",
                    event.get("indication"),
                    event.get("drug_name"),
                    "FDA",
                    event.get("source_url") or f"[FDA: {event.get('event_type')}]",
                    95,  # High confidence for FDA events
                ))
                count += 1

            conn.commit()

        logger.info(f"Aggregated {count} catalysts into catalysts_v2")
        return count

    # =========================================================================
    # INSIGHTS (proactive feed)
    # =========================================================================

    def insert_insight(
        self,
        company_id: int,
        insight_type: str,
        headline: str,
        body: Optional[str] = None,
        conviction_score: Optional[float] = None,
        factors: Optional[Dict[str, Any]] = None,
        source_citations: Optional[List[str]] = None,
        generated_by: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        catalyst_id: Optional[int] = None,
    ) -> int:
        """Insert a generated insight."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO insights
                (company_id, catalyst_id, insight_type, headline, body,
                 conviction_score, factors, source_citations, generated_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (company_id, catalyst_id, insight_type, headline, body,
                 conviction_score, json.dumps(factors) if factors else None,
                 json.dumps(source_citations) if source_citations else None,
                 generated_by, expires_at),
            )
            return cursor.fetchone()[0]

    def get_active_insights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get active insights for the proactive feed."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT i.*, c.ticker, c.name as company_name, c.market_cap_usd
                FROM insights i
                JOIN companies c ON i.company_id = c.id
                WHERE i.is_active = 1
                AND (i.expires_at IS NULL OR i.expires_at > datetime('now'))
                ORDER BY i.conviction_score DESC, i.generated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("factors"):
                    item["factors"] = json.loads(item["factors"])
                if item.get("source_citations"):
                    item["source_citations"] = json.loads(item["source_citations"])
                results.append(item)
            return results

    def get_top_insights(self, top_n: int = 3) -> List[Dict[str, Any]]:
        """Get top N insights for daily feed display."""
        return self.get_active_insights(limit=top_n)

    def deactivate_expired_insights(self) -> int:
        """Deactivate insights past their expiry date."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE insights
                SET is_active = 0
                WHERE expires_at < datetime('now') AND is_active = 1
                """
            )
            return cursor.rowcount

    # =========================================================================
    # USERS (local)
    # =========================================================================

    def upsert_user(
        self,
        email: str,
        subscription_status: str = "free",
        subscription_tier: str = "free",
        watchlist: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert or update a local user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users_local (email, subscription_status, subscription_tier, watchlist, preferences)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    subscription_status = excluded.subscription_status,
                    subscription_tier = excluded.subscription_tier,
                    watchlist = excluded.watchlist,
                    preferences = excluded.preferences,
                    last_login_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (email, subscription_status, subscription_tier,
                 json.dumps(watchlist) if watchlist else None,
                 json.dumps(preferences) if preferences else None),
            )
            return cursor.fetchone()[0]

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users_local WHERE email = ?",
                (email,),
            )
            row = cursor.fetchone()
            if row:
                item = dict(row)
                if item.get("watchlist"):
                    item["watchlist"] = json.loads(item["watchlist"])
                if item.get("preferences"):
                    item["preferences"] = json.loads(item["preferences"])
                return item
            return None

    # =========================================================================
    # EMAIL DIGESTS
    # =========================================================================

    def log_email_digest(
        self, user_id: int, insight_ids: List[int], status: str = "sent"
    ) -> int:
        """Log a sent email digest."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO email_digests (user_id, insight_ids, status)
                VALUES (?, ?, ?)
                RETURNING id
                """,
                (user_id, json.dumps(insight_ids), status),
            )
            return cursor.fetchone()[0]

    # =========================================================================
    # CHAT HISTORY
    # =========================================================================

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add a chat message to history."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_history (session_id, user_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (session_id, user_id, role, content,
                 json.dumps(metadata) if metadata else None),
            )
            return cursor.fetchone()[0]

    def get_chat_history(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM chat_history
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            )
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("metadata"):
                    item["metadata"] = json.loads(item["metadata"])
                results.append(item)
            return results

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            stats = {}
            tables = [
                "companies", "catalysts_v2", "fda_events", "sec_filings",
                "clinical_trials", "insights", "users_local"
            ]
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            return stats

    # =========================================================================
    # PHASE 3: USER MEMORY
    # =========================================================================

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users_local WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_watchlist(self, user_id: int, watchlist_json: str) -> bool:
        """Update user's watchlist."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users_local SET watchlist = ? WHERE id = ?",
                (watchlist_json, user_id),
            )
            return True

    def update_user_preferences(self, user_id: int, preferences_json: str) -> bool:
        """Update user's preferences."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users_local SET preferences = ? WHERE id = ?",
                (preferences_json, user_id),
            )
            return True

    def update_user_last_seen_insights(self, user_id: int, insights_json: str) -> bool:
        """Update user's last seen insights."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users_local SET last_seen_insights = ? WHERE id = ?",
                (insights_json, user_id),
            )
            return True

    def get_all_users_with_watchlists(self) -> List[Dict[str, Any]]:
        """Get all users who have watchlists."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM users_local
                WHERE watchlist IS NOT NULL AND watchlist != '[]' AND watchlist != '{}'
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # PHASE 3: CHAT SESSIONS (persistent)
    # =========================================================================

    def create_chat_session(self, user_id: int, session_id: str) -> int:
        """Create a new chat session."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_sessions (user_id, session_id)
                VALUES (?, ?)
                RETURNING id
                """,
                (user_id, session_id),
            )
            return cursor.fetchone()[0]

    def save_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[str] = None,
    ) -> int:
        """Save a chat message to a session."""
        with self.get_connection() as conn:
            # Get internal session ID
            cursor = conn.execute(
                "SELECT id FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Session not found: {session_id}")

            internal_session_id = row[0]

            # Insert message
            cursor = conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, metadata)
                VALUES (?, ?, ?, ?)
                RETURNING id
                """,
                (internal_session_id, role, content, metadata),
            )

            # Update message count
            conn.execute(
                """
                UPDATE chat_sessions
                SET message_count = message_count + 1
                WHERE id = ?
                """,
                (internal_session_id,),
            )

            return cursor.fetchone()[0]

    def get_chat_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from a chat session."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT cm.*
                FROM chat_messages cm
                JOIN chat_sessions cs ON cm.session_id = cs.id
                WHERE cs.session_id = ?
                ORDER BY cm.created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            )
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                if item.get("metadata"):
                    item["metadata"] = json.loads(item["metadata"])
                results.append(item)
            return results

    def get_user_chat_sessions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat sessions for a user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM chat_sessions
                WHERE user_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def end_chat_session(self, session_id: str) -> bool:
        """Mark a chat session as ended."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE chat_sessions
                SET ended_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (session_id,),
            )
            return True

    # =========================================================================
    # PHASE 3: WATCHLIST ALERTS
    # =========================================================================

    def create_alert(
        self,
        user_id: int,
        ticker: str,
        alert_type: str,
        trigger_event: str,
        catalyst_id: Optional[int] = None,
        severity: str = "info",
    ) -> int:
        """Create a watchlist alert."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO watchlist_alerts
                (user_id, ticker, alert_type, trigger_event, catalyst_id, severity)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (user_id, ticker, alert_type, trigger_event, catalyst_id, severity),
            )
            return cursor.fetchone()[0]

    def get_user_alerts(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get alerts for a user."""
        query = """
            SELECT wa.*, cv.catalyst_type, cv.catalyst_date
            FROM watchlist_alerts wa
            LEFT JOIN catalysts_v2 cv ON wa.catalyst_id = cv.id
            WHERE wa.user_id = ?
        """
        if unread_only:
            query += " AND wa.acknowledged_at IS NULL"

        query += " ORDER BY wa.created_at DESC LIMIT ?"

        with self.get_connection() as conn:
            cursor = conn.execute(query, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert as acknowledged."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE watchlist_alerts
                SET acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (alert_id,),
            )
            return True

    def get_unread_alert_count(self, user_id: int) -> int:
        """Get count of unread alerts for a user."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM watchlist_alerts
                WHERE user_id = ? AND acknowledged_at IS NULL
                """,
                (user_id,),
            )
            return cursor.fetchone()[0]

    # =========================================================================
    # PHASE 3: EXTRACTION VERIFICATIONS (dual-model)
    # =========================================================================

    def save_verification(
        self,
        source_type: str,
        source_id: int,
        field_name: str,
        primary_model: str,
        primary_value: str,
        secondary_model: str,
        secondary_value: str,
        is_match: bool,
        confidence_score: float,
        needs_review: bool = False,
    ) -> int:
        """Save an extraction verification result."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO extraction_verifications
                (source_type, source_id, field_name, primary_model, primary_value,
                 secondary_model, secondary_value, is_match, confidence_score, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (source_type, source_id, field_name, primary_model, primary_value,
                 secondary_model, secondary_value, is_match, confidence_score, needs_review),
            )
            return cursor.fetchone()[0]

    def get_verifications_needing_review(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get verifications that need manual review."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM extraction_verifications
                WHERE needs_review = 1 AND reviewed_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_verification_reviewed(
        self, verification_id: int, reviewed_by: str
    ) -> bool:
        """Mark a verification as reviewed."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE extraction_verifications
                SET reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
                WHERE id = ?
                """,
                (reviewed_by, verification_id),
            )
            return True

    # =========================================================================
    # PHASE 3: BACKTEST TRACKING
    # =========================================================================

    def save_backtest_run(
        self,
        sample_size: int,
        overall_accuracy: float,
        sec_accuracy: Optional[float] = None,
        trial_accuracy: Optional[float] = None,
        fda_accuracy: Optional[float] = None,
        alert_sent: bool = False,
    ) -> int:
        """Save a backtest run summary."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO backtest_runs
                (sample_size, overall_accuracy, sec_accuracy, trial_accuracy,
                 fda_accuracy, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (sample_size, overall_accuracy, sec_accuracy, trial_accuracy,
                 fda_accuracy, alert_sent),
            )
            return cursor.fetchone()[0]

    def save_backtest_result(
        self,
        run_id: int,
        source_type: str,
        source_id: int,
        field_name: str,
        original_value: str,
        reextracted_value: str,
        is_match: bool,
    ) -> int:
        """Save an individual backtest result."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO backtest_results
                (run_id, source_type, source_id, field_name, original_value,
                 reextracted_value, is_match)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (run_id, source_type, source_id, field_name, original_value,
                 reextracted_value, is_match),
            )
            return cursor.fetchone()[0]

    def get_recent_backtest_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent backtest runs."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM backtest_runs
                ORDER BY run_date DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_backtest_accuracy_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get accuracy trend over time."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT run_date, overall_accuracy, sec_accuracy,
                       trial_accuracy, fda_accuracy
                FROM backtest_runs
                WHERE run_date >= date('now', '-' || ? || ' days')
                ORDER BY run_date ASC
                """,
                (days,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_extractions(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent extractions for backtesting."""
        results = []
        with self.get_connection() as conn:
            # Get SEC filings
            cursor = conn.execute(
                """
                SELECT sf.id, sf.company_id, sf.filing_type, sf.accession_number,
                       sf.cash_runway_months, sf.cash_position_usd, sf.monthly_burn_rate_usd,
                       sf.raw_text, 'sec_filing' as source_type
                FROM sec_filings sf
                WHERE sf.extracted_at >= datetime('now', '-' || ? || ' days')
                """,
                (days,),
            )
            results.extend([dict(row) for row in cursor.fetchall()])

            # Get clinical trials with design scores
            cursor = conn.execute(
                """
                SELECT ct.id, ct.nct_id, ct.trial_design_score,
                       ct.trial_design_notes, 'trial' as source_type
                FROM clinical_trials ct
                WHERE ct.trial_design_score IS NOT NULL
                AND ct.updated_at >= datetime('now', '-' || ? || ' days')
                """,
                (days,),
            )
            results.extend([dict(row) for row in cursor.fetchall()])

        return results


# Singleton instance for convenience
_db_instance: Optional[SQLiteDB] = None


def get_db() -> SQLiteDB:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLiteDB()
        _db_instance.init_schema()
    return _db_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test database operations
    db = get_db()

    # Test company insert
    company_id = db.upsert_company("ACAD", "Acadia Pharmaceuticals", market_cap_usd=2.5e9)
    print(f"Inserted company ID: {company_id}")

    # Test stats
    stats = db.get_stats()
    print(f"Database stats: {stats}")
