"""User Memory Manager for Chat Context and Watchlists.

Per spec Phase 3 Section 2.1:
- Per-session memory: Tracks context entities within a session
- Per-user memory: Persistent watchlists and preferences across sessions
- Pronoun resolution: Resolves "they", "their", "it" to last referenced ticker
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionMemory:
    """Manages per-session context for chat interactions."""

    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        self.context_entities: Dict[str, Any] = {
            "last_ticker": None,
            "last_indication": None,
            "referenced_catalysts": [],
        }
        self.session_id: str = str(uuid.uuid4())

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to session history."""
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })

    def update_context(self, ticker: Optional[str] = None, indication: Optional[str] = None):
        """Update context entities based on latest interaction."""
        if ticker:
            self.context_entities["last_ticker"] = ticker
        if indication:
            self.context_entities["last_indication"] = indication

    def add_referenced_catalyst(self, catalyst: Dict[str, Any]):
        """Add a catalyst to the referenced list."""
        self.context_entities["referenced_catalysts"].append(catalyst)
        # Keep only last 5 referenced catalysts
        if len(self.context_entities["referenced_catalysts"]) > 5:
            self.context_entities["referenced_catalysts"] = \
                self.context_entities["referenced_catalysts"][-5:]

    def get_recent_messages(self, n: int = 10) -> List[Dict[str, str]]:
        """Get last n messages for LLM context."""
        return self.messages[-n:]

    def resolve_pronouns(self, query: str) -> str:
        """Resolve pronouns to last referenced ticker.

        Handles: they, their, its, it, the company, them
        """
        if not self.context_entities.get("last_ticker"):
            return query

        ticker = self.context_entities["last_ticker"]
        query_lower = query.lower()

        # Pronoun patterns to replace (order matters - longer first)
        replacements = [
            ("the company's", f"{ticker}'s"),
            ("the company", ticker),
            ("their", f"{ticker}'s"),
            ("them", ticker),
            ("they", ticker),
            ("its", f"{ticker}'s"),
            (" it ", f" {ticker} "),  # Avoid partial matches
        ]

        for old, new in replacements:
            if old in query_lower:
                # Case-insensitive replacement
                import re
                query = re.sub(re.escape(old), new, query, flags=re.IGNORECASE)
                logger.debug(f"Resolved pronoun '{old}' to '{new}'")
                break  # Only replace first match to avoid over-replacement

        return query


