"""Subscription page with pricing and Stripe Checkout integration."""

import logging

import streamlit as st

from utils.config import Config
from utils.stripe_integration import StripeIntegration

logger = logging.getLogger(__name__)


def main():
    """Render subscription page with pricing cards."""
    st.set_page_config(
        page_title="Subscribe - Biotech Radar",
        page_icon="💳",
        layout="centered",
    )

    st.title("💳 Subscribe to Biotech Radar")
    st.markdown(
        """
        Get unlimited access to our curated list of Phase 2/3 clinical trial catalysts
        for small-cap biotech stocks.
        """
    )

    # Load configuration
    config = Config.from_env()

    # Check if Stripe is configured
    if not config.is_configured:
        st.error(
            "Stripe is not configured. Please contact support or set up your "
            "environment variables (STRIPE_API_KEY, STRIPE_PRICE_MONTHLY, "
            "STRIPE_PRICE_ANNUAL)."
        )
        st.stop()

    # Get or set user email in session state
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    # Email input
    st.markdown("### Enter your email to continue")
    user_email = st.text_input(
        "Email Address",
        value=st.session_state.user_email,
        placeholder="your.email@example.com",
        help="We'll use this email for your subscription and login.",
    )

    if user_email:
        st.session_state.user_email = user_email

    # Pricing cards
    st.markdown("---")
    st.markdown("### Choose Your Plan")

    col1, col2 = st.columns(2)

    # Monthly Plan
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
                    <li>Updated daily</li>
                    <li>Cancel anytime</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")  # Spacing
        monthly_button = st.button(
            "Subscribe Monthly - $29/mo",
            key="monthly_btn",
            type="primary",
            use_container_width=True,
        )

    # Annual Plan
    with col2:
        st.markdown(
            """
            <div style="padding: 20px; border: 2px solid #2196F3; border-radius: 10px; text-align: center;">
                <h3>Annual</h3>
                <h1 style="color: #2196F3;">$232</h1>
                <p style="color: #666;">per year</p>
                <p><strong style="color: #4CAF50;">Save 33% ($116/year)</strong></p>
                <ul style="text-align: left; padding-left: 20px;">
                    <li>All Monthly features</li>
                    <li><strong>Priority support</strong></li>
                    <li><strong>Early access to new features</strong></li>
                    <li>Best value</li>
                    <li>Cancel anytime</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")  # Spacing
        annual_button = st.button(
            "Subscribe Annual - $232/yr",
            key="annual_btn",
            type="primary",
            use_container_width=True,
        )

    # Handle button clicks
    if monthly_button or annual_button:
        if not user_email or "@" not in user_email:
            st.error("Please enter a valid email address.")
            st.stop()

        plan = "monthly" if monthly_button else "annual"

        try:
            with st.spinner(f"Creating checkout session for {plan} plan..."):
                stripe_integration = StripeIntegration(config)
                checkout_url = stripe_integration.create_checkout_session(
                    user_email=user_email, plan=plan
                )

            # Redirect to Stripe Checkout
            st.success(f"Redirecting to Stripe Checkout for {plan} plan...")
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={checkout_url}">',
                unsafe_allow_html=True,
            )
            # Also provide a fallback link
            st.markdown(f"If you are not redirected automatically, [click here]({checkout_url}).")

        except ValueError as e:
            st.error(f"Configuration error: {e}")
            logger.error(f"Configuration error during checkout: {e}")

        except Exception as e:
            st.error("Failed to create checkout session. Please try again or contact support.")
            logger.error(f"Error creating checkout session: {e}", exc_info=True)

    # FAQ Section
    st.markdown("---")
    st.markdown("### Frequently Asked Questions")

    with st.expander("Can I cancel anytime?"):
        st.write(
            """
            Yes! You can cancel your subscription at any time from the Customer Portal.
            You'll continue to have access until the end of your current billing period.
            """
        )

    with st.expander("What payment methods do you accept?"):
        st.write(
            """
            We accept all major credit cards (Visa, MasterCard, American Express)
            through our secure payment processor, Stripe.
            """
        )

    with st.expander("Is my payment information secure?"):
        st.write(
            """
            Absolutely. We use Stripe for payment processing, which is PCI DSS Level 1
            certified - the highest level of security in the payment industry. We never
            store your credit card information.
            """
        )

    with st.expander("How often is the data updated?"):
        st.write(
            """
            Our catalyst dashboard is updated daily with the latest trial data from
            ClinicalTrials.gov and real-time stock prices from Yahoo Finance.
            """
        )

    with st.expander("Do you offer refunds?"):
        st.write(
            """
            We offer a 7-day money-back guarantee. If you're not satisfied with the
            service within the first 7 days, contact us for a full refund.
            """
        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 12px;">
            <p>By subscribing, you agree to our Terms of Service and Privacy Policy.</p>
            <p>Questions? Contact us at support@biotechradar.com</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
