# Feature Spec: Stripe Integration

## Overview

Implement full Stripe payment processing for monthly ($29) and annual ($232) subscriptions with automated billing and webhook-driven state management.

---

## User Stories

### As a free trial user
- **I want to** subscribe to a paid plan after my trial expires
- **So that** I can continue accessing catalyst data
- **Acceptance**: I can click "Subscribe", complete payment on Stripe Checkout, and immediately access the full dashboard

### As a paying subscriber
- **I want to** manage my subscription (upgrade, cancel)
- **So that** I have control over my billing
- **Acceptance**: I can access Stripe Customer Portal from app settings

### As a developer
- **I want** webhook-driven subscription updates
- **So that** subscription status is always in sync with Stripe
- **Acceptance**: When a subscription changes in Stripe, the database updates within 30 seconds

---

## Requirements

### Functional Requirements

1. **Stripe Products Setup**
   - Create two products in Stripe Dashboard:
     - Product 1: "Biotech Radar - Monthly" ($29/month, recurring)
     - Product 2: "Biotech Radar - Annual" ($232/year, recurring)
   - Store `price_id` for each in environment config

2. **Checkout Flow**
   - User clicks "Subscribe" button in app
   - App creates Stripe Checkout session via API
   - User redirects to Stripe-hosted checkout page
   - User enters payment info (Stripe handles PCI compliance)
   - On success: redirect to `{app_url}/success?session_id={SESSION_ID}`
   - On cancel: redirect to `{app_url}/canceled`

3. **Webhook Handling**
   - Listen for Stripe webhook events:
     - `checkout.session.completed` - Initial payment
     - `customer.subscription.created` - Subscription activated
     - `customer.subscription.updated` - Plan changed
     - `customer.subscription.deleted` - Subscription canceled
     - `invoice.payment_succeeded` - Recurring payment success
     - `invoice.payment_failed` - Payment failure
   - Verify webhook signature (HMAC SHA256)
   - Update PostgreSQL `subscriptions` table based on event

4. **Customer Portal**
   - User clicks "Manage Subscription" in settings
   - App creates Customer Portal session via Stripe API
   - User redirects to Stripe-hosted portal
   - User can:
     - Update payment method
     - Cancel subscription
     - View invoice history
     - Download receipts

5. **Subscription Status Check**
   - On every page load, check user's subscription status from DB
   - Cache result in session for 5 minutes
   - If `status = active` → show full dashboard
   - If `status = trialing` → show trial countdown
   - If `status = canceled` or `past_due` → show paywall

---

### Non-Functional Requirements

- **Security**: All webhook payloads must verify signature
- **Performance**: Checkout session creation <500ms
- **Reliability**: Webhook processing with retry (3 attempts)
- **Idempotency**: Handle duplicate webhooks gracefully

---

## Technical Design

### Architecture

```
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│  Streamlit   │  create   │    Stripe    │  webhook  │  n8n/Webhook │
│     App      │  session  │   Checkout   │  events   │   Handler    │
└──────┬───────┘           └──────┬───────┘           └──────┬───────┘
       │                          │                          │
       │ 1. POST /create-checkout │                          │
       ├──────────────────────────►                          │
       │                          │                          │
       │ 2. Return checkout_url   │                          │
       ◄──────────────────────────┤                          │
       │                          │                          │
       │ 3. Redirect user         │                          │
       ├──────────────────────────►                          │
       │                          │                          │
       │                          │ 4. Payment completed     │
       │                          ├──────────────────────────►
       │                          │                          │
       │                          │                          │ 5. Verify signature
       │                          │                          │ 6. Update DB
       │                          │                          │
       │ 7. Redirect to /success  │                          │
       ◄──────────────────────────┤                          │
       │                          │                          │
       │ 8. Check DB → Show dashboard                        │
       │                          │                          │
```

---

### Database Schema

See: `architecture/02-target-architecture.md` for full schema

**Key Tables**:
- `users.stripe_customer_id` - Links user to Stripe customer
- `subscriptions.stripe_subscription_id` - Links to Stripe subscription
- `subscriptions.status` - `active`, `trialing`, `canceled`, `past_due`

---

### API Endpoints

#### 1. Create Checkout Session

**Endpoint**: `POST /api/create-checkout-session`

