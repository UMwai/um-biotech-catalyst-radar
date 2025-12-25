"""Trial countdown banner component."""

import streamlit as st

from utils.trial_manager import TrialManager


def render_trial_banner(user_email: str) -> None:
    """Render trial countdown banner.

    Shows countdown timer during trial, subscribe CTA when close to expiration,
    and expiration notice after trial ends.

    Args:
        user_email: Logged-in user's email
    """
    trial_mgr = TrialManager(user_email)

    # Skip if user has paid subscription
    if trial_mgr.has_active_subscription():
        return

    # Trial active
    if trial_mgr.is_trial_active():
        days_remaining = trial_mgr.get_days_remaining()
        hours_remaining = trial_mgr.get_hours_remaining()

        # Different messages based on time remaining
        if days_remaining > 1:
            # More than 1 day: Show days remaining (info banner)
            message = f"⏱️ **Free trial:** {days_remaining} days remaining"
            st.info(message)

        elif days_remaining == 1:
            # Last day: Show hours remaining (warning banner)
            message = f"⏱️ **Free trial expires tomorrow** ({hours_remaining} hours left)"
            st.warning(message)

            # Show subscribe button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Subscribe Now →", type="primary", use_container_width=True):
                    # Navigate to subscribe page
                    # Note: Streamlit doesn't have native page switching yet,
                    # so we'll use query params or session state
                    st.session_state["show_subscribe_page"] = True
                    st.rerun()

        else:
            # Less than 24 hours: Show hours (urgent warning)
            message = f"⏱️ **Trial expires in {hours_remaining} hours** - Subscribe to keep access"
            st.warning(message)

            # Show subscribe button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Subscribe Now →", type="primary", use_container_width=True):
                    st.session_state["show_subscribe_page"] = True
                    st.rerun()

    # Trial expired
    elif trial_mgr.is_trial_expired():
        st.error(
            "❌ **Your trial has expired.** Subscribe to continue accessing catalyst data."
        )

        # Show subscribe button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button(
                "View Subscription Options →", type="primary", use_container_width=True
            ):
                st.session_state["show_subscribe_page"] = True
                st.rerun()


def render_trial_info_sidebar(user_email: str) -> None:
    """Render trial info in sidebar (compact version).

    Args:
        user_email: Logged-in user's email
    """
    trial_mgr = TrialManager(user_email)

    # Skip if user has paid subscription
    if trial_mgr.has_active_subscription():
        st.sidebar.success("✓ **Active Subscription**")
        return

    # Show trial status
    if trial_mgr.is_trial_active():
        days_remaining = trial_mgr.get_days_remaining()
        hours_remaining = trial_mgr.get_hours_remaining()

        if days_remaining > 1:
            st.sidebar.info(f"**Trial:** {days_remaining} days left")
        elif days_remaining == 1:
            st.sidebar.warning(f"**Trial:** {hours_remaining}h left")
        else:
            st.sidebar.warning(f"**Trial:** {hours_remaining}h left")

    elif trial_mgr.is_trial_expired():
        st.sidebar.error("**Trial Expired**")
