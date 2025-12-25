"""Stripe payment integration for Biotech Radar subscriptions."""

import logging
from typing import Optional

import stripe

from .config import Config

logger = logging.getLogger(__name__)


class StripeIntegration:
    """Handles Stripe payment operations for subscriptions."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize Stripe integration.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or Config.from_env()
        stripe.api_key = self.config.stripe_api_key
        logger.info(
            f"Stripe integration initialized in {self.config.app_env} mode"
        )

    def create_checkout_session(
        self, user_email: str, plan: str = "monthly"
    ) -> str:
        """Create Stripe Checkout session.

        Args:
            user_email: User's email address
            plan: "monthly" or "annual"

        Returns:
            Checkout URL

        Raises:
            ValueError: If plan is invalid
            stripe.error.StripeError: If Stripe API call fails
        """
        if plan not in ["monthly", "annual"]:
            raise ValueError(f"Invalid plan: {plan}. Must be 'monthly' or 'annual'")

        price_id = (
            self.config.stripe_price_monthly
            if plan == "monthly"
            else self.config.stripe_price_annual
        )

        if not price_id:
            raise ValueError(
                f"Stripe price ID not configured for {plan} plan. "
                f"Please set STRIPE_PRICE_{plan.upper()} in environment."
            )

        try:
            session = stripe.checkout.Session.create(
                customer_email=user_email,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{self.config.app_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.config.app_url}/canceled",
                metadata={"user_email": user_email, "plan": plan},
            )

            logger.info(
                f"Created checkout session for {user_email} ({plan}): {session.id}"
            )
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    def create_portal_session(self, customer_id: str) -> str:
        """Create Customer Portal session for subscription management.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Customer Portal URL

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not customer_id:
            raise ValueError("Customer ID is required")

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{self.config.app_url}/settings",
            )

            logger.info(
                f"Created portal session for customer {customer_id}: {session.id}"
            )
            return session.url

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    def get_subscription_status(self, user_email: str) -> Optional[dict]:
        """Get user's subscription status from Stripe.

        This method queries Stripe API to find active subscriptions for the user.
        In production, you should cache this result in your database.

        Args:
            user_email: User's email address

        Returns:
            Dict with subscription info or None if no active subscription:
            {
                "status": "active" | "trialing" | "canceled" | "past_due",
                "customer_id": "cus_...",
                "subscription_id": "sub_...",
                "plan_id": "price_...",
                "current_period_end": timestamp,
            }

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not user_email:
            logger.warning("No email provided for subscription status check")
            return None

        try:
            # Find customer by email
            customers = stripe.Customer.list(email=user_email, limit=1)

            if not customers.data:
                logger.debug(f"No Stripe customer found for {user_email}")
                return None

            customer = customers.data[0]

            # Get active subscriptions
            subscriptions = stripe.Subscription.list(
                customer=customer.id,
                status="all",
                limit=1,
            )

            if not subscriptions.data:
                logger.debug(f"No subscriptions found for {user_email}")
                return None

            subscription = subscriptions.data[0]

            result = {
                "status": subscription.status,
                "customer_id": customer.id,
                "subscription_id": subscription.id,
                "plan_id": subscription.items.data[0].price.id,
                "current_period_end": subscription.current_period_end,
            }

            logger.info(
                f"Subscription status for {user_email}: {result['status']}"
            )
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription status: {e}")
            raise

    def verify_webhook_signature(
        self, payload: bytes, sig_header: str
    ) -> Optional[stripe.Event]:
        """Verify Stripe webhook signature and construct event.

        Args:
            payload: Raw webhook payload
            sig_header: Stripe-Signature header value

        Returns:
            Stripe Event object or None if verification fails

        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
        """
        if not self.config.stripe_webhook_secret:
            logger.error("Webhook secret not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.config.stripe_webhook_secret
            )
            logger.info(f"Webhook verified: {event.type}")
            return event

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise
