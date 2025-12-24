"""
UI component for managing saved searches.

This module provides:
- List view of user's saved searches
- Create/edit/delete functionality
- Test search functionality
- Pause/resume toggle
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

from supabase import create_client, Client
import os


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        st.error("Supabase configuration missing")
        st.stop()

    return create_client(supabase_url, supabase_key)


def render_saved_searches(user_id: str) -> None:
    """
    Render the saved searches management interface.

    Args:
        user_id: Current user's UUID
    """
    st.subheader("My Saved Searches")

    supabase = get_supabase_client()

    # Get user tier for limit checking
    try:
        tier_response = supabase.rpc("get_user_tier", {"p_user_id": user_id}).execute()
        user_tier = tier_response.data or "free"
    except:
        user_tier = "free"

    # Fetch user's saved searches
    try:
        response = supabase.table("saved_searches").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).execute()

        searches = response.data or []
    except Exception as e:
        st.error(f"Error loading saved searches: {e}")
        searches = []

    # Display search limit
    search_limit = 3 if user_tier in ["free", "trial"] else "Unlimited"
    active_count = len([s for s in searches if s["active"]])

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Active searches: {active_count} / {search_limit}")
    with col2:
        if st.button("➕ New Search", type="primary", use_container_width=True):
            st.session_state.show_create_modal = True

    st.divider()

    # Display searches
    if not searches:
        st.info(
            "No saved searches yet. Create your first search to start receiving alerts "
            "when new catalysts matching your criteria are added."
        )
    else:
        for search in searches:
            _render_search_card(supabase, search, user_tier)

    # Create/Edit modal
    if st.session_state.get("show_create_modal"):
        _render_create_modal(supabase, user_id, user_tier)

    if st.session_state.get("show_edit_modal"):
        _render_edit_modal(supabase, st.session_state.get("edit_search_id"))


def _render_search_card(supabase: Client, search: Dict[str, Any], user_tier: str) -> None:
    """Render a single saved search card."""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            # Search name and status
            status_icon = "✅" if search["active"] else "⏸️"
            st.markdown(f"### {status_icon} {search['name']}")

            # Query parameters (human-readable)
            params = search["query_params"]
            param_strings = []

            if params.get("phase"):
                param_strings.append(f"**Phase:** {params['phase']}")
            if params.get("therapeutic_area"):
                param_strings.append(f"**Area:** {params['therapeutic_area']}")
            if params.get("max_market_cap"):
                cap_b = params["max_market_cap"] / 1_000_000_000
                param_strings.append(f"**Max Cap:** ${cap_b:.1f}B")
            if params.get("min_market_cap"):
                cap_b = params["min_market_cap"] / 1_000_000_000
                param_strings.append(f"**Min Cap:** ${cap_b:.1f}B")

            if param_strings:
                st.markdown(" • ".join(param_strings))

            # Notification channels
            channels = search["notification_channels"]
            channel_icons = {
                "email": "📧",
                "sms": "📱",
                "slack": "💬"
            }
            channel_str = " ".join([channel_icons.get(ch, ch) for ch in channels])
            st.caption(f"Channels: {channel_str}")

        with col2:
            # Last checked
            if search.get("last_checked"):
                last_checked = datetime.fromisoformat(search["last_checked"].replace("Z", "+00:00"))
                st.caption(f"Last checked: {last_checked.strftime('%m/%d %H:%M')}")
            else:
                st.caption("Never checked")

            # Get match count from last 7 days
            match_count = _get_match_count(supabase, search["id"])
            st.metric("Matches (7d)", match_count)

        # Action buttons
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Edit", key=f"edit_{search['id']}", use_container_width=True):
                st.session_state.show_edit_modal = True
                st.session_state.edit_search_id = search["id"]
                st.rerun()

        with col2:
            if st.button("Test", key=f"test_{search['id']}", use_container_width=True):
                _test_search(supabase, search)

        with col3:
            toggle_label = "Resume" if not search["active"] else "Pause"
            if st.button(toggle_label, key=f"toggle_{search['id']}", use_container_width=True):
                _toggle_search(supabase, search["id"], not search["active"])
                st.rerun()

        with col4:
            if st.button("Delete", key=f"delete_{search['id']}", type="secondary", use_container_width=True):
                _delete_search(supabase, search["id"])
                st.rerun()


def _get_match_count(supabase: Client, search_id: str) -> int:
    """Get number of matches in last 7 days for a search."""
    try:
        response = supabase.table("alert_notifications").select(
            "id", count="exact"
        ).eq("saved_search_id", search_id).gte(
            "notification_sent_at",
            (datetime.now() - timedelta(days=7)).isoformat()
        ).execute()

        return response.count or 0
    except:
        return 0


def _test_search(supabase: Client, search: Dict[str, Any]) -> None:
    """Test a saved search and display results."""
    try:
        query = supabase.table("catalysts").select("*")
        params = search["query_params"]

        # Apply filters (same logic as alert agent)
        if params.get("phase"):
            query = query.eq("phase", params["phase"])
        if params.get("max_market_cap"):
            query = query.lt("market_cap", params["max_market_cap"])
        if params.get("min_market_cap"):
            query = query.gte("market_cap", params["min_market_cap"])
        if params.get("therapeutic_area"):
            query = query.ilike("indication", f"%{params['therapeutic_area']}%")

        query = query.not_.is_("ticker", "null")
        query = query.order("completion_date", desc=False).limit(10)

        response = query.execute()
        results = response.data or []

        st.success(f"Found {len(results)} matching catalysts")

        if results:
            st.dataframe(
                [
                    {
                        "Ticker": r["ticker"],
                        "Phase": r["phase"],
                        "Indication": r["indication"][:50] + "...",
                        "Date": r["completion_date"]
                    }
                    for r in results
                ],
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:
        st.error(f"Error testing search: {e}")


def _toggle_search(supabase: Client, search_id: str, active: bool) -> None:
    """Toggle search active status."""
    try:
        supabase.table("saved_searches").update({"active": active}).eq("id", search_id).execute()
        st.success(f"Search {'activated' if active else 'paused'} successfully")
    except Exception as e:
        st.error(f"Error toggling search: {e}")


def _delete_search(supabase: Client, search_id: str) -> None:
    """Delete a saved search."""
    try:
        supabase.table("saved_searches").delete().eq("id", search_id).execute()
        st.success("Search deleted successfully")
    except Exception as e:
        st.error(f"Error deleting search: {e}")


def _render_create_modal(supabase: Client, user_id: str, user_tier: str) -> None:
    """Render the create search modal."""
    with st.form("create_search_form"):
        st.subheader("Create Saved Search")

        name = st.text_input(
            "Search Name*",
            placeholder="e.g., Oncology under $500M",
            help="Give this search a memorable name"
        )

        st.markdown("#### Filter Criteria")

        col1, col2 = st.columns(2)
        with col1:
            phase = st.selectbox(
                "Phase",
                ["", "Phase 2", "Phase 3", "Phase 2/Phase 3"],
                help="Filter by trial phase"
            )

            therapeutic_area = st.text_input(
                "Therapeutic Area",
                placeholder="e.g., oncology, neurology",
                help="Filter by indication (case-insensitive)"
            )

        with col2:
            max_market_cap = st.number_input(
                "Max Market Cap ($B)",
                min_value=0.0,
                max_value=10.0,
                value=5.0,
                step=0.5,
                help="Maximum market capitalization in billions"
            )

            min_market_cap = st.number_input(
                "Min Market Cap ($B)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.5,
                help="Minimum market capitalization in billions"
            )

        st.markdown("#### Notification Settings")

        # Email always enabled
        email_enabled = True
        st.checkbox("📧 Email", value=True, disabled=True, help="Email notifications (always enabled)")

        # SMS and Slack for Pro tier only
        sms_enabled = st.checkbox(
            "📱 SMS",
            value=False,
            disabled=(user_tier != "pro"),
            help="SMS notifications (Pro tier only)" if user_tier != "pro" else "SMS notifications"
        )

        slack_enabled = st.checkbox(
            "💬 Slack",
            value=False,
            disabled=(user_tier != "pro"),
            help="Slack notifications (Pro tier only)" if user_tier != "pro" else "Slack notifications"
        )

        if user_tier != "pro" and (sms_enabled or slack_enabled):
            st.info("Upgrade to Pro tier to enable SMS and Slack notifications")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Create Search", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if submit:
            if not name:
                st.error("Please provide a search name")
            else:
                # Build query params
                query_params = {}
                if phase:
                    query_params["phase"] = phase
                if therapeutic_area:
                    query_params["therapeutic_area"] = therapeutic_area
                if max_market_cap > 0:
                    query_params["max_market_cap"] = int(max_market_cap * 1_000_000_000)
                if min_market_cap > 0:
                    query_params["min_market_cap"] = int(min_market_cap * 1_000_000_000)

                # Build notification channels
                channels = ["email"]
                if sms_enabled and user_tier == "pro":
                    channels.append("sms")
                if slack_enabled and user_tier == "pro":
                    channels.append("slack")

                # Create search
                try:
                    supabase.table("saved_searches").insert({
                        "user_id": user_id,
                        "name": name,
                        "query_params": query_params,
                        "notification_channels": channels,
                        "active": True
                    }).execute()

                    st.success(f"Search '{name}' created successfully!")
                    st.session_state.show_create_modal = False
                    st.rerun()

                except Exception as e:
                    st.error(f"Error creating search: {e}")

        if cancel:
            st.session_state.show_create_modal = False
            st.rerun()


def _render_edit_modal(supabase: Client, search_id: str) -> None:
    """Render the edit search modal."""
    # Fetch current search data
    try:
        response = supabase.table("saved_searches").select("*").eq("id", search_id).single().execute()
        search = response.data
    except Exception as e:
        st.error(f"Error loading search: {e}")
        return

    with st.form("edit_search_form"):
        st.subheader(f"Edit: {search['name']}")

        name = st.text_input("Search Name*", value=search["name"])

        st.markdown("#### Filter Criteria")

        params = search["query_params"]

        col1, col2 = st.columns(2)
        with col1:
            phase = st.selectbox(
                "Phase",
                ["", "Phase 2", "Phase 3", "Phase 2/Phase 3"],
                index=["", "Phase 2", "Phase 3", "Phase 2/Phase 3"].index(params.get("phase", ""))
            )

            therapeutic_area = st.text_input(
                "Therapeutic Area",
                value=params.get("therapeutic_area", "")
            )

        with col2:
            max_cap_b = params.get("max_market_cap", 5_000_000_000) / 1_000_000_000
            max_market_cap = st.number_input(
                "Max Market Cap ($B)",
                min_value=0.0,
                max_value=10.0,
                value=float(max_cap_b),
                step=0.5
            )

            min_cap_b = params.get("min_market_cap", 0) / 1_000_000_000
            min_market_cap = st.number_input(
                "Min Market Cap ($B)",
                min_value=0.0,
                max_value=10.0,
                value=float(min_cap_b),
                step=0.5
            )

        st.markdown("#### Notification Settings")

        channels = search["notification_channels"]
        email_enabled = True
        st.checkbox("📧 Email", value=True, disabled=True)

        sms_enabled = st.checkbox("📱 SMS", value="sms" in channels)
        slack_enabled = st.checkbox("💬 Slack", value="slack" in channels)

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if submit:
            # Build updated data
            query_params = {}
            if phase:
                query_params["phase"] = phase
            if therapeutic_area:
                query_params["therapeutic_area"] = therapeutic_area
            if max_market_cap > 0:
                query_params["max_market_cap"] = int(max_market_cap * 1_000_000_000)
            if min_market_cap > 0:
                query_params["min_market_cap"] = int(min_market_cap * 1_000_000_000)

            channels = ["email"]
            if sms_enabled:
                channels.append("sms")
            if slack_enabled:
                channels.append("slack")

            # Update search
            try:
                supabase.table("saved_searches").update({
                    "name": name,
                    "query_params": query_params,
                    "notification_channels": channels
                }).eq("id", search_id).execute()

                st.success("Search updated successfully!")
                st.session_state.show_edit_modal = False
                st.session_state.edit_search_id = None
                st.rerun()

            except Exception as e:
                st.error(f"Error updating search: {e}")

        if cancel:
            st.session_state.show_edit_modal = False
            st.session_state.edit_search_id = None
            st.rerun()


# Import for date calculations
from datetime import timedelta
