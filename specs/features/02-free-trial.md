# Feature Spec: 7-Day Free Trial System

## Overview

Implement a 7-day free trial with countdown UI, automatic expiration, and seamless transition to paywall or paid subscription.

---

## User Stories

### As a new user
- **I want to** try the platform for 7 days without payment
- **So that** I can evaluate if it meets my needs
- **Acceptance**: I can sign up with just email, access full features, see countdown timer

### As a trial user on day 6
- **I want to** be reminded my trial is expiring
- **So that** I can decide to subscribe before losing access
- **Acceptance**: I receive an email 24 hours before expiration

### As a trial user on day 7+
- **I want to** see a clear paywall with subscription options
- **So that** I can easily subscribe to continue
- **Acceptance**: Dashboard shows paywall, not data (except preview)

---

## Requirements

### Functional Requirements

1. **Trial Signup**
   - User enters email only (no credit card required)
   - System creates user record with:
     - `trial_start_date = NOW()`
     - `trial_end_date = NOW() + 7 days`
   - Send welcome email immediately

2. **Trial Countdown UI**
   - Show banner on all pages: "Trial expires in X days"
   - Day 6+: Change to "Trial expires in X hours"
   - Day 7+: Replace with "Trial expired" + subscribe CTA

3. **Access Control**
   - Days 1-7: Full access to all features
   - Day 7+: Show paywall, block data access
   - Exception: Allow 10-row preview of data (marketing)

4. **Trial Expiration**
   - Automatic at `trial_end_date`
   - No manual intervention needed
   - Check on every page load

5. **Trial → Paid Transition**
   - When user subscribes during trial:
     - Mark trial as "converted"
     - Grant full access immediately
     - Don't charge until trial would have ended (optional)

---

### Non-Functional Requirements

- **Performance**: Trial status check <50ms
- **Accuracy**: Countdown timer accurate to the minute
- **UX**: Clear, non-aggressive messaging
- **Security**: Trial cannot be extended by clearing cookies

---

## Technical Design

### Database Schema

**users table** (already defined, excerpt):
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    trial_converted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Helper function** (optional):
```sql
CREATE FUNCTION get_trial_status(user_id UUID)
RETURNS TABLE (
    status VARCHAR(20), -- active, expired, converted
    days_remaining INTEGER,
    hours_remaining INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE
            WHEN u.trial_converted = TRUE THEN 'converted'
            WHEN NOW() < u.trial_end_date THEN 'active'
            ELSE 'expired'
        END AS status,
        EXTRACT(DAY FROM (u.trial_end_date - NOW()))::INTEGER AS days_remaining,
        EXTRACT(HOUR FROM (u.trial_end_date - NOW()))::INTEGER AS hours_remaining
    FROM users u
    WHERE u.id = user_id;
END;
$$ LANGUAGE plpgsql;
```

---

### Streamlit Implementation

**File**: `src/utils/trial_manager.py`

