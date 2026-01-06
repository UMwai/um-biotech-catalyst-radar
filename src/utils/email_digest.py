"""Email Digest System for daily catalyst alerts.

Per spec Section 5.1:
- Daily summary of catalysts, watchlist changes
- Send time: 7 AM ET
- Provider: Resend (free tier: 3K emails/month) or SendGrid

Email content:
- Top 3 opportunities
- Watchlist updates
- Unsubscribe link
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# HTML Email Template
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Biotech Catalyst Radar - Daily Digest</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            padding-bottom: 20px;
            border-bottom: 2px solid #4F46E5;
            margin-bottom: 25px;
        }}
        .header h1 {{
            color: #4F46E5;
            margin: 0;
            font-size: 24px;
        }}
        .header p {{
            color: #666;
            margin: 5px 0 0 0;
        }}
        .insight-card {{
            background: #f8f9fa;
            border-left: 4px solid #4F46E5;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}
        .insight-card.high {{
            border-left-color: #10B981;
        }}
        .insight-card.medium {{
            border-left-color: #F59E0B;
        }}
        .ticker {{
            font-size: 18px;
            font-weight: bold;
            color: #1F2937;
            margin-bottom: 5px;
        }}
        .headline {{
            font-size: 14px;
            color: #4B5563;
            margin-bottom: 8px;
        }}
        .meta {{
            font-size: 12px;
            color: #9CA3AF;
        }}
        .score {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        .score.high {{
            background: #D1FAE5;
            color: #065F46;
        }}
        .score.medium {{
            background: #FEF3C7;
            color: #92400E;
        }}
        .score.low {{
            background: #F3F4F6;
            color: #6B7280;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
            margin: 25px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #E5E7EB;
        }}
        .cta {{
            text-align: center;
            margin: 30px 0;
        }}
        .cta a {{
            display: inline-block;
            background: #4F46E5;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
        }}
        .cta a:hover {{
            background: #4338CA;
        }}
        .footer {{
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #E5E7EB;
            margin-top: 25px;
            font-size: 12px;
            color: #9CA3AF;
        }}
        .footer a {{
            color: #6B7280;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧬 Biotech Catalyst Radar</h1>
            <p>{date}</p>
        </div>

        <div class="section-title">🎯 Today's Top Opportunities</div>
        {insights_html}

        {watchlist_section}

        <div class="cta">
            <a href="{dashboard_url}">View Full Dashboard</a>
        </div>

        <div class="footer">
            <p>You're receiving this because you signed up for Biotech Catalyst Radar.</p>
            <p>
                <a href="{unsubscribe_url}">Unsubscribe</a> |
                <a href="{preferences_url}">Email Preferences</a>
            </p>
            <p>© {year} Biotech Catalyst Radar</p>
        </div>
    </div>
</body>
</html>
"""

INSIGHT_CARD_TEMPLATE = """
<div class="insight-card {conviction_class}">
    <div class="ticker">{ticker} <span class="score {conviction_class}">{score}</span></div>
    <div class="headline">{headline}</div>
    <div class="meta">
        📅 {catalyst_type} in {days_until} days |
        💊 {indication} |
        📊 Source: {source}
    </div>
</div>
"""

WATCHLIST_SECTION_TEMPLATE = """
<div class="section-title">👁️ Watchlist Updates</div>
{watchlist_items}
"""

WATCHLIST_ITEM_TEMPLATE = """
<div class="insight-card">
    <div class="ticker">{ticker}</div>
    <div class="headline">{update}</div>
</div>
"""


