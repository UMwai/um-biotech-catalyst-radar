# Stripe Integration Testing Guide

This guide provides step-by-step instructions for testing the Stripe payment integration for Biotech Radar.

## Table of Contents
- [Setup](#setup)
- [Running Unit Tests](#running-unit-tests)
- [Testing with Stripe Test Mode](#testing-with-stripe-test-mode)
- [Test Scenarios](#test-scenarios)
- [Troubleshooting](#troubleshooting)

---

## Setup

### 1. Create Stripe Test Account

1. Sign up at [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Activate test mode (toggle in the top-right corner)
3. Navigate to **Developers → API keys** to get your test keys

### 2. Create Test Products

1. Go to **Products** in Stripe Dashboard
2. Click **+ Add product**

**Monthly Plan:**
- Name: `Biotech Radar - Monthly`
- Description: `Monthly subscription to Biotech Radar catalyst dashboard`
- Pricing: `$29.00 USD` per month, recurring
- Copy the **Price ID** (starts with `price_`)

**Annual Plan:**
- Name: `Biotech Radar - Annual`
- Description: `Annual subscription to Biotech Radar catalyst dashboard`
- Pricing: `$232.00 USD` per year, recurring
- Copy the **Price ID** (starts with `price_`)

### 3. Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Stripe Configuration (TEST MODE)
STRIPE_API_KEY=sk_test_51...  # From Developers → API keys
STRIPE_PRICE_MONTHLY=price_...  # Monthly product price ID
STRIPE_PRICE_ANNUAL=price_...  # Annual product price ID
STRIPE_WEBHOOK_SECRET=whsec_...  # We'll get this later

# App Configuration
APP_ENV=development
APP_URL=http://localhost:8501
DEBUG=true
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running Unit Tests

The Stripe integration includes comprehensive unit tests with mocked Stripe API calls.

### Run All Tests

```bash
pytest tests/test_stripe_integration.py -v
```

### Run Specific Test

```bash
# Test checkout session creation
pytest tests/test_stripe_integration.py::TestStripeIntegration::test_create_checkout_session_monthly -v

# Test subscription status checking
pytest tests/test_stripe_integration.py::TestStripeIntegration::test_get_subscription_status_active -v

# Test webhook verification
pytest tests/test_stripe_integration.py::TestStripeIntegration::test_verify_webhook_signature -v
```

### Expected Output

```
============================== test session starts ==============================
tests/test_stripe_integration.py::TestStripeIntegration::test_initialization PASSED
tests/test_stripe_integration.py::TestStripeIntegration::test_create_checkout_session_monthly PASSED
...
============================== 20 passed in 0.79s ==============================
```

---

## Testing with Stripe Test Mode

### 1. Launch the Application

```bash
streamlit run src/app.py
```

The app should start at `http://localhost:8501`

### 2. Navigate to Subscribe Page

**Option A:** Direct URL
- Open `http://localhost:8501/subscribe`

**Option B:** Via Streamlit Pages
- The subscribe page should appear in the sidebar navigation

### 3. Test Checkout Flow

1. **Enter Email:** Use any test email (e.g., `test@example.com`)
2. **Click Subscribe:** Choose Monthly or Annual
3. **Stripe Checkout:** You'll be redirected to Stripe's hosted checkout page

### 4. Use Stripe Test Cards

**Successful Payment:**
```
Card Number: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/34)
CVC: Any 3 digits (e.g., 123)
ZIP: Any 5 digits (e.g., 12345)
```

**Declined Card:**
```
Card Number: 4000 0000 0000 0002
Expiry: Any future date
CVC: Any 3 digits
```

**Requires Authentication (3D Secure):**
```
Card Number: 4000 0025 0000 3155
Expiry: Any future date
CVC: Any 3 digits
```

More test cards: [https://stripe.com/docs/testing#cards](https://stripe.com/docs/testing#cards)

### 5. Verify Success Flow

After successful payment:
1. You should be redirected to `/success?session_id=cs_test_...`
2. The success page should display:
   - Success message
   - Session ID (for support)
   - "Go to Dashboard" button
   - Subscription details

### 6. Test Cancel Flow

1. On the Stripe Checkout page, click the back arrow or close button
2. You should be redirected to `/canceled`
3. The canceled page should display:
   - Cancellation message
   - Options to retry or view free dashboard
   - Pricing reminder

---

## Test Scenarios

### Scenario 1: Monthly Subscription

**Steps:**
1. Navigate to `/subscribe`
2. Enter email: `monthly@example.com`
3. Click "Subscribe Monthly - $29/mo"
4. Complete payment with test card `4242 4242 4242 4242`
5. Verify redirect to `/success`

**Expected Result:**
- Checkout session created
- Payment processed in Stripe Dashboard
- User redirected to success page
- Subscription visible in Stripe Dashboard → Customers

### Scenario 2: Annual Subscription

**Steps:**
1. Navigate to `/subscribe`
2. Enter email: `annual@example.com`
3. Click "Subscribe Annual - $232/yr"
4. Complete payment with test card
5. Verify redirect to `/success`

**Expected Result:**
- Annual subscription created
- 33% discount reflected in total ($232 vs $348)

### Scenario 3: Declined Card

**Steps:**
1. Navigate to `/subscribe`
2. Enter email: `declined@example.com`
3. Click subscribe
4. Use declined test card `4000 0000 0000 0002`

**Expected Result:**
- Stripe shows "Your card was declined" error
- User remains on Stripe Checkout page
- No subscription created

### Scenario 4: Checkout Cancellation

**Steps:**
1. Start checkout process
2. Click back button or close Stripe Checkout
3. Verify redirect to `/canceled`

**Expected Result:**
- User redirected to canceled page
- No charges made
- Options to retry or view dashboard

### Scenario 5: Subscription Status Check

**Test Code:**
```python
from src.utils.stripe_integration import StripeIntegration
from src.utils.config import Config

config = Config.from_env()
stripe_integration = StripeIntegration(config)

# Check subscription for a customer who completed payment
status = stripe_integration.get_subscription_status("monthly@example.com")

print(f"Status: {status['status']}")
print(f"Customer ID: {status['customer_id']}")
print(f"Subscription ID: {status['subscription_id']}")
```

**Expected Output:**
```python
{
    'status': 'active',
    'customer_id': 'cus_...',
    'subscription_id': 'sub_...',
    'plan_id': 'price_...',
    'current_period_end': 1735689600
}
```

### Scenario 6: Customer Portal

**Steps:**
1. Get customer ID from Stripe Dashboard or API
2. Test portal session creation:

```python
from src.utils.stripe_integration import StripeIntegration

stripe_integration = StripeIntegration()
portal_url = stripe_integration.create_portal_session("cus_test_123")
print(portal_url)
```

3. Open the portal URL in browser
4. Verify customer can:
   - View subscription details
   - Update payment method
   - Cancel subscription
   - View invoice history

---

## Webhook Testing (Advanced)

### 1. Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux
wget https://github.com/stripe/stripe-cli/releases/download/v1.19.0/stripe_1.19.0_linux_x86_64.tar.gz
tar -xvf stripe_1.19.0_linux_x86_64.tar.gz
```

### 2. Login to Stripe CLI

```bash
stripe login
```

### 3. Forward Webhooks to Local Server

You'll need to set up a webhook endpoint (typically using n8n or a custom Flask/FastAPI server):

```bash
# Forward to local webhook server (e.g., n8n running on port 5678)
stripe listen --forward-to localhost:5678/webhook/stripe
```

This will output a webhook signing secret:
```
> Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxx
```

Add this to your `.env`:
```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### 4. Trigger Test Webhooks

```bash
# Test subscription created
stripe trigger customer.subscription.created

# Test payment succeeded
stripe trigger invoice.payment_succeeded

# Test payment failed
stripe trigger invoice.payment_failed

# Test subscription canceled
stripe trigger customer.subscription.deleted
```

### 5. Verify Webhook Signature

```python
from src.utils.stripe_integration import StripeIntegration

stripe_integration = StripeIntegration()

# Simulate webhook payload
payload = b'{"type": "customer.subscription.created", "data": {...}}'
sig_header = "t=1234567890,v1=signature_here"

event = stripe_integration.verify_webhook_signature(payload, sig_header)
print(event.type)  # Should print: customer.subscription.created
```

---

## Troubleshooting

### Issue: "Stripe is not configured" Error

**Cause:** Missing or invalid environment variables

**Solution:**
1. Verify `.env` file exists and contains all required variables
2. Check that variable names match exactly (case-sensitive)
3. Restart the Streamlit app to reload environment variables

```bash
# Verify configuration
python -c "from src.utils.config import Config; c = Config.from_env(); print(c.is_configured)"
```

### Issue: "Invalid API key" Error

**Cause:** Using production keys in test mode or vice versa

**Solution:**
1. Ensure you're using test mode keys (start with `sk_test_`)
2. Verify the key is copied correctly (no extra spaces)
3. Check that the key hasn't been deleted in Stripe Dashboard

### Issue: Checkout Session Creation Fails

**Cause:** Invalid price ID or network issues

**Solution:**
1. Verify price IDs in Stripe Dashboard → Products
2. Ensure price IDs start with `price_`
3. Check network connectivity
4. View detailed error in logs:

```bash
# Run with debug logging
DEBUG=true streamlit run src/app.py
```

### Issue: Redirect Not Working

**Cause:** Browser security or Streamlit limitations

**Solution:**
1. Use the fallback link displayed on screen
2. Manually copy the checkout URL from logs
3. Try a different browser (Chrome/Firefox recommended)

### Issue: Tests Failing

**Cause:** Missing dependencies or import errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run tests with verbose output
pytest tests/test_stripe_integration.py -v -s
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Switch to Stripe **live mode** keys
- [ ] Update `APP_ENV=production` in `.env`
- [ ] Update `APP_URL` to production domain
- [ ] Create live products in Stripe Dashboard
- [ ] Set up webhook endpoint with HTTPS
- [ ] Configure webhook events in Stripe Dashboard
- [ ] Test with real payment (small amount)
- [ ] Enable Stripe Radar for fraud detection
- [ ] Set up monitoring and alerts
- [ ] Review Stripe tax settings (if applicable)
- [ ] Test subscription cancellation flow
- [ ] Verify email receipts are being sent

---

## Resources

- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Test Cards](https://stripe.com/docs/testing#cards)
- [Stripe Checkout Documentation](https://stripe.com/docs/payments/checkout)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Customer Portal](https://stripe.com/docs/billing/subscriptions/integrating-customer-portal)

---

## Support

For issues or questions:
- Check the [Stripe Dashboard logs](https://dashboard.stripe.com/logs)
- Review the application logs (Streamlit console output)
- Test in Stripe test mode first
- Contact: development team or support@biotechradar.com

---

**Last Updated:** 2025-12-24
**Version:** 1.0