```python
"""Trial management and access control."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import streamlit as st
from .db import get_user, update_user

class TrialManager:
    """Manage free trial lifecycle."""

    TRIAL_DURATION_DAYS = 7

    def __init__(self, user_email: str):
        self.user_email = user_email
        self.user = get_user(user_email)

    def is_trial_active(self) -> bool:
        """Check if user's trial is still active."""
        if not self.user or not self.user.get('trial_end_date'):
            return False

        trial_end = self.user['trial_end_date']
        return datetime.now() < trial_end

    def is_trial_expired(self) -> bool:
        """Check if trial has expired."""
        if not self.user or not self.user.get('trial_end_date'):
            return False

        trial_end = self.user['trial_end_date']
        return datetime.now() >= trial_end

    def has_active_subscription(self) -> bool:
        """Check if user has paid subscription."""
        if not self.user:
            return False

        # Check subscriptions table
        from .db import get_user_subscription
        subscription = get_user_subscription(self.user['id'])
        return subscription and subscription['status'] == 'active'

    def get_days_remaining(self) -> int:
        """Get days remaining in trial."""
        if not self.user or not self.user.get('trial_end_date'):
            return 0

        trial_end = self.user['trial_end_date']
        diff = trial_end - datetime.now()
        return max(0, diff.days)

    def get_hours_remaining(self) -> int:
        """Get hours remaining in trial."""
        if not self.user or not self.user.get('trial_end_date'):
            return 0

        trial_end = self.user['trial_end_date']
        diff = trial_end - datetime.now()
        return max(0, int(diff.total_seconds() / 3600))

    def start_trial(self) -> None:
        """Start trial for new user."""
        if not self.user:
            raise ValueError("User not found")

        trial_start = datetime.now()
        trial_end = trial_start + timedelta(days=self.TRIAL_DURATION_DAYS)

        update_user(
            self.user['id'],
            {
                'trial_start_date': trial_start,
                'trial_end_date': trial_end
            }
        )

        # Trigger welcome email workflow
        from .n8n import trigger_workflow
        trigger_workflow('new_trial_user', {'user_id': self.user['id']})

    def mark_converted(self) -> None:
        """Mark trial as converted to paid."""
        if not self.user:
            raise ValueError("User not found")

        update_user(self.user['id'], {'trial_converted': True})

    def should_show_paywall(self) -> bool:
        """Determine if paywall should be shown."""
        # Show paywall if:
        # 1. Trial expired AND
        # 2. No active subscription
        return self.is_trial_expired() and not self.has_active_subscription()

    def get_access_level(self) -> str:
        """Get user's access level.

        Returns:
            'full' - Full access (active trial or paid)
            'preview' - Limited preview (expired trial, no payment)
            'none' - No access (not logged in)
        """
        if not self.user:
            return 'none'

        if self.has_active_subscription() or self.is_trial_active():
            return 'full'

        return 'preview'
```

---

### UI Components

**File**: `src/ui/trial_banner.py`

```python
"""Trial countdown banner component."""

import streamlit as st
from utils.trial_manager import TrialManager

def render_trial_banner(user_email: str) -> None:
    """Render trial countdown banner.

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

        if days_remaining > 1:
            message = f"⏱️ **Free trial:** {days_remaining} days remaining"
            color = "info"
        elif days_remaining == 1:
            message = f"⏱️ **Free trial expires tomorrow** ({hours_remaining} hours left)"
            color = "warning"
        else:
            message = f"⏱️ **Trial expires in {hours_remaining} hours**"
            color = "warning"

        st.warning(message) if color == "warning" else st.info(message)

        # Show subscribe button on day 6+
        if days_remaining <= 1:
            if st.button("Subscribe Now →", type="primary"):
                st.switch_page("pages/subscribe.py")

    # Trial expired
    elif trial_mgr.is_trial_expired():
        st.error("❌ **Your trial has expired.** Subscribe to continue accessing catalyst data.")
        if st.button("View Subscription Options →", type="primary"):
            st.switch_page("pages/subscribe.py")
```

**Usage in app.py**:
```python
from ui.trial_banner import render_trial_banner

def main():
    st.set_page_config(...)

    # Check if user is logged in
    if 'user_email' in st.session_state:
        render_trial_banner(st.session_state.user_email)

    # Rest of app...
```

---

### Paywall Component

**File**: `src/ui/paywall.py`