class UserMemory:
    """Manages per-user persistent memory (watchlists and preferences)."""

    def __init__(self, db=None):
        """Initialize user memory manager.

        Args:
            db: SQLiteDB instance (optional, lazy loaded)
        """
        self.db = db
        self._init_db()

    def _init_db(self):
        """Lazy load database connection."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def get_watchlist(self, user_id: int) -> Dict[str, Any]:
        """Get user's watchlist.

        Returns:
            {
                "tickers": [
                    {"symbol": "ACAD", "added_at": "2026-01-05", "notes": "Phase 3 Rett"},
                    ...
                ]
            }
        """
        if self.db is None:
            return {"tickers": []}

        try:
            user = self.db.get_user(user_id)
            if user and user.get("watchlist"):
                return json.loads(user["watchlist"])
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")

        return {"tickers": []}

    def add_to_watchlist(self, user_id: int, ticker: str, notes: str = "") -> bool:
        """Add a ticker to user's watchlist.

        Args:
            user_id: User ID
            ticker: Ticker symbol
            notes: Optional notes

        Returns:
            True if added successfully
        """
        if self.db is None:
            return False

        try:
            watchlist = self.get_watchlist(user_id)

            # Check if already in watchlist
            existing_symbols = [t["symbol"] for t in watchlist.get("tickers", [])]
            if ticker.upper() in existing_symbols:
                logger.info(f"{ticker} already in watchlist")
                return True

            # Add new ticker
            watchlist.setdefault("tickers", []).append({
                "symbol": ticker.upper(),
                "added_at": datetime.now().strftime("%Y-%m-%d"),
                "notes": notes,
            })

            # Save back to database
            self.db.update_user_watchlist(user_id, json.dumps(watchlist))
            logger.info(f"Added {ticker} to user {user_id} watchlist")
            return True

        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
            return False

    def remove_from_watchlist(self, user_id: int, ticker: str) -> bool:
        """Remove a ticker from user's watchlist."""
        if self.db is None:
            return False

        try:
            watchlist = self.get_watchlist(user_id)
            watchlist["tickers"] = [
                t for t in watchlist.get("tickers", [])
                if t["symbol"] != ticker.upper()
            ]

            self.db.update_user_watchlist(user_id, json.dumps(watchlist))
            logger.info(f"Removed {ticker} from user {user_id} watchlist")
            return True

        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
            return False

    def get_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user's preferences.

        Returns:
            {
                "notifications": {
                    "email_digest": true,
                    "in_app_alerts": true,
                    "alert_triggers": ["date_window", "timeline_change", "red_flag"]
                },
                "filters": {
                    "therapeutic_areas": ["oncology", "neurology"],
                    "max_market_cap_usd": 5000000000,
                    "catalyst_window_days": 90
                }
            }
        """
        if self.db is None:
            return self._default_preferences()

        try:
            user = self.db.get_user(user_id)
            if user and user.get("preferences"):
                prefs = json.loads(user["preferences"])
                # Merge with defaults to ensure all keys exist
                return {**self._default_preferences(), **prefs}
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")

        return self._default_preferences()

    def _default_preferences(self) -> Dict[str, Any]:
        """Return default preferences."""
        return {
            "notifications": {
                "email_digest": True,
                "in_app_alerts": True,
                "alert_triggers": ["date_window", "timeline_change", "red_flag"],
            },
            "filters": {
                "therapeutic_areas": [],
                "max_market_cap_usd": None,
                "catalyst_window_days": 90,
            },
        }

    def update_preferences(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user's preferences.

        Args:
            user_id: User ID
            updates: Dict of preference updates (merged with existing)

        Returns:
            True if updated successfully
        """
        if self.db is None:
            return False

        try:
            current = self.get_preferences(user_id)

            # Deep merge updates
            for key, value in updates.items():
                if isinstance(value, dict) and isinstance(current.get(key), dict):
                    current[key].update(value)
                else:
                    current[key] = value

            self.db.update_user_preferences(user_id, json.dumps(current))
            logger.info(f"Updated preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False

    def get_last_seen_insights(self, user_id: int) -> List[int]:
        """Get IDs of insights user has already seen."""
        if self.db is None:
            return []

        try:
            user = self.db.get_user(user_id)
            if user and user.get("last_seen_insights"):
                return json.loads(user["last_seen_insights"])
        except Exception as e:
            logger.error(f"Error getting last seen insights: {e}")

        return []

    def mark_insight_seen(self, user_id: int, insight_id: int) -> bool:
        """Mark an insight as seen by user."""
        if self.db is None:
            return False

        try:
            seen = self.get_last_seen_insights(user_id)
            if insight_id not in seen:
                seen.append(insight_id)
                # Keep only last 100 seen insights
                seen = seen[-100:]
                self.db.update_user_last_seen_insights(user_id, json.dumps(seen))
            return True

        except Exception as e:
            logger.error(f"Error marking insight seen: {e}")
            return False


class ChatSessionManager:
    """Manages persistent chat session storage."""

    def __init__(self, db=None):
        """Initialize chat session manager."""
        self.db = db
        self._init_db()

    def _init_db(self):
        """Lazy load database connection."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def create_session(self, user_id: int) -> Optional[str]:
        """Create a new chat session.

        Returns:
            session_id (UUID string) or None on failure
        """
        if self.db is None:
            return None

        session_id = str(uuid.uuid4())
        try:
            self.db.create_chat_session(user_id, session_id)
            return session_id
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return None

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save a chat message to the session."""
        if self.db is None:
            return False

        try:
            self.db.save_chat_message(
                session_id=session_id,
                role=role,
                content=content,
                metadata=json.dumps(metadata) if metadata else None
            )
            return True
        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return False

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get messages from a chat session."""
        if self.db is None:
            return []

        try:
            return self.db.get_chat_messages(session_id, limit=limit)
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return []

    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent chat sessions for a user."""
        if self.db is None:
            return []

        try:
            return self.db.get_user_chat_sessions(user_id, limit=limit)
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    def end_session(self, session_id: str) -> bool:
        """Mark a chat session as ended."""
        if self.db is None:
            return False

        try:
            self.db.end_chat_session(session_id)
            return True
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