**Request**:
```json
{
  "user_email": "user@example.com",
  "price_id": "price_1234567890abcdef",
  "success_url": "https://biotech-radar.com/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://biotech-radar.com/canceled"
}
```

**Response**:
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

**Implementation** (Streamlit):
```python
import stripe
import streamlit as st
from utils.config import Config

def create_checkout_session(user_email: str, price_id: str):
    config = Config.from_env()
    stripe.api_key = config.stripe_api_key

    session = stripe.checkout.Session.create(
        customer_email=user_email,
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=config.app_url + '/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=config.app_url + '/canceled',
    )

    return session.url
```

---

#### 2. Webhook Handler

**Endpoint**: `POST /api/stripe-webhooks`

**Headers**:
- `Stripe-Signature`: HMAC SHA256 signature

**Payload** (example for `customer.subscription.created`):
```json
{
  "id": "evt_1234567890abcdef",
  "type": "customer.subscription.created",
  "data": {
    "object": {
      "id": "sub_1234567890abcdef",
      "customer": "cus_1234567890abcdef",
      "status": "active",
      "current_period_end": 1704067200,
      "items": {
        "data": [{
          "price": {
            "id": "price_1234567890abcdef"
          }
        }]
      }
    }
  }
}
```

**Implementation** (n8n workflow):
1. **Webhook Trigger** - Receive POST from Stripe
2. **Function Node** - Verify signature:
   ```javascript
   const crypto = require('crypto');
   const signature = $('Webhook').item.headers['stripe-signature'];
   const secret = $env('STRIPE_WEBHOOK_SECRET');
   const payload = JSON.stringify($('Webhook').item.body);

   const expectedSignature = crypto
     .createHmac('sha256', secret)
     .update(payload)
     .digest('hex');

   if (signature !== expectedSignature) {
     throw new Error('Invalid signature');
   }

   return { verified: true };
   ```
3. **Switch Node** - Route by event type
4. **PostgreSQL Node** - Update subscription table
5. **SendGrid Node** - Send confirmation email (optional)

---

#### 3. Customer Portal Session

**Endpoint**: `POST /api/create-portal-session`

**Request**:
```json
{
  "stripe_customer_id": "cus_1234567890abcdef",
  "return_url": "https://biotech-radar.com/settings"
}
```

**Response**:
```json
{
  "portal_url": "https://billing.stripe.com/p/session/..."
}
```

**Implementation**:
```python
def create_portal_session(customer_id: str):
    config = Config.from_env()
    stripe.api_key = config.stripe_api_key

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=config.app_url + '/settings',
    )

    return session.url
```

---

### Streamlit Integration

**File**: `src/utils/stripe_integration.py`

```python
"""Stripe payment integration."""

import stripe
import streamlit as st
from typing import Optional
from .config import Config
from .db import get_user_subscription

class StripeIntegration:
    def __init__(self):
        config = Config.from_env()
        stripe.api_key = config.stripe_api_key
        self.config = config

    def create_checkout_session(self, user_email: str, plan: str = "monthly") -> str:
        """Create Stripe Checkout session.

        Args:
            user_email: User's email address
            plan: "monthly" or "annual"

        Returns:
            Checkout URL
        """
        price_id = (
            self.config.stripe_price_monthly
            if plan == "monthly"
            else self.config.stripe_price_annual
        )

        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{self.config.app_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{self.config.app_url}/canceled",
            metadata={'user_email': user_email},
        )

        return session.url

    def create_portal_session(self, customer_id: str) -> str:
        """Create Customer Portal session."""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{self.config.app_url}/settings",
        )
        return session.url

    def get_subscription_status(self, user_email: str) -> Optional[dict]:
        """Get user's subscription status from database.

        Returns:
            Dict with status, plan_id, expires_at
        """
        return get_user_subscription(user_email)
```

**Usage in app**:
```python
from utils.stripe_integration import StripeIntegration

# In subscription page
if st.button("Subscribe - Monthly ($29/mo)"):
    stripe_integration = StripeIntegration()
    checkout_url = stripe_integration.create_checkout_session(
        user_email=st.session_state.user_email,
        plan="monthly"
    )
    st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)

if st.button("Subscribe - Annual ($232/yr)"):
    stripe_integration = StripeIntegration()
    checkout_url = stripe_integration.create_checkout_session(
        user_email=st.session_state.user_email,
        plan="annual"
    )
    st.markdown(f'<meta http-equiv="refresh" content="0; url={checkout_url}">', unsafe_allow_html=True)
```