class EmailDigest:
    """Send daily email digests with catalyst insights."""

    def __init__(
        self,
        provider: str = "resend",
        from_email: str = "digest@biotechradar.com",
        dashboard_url: str = "https://biotechradar.streamlit.app",
    ):
        """Initialize email digest sender.

        Args:
            provider: Email provider ('resend' or 'sendgrid')
            from_email: Sender email address
            dashboard_url: URL to dashboard for CTA links
        """
        self.provider = provider
        self.from_email = from_email
        self.dashboard_url = dashboard_url

        # Get API keys from environment
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

    def generate_html(
        self,
        insights: List[Dict[str, Any]],
        watchlist_updates: Optional[List[Dict[str, Any]]] = None,
        user_email: str = "",
    ) -> str:
        """Generate HTML email content.

        Args:
            insights: List of insight dicts (top 3)
            watchlist_updates: Optional list of watchlist updates
            user_email: User's email for unsubscribe link

        Returns:
            Rendered HTML string
        """
        # Generate insight cards
        insights_html = ""
        for insight in insights[:3]:
            score = insight.get("conviction_score", 50)

            if score >= 75:
                conviction_class = "high"
                score_label = f"High ({score})"
            elif score >= 50:
                conviction_class = "medium"
                score_label = f"Medium ({score})"
            else:
                conviction_class = "low"
                score_label = f"Low ({score})"

            insights_html += INSIGHT_CARD_TEMPLATE.format(
                ticker=insight.get("ticker", "N/A"),
                conviction_class=conviction_class,
                score=score_label,
                headline=insight.get("headline", "No headline"),
                catalyst_type=insight.get("catalyst_type", "Catalyst"),
                days_until=insight.get("days_until", "?"),
                indication=insight.get("indication", "Unspecified")[:40],
                source=insight.get("source", "Internal"),
            )

        # Generate watchlist section
        watchlist_section = ""
        if watchlist_updates:
            watchlist_items = ""
            for update in watchlist_updates[:5]:
                watchlist_items += WATCHLIST_ITEM_TEMPLATE.format(
                    ticker=update.get("ticker", "N/A"),
                    update=update.get("update", "No update"),
                )
            watchlist_section = WATCHLIST_SECTION_TEMPLATE.format(
                watchlist_items=watchlist_items
            )

        # Render full email
        today = datetime.now().strftime("%B %d, %Y")
        year = datetime.now().year

        # Generate unsubscribe URL (would be tokenized in production)
        import hashlib
        unsub_token = hashlib.md5(user_email.encode()).hexdigest()[:16]

        html = EMAIL_TEMPLATE.format(
            date=today,
            insights_html=insights_html or "<p>No new opportunities today. Check back tomorrow!</p>",
            watchlist_section=watchlist_section,
            dashboard_url=self.dashboard_url,
            unsubscribe_url=f"{self.dashboard_url}/unsubscribe?token={unsub_token}",
            preferences_url=f"{self.dashboard_url}/preferences?token={unsub_token}",
            year=year,
        )

        return html

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send email using configured provider.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML email body

        Returns:
            True if sent successfully
        """
        if self.provider == "resend":
            return self._send_via_resend(to_email, subject, html_content)
        elif self.provider == "sendgrid":
            return self._send_via_sendgrid(to_email, subject, html_content)
        else:
            logger.error(f"Unknown email provider: {self.provider}")
            return False

    def _send_via_resend(
        self, to_email: str, subject: str, html_content: str
    ) -> bool:
        """Send email via Resend API."""
        if not self.resend_api_key:
            logger.warning("RESEND_API_KEY not set, skipping email send")
            return False

        try:
            import resend
            resend.api_key = self.resend_api_key

            params = {
                "from": self.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)
            logger.info(f"Email sent via Resend to {to_email}: {response}")
            return True

        except ImportError:
            logger.error("resend package not installed")
            return False
        except Exception as e:
            logger.error(f"Resend send failed: {e}")
            return False

    def _send_via_sendgrid(
        self, to_email: str, subject: str, html_content: str
    ) -> bool:
        """Send email via SendGrid API."""
        if not self.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY not set, skipping email send")
            return False

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            logger.info(f"Email sent via SendGrid to {to_email}: {response.status_code}")
            return response.status_code in [200, 201, 202]

        except ImportError:
            logger.error("sendgrid package not installed")
            return False
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False

    def send_digest(
        self,
        to_email: str,
        insights: List[Dict[str, Any]],
        watchlist_updates: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send a complete digest email to a user.

        Args:
            to_email: Recipient email
            insights: Top insights to include
            watchlist_updates: Optional watchlist updates

        Returns:
            True if sent successfully
        """
        # Generate HTML
        html = self.generate_html(
            insights=insights,
            watchlist_updates=watchlist_updates,
            user_email=to_email,
        )

        # Generate subject
        today = datetime.now().strftime("%b %d")
        top_ticker = insights[0].get("ticker", "BIOTECH") if insights else "BIOTECH"
        subject = f"🧬 Daily Catalyst Alert ({today}) - {top_ticker} and more"

        return self.send_email(to_email, subject, html)


