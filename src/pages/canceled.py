"""Payment canceled page - shown when user cancels Stripe Checkout."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def main():
    """Render payment canceled page."""
    st.set_page_config(
        page_title="Payment Canceled - Biotech Radar",
        page_icon="❌",
        layout="centered",
    )

    # Canceled header
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 20px;">
            <h1 style="color: #FF9800; font-size: 64px;">⚠️</h1>
            <h1>Payment Canceled</h1>
            <p style="font-size: 18px; color: #666;">
                Your payment was not processed. No charges were made to your account.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # What happened section
    st.info(
        """
        **What happened?**

        You canceled the checkout process before completing payment. This is completely
        normal - you can try again whenever you're ready!
        """
    )

    # Reasons for cancellation
    st.markdown("### Common Reasons for Cancellation")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **Technical Issues:**
            - ❓ Browser compatibility issues
            - ❓ Payment method not accepted
            - ❓ Network connection problems
            - ❓ Form validation errors

            If you experienced technical issues, please try:
            - Using a different browser
            - Checking your internet connection
            - Contacting our support team
            """
        )

    with col2:
        st.markdown(
            """
            **Decision-Making:**
            - 💭 Need more time to decide
            - 💭 Want to compare pricing
            - 💭 Have questions about features
            - 💭 Prefer to talk to support first

            We're here to help! Reach out if you have any questions.
            """
        )

    st.markdown("---")

    # Action buttons
    st.markdown("### What would you like to do?")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "Try Again - Return to Pricing",
            key="retry_btn",
            type="primary",
            use_container_width=True,
        ):
            st.switch_page("pages/subscribe.py")

        st.markdown("")  # Spacing

        if st.button(
            "View Free Dashboard",
            key="free_dashboard_btn",
            use_container_width=True,
        ):
            st.switch_page("app.py")

    st.markdown("---")

    # Still interested section
    st.markdown("### Still Interested? Here's What You're Missing")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            **Premium Features:**
            - 📊 Full access to all catalyst data
            - 📈 Real-time stock prices & charts
            - 🔍 Advanced filtering & sorting
            - 📅 Daily data updates
            - 📥 Export to CSV
            """
        )

    with col2:
        st.markdown(
            """
            **Subscription Benefits:**
            - ✅ Cancel anytime
            - ✅ 7-day money-back guarantee
            - ✅ Priority customer support
            - ✅ Early access to new features
            - ✅ Secure payment via Stripe
            """
        )

    # Pricing reminder
    st.markdown("---")
    st.markdown("### Our Pricing Plans")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="padding: 20px; border: 2px solid #4CAF50; border-radius: 10px; text-align: center;">
                <h3>Monthly</h3>
                <h1 style="color: #4CAF50;">$29</h1>
                <p style="color: #666;">per month</p>
                <ul style="text-align: left; padding-left: 20px;">
                    <li>Full access to catalyst dashboard</li>
                    <li>Phase 2/3 trial data</li>
                    <li>Market cap & price charts</li>
                    <li>Cancel anytime</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="padding: 20px; border: 2px solid #2196F3; border-radius: 10px; text-align: center;">
                <h3>Annual</h3>
                <h1 style="color: #2196F3;">$232</h1>
                <p style="color: #666;">per year</p>
                <p><strong style="color: #4CAF50;">Save $116/year</strong></p>
                <ul style="text-align: left; padding-left: 20px;">
                    <li>All Monthly features</li>
                    <li>Priority support</li>
                    <li>Early access to features</li>
                    <li>Best value (33% savings)</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # FAQ Section
    st.markdown("---")
    st.markdown("### Have Questions?")

    with st.expander("Is my payment information secure?"):
        st.write(
            """
            Yes! We use Stripe for payment processing, which is PCI DSS Level 1
            certified - the highest level of security in the payment industry. We never
            store your credit card information on our servers.
            """
        )

    with st.expander("What payment methods do you accept?"):
        st.write(
            """
            We accept all major credit cards including Visa, MasterCard, American
            Express, and Discover through our secure payment processor, Stripe.
            """
        )

    with st.expander("Can I get a refund if I'm not satisfied?"):
        st.write(
            """
            Yes! We offer a 7-day money-back guarantee. If you're not satisfied with
            the service within the first 7 days, contact us at support@biotechradar.com
            for a full refund, no questions asked.
            """
        )

    with st.expander("Can I try the service before subscribing?"):
        st.write(
            """
            Yes! You can view a limited preview of the catalyst dashboard without
            subscribing. Click "View Free Dashboard" above to see a sample of our data.
            """
        )

    with st.expander("Do you offer discounts or promotions?"):
        st.write(
            """
            Our annual plan already includes a 33% discount ($116 savings per year)
            compared to the monthly plan. We occasionally run promotions - sign up for
            our newsletter to be notified.
            """
        )

    # Contact support section
    st.markdown("---")
    st.markdown("### Need Help or Have Questions?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            **📧 Email Support**

            [support@biotechradar.com](mailto:support@biotechradar.com)

            We typically respond within 24 hours.
            """
        )

    with col2:
        st.markdown(
            """
            **📚 Help Center**

            [View Documentation](https://biotechradar.com/help)

            Browse our guides and FAQs.
            """
        )

    with col3:
        st.markdown(
            """
            **💬 Live Chat**

            Chat with our team (coming soon)

            Available M-F, 9am-5pm EST.
            """
        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>Ready to subscribe? <a href="/subscribe">View our pricing plans</a></p>
            <p>Questions? Email us at support@biotechradar.com</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Log the cancellation (for analytics)
    logger.info(f"User canceled checkout (email: {st.session_state.get('user_email', 'unknown')})")


if __name__ == "__main__":
    main()
