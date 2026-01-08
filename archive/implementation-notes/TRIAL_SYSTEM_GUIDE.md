# 7-Day Free Trial System - Implementation Guide

## Overview

The 7-day free trial system has been successfully implemented for the Biotech Radar SaaS. This guide explains how to test and use the trial management features.

---

## Implementation Summary

### Files Created

1. **src/utils/trial_manager.py** - Core trial management logic
   - `TrialManager` class with all trial lifecycle methods
   - Timezone-aware datetime handling (UTC)
   - Integration with user database and subscriptions

2. **src/ui/trial_banner.py** - Trial countdown UI component
   - `render_trial_banner()` - Main banner shown at top of app
   - `render_trial_info_sidebar()` - Compact sidebar version
   - Progressive urgency (info → warning → error)
   - Subscribe button on days 6-7

3. **src/ui/paywall.py** - Paywall for expired trials
   - `render_paywall()` - Full-screen paywall with pricing cards
   - `render_upgrade_prompt()` - Subtle upgrade prompts during trial
   - Monthly ($29/mo) and Annual ($232/yr) pricing cards
   - FAQ section for common questions

4. **tests/test_trial_manager.py** - Comprehensive test suite
   - 9 test cases covering all trial scenarios
   - Mocked database for isolated testing
   - Tests for active trials, expired trials, conversions, and edge cases

### Files Modified

1. **src/app.py** - Integrated trial banner and testing controls
   - Added trial banner at top of app
   - Added sidebar trial status display
   - Added debug controls for trial testing (when DEBUG=true)

2. **src/ui/dashboard.py** - Integrated paywall component
   - Paywall shows for expired trials without subscriptions
   - 10-row preview still visible after trial expires
   - Full access during trial or with active subscription

---

## Testing the Trial Flow

### Prerequisites

```bash
# Ensure DEBUG mode is enabled in .env
echo "DEBUG=true" >> .env

# Run the Streamlit app
streamlit run src/app.py
```

### Test Scenario 1: Active Trial (Days 1-5)

1. **Setup**: Open the app in DEBUG mode
2. **In Sidebar**:
   - Enter email: `test-day3@example.com`
   - Click "Set Test User"
3. **Expected Behavior**:
   - Top banner shows: "⏱️ **Free trial:** X days remaining" (blue info box)
   - Sidebar shows: "**Trial:** X days left"
   - Full access to all catalysts (no paywall)
   - Dashboard displays normally

### Test Scenario 2: Trial Expiring Soon (Day 6)

1. **Setup**: Use the trial manager to create a user with 1 day remaining
2. **Expected Behavior**:
   - Top banner shows: "⏱️ **Free trial expires tomorrow** (24 hours left)" (orange warning)
   - "Subscribe Now →" button appears next to banner
   - Sidebar shows: "**Trial:** 24h left" (warning color)
   - Still has full access to dashboard

### Test Scenario 3: Trial Expiring Today (Day 7)

1. **Setup**: Create user with <24 hours remaining
2. **Expected Behavior**:
   - Top banner shows: "⏱️ **Trial expires in X hours**" (orange warning)
   - "Subscribe Now →" button prominent
   - Sidebar shows urgent warning
   - Still has access until exact expiration time

### Test Scenario 4: Expired Trial (Day 8+)

1. **Setup**: Create user with trial_end_date in the past
2. **Expected Behavior**:
   - Top banner shows: "❌ **Your trial has expired.**" (red error)
   - "View Subscription Options →" button
   - Sidebar shows: "**Trial Expired**" (red)
   - Paywall blocks dashboard content
   - Only 10-row preview visible

### Test Scenario 5: Converted Trial (Paid Subscription)

1. **Setup**: Create user with expired trial + active subscription
2. **Expected Behavior**:
   - No trial banner shown
   - Sidebar shows: "✓ **Active Subscription**" (green)
   - Full access to all features
   - No paywall

---

## Manual Testing with TrialManager

You can test trial functionality programmatically:

```python
from src.utils.trial_manager import TrialManager
from datetime import datetime, timedelta, timezone

# Create a trial manager for a user
trial_mgr = TrialManager("test@example.com")

# Check trial status
print(f"Trial active: {trial_mgr.is_trial_active()}")
print(f"Days remaining: {trial_mgr.get_days_remaining()}")
print(f"Hours remaining: {trial_mgr.get_hours_remaining()}")
print(f"Access level: {trial_mgr.get_access_level()}")  # 'full', 'preview', or 'none'
print(f"Should show paywall: {trial_mgr.should_show_paywall()}")

# Get complete status
status = trial_mgr.get_trial_status()
print(status)
# {
#   'is_active': True,
#   'is_expired': False,
#   'has_subscription': False,
#   'days_remaining': 5,
#   'hours_remaining': 120,
#   'access_level': 'full',
#   'should_show_paywall': False
# }
```

---

## Running Automated Tests

```bash
# Run all trial manager tests
pytest tests/test_trial_manager.py -v

# Run specific test
pytest tests/test_trial_manager.py::test_trial_active_day_3 -v

# Run with coverage
pytest tests/test_trial_manager.py --cov=src/utils/trial_manager --cov-report=html
```