def run_daily_digest_job(db=None) -> Dict[str, int]:
    """Run the daily digest email job.

    This is called by GitHub Actions cron at 7 AM ET.

    Args:
        db: Optional database instance

    Returns:
        Dict with sent/failed counts
    """
    from data.feed_generator import FeedGenerator

    logger.info("Starting daily digest job...")

    if db is None:
        from utils.sqlite_db import get_db
        db = get_db()

    # Generate today's insights
    generator = FeedGenerator(db=db)
    insights = generator.generate_feed(days_ahead=90, limit=5, use_llm=False)

    if not insights:
        logger.warning("No insights generated, skipping digest")
        return {"sent": 0, "failed": 0, "skipped": 1}

    # Get all users who should receive digest
    # For MVP, this would query users_local table
    try:
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT email, watchlist FROM users_local
                WHERE subscription_status != 'cancelled'
                """
            )
            users = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        users = []

    if not users:
        logger.info("No users to send digest to")
        return {"sent": 0, "failed": 0, "skipped": 0}

    # Send digests
    email_sender = EmailDigest()
    results = {"sent": 0, "failed": 0, "skipped": 0}

    for user in users:
        email = user.get("email")
        if not email:
            results["skipped"] += 1
            continue

        # Get watchlist updates (if any)
        watchlist_updates = []  # Would populate from user's watchlist

        try:
            success = email_sender.send_digest(
                to_email=email,
                insights=insights,
                watchlist_updates=watchlist_updates,
            )

            if success:
                # Log to database
                try:
                    user_id = db.get_user_by_email(email).get("id") if db.get_user_by_email(email) else None
                    if user_id:
                        db.log_email_digest(
                            user_id=user_id,
                            insight_ids=[i.get("id") for i in insights if i.get("id")],
                            status="sent",
                        )
                except Exception as log_err:
                    logger.warning(f"Failed to log email digest: {log_err}")

                results["sent"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            logger.error(f"Failed to send digest to {email}: {e}")
            results["failed"] += 1

    logger.info(f"Daily digest complete: {results}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test email generation (doesn't send)
    sender = EmailDigest()

    test_insights = [
        {
            "ticker": "ACAD",
            "headline": "ACAD: PDUFA in 14 days - HIGH URGENCY",
            "catalyst_type": "PDUFA",
            "days_until": 14,
            "indication": "Rett Syndrome",
            "conviction_score": 85,
            "source": "FDA",
        },
        {
            "ticker": "SAVA",
            "headline": "SAVA: Phase 3 readout approaching",
            "catalyst_type": "Phase 3 Readout",
            "days_until": 45,
            "indication": "Alzheimer's Disease",
            "conviction_score": 72,
            "source": "CTgov",
        },
        {
            "ticker": "AXSM",
            "headline": "AXSM: Near-term PDUFA for depression treatment",
            "catalyst_type": "PDUFA",
            "days_until": 22,
            "indication": "Treatment-Resistant Depression",
            "conviction_score": 78,
            "source": "SEC",
        },
    ]

    html = sender.generate_html(
        insights=test_insights,
        watchlist_updates=[{"ticker": "MRNA", "update": "Trial enrollment complete"}],
        user_email="test@example.com",
    )

    # Save test email to file for review
    with open("test_email.html", "w") as f:
        f.write(html)

    print("Test email saved to test_email.html")
