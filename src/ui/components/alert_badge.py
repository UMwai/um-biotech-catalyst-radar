"""Alert Badge UI Component.

Per spec Phase 3 Section 2.2:
- In-app alert display component
- Shows unread alert count
- Expandable alert list with acknowledge/dismiss functionality
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def render_alert_badge(user_id: int) -> None:
    """Render the alert badge in the UI.

    Shows a notification badge with unread alert count and expandable list.

    Args:
        user_id: User ID to show alerts for
    """
    try:
        from agents.watchlist_agent import get_watchlist_agent

        agent = get_watchlist_agent()
        unread_alerts = agent.get_user_unread_alerts(user_id)

        if not unread_alerts:
            return

        # Show badge with count
        count = len(unread_alerts)
        severity_emoji = _get_severity_emoji(unread_alerts)

        with st.expander(f"{severity_emoji} {count} Alert{'s' if count != 1 else ''}", expanded=False):
            for alert in unread_alerts:
                _render_alert_card(alert, agent)

    except Exception as e:
        logger.error(f"Error rendering alert badge: {e}")


def _get_severity_emoji(alerts: List[Dict[str, Any]]) -> str:
    """Get emoji based on highest severity alert."""
    severities = [a.get("severity", "info") for a in alerts]

    if "critical" in severities:
        return "🔴"
    elif "warning" in severities:
        return "🟡"
    else:
        return "🔵"


def _render_alert_card(alert: Dict[str, Any], agent) -> None:
    """Render a single alert card.

    Args:
        alert: Alert dict
        agent: WatchlistAgent instance for acknowledge
    """
    severity = alert.get("severity", "info")
    ticker = alert.get("ticker", "???")
    trigger = alert.get("trigger_event", "Unknown event")
    created_at = alert.get("created_at", "")
    alert_id = alert.get("id")

    # Severity styling
    severity_colors = {
        "critical": "#ff4444",
        "warning": "#ffaa00",
        "info": "#4488ff",
    }
    color = severity_colors.get(severity, "#888888")

    # Card layout
    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown(
            f"""
            <div style="
                border-left: 3px solid {color};
                padding-left: 10px;
                margin-bottom: 10px;
            ">
                <strong>{ticker}</strong><br/>
                <span style="font-size: 0.9em;">{trigger}</span><br/>
                <span style="font-size: 0.8em; color: #888;">{created_at}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        if alert_id and st.button("Dismiss", key=f"dismiss_{alert_id}"):
            agent.acknowledge_alert(alert_id)
            st.rerun()


def render_alert_summary(user_id: int) -> None:
    """Render a compact alert summary for the dashboard header.

    Args:
        user_id: User ID
    """
    try:
        from utils.sqlite_db import get_db

        db = get_db()
        count = db.get_unread_alert_count(user_id)

        if count > 0:
            if count >= 5:
                st.warning(f"You have {count} unread alerts!")
            else:
                st.info(f"You have {count} new alert{'s' if count != 1 else ''}.")

    except Exception as e:
        logger.error(f"Error rendering alert summary: {e}")


def render_alerts_page(user_id: int) -> None:
    """Render full alerts management page.

    Args:
        user_id: User ID
    """
    st.markdown("## Alerts")

    try:
        from agents.watchlist_agent import get_watchlist_agent
        from utils.sqlite_db import get_db

        agent = get_watchlist_agent()
        db = get_db()

        # Tabs for unread/all alerts
        tab1, tab2 = st.tabs(["Unread", "All Alerts"])

        with tab1:
            unread = db.get_user_alerts(user_id, unread_only=True)
            if not unread:
                st.success("No unread alerts!")
            else:
                for alert in unread:
                    _render_alert_card(alert, agent)

        with tab2:
            all_alerts = db.get_user_alerts(user_id, unread_only=False)
            if not all_alerts:
                st.info("No alerts yet. Add tickers to your watchlist to receive alerts.")
            else:
                for alert in all_alerts:
                    acknowledged = alert.get("acknowledged_at") is not None
                    if acknowledged:
                        st.markdown(
                            f"<span style='color: #888;'>~{alert.get('trigger_event', '')}~</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        _render_alert_card(alert, agent)

    except Exception as e:
        logger.error(f"Error rendering alerts page: {e}")
        st.error("Could not load alerts.")


def render_watchlist_manager(user_id: int) -> None:
    """Render watchlist management UI.

    Args:
        user_id: User ID
    """
    st.markdown("## My Watchlist")

    try:
        from utils.user_memory import UserMemory

        memory = UserMemory()
        watchlist = memory.get_watchlist(user_id)
        tickers = watchlist.get("tickers", [])

        # Display current watchlist
        if tickers:
            st.markdown("### Current Tickers")
            for i, item in enumerate(tickers):
                symbol = item.get("symbol") if isinstance(item, dict) else item
                notes = item.get("notes", "") if isinstance(item, dict) else ""

                col1, col2, col3 = st.columns([2, 3, 1])

                with col1:
                    st.markdown(f"**{symbol}**")

                with col2:
                    st.markdown(f"<span style='color: #888;'>{notes}</span>", unsafe_allow_html=True)

                with col3:
                    if st.button("Remove", key=f"remove_{symbol}_{i}"):
                        memory.remove_from_watchlist(user_id, symbol)
                        st.rerun()
        else:
            st.info("Your watchlist is empty. Add tickers below to receive alerts.")

        # Add new ticker
        st.markdown("### Add Ticker")
        col1, col2, col3 = st.columns([2, 3, 1])

        with col1:
            new_ticker = st.text_input("Ticker", placeholder="ACAD", key="new_ticker")

        with col2:
            new_notes = st.text_input("Notes (optional)", placeholder="Phase 3 readout", key="new_notes")

        with col3:
            st.markdown("")  # Spacing
            if st.button("Add"):
                if new_ticker:
                    memory.add_to_watchlist(user_id, new_ticker.upper(), new_notes)
                    st.success(f"Added {new_ticker.upper()} to watchlist!")
                    st.rerun()

    except Exception as e:
        logger.error(f"Error rendering watchlist manager: {e}")
        st.error("Could not load watchlist.")