### Test Coverage

All 9 tests pass successfully:

✅ `test_trial_active_day_3` - Trial is active on day 3
✅ `test_trial_expired_day_8` - Trial expired after 7 days
✅ `test_converted_trial_no_paywall` - Paid subscribers don't see paywall
✅ `test_trial_last_day` - Hour countdown on last day
✅ `test_start_trial` - Starting a new trial
✅ `test_start_trial_already_started` - Prevents duplicate trials
✅ `test_no_user` - Handles non-existent users gracefully
✅ `test_trial_status_summary` - Complete status information
✅ `test_mark_converted` - Mark trial as converted to paid

---

## Integration with Database

The trial system uses the PostgreSQL database layer (`src/utils/db.py`):

### Required Database Tables

```sql
-- Users table (trial fields)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    trial_converted BOOLEAN DEFAULT FALSE,
    ...
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    stripe_subscription_id VARCHAR(255),
    status VARCHAR(50),  -- 'active', 'canceled', 'past_due'
    plan_id VARCHAR(100), -- 'monthly', 'annual'
    current_period_end TIMESTAMP,
    ...
);
```

### Database Functions Used

- `get_user_by_email(email)` - Fetch user by email
- `get_user_subscription(user_id)` - Get user's active subscription
- `update_user(user_id, updates)` - Update user fields (trial dates, etc.)

---

## UI Component Usage

### In Your Streamlit App

```python
from ui.trial_banner import render_trial_banner, render_trial_info_sidebar
from ui.paywall import render_paywall, render_upgrade_prompt

# At the top of your app (after title)
if "user_email" in st.session_state:
    render_trial_banner(st.session_state["user_email"])

# In sidebar
with st.sidebar:
    if "user_email" in st.session_state:
        render_trial_info_sidebar(st.session_state["user_email"])

# In dashboard before showing data
if user_email:
    paywall_shown = render_paywall(user_email)
    if paywall_shown:
        return  # Stop rendering, user needs to subscribe

# Optional: Subtle upgrade prompts during trial
if user_email:
    render_upgrade_prompt(user_email, context="charts")
```

---

## Trial Lifecycle

### Day 1: Welcome

- User signs up with email
- `trial_start_date` and `trial_end_date` set automatically
- Blue info banner: "Free trial: 7 days remaining"
- Full access to all features

### Days 2-5: Evaluation

- Blue info banner: "Free trial: X days remaining"
- User explores features
- No upgrade prompts (non-aggressive approach)

### Day 6: Reminder

- Orange warning banner: "Trial expires tomorrow (24 hours left)"
- "Subscribe Now →" button appears
- Optional: Send reminder email (via n8n workflow)

### Day 7: Last Chance

- Orange warning banner: "Trial expires in X hours"
- Prominent subscribe button
- User can still access features until exact expiration time

### Day 8+: Paywall

- Red error banner: "Your trial has expired"
- Paywall blocks dashboard content
- 10-row preview still visible (marketing)
- Pricing cards displayed (Monthly $29, Annual $232)

### After Subscription

- No trial banner shown
- Green success: "✓ Active Subscription"
- `trial_converted = TRUE` in database
- Full access permanently (until cancellation)

---

## Configuration

### Environment Variables

The trial system respects these environment variables:

```bash
# App configuration
DEBUG=true                    # Enable debug mode and trial testing controls
APP_ENV=development           # development | production

# Trial duration (optional override, defaults to 7 days)
TRIAL_DURATION_DAYS=7

# Database (PostgreSQL)
DATABASE_URL=postgresql://...
# OR individual components:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=biotech_radar
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## Troubleshooting

### Issue: "User not found"

**Cause**: User hasn't been created in database yet
**Solution**: Create user first using `create_user(email)` from `src.utils.db`

### Issue: Trial dates are None

**Cause**: `start_trial()` hasn't been called
**Solution**: Call `trial_mgr.start_trial()` after user creation

### Issue: Paywall shows for active subscribers

**Cause**: Subscription status not updated in database
**Solution**: Verify subscription status is 'active' in subscriptions table

### Issue: Timezone mismatch errors

**Cause**: Mixing timezone-aware and naive datetime objects
**Solution**: All trial dates use UTC timezone (`datetime.now(timezone.utc)`)

---

## Next Steps

1. **Database Setup**: Ensure PostgreSQL is configured with the required schema
2. **User Authentication**: Implement proper email/password authentication (replace session state)
3. **Stripe Integration**: Connect paywall buttons to Stripe Checkout (see `specs/features/01-stripe-integration.md`)
4. **Email Automation**: Set up n8n workflows for trial conversion emails (see `specs/workflows/04-trial-conversion.md`)
5. **Analytics**: Track trial conversion rates and user engagement

---

## Support

For questions or issues:
- Review the spec: `specs/features/02-free-trial.md`
- Check test cases: `tests/test_trial_manager.py`
- Examine implementation: `src/utils/trial_manager.py`

---

**Last Updated**: 2024-12-24
**Status**: ✅ Implemented and Tested
**All Tests Passing**: 9/9
