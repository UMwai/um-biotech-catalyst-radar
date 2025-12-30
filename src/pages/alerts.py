"""
Alert Agent Page - Manage saved searches and notification preferences.

This page allows users to:
- Create and manage saved searches
- View alert history
- Configure notification preferences (quiet hours, rate limits, channels)
"""

import streamlit as st
from datetime import datetime
import os

from supabase import create_client, Client

# Import UI components
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.saved_searches import render_saved_searches


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        st.error("Supabase configuration missing")
        st.stop()

    return create_client(supabase_url, supabase_key)


def main():
    """Main entry point for alerts page."""
    st.set_page_config(
        page_title="Alert Agent - Biotech Catalyst Radar", page_icon="🔔", layout="wide"
    )

    # Check if user is logged in
    if "user_id" not in st.session_state:
        st.warning("Please log in to access alerts")
        st.stop()

    user_id = st.session_state.user_id

    # Page header
    st.title("🔔 Alert Agent")
    st.markdown(
        "Create saved searches and receive automatic notifications when new catalysts "
        "matching your criteria are added to the database."
    )

    st.divider()

    # Get Supabase client
    supabase = get_supabase_client()

    # Get user tier
    try:
        tier_response = supabase.rpc("get_user_tier", {"p_user_id": user_id}).execute()
        user_tier = tier_response.data or "free"
    except:
        user_tier = "free"

    # Show tier upgrade CTA if not Pro
    if user_tier != "pro":
        st.info(
            f"**Current Plan: {user_tier.title()}** - "
            "Upgrade to Pro for unlimited searches and SMS/Slack notifications. "
            "[Upgrade Now](/subscribe)"
        )
        st.divider()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 My Saved Searches", "📬 Alert History", "⚙️ Settings"])

    with tab1:
        render_saved_searches(user_id)

    with tab2:
        render_alert_history(supabase, user_id)

    with tab3:
        render_notification_settings(supabase, user_id, user_tier)

    # First-time user wizard
    if not st.session_state.get("alerts_onboarded"):
        render_quick_start_wizard(supabase, user_id, user_tier)


