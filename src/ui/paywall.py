"""Paywall component for expired trials."""

import streamlit as st

from utils.trial_manager import TrialManager


def render_paywall(user_email: str) -> bool:
    """Render paywall if needed.

    Shows pricing cards and subscribe CTAs when trial has expired
    and user doesn't have an active subscription.

    Args:
        user_email: User's email

    Returns:
        True if paywall shown (block content), False otherwise
    """
    trial_mgr = TrialManager(user_email)

    if not trial_mgr.should_show_paywall():
        return False

    # Show paywall
    st.markdown(
        """
    <div style="text-align: center; padding: 60px 20px;">
        <h1>🔒 Your Free Trial Has Ended</h1>
        <p style="font-size: 1.2em; color: #666;">
            Subscribe to continue accessing biotech catalyst data
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Pricing cards
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Choose Your Plan")

        # Monthly plan card
        st.markdown(
            """
        <div style="border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 10px 0; background: #f8f9fa;">
            <h3 style="margin-top: 0;">Monthly Plan</h3>
            <p style="font-size: 2em; font-weight: bold; margin: 10px 0;">
                $29<span style="font-size: 0.5em; font-weight: normal;">/month</span>
            </p>
            <ul style="text-align: left; margin: 15px 0;">
                <li>Full catalyst dashboard</li>
                <li>Real-time price charts</li>
                <li>Daily data updates</li>
                <li>Cancel anytime</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Subscribe button for monthly
        if st.button(
            "Subscribe Monthly - $29/mo",
            key="subscribe_monthly",
            type="primary",
            use_container_width=True,
        ):
            # Set session state to trigger checkout
            st.session_state["checkout_plan"] = "monthly"
            st.session_state["show_subscribe_page"] = True
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Annual plan card
        st.markdown(
            """
        <div style="border: 2px solid #28a745; border-radius: 8px; padding: 20px; margin: 10px 0; background: #f0f8f0;">
            <h3 style="margin-top: 0;">
                Annual Plan
                <span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.7em;">
                    SAVE 33%
                </span>
            </h3>
            <p style="font-size: 2em; font-weight: bold; margin: 10px 0;">
                $232<span style="font-size: 0.5em; font-weight: normal;">/year</span>
            </p>
            <p style="color: #666; margin: 5px 0;">Only $19.33/month</p>
            <ul style="text-align: left; margin: 15px 0;">
                <li>Everything in Monthly</li>
                <li>Save $116/year</li>
                <li>Lock in pricing</li>
                <li>Priority support</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Subscribe button for annual
        if st.button(
            "Subscribe Annual - $232/yr (Best Value)",
            key="subscribe_annual",
            type="secondary",
            use_container_width=True,
        ):
            # Set session state to trigger checkout
            st.session_state["checkout_plan"] = "annual"
            st.session_state["show_subscribe_page"] = True
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # FAQ section
    with st.expander("❓ Frequently Asked Questions"):
        st.markdown(
            """
        **Can I cancel anytime?**
        Yes, you can cancel your subscription at any time from your account settings.

        **Will I get a refund if I cancel?**
        Monthly subscriptions: No refunds, but you keep access until the end of your billing period.
        Annual subscriptions: Prorated refunds available within 30 days.

        **What payment methods do you accept?**
        We accept all major credit cards (Visa, MasterCard, Amex) via Stripe.

        **Is my payment information secure?**
        Yes, all payments are processed through Stripe, a PCI-compliant payment processor.
        We never store your credit card information.

        **Can I switch between plans?**
        Yes, you can upgrade or downgrade your plan at any time from your account settings.
        """
        )

    return True  # Paywall shown, block content


def render_upgrade_prompt(user_email: str, context: str = "general") -> None:
    """Render upgrade prompt for trial users (non-blocking).

    Shows a subtle upgrade prompt without blocking content.
    Used for in-trial upgrade encouragement.

    Args:
        user_email: User's email
        context: Context for the prompt (e.g., 'charts', 'export', 'alerts')
    """
    trial_mgr = TrialManager(user_email)

    # Only show to trial users (not paid subscribers)
    if not trial_mgr.is_trial_active():
        return

    # Only show on last 2 days of trial
    if trial_mgr.get_days_remaining() > 2:
        return

    # Context-specific messages
    messages = {
        "general": "Love what you see? Subscribe now to lock in your access!",
        "charts": "Unlock unlimited chart access with a paid subscription.",
        "export": "Export data to CSV with a paid subscription.",
        "alerts": "Get email alerts for new catalysts with a paid subscription.",
    }

    message = messages.get(context, messages["general"])

    # Show subtle prompt
    st.info(f"💡 {message}")

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("View Plans →", key=f"upgrade_{context}", use_container_width=True):
            st.session_state["show_subscribe_page"] = True
            st.rerun()