---

## Environment Variables

Add to `.env`:

```bash
# Stripe Keys
STRIPE_API_KEY=sk_live_...           # Secret key (from Stripe Dashboard)
STRIPE_WEBHOOK_SECRET=whsec_...      # Webhook signing secret

# Stripe Price IDs
STRIPE_PRICE_MONTHLY=price_...       # Monthly plan price ID
STRIPE_PRICE_ANNUAL=price_...        # Annual plan price ID

# App URLs
APP_URL=https://biotech-radar.streamlit.app
STRIPE_SUCCESS_URL=${APP_URL}/success
STRIPE_CANCEL_URL=${APP_URL}/canceled
```

---

## Testing Plan

### Test Mode (Stripe Test Keys)

1. **Create test products** in Stripe Dashboard (test mode)
2. **Use test card**: `4242 4242 4242 4242`, any future expiry, any CVC
3. **Test scenarios**:
   - [ ] Successful monthly subscription
   - [ ] Successful annual subscription
   - [ ] Declined card (use `4000 0000 0000 0002`)
   - [ ] Subscription cancellation
   - [ ] Failed payment (use `4000 0000 0000 0341`)

### Webhook Testing

1. **Use Stripe CLI** for local testing:
   ```bash
   stripe listen --forward-to localhost:5678/webhook/stripe
   stripe trigger customer.subscription.created
   stripe trigger invoice.payment_failed
   ```

2. **Verify**:
   - [ ] Webhook signature validation works
   - [ ] Database updates correctly
   - [ ] Duplicate events are idempotent

### Integration Testing

1. **End-to-end flow**:
   - [ ] Sign up → start trial → subscribe → verify access
   - [ ] Subscribe → cancel → verify paywall reappears
   - [ ] Subscribe → payment fails → verify status = past_due

---

## Success Criteria

- [ ] User can complete checkout in <60 seconds
- [ ] Webhook processing latency <5 seconds
- [ ] Zero failed webhooks over 7 days
- [ ] Customer Portal accessible from settings
- [ ] Test payment in Stripe test mode succeeds
- [ ] Production payment (real money) tested with team member

---

## Rollout Plan

### Week 1: Setup
- [ ] Create Stripe account
- [ ] Set up products and pricing
- [ ] Configure webhook endpoint
- [ ] Test in Stripe test mode

### Week 2: Implementation
- [ ] Implement checkout session creation
- [ ] Build n8n webhook handler
- [ ] Add Customer Portal link
- [ ] Add subscription status check

### Week 3: Testing
- [ ] End-to-end testing (test mode)
- [ ] Webhook reliability testing
- [ ] Edge case testing (failed payments, cancellations)
- [ ] Security review (signature validation)

### Week 4: Launch
- [ ] Switch to live Stripe keys
- [ ] Test with real payment (internal team)
- [ ] Monitor webhook logs for 48 hours
- [ ] Launch to first 10 beta users

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Webhook failures | High | Retry logic + manual reconciliation script |
| Duplicate webhooks | Medium | Idempotent processing (check event_id) |
| Signature verification bugs | High | Unit tests + Stripe CLI testing |
| User confusion in checkout | Medium | Clear pricing page + onboarding |
| Fraud/chargebacks | Low | Stripe Radar (automatic fraud detection) |

---

## Future Enhancements (Post-MVP)

- [ ] Add coupon/promo code support
- [ ] Implement usage-based billing (API calls)
- [ ] Add team/enterprise plans
- [ ] Integrate with Stripe Tax (automatic sales tax)
- [ ] Add annual → monthly downgrade flow

---

## References

- [Stripe Checkout Documentation](https://stripe.com/docs/payments/checkout)
- [Stripe Customer Portal](https://stripe.com/docs/billing/subscriptions/integrating-customer-portal)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Test Cards](https://stripe.com/docs/testing#cards)

---

**Last Updated**: 2025-12-24
**Status**: 📝 Spec Draft - Ready for Review
**Owner**: Development Team
**Implementation Target**: Week 3-4