```python
"""Paywall component for expired trials."""

import streamlit as st
from utils.trial_manager import TrialManager

def render_paywall(user_email: str) -> bool:
    """Render paywall if needed.

    Args:
        user_email: User's email

    Returns:
        True if paywall shown (block content), False otherwise
    """
    trial_mgr = TrialManager(user_email)

    if not trial_mgr.should_show_paywall():
        return False

    # Show paywall
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <h1>🔒 Your Free Trial Has Ended</h1>
        <p style="font-size: 1.2em; color: #666;">
            Subscribe to continue accessing biotech catalyst data
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Choose Your Plan")

        # Monthly plan
        st.markdown("""
        <div style="border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 10px 0;">
            <h3>Monthly Plan</h3>
            <p style="font-size: 2em; font-weight: bold;">$29<span style="font-size: 0.5em;">/month</span></p>
            <ul style="text-align: left;">
                <li>Full catalyst dashboard</li>
                <li>Price charts</li>
                <li>Daily updates</li>
                <li>Cancel anytime</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Subscribe Monthly - $29/mo", type="primary", use_container_width=True):
            st.switch_page("pages/checkout.py?plan=monthly")

        # Annual plan
        st.markdown("""
        <div style="border: 2px solid #28a745; border-radius: 8px; padding: 20px; margin: 10px 0;">
            <h3>Annual Plan <span style="background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.7em;">SAVE 33%</span></h3>
            <p style="font-size: 2em; font-weight: bold;">$232<span style="font-size: 0.5em;">/year</span></p>
            <p style="color: #666;">Only $19.33/month</p>
            <ul style="text-align: left;">
                <li>Everything in Monthly</li>
                <li>Save $116/year</li>
                <li>Lock in pricing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Subscribe Annual - $232/yr", type="secondary", use_container_width=True):
            st.switch_page("pages/checkout.py?plan=annual")

    return True  # Paywall shown, block content
```

**Usage in dashboard**:
```python
from ui.paywall import render_paywall

def render_dashboard(df, user_email):
    # Check paywall first
    if render_paywall(user_email):
        return  # Stop here, don't show data

    # Show full dashboard
    st.dataframe(df)
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_trial_manager.py

from datetime import datetime, timedelta
from utils.trial_manager import TrialManager

def test_trial_active_day_3():
    """Test trial is active on day 3."""
    user = create_test_user(
        trial_start_date=datetime.now() - timedelta(days=3),
        trial_end_date=datetime.now() + timedelta(days=4)
    )
    mgr = TrialManager(user['email'])
    assert mgr.is_trial_active() == True
    assert mgr.get_days_remaining() == 4

def test_trial_expired_day_8():
    """Test trial is expired on day 8."""
    user = create_test_user(
        trial_start_date=datetime.now() - timedelta(days=8),
        trial_end_date=datetime.now() - timedelta(days=1)
    )
    mgr = TrialManager(user['email'])
    assert mgr.is_trial_expired() == True
    assert mgr.should_show_paywall() == True

def test_converted_trial_no_paywall():
    """Test converted trial doesn't show paywall."""
    user = create_test_user(
        trial_start_date=datetime.now() - timedelta(days=10),
        trial_end_date=datetime.now() - timedelta(days=3),
        trial_converted=True,
        subscription_status='active'
    )
    mgr = TrialManager(user['email'])
    assert mgr.should_show_paywall() == False
```

### Integration Tests

1. **Trial signup flow**:
   - [ ] Sign up → trial_start_date and trial_end_date set correctly
   - [ ] Welcome email sent
   - [ ] User can access dashboard

2. **Trial countdown**:
   - [ ] Day 3: Banner shows "4 days remaining"
   - [ ] Day 6: Banner shows "Trial expires tomorrow"
   - [ ] Day 7: Paywall appears

3. **Trial → Paid conversion**:
   - [ ] Subscribe during trial → Full access
   - [ ] trial_converted = TRUE in database
   - [ ] No paywall shown after subscription

---

## Success Criteria

- [ ] Trial signup takes <30 seconds
- [ ] Countdown timer accurate to ±1 hour
- [ ] Paywall appears exactly at trial_end_date
- [ ] No way to extend trial without payment
- [ ] 10%+ trial → paid conversion rate

---

## Rollout Plan

### Week 1: Development
- [ ] Build TrialManager class
- [ ] Implement trial_banner component
- [ ] Build paywall component
- [ ] Unit tests

### Week 2: Integration
- [ ] Add to app.py
- [ ] Test with staging database
- [ ] QA with multiple test users

### Week 3: Launch
- [ ] Deploy to production
- [ ] Monitor first 100 trial signups
- [ ] Track conversion metrics

---

**Last Updated**: 2025-12-24
**Status**: 📝 Spec Draft - Ready for Implementation
**Owner**: Development Team
**Implementation Target**: Week 3-4
