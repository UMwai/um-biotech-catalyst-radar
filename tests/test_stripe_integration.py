"""Tests for Stripe payment integration."""

import pytest
from unittest.mock import Mock, patch

import stripe

from src.utils.config import Config
from src.utils.stripe_integration import StripeIntegration


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        stripe_api_key="sk_test_fake_key_12345",
        stripe_price_monthly="price_monthly_test_123",
        stripe_price_annual="price_annual_test_456",
        stripe_webhook_secret="whsec_test_secret_789",
        stripe_payment_link="https://checkout.stripe.com/test",
        app_env="test",
        app_url="http://localhost:8501",
        debug=True,
    )


@pytest.fixture
def stripe_integration(mock_config):
    """Create StripeIntegration instance with mock config."""
    return StripeIntegration(config=mock_config)


class TestStripeIntegration:
    """Test suite for StripeIntegration class."""

    def test_initialization(self, stripe_integration, mock_config):
        """Test that StripeIntegration initializes correctly."""
        assert stripe_integration.config == mock_config
        assert stripe.api_key == mock_config.stripe_api_key

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_monthly(self, mock_create, stripe_integration, mock_config):
        """Test creating a monthly checkout session."""
        # Mock Stripe response
        mock_session = Mock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_123"
        mock_create.return_value = mock_session

        # Create checkout session
        user_email = "test@example.com"
        checkout_url = stripe_integration.create_checkout_session(
            user_email=user_email, plan="monthly"
        )

        # Verify Stripe API was called correctly
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]

        assert call_args["customer_email"] == user_email
        assert call_args["payment_method_types"] == ["card"]
        assert call_args["line_items"] == [
            {"price": mock_config.stripe_price_monthly, "quantity": 1}
        ]
        assert call_args["mode"] == "subscription"
        assert (
            call_args["success_url"]
            == f"{mock_config.app_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        )
        assert call_args["cancel_url"] == f"{mock_config.app_url}/canceled"
        assert call_args["metadata"]["user_email"] == user_email
        assert call_args["metadata"]["plan"] == "monthly"

        # Verify return value
        assert checkout_url == mock_session.url

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_annual(self, mock_create, stripe_integration, mock_config):
        """Test creating an annual checkout session."""
        # Mock Stripe response
        mock_session = Mock()
        mock_session.id = "cs_test_456"
        mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_456"
        mock_create.return_value = mock_session

        # Create checkout session
        user_email = "annual@example.com"
        checkout_url = stripe_integration.create_checkout_session(
            user_email=user_email, plan="annual"
        )

        # Verify correct price ID was used
        call_args = mock_create.call_args[1]
        assert call_args["line_items"] == [
            {"price": mock_config.stripe_price_annual, "quantity": 1}
        ]
        assert call_args["metadata"]["plan"] == "annual"

        # Verify return value
        assert checkout_url == mock_session.url

    def test_create_checkout_session_invalid_plan(self, stripe_integration):
        """Test that invalid plan raises ValueError."""
        with pytest.raises(ValueError, match="Invalid plan"):
            stripe_integration.create_checkout_session(
                user_email="test@example.com", plan="invalid_plan"
            )

    def test_create_checkout_session_missing_price_id(self, mock_config):
        """Test that missing price ID raises ValueError."""
        # Create config with empty price IDs
        config = Config(
            stripe_api_key="sk_test_key",
            stripe_price_monthly="",
            stripe_price_annual="",
            stripe_webhook_secret="whsec_test",
            stripe_payment_link="",
            app_env="test",
            app_url="http://localhost:8501",
            debug=True,
        )
        integration = StripeIntegration(config=config)

        with pytest.raises(ValueError, match="Stripe price ID not configured"):
            integration.create_checkout_session(user_email="test@example.com", plan="monthly")

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_stripe_error(self, mock_create, stripe_integration):
        """Test handling of Stripe API errors."""
        # Mock Stripe error
        mock_create.side_effect = stripe.error.StripeError("API Error")

        with pytest.raises(stripe.error.StripeError):
            stripe_integration.create_checkout_session(
                user_email="test@example.com", plan="monthly"
            )

    @patch("stripe.billing_portal.Session.create")
    def test_create_portal_session(self, mock_create, stripe_integration, mock_config):
        """Test creating a customer portal session."""
        # Mock Stripe response
        mock_session = Mock()
        mock_session.id = "bps_test_789"
        mock_session.url = "https://billing.stripe.com/p/session/test_789"
        mock_create.return_value = mock_session

        # Create portal session
        customer_id = "cus_test_customer_123"
        portal_url = stripe_integration.create_portal_session(customer_id=customer_id)

        # Verify Stripe API was called correctly
        mock_create.assert_called_once_with(
            customer=customer_id,
            return_url=f"{mock_config.app_url}/settings",
        )

        # Verify return value
        assert portal_url == mock_session.url

    def test_create_portal_session_empty_customer_id(self, stripe_integration):
        """Test that empty customer ID raises ValueError."""
        with pytest.raises(ValueError, match="Customer ID is required"):
            stripe_integration.create_portal_session(customer_id="")

    @patch("stripe.billing_portal.Session.create")
    def test_create_portal_session_stripe_error(self, mock_create, stripe_integration):
        """Test handling of Stripe API errors in portal session."""
        mock_create.side_effect = stripe.error.InvalidRequestError(
            "Customer not found", param="customer"
        )

        with pytest.raises(stripe.error.InvalidRequestError):
            stripe_integration.create_portal_session(customer_id="cus_invalid")

    @patch("stripe.Subscription.list")
    @patch("stripe.Customer.list")
    def test_get_subscription_status_active(
        self, mock_customer_list, mock_subscription_list, stripe_integration
    ):
        """Test getting subscription status for active subscriber."""
        # Mock customer
        mock_customer = Mock()
        mock_customer.id = "cus_test_123"
        mock_customer_list.return_value = Mock(data=[mock_customer])

        # Mock subscription
        mock_price = Mock()
        mock_price.id = "price_monthly_test_123"

        mock_item = Mock()
        mock_item.price = mock_price

        mock_subscription = Mock()
        mock_subscription.id = "sub_test_456"
        mock_subscription.status = "active"
        mock_subscription.current_period_end = 1735689600
        mock_subscription.items = Mock(data=[mock_item])
        mock_subscription_list.return_value = Mock(data=[mock_subscription])

        # Get subscription status
        user_email = "active@example.com"
        status = stripe_integration.get_subscription_status(user_email=user_email)

        # Verify API calls
        mock_customer_list.assert_called_once_with(email=user_email, limit=1)
        mock_subscription_list.assert_called_once_with(
            customer=mock_customer.id,
            status="all",
            limit=1,
        )

        # Verify return value
        assert status == {
            "status": "active",
            "customer_id": "cus_test_123",
            "subscription_id": "sub_test_456",
            "plan_id": "price_monthly_test_123",
            "current_period_end": 1735689600,
        }

    @patch("stripe.Customer.list")
    def test_get_subscription_status_no_customer(self, mock_customer_list, stripe_integration):
        """Test getting subscription status when customer doesn't exist."""
        mock_customer_list.return_value = Mock(data=[])

        status = stripe_integration.get_subscription_status(user_email="nonexistent@example.com")

        assert status is None

    @patch("stripe.Subscription.list")
    @patch("stripe.Customer.list")
    def test_get_subscription_status_no_subscription(
        self, mock_customer_list, mock_subscription_list, stripe_integration
    ):
        """Test getting subscription status when customer has no subscription."""
        # Mock customer exists but no subscriptions
        mock_customer = Mock()
        mock_customer.id = "cus_test_123"
        mock_customer_list.return_value = Mock(data=[mock_customer])
        mock_subscription_list.return_value = Mock(data=[])

        status = stripe_integration.get_subscription_status(user_email="nosub@example.com")

        assert status is None

    def test_get_subscription_status_empty_email(self, stripe_integration):
        """Test getting subscription status with empty email."""
        status = stripe_integration.get_subscription_status(user_email="")
        assert status is None

    @patch("stripe.Subscription.list")
    @patch("stripe.Customer.list")
    def test_get_subscription_status_stripe_error(
        self, mock_customer_list, mock_subscription_list, stripe_integration
    ):
        """Test handling of Stripe API errors in subscription status."""
        mock_customer_list.side_effect = stripe.error.APIConnectionError("Network error")

        with pytest.raises(stripe.error.APIConnectionError):
            stripe_integration.get_subscription_status(user_email="error@example.com")

    @patch("stripe.Webhook.construct_event")
    def test_verify_webhook_signature(self, mock_construct_event, stripe_integration, mock_config):
        """Test webhook signature verification."""
        # Mock webhook event
        mock_event = Mock()
        mock_event.type = "customer.subscription.created"
        mock_construct_event.return_value = mock_event

        payload = b'{"type": "customer.subscription.created"}'
        sig_header = "t=1234567890,v1=fake_signature"

        event = stripe_integration.verify_webhook_signature(payload=payload, sig_header=sig_header)

        # Verify Stripe API was called
        mock_construct_event.assert_called_once_with(
            payload, sig_header, mock_config.stripe_webhook_secret
        )

        # Verify return value
        assert event == mock_event
        assert event.type == "customer.subscription.created"

    @patch("stripe.Webhook.construct_event")
    def test_verify_webhook_signature_invalid(self, mock_construct_event, stripe_integration):
        """Test webhook signature verification with invalid signature."""
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", sig_header="invalid"
        )

        payload = b'{"type": "test"}'
        sig_header = "invalid_signature"

        with pytest.raises(stripe.error.SignatureVerificationError):
            stripe_integration.verify_webhook_signature(payload=payload, sig_header=sig_header)

    def test_verify_webhook_signature_no_secret(self, mock_config):
        """Test webhook verification when secret is not configured."""
        config = Config(
            stripe_api_key="sk_test_key",
            stripe_price_monthly="price_123",
            stripe_price_annual="price_456",
            stripe_webhook_secret="",
            stripe_payment_link="",
            app_env="test",
            app_url="http://localhost:8501",
            debug=True,
        )
        integration = StripeIntegration(config=config)

        payload = b'{"type": "test"}'
        sig_header = "signature"

        event = integration.verify_webhook_signature(payload=payload, sig_header=sig_header)

        assert event is None


class TestStripeIntegrationEdgeCases:
    """Test edge cases and error handling."""

    @patch("stripe.checkout.Session.create")
    def test_network_timeout(self, mock_create, stripe_integration):
        """Test handling of network timeout errors."""
        mock_create.side_effect = stripe.error.APIConnectionError("Connection timeout")

        with pytest.raises(stripe.error.APIConnectionError):
            stripe_integration.create_checkout_session(
                user_email="test@example.com", plan="monthly"
            )

    @patch("stripe.checkout.Session.create")
    def test_rate_limit_error(self, mock_create, stripe_integration):
        """Test handling of rate limit errors."""
        mock_create.side_effect = stripe.error.RateLimitError("Too many requests")

        with pytest.raises(stripe.error.RateLimitError):
            stripe_integration.create_checkout_session(
                user_email="test@example.com", plan="monthly"
            )

    @patch("stripe.checkout.Session.create")
    def test_authentication_error(self, mock_create, stripe_integration):
        """Test handling of authentication errors."""
        mock_create.side_effect = stripe.error.AuthenticationError("Invalid API key")

        with pytest.raises(stripe.error.AuthenticationError):
            stripe_integration.create_checkout_session(
                user_email="test@example.com", plan="monthly"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
