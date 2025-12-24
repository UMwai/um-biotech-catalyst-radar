"""Payment success page - shown after successful Stripe Checkout."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def main():
    """Render payment success page."""
    st.set_page_config(
        page_title="Payment Successful - Biotech Radar",
        page_icon="✅",
        layout="centered",
    )

    # Get session_id from URL parameters
    query_params = st.query_params
    session_id = query_params.get("session_id", None)

    # Success header
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 20px;">
            <h1 style="color: #4CAF50; font-size: 64px;">✅</h1>
            <h1>Payment Successful!</h1>
            <p style="font-size: 18px; color: #666;">
                Thank you for subscribing to Biotech Radar
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # What happens next section
    st.markdown("### What happens next?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px;">
                <h3 style="color: #2196F3;">📧</h3>
                <h4>1. Check Your Email</h4>
                <p style="color: #666;">
                    You'll receive a confirmation email with your receipt and subscription details.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px;">
                <h3 style="color: #2196F3;">🔓</h3>
                <h4>2. Access Dashboard</h4>
                <p style="color: #666;">
                    Your account is now active. Click below to access the full catalyst dashboard.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px;">
                <h3 style="color: #2196F3;">📊</h3>
                <h4>3. Start Trading</h4>
                <p style="color: #666;">
                    Browse upcoming catalysts and identify potential run-up opportunities.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Action buttons
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "Go to Dashboard →",
            key="dashboard_btn",
            type="primary",
            use_container_width=True,
        ):
            st.switch_page("app.py")

    st.markdown("")  # Spacing

    # Session info (for debugging)
    if session_id:
        st.session_state.checkout_session_id = session_id
        if st.session_state.get("user_email"):
            st.session_state.is_subscribed = True
            logger.info(
                f"User {st.session_state.user_email} completed subscription "
                f"(session: {session_id})"
            )

        # Show session ID in expander (for debugging/support)
        with st.expander("🔍 Payment Details (for support)"):
            st.code(f"Session ID: {session_id}")
            st.caption(
                "If you need support, please provide this Session ID to our team."
            )

    # Subscription management info
    st.markdown("---")
    st.markdown("### Manage Your Subscription")

    st.info(
        """
        **Need to update your payment method or cancel your subscription?**

        You can manage your subscription anytime from the Settings page or by visiting
        the Stripe Customer Portal. You'll find a link in your confirmation email.
        """
    )

    # What you get section
    st.markdown("---")
    st.markdown("### What's Included in Your Subscription")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **Full Access Features:**
            - ✅ Unlimited catalyst data
            - ✅ Phase 2/3 clinical trials
            - ✅ Small-cap biotech focus (<$5B market cap)
            - ✅ Real-time stock prices & charts
            - ✅ Daily data updates
            """
        )

    with col2:
        st.markdown(
            """
            **Premium Benefits:**
            - ✅ Advanced filtering & sorting
            - ✅ Export data to CSV
            - ✅ Email alerts (coming soon)
            - ✅ Priority customer support
            - ✅ Early access to new features
            """
        )

    # Help section
    st.markdown("---")
    st.markdown("### Need Help?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            **📚 Documentation**

            Check our [Help Center](https://biotechradar.com/help) for guides
            and tutorials.
            """
        )

    with col2:
        st.markdown(
            """
            **💬 Support**

            Email us at [support@biotechradar.com](mailto:support@biotechradar.com)
            for assistance.
            """
        )

    with col3:
        st.markdown(
            """
            **💳 Billing**

            Manage your subscription in the
            [Customer Portal](https://billing.stripe.com/p/login/test_...).
            """
        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>Questions about your subscription? Contact support@biotechradar.com</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
