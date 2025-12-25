"""
Alert Agent for Biotech Catalyst Radar.

This module provides proactive monitoring of saved searches and sends
notifications when new catalysts matching user criteria are added.

Features:
- Check saved searches against new catalysts
- Send multi-channel notifications (email, SMS, Slack)
- Deduplication to prevent duplicate alerts
- Rate limiting and quiet hours
- Tier-based channel restrictions

Usage:
    from src.agents import AlertAgent

    agent = AlertAgent()
    agent.check_saved_searches()
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

import requests
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SavedSearch:
    """Saved search configuration."""
    id: str
    user_id: str
    name: str
    query_params: Dict[str, Any]
    notification_channels: List[str]
    last_checked: Optional[datetime]
    active: bool


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    user_id: str
    max_alerts_per_day: int
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    user_timezone: str
    email_enabled: bool
    sms_enabled: bool
    slack_enabled: bool
    phone_number: Optional[str]
    slack_webhook_url: Optional[str]


# ============================================================================
# ALERT AGENT
# ============================================================================

class AlertAgent:
    """
    Proactive alert monitoring agent.

    Monitors saved searches and sends notifications when new catalysts
    matching user criteria are discovered.
    """

    def __init__(self):
        """Initialize the AlertAgent with Supabase and notification clients."""
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Notification API keys
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")

        logger.info("AlertAgent initialized successfully")

    def check_saved_searches(self) -> Dict[str, Any]:
        """
        Check all active saved searches and send notifications for new matches.

        This is the main entry point for the alert monitoring system.

        Returns:
            Dict with statistics about the check run
        """
        logger.info("🔍 Starting saved searches check...")

        stats = {
            "searches_checked": 0,
            "matches_found": 0,
            "notifications_sent": 0,
            "errors": 0,
            "started_at": datetime.now().isoformat()
        }

        try:
            # Fetch all active saved searches
            searches = self._fetch_active_searches()
            logger.info(f"Found {len(searches)} active saved searches")

            for search in searches:
                try:
                    stats["searches_checked"] += 1

                    # Find new matches since last check
                    new_matches = self.find_new_matches(
                        search.query_params,
                        search.last_checked
                    )

                    if new_matches:
                        logger.info(
                            f"Found {len(new_matches)} new matches for search '{search.name}'"
                        )
                        stats["matches_found"] += len(new_matches)

                        # Send notifications for each match
                        for catalyst in new_matches:
                            success = self.send_notification(
                                user_id=search.user_id,
                                search_name=search.name,
                                search_id=search.id,
                                catalyst=catalyst,
                                channels=search.notification_channels
                            )

                            if success:
                                stats["notifications_sent"] += 1

                    # Update last_checked timestamp
                    self._update_last_checked(search.id)

                except Exception as e:
                    logger.error(f"Error processing search {search.id}: {e}")
                    stats["errors"] += 1
                    continue

            stats["completed_at"] = datetime.now().isoformat()
            logger.info(f"✅ Check completed: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error in check_saved_searches: {e}")
            stats["errors"] += 1
            stats["error_message"] = str(e)
            return stats

    def find_new_matches(
        self,
        search_params: Dict[str, Any],
        last_checked: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """
        Find catalysts matching search criteria added since last check.

        Args:
            search_params: Query parameters (therapeutic_area, max_market_cap, phase, etc.)
            last_checked: Last time this search was checked (None for first run)

        Returns:
            List of catalyst dictionaries matching the criteria
        """
        try:
            # Build query
            query = self.supabase.table("catalysts").select("*")

            # Filter by last_checked (only new catalysts)
            if last_checked:
                query = query.gte("created_at", last_checked.isoformat())

            # Apply search filters
            if "phase" in search_params and search_params["phase"]:
                query = query.eq("phase", search_params["phase"])

            if "max_market_cap" in search_params and search_params["max_market_cap"]:
                query = query.lt("market_cap", search_params["max_market_cap"])

            if "min_market_cap" in search_params and search_params["min_market_cap"]:
                query = query.gte("market_cap", search_params["min_market_cap"])

            if "therapeutic_area" in search_params and search_params["therapeutic_area"]:
                # Search in indication field (case-insensitive)
                query = query.ilike("indication", f"%{search_params['therapeutic_area']}%")

            if "min_enrollment" in search_params and search_params["min_enrollment"]:
                query = query.gte("enrollment", search_params["min_enrollment"])

            if "completion_date_start" in search_params and search_params["completion_date_start"]:
                query = query.gte("completion_date", search_params["completion_date_start"])

            if "completion_date_end" in search_params and search_params["completion_date_end"]:
                query = query.lte("completion_date", search_params["completion_date_end"])

            # Only return catalysts with tickers (tradeable stocks)
            query = query.not_.is_("ticker", "null")

            # Order by completion date
            query = query.order("completion_date", desc=False)

            # Execute query
            response = query.execute()

            return response.data

        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return []

    def send_notification(
        self,
        user_id: str,
        search_name: str,
        search_id: str,
        catalyst: Dict[str, Any],
        channels: List[str]
    ) -> bool:
        """
        Send alert notification via specified channels.

        Args:
            user_id: User UUID
            search_name: Name of the saved search
            search_id: Saved search UUID
            catalyst: Catalyst data dictionary
            channels: List of channels to use (email, sms, slack)

        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Check if already notified about this catalyst
            if self._is_duplicate_alert(search_id, catalyst["id"]):
                logger.info(f"Skipping duplicate alert for catalyst {catalyst['id']}")
                return False

            # Check user preferences and limits
            if not self._can_send_notification(user_id):
                logger.info(f"Skipping notification for user {user_id} (rate limit or quiet hours)")
                return False

            # Format alert message
            alert_message = self.format_alert_message(catalyst, search_name)

            # Get user tier to check channel permissions
            user_tier = self._get_user_tier(user_id)

            # Send via each channel
            sent_channels = []

            if "email" in channels:
                if self._send_email(user_id, alert_message):
                    sent_channels.append("email")

            if "sms" in channels:
                if user_tier == "pro":
                    if self._send_sms(user_id, alert_message):
                        sent_channels.append("sms")
                else:
                    logger.info(f"SMS skipped for user {user_id} (Pro tier required)")

            if "slack" in channels:
                if user_tier == "pro":
                    if self._send_slack(user_id, alert_message):
                        sent_channels.append("slack")
                else:
                    logger.info(f"Slack skipped for user {user_id} (Pro tier required)")

            # Log notification to database
            if sent_channels:
                self._log_notification(
                    search_id=search_id,
                    catalyst_id=catalyst["id"],
                    user_id=user_id,
                    channels_used=sent_channels,
                    alert_content=alert_message
                )
                logger.info(
                    f"✅ Sent notification to user {user_id} via {', '.join(sent_channels)}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    def format_alert_message(
        self,
        catalyst: Dict[str, Any],
        search_name: str
    ) -> Dict[str, Any]:
        """
        Format notification content for a catalyst alert.

        Args:
            catalyst: Catalyst data dictionary
            search_name: Name of the saved search

        Returns:
            Dict with formatted message content
        """
        # Format market cap
        market_cap_str = "N/A"
        if catalyst.get("market_cap"):
            market_cap_b = catalyst["market_cap"] / 1_000_000_000
            market_cap_str = f"${market_cap_b:.2f}B"

        # Format price
        price_str = "N/A"
        if catalyst.get("current_price"):
            price_str = f"${catalyst['current_price']:.2f}"

        # Format completion date
        completion_date_str = catalyst.get("completion_date", "TBD")

        # Calculate days until catalyst
        days_until = None
        if catalyst.get("completion_date"):
            try:
                completion_date = datetime.fromisoformat(
                    catalyst["completion_date"].replace("Z", "+00:00")
                )
                days_until = (completion_date - datetime.now()).days
            except:
                pass

        return {
            "search_name": search_name,
            "ticker": catalyst.get("ticker", "N/A"),
            "sponsor": catalyst.get("sponsor", "Unknown"),
            "phase": catalyst.get("phase", "N/A"),
            "indication": catalyst.get("indication", "N/A"),
            "completion_date": completion_date_str,
            "days_until": days_until,
            "market_cap": market_cap_str,
            "current_price": price_str,
            "enrollment": catalyst.get("enrollment"),
            "nct_id": catalyst.get("nct_id"),
            "catalyst_id": catalyst.get("id")
        }

    # ========================================================================
    # NOTIFICATION CHANNELS
    # ========================================================================

    def _send_email(self, user_id: str, alert_message: Dict[str, Any]) -> bool:
        """Send email notification via SendGrid."""
        if not self.sendgrid_api_key:
            logger.warning("SendGrid API key not configured")
            return False

        try:
            # Get user email
            user_response = self.supabase.table("users").select("email").eq("id", user_id).single().execute()
            user_email = user_response.data["email"]

            # Format email content
            subject = f"🚀 New Catalyst Alert: {alert_message['ticker']} - {alert_message['search_name']}"

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #2c3e50;">New Catalyst Match: {alert_message['ticker']}</h2>

                <p>Your saved search "<strong>{alert_message['search_name']}</strong>" found a new match:</p>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">{alert_message['ticker']} - {alert_message['sponsor']}</h3>

                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Phase:</strong></td>
                            <td>{alert_message['phase']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Indication:</strong></td>
                            <td>{alert_message['indication']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Catalyst Date:</strong></td>
                            <td>{alert_message['completion_date']}</td>
                        </tr>
                        {f'<tr><td style="padding: 8px 0;"><strong>Days Until:</strong></td><td>{alert_message["days_until"]} days</td></tr>' if alert_message.get('days_until') else ''}
                        <tr>
                            <td style="padding: 8px 0;"><strong>Market Cap:</strong></td>
                            <td>{alert_message['market_cap']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Current Price:</strong></td>
                            <td>{alert_message['current_price']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>NCT ID:</strong></td>
                            <td><a href="https://clinicaltrials.gov/study/{alert_message['nct_id']}">{alert_message['nct_id']}</a></td>
                        </tr>
                    </table>
                </div>

                <p style="margin-top: 30px;">
                    <a href="https://biotechcatalyst.app/dashboard" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Full Details</a>
                </p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #dee2e6;">

                <p style="font-size: 12px; color: #6c757d;">
                    You received this email because you have an active saved search with alerts enabled.
                    <a href="https://biotechcatalyst.app/alerts">Manage your alerts</a>
                </p>
            </body>
            </html>
            """

            # Send via SendGrid API
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.sendgrid_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": user_email}]}],
                    "from": {"email": "alerts@biotechcatalyst.app", "name": "Biotech Catalyst Radar"},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_content}]
                }
            )

            if response.status_code == 202:
                logger.info(f"Email sent to {user_email}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _send_sms(self, user_id: str, alert_message: Dict[str, Any]) -> bool:
        """Send SMS notification via Twilio (Pro tier only)."""
        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_from_number]):
            logger.warning("Twilio credentials not configured")
            return False

        try:
            # Get user phone number
            prefs = self._get_user_preferences(user_id)
            if not prefs or not prefs.phone_number:
                logger.warning(f"No phone number configured for user {user_id}")
                return False

            # Format SMS content (160 chars max for single message)
            sms_text = (
                f"🚀 New Catalyst: {alert_message['ticker']} "
                f"({alert_message['phase']}) - {alert_message['completion_date']}. "
                f"Market Cap: {alert_message['market_cap']}. "
                f"View: https://biotechcatalyst.app"
            )

            # Send via Twilio API
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json",
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                data={
                    "To": prefs.phone_number,
                    "From": self.twilio_from_number,
                    "Body": sms_text
                }
            )

            if response.status_code == 201:
                logger.info(f"SMS sent to {prefs.phone_number}")
                return True
            else:
                logger.error(f"Twilio error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    def _send_slack(self, user_id: str, alert_message: Dict[str, Any]) -> bool:
        """Send Slack notification via webhook (Pro tier only)."""
        try:
            # Get user Slack webhook URL
            prefs = self._get_user_preferences(user_id)
            if not prefs or not prefs.slack_webhook_url:
                logger.warning(f"No Slack webhook configured for user {user_id}")
                return False

            # Format Slack message
            slack_payload = {
                "text": f"🚀 New Catalyst Alert: {alert_message['ticker']}",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🚀 New Catalyst: {alert_message['ticker']}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Search:*\n{alert_message['search_name']}"},
                            {"type": "mrkdwn", "text": f"*Phase:*\n{alert_message['phase']}"},
                            {"type": "mrkdwn", "text": f"*Sponsor:*\n{alert_message['sponsor']}"},
                            {"type": "mrkdwn", "text": f"*Catalyst Date:*\n{alert_message['completion_date']}"},
                            {"type": "mrkdwn", "text": f"*Market Cap:*\n{alert_message['market_cap']}"},
                            {"type": "mrkdwn", "text": f"*Price:*\n{alert_message['current_price']}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Indication:* {alert_message['indication']}"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View Details"},
                                "url": "https://biotechcatalyst.app/dashboard"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "View on ClinicalTrials.gov"},
                                "url": f"https://clinicaltrials.gov/study/{alert_message['nct_id']}"
                            }
                        ]
                    }
                ]
            }

            # Send to Slack
            response = requests.post(
                prefs.slack_webhook_url,
                json=slack_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.info(f"Slack message sent to user {user_id}")
                return True
            else:
                logger.error(f"Slack webhook error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    # ========================================================================
    # HELPER FUNCTIONS
    # ========================================================================

    def _fetch_active_searches(self) -> List[SavedSearch]:
        """Fetch all active saved searches."""
        try:
            response = self.supabase.table("saved_searches").select("*").eq("active", True).execute()

            return [
                SavedSearch(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    query_params=row["query_params"],
                    notification_channels=row["notification_channels"],
                    last_checked=datetime.fromisoformat(row["last_checked"].replace("Z", "+00:00")) if row.get("last_checked") else None,
                    active=row["active"]
                )
                for row in response.data
            ]

        except Exception as e:
            logger.error(f"Error fetching saved searches: {e}")
            return []

    def _update_last_checked(self, search_id: str):
        """Update last_checked timestamp for a saved search."""
        try:
            self.supabase.table("saved_searches").update({
                "last_checked": datetime.now().isoformat()
            }).eq("id", search_id).execute()

        except Exception as e:
            logger.error(f"Error updating last_checked: {e}")

    def _is_duplicate_alert(self, search_id: str, catalyst_id: str) -> bool:
        """Check if alert was already sent for this catalyst."""
        try:
            response = self.supabase.table("alert_notifications").select("id").eq(
                "saved_search_id", search_id
            ).eq(
                "catalyst_id", catalyst_id
            ).execute()

            return len(response.data) > 0

        except Exception as e:
            logger.error(f"Error checking duplicate alert: {e}")
            return False

    def _can_send_notification(self, user_id: str) -> bool:
        """Check if user can receive notification (rate limits, quiet hours)."""
        try:
            # Check rate limit
            response = self.supabase.rpc("can_receive_alert", {"p_user_id": user_id}).execute()
            can_receive = response.data

            if not can_receive:
                return False

            # Check quiet hours
            response = self.supabase.rpc("is_quiet_hours", {"p_user_id": user_id}).execute()
            is_quiet = response.data

            return not is_quiet

        except Exception as e:
            logger.error(f"Error checking notification permissions: {e}")
            return True  # Allow notification on error (fail open)

    def _get_user_tier(self, user_id: str) -> str:
        """Get user tier (free, trial, pro)."""
        try:
            response = self.supabase.rpc("get_user_tier", {"p_user_id": user_id}).execute()
            return response.data or "free"

        except Exception as e:
            logger.error(f"Error getting user tier: {e}")
            return "free"

    def _get_user_preferences(self, user_id: str) -> Optional[NotificationPreferences]:
        """Get user notification preferences."""
        try:
            response = self.supabase.table("notification_preferences").select("*").eq(
                "user_id", user_id
            ).single().execute()

            if response.data:
                return NotificationPreferences(**response.data)

            return None

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None

    def _log_notification(
        self,
        search_id: str,
        catalyst_id: str,
        user_id: str,
        channels_used: List[str],
        alert_content: Dict[str, Any]
    ):
        """Log notification to database."""
        try:
            self.supabase.table("alert_notifications").insert({
                "saved_search_id": search_id,
                "catalyst_id": catalyst_id,
                "user_id": user_id,
                "channels_used": channels_used,
                "alert_content": alert_content,
                "notification_sent_at": datetime.now().isoformat()
            }).execute()

        except Exception as e:
            logger.error(f"Error logging notification: {e}")


# ============================================================================
# CLI ENTRY POINT (for testing)
# ============================================================================

if __name__ == "__main__":
    agent = AlertAgent()
    results = agent.check_saved_searches()
    print(json.dumps(results, indent=2))