def render_alert_history(supabase: Client, user_id: str) -> None:
    """Render alert notification history."""
    st.subheader("Alert History")

    # Fetch alert notifications
    try:
        response = (
            supabase.table("alert_notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("notification_sent_at", desc=True)
            .limit(50)
            .execute()
        )

        notifications = response.data or []
    except Exception as e:
        st.error(f"Error loading alert history: {e}")
        notifications = []

    if not notifications:
        st.info("No alerts sent yet. Create a saved search to start receiving notifications.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    total_alerts = len(notifications)
    alerts_today = len(
        [
            n
            for n in notifications
            if datetime.fromisoformat(n["notification_sent_at"].replace("Z", "+00:00")).date()
            == datetime.now().date()
        ]
    )
    unacknowledged = len([n for n in notifications if not n.get("user_acknowledged")])

    with col1:
        st.metric("Total Alerts", total_alerts)
    with col2:
        st.metric("Today", alerts_today)
    with col3:
        st.metric("Unread", unacknowledged)

    st.divider()

    # Display notifications
    for notification in notifications:
        _render_notification_card(supabase, notification)


def _render_notification_card(supabase: Client, notification: Dict[str, Any]) -> None:
    """Render a single notification card."""
    alert_content = notification.get("alert_content", {})
    sent_at = datetime.fromisoformat(notification["notification_sent_at"].replace("Z", "+00:00"))
    acknowledged = notification.get("user_acknowledged", False)

    with st.container(border=True):
        col1, col2 = st.columns([4, 1])

        with col1:
            # Alert title
            ack_icon = "✅" if acknowledged else "🔔"
            st.markdown(
                f"### {ack_icon} {alert_content.get('ticker', 'N/A')} - {alert_content.get('search_name', 'Alert')}"
            )

            # Alert details
            st.markdown(
                f"**Phase:** {alert_content.get('phase', 'N/A')} | "
                f"**Catalyst Date:** {alert_content.get('completion_date', 'N/A')} | "
                f"**Market Cap:** {alert_content.get('market_cap', 'N/A')}"
            )

            st.caption(f"**Indication:** {alert_content.get('indication', 'N/A')}")

            # Channels used
            channels = notification.get("channels_used", [])
            channel_icons = {"email": "📧", "sms": "📱", "slack": "💬"}
            channel_str = " ".join([channel_icons.get(ch, ch) for ch in channels])
            st.caption(f"Sent via: {channel_str} • {sent_at.strftime('%Y-%m-%d %H:%M')}")

        with col2:
            # Acknowledge button
            if not acknowledged:
                if st.button(
                    "Mark as Read",
                    key=f"ack_{notification['id']}",
                    use_container_width=True,
                ):
                    _acknowledge_notification(supabase, notification["id"])
                    st.rerun()

            # View on ClinicalTrials.gov
            nct_id = alert_content.get("nct_id")
            if nct_id:
                st.link_button(
                    "View Trial",
                    f"https://clinicaltrials.gov/study/{nct_id}",
                    use_container_width=True,
                )


def _acknowledge_notification(supabase: Client, notification_id: str) -> None:
    """Mark notification as acknowledged."""
    try:
        supabase.table("alert_notifications").update(
            {"user_acknowledged": True, "acknowledged_at": datetime.now().isoformat()}
        ).eq("id", notification_id).execute()

        st.success("Marked as read")
    except Exception as e:
        st.error(f"Error: {e}")


def render_notification_settings(supabase: Client, user_id: str, user_tier: str) -> None:
    """Render notification preferences settings."""
    st.subheader("Notification Settings")

    # Fetch current preferences
    try:
        response = (
            supabase.table("notification_preferences")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        prefs = response.data
        has_prefs = True
    except:
        # Create default preferences
        prefs = {
            "user_id": user_id,
            "max_alerts_per_day": 10,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "user_timezone": "America/New_York",
            "email_enabled": True,
            "sms_enabled": False,
            "slack_enabled": False,
            "phone_number": None,
            "slack_webhook_url": None,
        }
        has_prefs = False

    with st.form("notification_settings_form"):
        st.markdown("#### Rate Limiting")

        max_alerts = st.slider(
            "Maximum alerts per day",
            min_value=1,
            max_value=50,
            value=prefs.get("max_alerts_per_day", 10),
            help="Prevent notification overload by limiting daily alerts",
        )

        st.markdown("#### Quiet Hours")

        col1, col2, col3 = st.columns(3)

        with col1:
            quiet_start = st.time_input(
                "Start time",
                value=datetime.strptime(prefs["quiet_hours_start"], "%H:%M:%S").time()
                if prefs.get("quiet_hours_start")
                else None,
                help="No notifications will be sent during quiet hours",
            )

        with col2:
            quiet_end = st.time_input(
                "End time",
                value=datetime.strptime(prefs["quiet_hours_end"], "%H:%M:%S").time()
                if prefs.get("quiet_hours_end")
                else None,
            )

        with col3:
            timezone = st.selectbox(
                "Timezone",
                [
                    "America/New_York",
                    "America/Chicago",
                    "America/Denver",
                    "America/Los_Angeles",
                    "America/Anchorage",
                    "Pacific/Honolulu",
                    "Europe/London",
                    "Europe/Paris",
                ],
                index=0
                if not prefs.get("user_timezone")
                else [
                    "America/New_York",
                    "America/Chicago",
                    "America/Denver",
                    "America/Los_Angeles",
                    "America/Anchorage",
                    "Pacific/Honolulu",
                    "Europe/London",
                    "Europe/Paris",
                ].index(prefs.get("user_timezone", "America/New_York")),
            )

        st.markdown("#### Channel Configuration")

        # Email (always enabled)
        st.checkbox("📧 Email notifications", value=True, disabled=True)

        # SMS (Pro only)
        sms_enabled = st.checkbox(
            "📱 SMS notifications (Pro only)",
            value=prefs.get("sms_enabled", False),
            disabled=(user_tier != "pro"),
        )

        if sms_enabled:
            phone_number = st.text_input(
                "Phone number (E.164 format)",
                value=prefs.get("phone_number", ""),
                placeholder="+12025551234",
                help="Include country code, e.g., +1 for US",
            )
        else:
            phone_number = prefs.get("phone_number")

        # Slack (Pro only)
        slack_enabled = st.checkbox(
            "💬 Slack notifications (Pro only)",
            value=prefs.get("slack_enabled", False),
            disabled=(user_tier != "pro"),
        )

        if slack_enabled:
            slack_webhook = st.text_input(
                "Slack webhook URL",
                value=prefs.get("slack_webhook_url", ""),
                placeholder="https://hooks.slack.com/services/...",
                type="password",
                help="Create a webhook in your Slack workspace settings",
            )
        else:
            slack_webhook = prefs.get("slack_webhook_url")

        if user_tier != "pro":
            st.info("Upgrade to Pro tier to enable SMS and Slack notifications")

        # Submit button
        submit = st.form_submit_button("Save Settings", type="primary", use_container_width=True)

        if submit:
            settings_data = {
                "user_id": user_id,
                "max_alerts_per_day": max_alerts,
                "quiet_hours_start": quiet_start.strftime("%H:%M:%S") if quiet_start else None,
                "quiet_hours_end": quiet_end.strftime("%H:%M:%S") if quiet_end else None,
                "user_timezone": timezone,
                "email_enabled": True,
                "sms_enabled": sms_enabled and user_tier == "pro",
                "slack_enabled": slack_enabled and user_tier == "pro",
                "phone_number": phone_number if sms_enabled else None,
                "slack_webhook_url": slack_webhook if slack_enabled else None,
            }

            try:
                if has_prefs:
                    # Update existing preferences
                    supabase.table("notification_preferences").update(settings_data).eq(
                        "user_id", user_id
                    ).execute()
                else:
                    # Insert new preferences
                    supabase.table("notification_preferences").insert(settings_data).execute()

                st.success("Settings saved successfully!")

            except Exception as e:
                st.error(f"Error saving settings: {e}")


def render_quick_start_wizard(supabase: Client, user_id: str, user_tier: str) -> None:
    """Show quick start wizard for first-time users."""
    # Check if user has any saved searches
    try:
        response = (
            supabase.table("saved_searches")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        has_searches = (response.count or 0) > 0
    except:
        has_searches = False

    if has_searches:
        return

    # Show modal
    with st.expander("🚀 Quick Start Guide", expanded=True):
        st.markdown("""
        ### Welcome to the Alert Agent!

        Get notified automatically when new catalysts matching your criteria are added.

        #### How it works:
        1. **Create a saved search** with your preferred filters (phase, therapeutic area, market cap, etc.)
        2. **Choose notification channels** (email, SMS, Slack)
        3. **Sit back and relax** - you'll be alerted when new matches appear

        #### Popular search templates:

        - **Small-cap oncology:** Phase 3, Oncology, <$2B market cap
        - **Rare disease:** Phase 2/3, Rare disease, <$5B market cap
        - **Neurology catalysts:** Phase 3, Neurology, <$3B market cap

        Click **New Search** above to get started!
        """)

        if st.button("Got it, don't show again", use_container_width=True):
            st.session_state.alerts_onboarded = True
            st.rerun()


# Import for type hints


if __name__ == "__main__":
    main()
