"""Stripe subscription gating logic."""

from typing import Dict, Optional

import streamlit as st

# Note: In production, implement proper Stripe Customer Portal integration
# This is a simplified version for MVP


def check_subscription(email: Optional[str] = None) -> bool:
    """Check if user has active subscription.

    For MVP, this uses a simple session-based check.
    In production, integrate with Stripe Customer Portal.

    Args:
        email: User's email address

    Returns:
        True if user has active subscription
    """
    # Check session state first (for demo/testing)
    if st.session_state.get("is_subscribed", False):
        return True

    # In production, check Stripe API
    # stripe.api_key = config.stripe_api_key
    # customers = stripe.Customer.list(email=email)
    # for customer in customers.data:
    #     subscriptions = stripe.Subscription.list(customer=customer.id, status="active")
    #     if subscriptions.data:
    #         return True

    return False


def create_checkout_url(price_id: str, success_url: str, cancel_url: str) -> Optional[str]:
    """Create Stripe Checkout session URL.

    Args:
        price_id: Stripe Price ID
        success_url: URL to redirect after success
        cancel_url: URL to redirect after cancel

    Returns:
        Checkout session URL or None on error
    """
    # In production:
    # import stripe
    # session = stripe.checkout.Session.create(
    #     payment_method_types=["card"],
    #     line_items=[{"price": price_id, "quantity": 1}],
    #     mode="subscription",
    #     success_url=success_url,
    #     cancel_url=cancel_url,
    # )
    # return session.url

    # For MVP, return Stripe Payment Link
    return None


def handle_webhook(payload: bytes, sig_header: str, webhook_secret: str) -> Optional[Dict]:
    """Handle Stripe webhook event.

    Args:
        payload: Raw webhook payload
        sig_header: Stripe-Signature header
        webhook_secret: Webhook secret

    Returns:
        Event data or None on error
    """
    # In production:
    # import stripe
    # try:
    #     event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    #     return event
    # except stripe.error.SignatureVerificationError:
    #     return None

    return None
