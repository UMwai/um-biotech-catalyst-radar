"""Watchlist Agent for Background Monitoring.

Per spec Phase 3 Section 2.2:
- Background monitoring of user's saved tickers
- Proactive alerts on material changes
- Alert triggers: date_window, timeline_change, red_flag
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Alert trigger configuration
ALERT_TRIGGERS = {
    "date_window": {
        "thresholds": [90, 30, 14, 7],  # Days until catalyst
        "severity_map": {
            90: "info",
            30: "info",
            14: "warning",
            7: "critical",
        },
        "message_template": "{ticker}: {catalyst_type} in {days} days",
    },
    "timeline_change": {
        "message_template": "{ticker}: {catalyst_type} date changed to {new_date}",
        "severity": "warning",
    },
    "red_flag": {
        "conditions": [
            ("cash_runway_months", "<", 6),
            ("clinical_hold", "=", True),
            ("ceo_departure", "=", True),
            ("going_concern_warning", "=", True),
        ],
        "severity": "critical",
        "message_template": "{ticker}: RED FLAG - {condition}",
    },
}


class Alert:
    """Represents an alert to be sent to a user."""

    def __init__(
        self,
        user_id: int,
        ticker: str,
        alert_type: str,
        trigger_event: str,
        catalyst_id: Optional[int] = None,
        severity: str = "info",
    ):
        self.user_id = user_id
        self.ticker = ticker
        self.alert_type = alert_type
        self.trigger_event = trigger_event
        self.catalyst_id = catalyst_id
        self.severity = severity
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "ticker": self.ticker,
            "alert_type": self.alert_type,
            "trigger_event": self.trigger_event,
            "catalyst_id": self.catalyst_id,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
        }


class WatchlistAgent:
    """Background agent that monitors user watchlists for alert conditions."""

    def __init__(self, db=None):
        """Initialize watchlist agent.

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

    def check_user_watchlist(self, user_id: int) -> List[Alert]:
        """Check all tickers in user's watchlist for alert conditions.

        Args:
            user_id: User ID to check

        Returns:
            List of Alert objects for triggered conditions
        """
        if self.db is None:
            return []

        try:
            user = self.db.get_user(user_id)
            if not user:
                return []

            watchlist_str = user.get("watchlist", "[]")
            watchlist = json.loads(watchlist_str) if watchlist_str else {"tickers": []}

            alerts = []
            for item in watchlist.get("tickers", []):
                ticker = item.get("symbol") if isinstance(item, dict) else item

                # Check date windows
                alerts.extend(self._check_date_windows(ticker, user_id))

                # Check timeline changes
                alerts.extend(self._check_timeline_changes(ticker, user_id))

                # Check red flags
                alerts.extend(self._check_red_flags(ticker, user_id))

            return alerts

        except Exception as e:
            logger.error(f"Error checking watchlist for user {user_id}: {e}")
            return []

    def _check_date_windows(self, ticker: str, user_id: int) -> List[Alert]:
        """Check if any catalysts are entering date windows.

        Returns alerts for catalysts that are now within threshold days.
        """
        alerts = []
        if self.db is None:
            return alerts

        try:
            # Get catalysts for this ticker
            catalysts = self.db.get_all_catalysts(days_ahead=90)
            ticker_catalysts = [c for c in catalysts if c.get("ticker") == ticker]

            today = datetime.now().date()

            for catalyst in ticker_catalysts:
                catalyst_date_str = catalyst.get("catalyst_date")
                if not catalyst_date_str:
                    continue

                # Parse date
                if isinstance(catalyst_date_str, str):
                    catalyst_date = datetime.strptime(catalyst_date_str, "%Y-%m-%d").date()
                else:
                    catalyst_date = catalyst_date_str

                days_until = (catalyst_date - today).days

                # Check thresholds
                thresholds = ALERT_TRIGGERS["date_window"]["thresholds"]
                for threshold in thresholds:
                    # Alert if we just crossed into this window (days_until == threshold)
                    # In practice, we check if days_until <= threshold and no recent alert
                    if days_until <= threshold:
                        # Check if we already sent this alert
                        if self._alert_already_sent(user_id, ticker, "date_window", threshold):
                            continue

                        severity = ALERT_TRIGGERS["date_window"]["severity_map"].get(
                            threshold, "info"
                        )
                        message = ALERT_TRIGGERS["date_window"]["message_template"].format(
                            ticker=ticker,
                            catalyst_type=catalyst.get("catalyst_type", "Catalyst"),
                            days=days_until,
                        )

                        alerts.append(Alert(
                            user_id=user_id,
                            ticker=ticker,
                            alert_type="date_window",
                            trigger_event=message,
                            catalyst_id=catalyst.get("id"),
                            severity=severity,
                        ))
                        break  # Only alert for the most urgent threshold

        except Exception as e:
            logger.error(f"Error checking date windows for {ticker}: {e}")

        return alerts

    def _check_timeline_changes(self, ticker: str, user_id: int) -> List[Alert]:
        """Check if catalyst dates have changed from previous values.

        This requires tracking previous catalyst dates (not yet implemented).
        """
        # TODO: Implement timeline change detection
        # This would require storing previous catalyst dates and comparing
        return []

    def _check_red_flags(self, ticker: str, user_id: int) -> List[Alert]:
        """Check for red flag conditions (cash runway, clinical hold, etc.)."""
        alerts = []
        if self.db is None:
            return alerts

        try:
            # Get latest SEC filing for cash runway
            for filing_type in ["10-Q", "10-K"]:
                filing = self.db.get_latest_sec_filing(ticker, filing_type)
                if filing:
                    # Check cash runway
                    cash_runway = filing.get("cash_runway_months")
                    if cash_runway is not None and cash_runway < 6:
                        if not self._alert_already_sent(
                            user_id, ticker, "red_flag", "cash_runway"
                        ):
                            message = ALERT_TRIGGERS["red_flag"]["message_template"].format(
                                ticker=ticker,
                                condition=f"Cash runway only {cash_runway:.0f} months",
                            )
                            alerts.append(Alert(
                                user_id=user_id,
                                ticker=ticker,
                                alert_type="red_flag",
                                trigger_event=message,
                                severity="critical",
                            ))
                    break

        except Exception as e:
            logger.error(f"Error checking red flags for {ticker}: {e}")

        return alerts

    def _alert_already_sent(
        self,
        user_id: int,
        ticker: str,
        alert_type: str,
        context: Any,
    ) -> bool:
        """Check if we already sent a similar alert recently.

        Args:
            user_id: User ID
            ticker: Ticker symbol
            alert_type: Type of alert
            context: Additional context (threshold, condition type, etc.)

        Returns:
            True if a similar alert was sent in the last 24 hours
        """
        if self.db is None:
            return False

        try:
            # Get recent alerts
            alerts = self.db.get_user_alerts(user_id, unread_only=False, limit=100)

            # Check for similar recent alerts
            cutoff = datetime.now() - timedelta(hours=24)

            for alert in alerts:
                if alert.get("ticker") != ticker:
                    continue
                if alert.get("alert_type") != alert_type:
                    continue

                # Check if recent
                created_at_str = alert.get("created_at")
                if created_at_str:
                    if isinstance(created_at_str, str):
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", ""))
                    else:
                        created_at = created_at_str

                    if created_at > cutoff:
                        return True

        except Exception as e:
            logger.warning(f"Error checking for duplicate alerts: {e}")

        return False

    def run_daily_check(self) -> Dict[str, Any]:
        """Run watchlist check for all users.

        This is called by the daily cron job.

        Returns:
            Summary of alerts generated
        """
        if self.db is None:
            return {"error": "Database not available"}

        summary = {
            "users_checked": 0,
            "alerts_generated": 0,
            "alerts_by_type": {},
        }

        try:
            users = self.db.get_all_users_with_watchlists()
            summary["users_checked"] = len(users)

            for user in users:
                user_id = user.get("id")
                alerts = self.check_user_watchlist(user_id)

                for alert in alerts:
                    self._save_and_notify(user, alert)
                    summary["alerts_generated"] += 1

                    alert_type = alert.alert_type
                    summary["alerts_by_type"][alert_type] = (
                        summary["alerts_by_type"].get(alert_type, 0) + 1
                    )

            logger.info(
                f"Daily watchlist check complete: {summary['users_checked']} users, "
                f"{summary['alerts_generated']} alerts"
            )

        except Exception as e:
            logger.error(f"Error in daily watchlist check: {e}")
            summary["error"] = str(e)

        return summary

    def _save_and_notify(self, user: Dict[str, Any], alert: Alert) -> None:
        """Save alert to database and send notification.

        Args:
            user: User dict
            alert: Alert object
        """
        if self.db is None:
            return

        try:
            # Save to database
            alert_id = self.db.create_alert(
                user_id=alert.user_id,
                ticker=alert.ticker,
                alert_type=alert.alert_type,
                trigger_event=alert.trigger_event,
                catalyst_id=alert.catalyst_id,
                severity=alert.severity,
            )

            logger.info(f"Created alert {alert_id} for user {alert.user_id}: {alert.trigger_event}")

            # TODO: Send email/in-app notification
            # For now, just log it

        except Exception as e:
            logger.error(f"Error saving alert: {e}")

    def get_user_unread_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        """Get unread alerts for a user (for in-app display).

        Args:
            user_id: User ID

        Returns:
            List of unread alert dicts
        """
        if self.db is None:
            return []

        return self.db.get_user_alerts(user_id, unread_only=True)

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert as acknowledged/read.

        Args:
            alert_id: Alert ID

        Returns:
            True if successful
        """
        if self.db is None:
            return False

        return self.db.acknowledge_alert(alert_id)


# Singleton instance
_agent_instance: Optional[WatchlistAgent] = None


def get_watchlist_agent() -> WatchlistAgent:
    """Get the singleton watchlist agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = WatchlistAgent()
    return _agent_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test the agent
    agent = get_watchlist_agent()

    # Run daily check
    result = agent.run_daily_check()
    print(f"Daily check result: {result}")
