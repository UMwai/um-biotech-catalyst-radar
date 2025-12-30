# Biotech Run-Up Radar - System Architecture

## Overview

A micro-SaaS dashboard that tracks Phase 2/3 clinical trial catalysts for small-cap biotech stocks, enabling retail traders to capitalize on pre-catalyst run-ups.

## Target Architecture

```
                               Biotech Run-Up Radar
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   +-----------------+       +------------------+       +------------------+       |
|   |                 |       |                  |       |                  |       |
|   |  Streamlit App  | <---> |  Supabase        | <---> |  Edge Functions  |       |
|   |  (Frontend)     |       |  (PostgreSQL)    |       |  (Automation)    |       |
|   |                 |       |                  |       |                  |       |
|   +-----------------+       +------------------+       +------------------+       |
|                                     ^                          ^                  |
|                                     |                          |                  |
|                                     v                          v                  |
|   +-----------------+       +------------------+       +------------------+       |
|   |                 |       |                  |       |                  |       |
|   |  Stripe API     |       |  SendGrid        |       |  ClinicalTrials  |       |
|   |  (Payments)     |       |  (Email)         |       |  .gov API        |       |
|   |                 |       |                  |       |                  |       |
|   +-----------------+       +------------------+       +------------------+       |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## System Components

### 1. Frontend Layer (Streamlit)

**Purpose**: User-facing dashboard for browsing catalyst data

**Technology**: Streamlit on Streamlit Community Cloud (free tier)

**Key Features**:
- Interactive catalyst table with filters
- Phase/date range/sector filtering
- Price charts with catalyst date overlay
- Paywall for premium content (10 free rows)
- Subscription management integration

**File Structure**:
```
src/
+-- app.py                    # Main Streamlit application
+-- pages/
|   +-- subscribe.py          # Subscription/checkout page
+-- ui/
|   +-- dashboard.py          # Main dashboard view
|   +-- charts.py             # Plotly price charts
|   +-- paywall.py            # Premium content gate
|   +-- trial_banner.py       # Trial status display
+-- utils/
    +-- config.py             # Environment configuration
    +-- stripe_gate.py        # Subscription checking
    +-- trial_manager.py      # Trial period logic
    +-- db.py                 # Supabase database utilities
```

### 2. Data Layer (Supabase)

**Purpose**: Store catalysts, users, subscriptions, and analytics

**Technology**: Supabase (PostgreSQL + Auth + Edge Functions)

**Database Schema**:

```sql
-- Core catalyst data
CREATE TABLE catalysts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nct_id VARCHAR(20) UNIQUE NOT NULL,
    sponsor_name TEXT NOT NULL,
    ticker VARCHAR(10),
    phase VARCHAR(10) NOT NULL,
    indication TEXT,
    primary_completion_date DATE,
    market_cap DECIMAL(15,2),
    current_price DECIMAL(10,2),
    price_30d_change DECIMAL(5,2),
    fuzzy_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User accounts
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    subscription_status TEXT DEFAULT 'free',
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscription tracking
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    stripe_subscription_id TEXT UNIQUE,
    plan_type TEXT NOT NULL, -- 'starter', 'pro', 'annual'
    status TEXT NOT NULL,    -- 'active', 'canceled', 'past_due'
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email communication log
CREATE TABLE email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    email_type TEXT NOT NULL,  -- 'trial_welcome', 'trial_day3', etc.
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ
);

-- Analytics events
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    event_type TEXT NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Row Level Security (RLS)**:
- Free users: see only 10 catalyst rows
- Subscribers: see all catalyst rows
- Users can only access their own data

### 3. Automation Layer (Supabase Edge Functions)

**Purpose**: Daily data refresh, email automation, webhook handling

**Edge Functions**:

| Function | Trigger | Purpose |
|----------|---------|---------|
| `daily-sync` | Cron (6 AM UTC) | Fetch trials, map tickers, enrich stock data |
| `stripe-webhook` | HTTP POST | Handle Stripe subscription events |
| `send-trial-email` | Cron (hourly) | Send trial conversion email sequence |
| `cleanup-expired` | Cron (daily) | Archive old trials, cleanup data |

**Daily Sync Flow**:
```
1. Query ClinicalTrials.gov API v2
   - Phase 2/3 trials
   - Completing in next 90 days
2. Fuzzy match sponsors to tickers
   - Manual overrides first
   - Then fuzzy matching (min score 80)
3. Enrich with stock data (yfinance)
   - Market cap, price, 30-day change
   - Filter: market cap < $5B
4. Upsert to catalysts table
5. Log sync completion
```

### 4. Payment Layer (Stripe)

**Purpose**: Handle subscriptions and billing

**Products**:
| Plan | Price | Stripe Price ID |
|------|-------|-----------------|
| Early Bird | $19/month | price_starter_early |
| Starter | $29/month | price_starter |
| Pro | $39/month | price_pro |
| Annual | $149/year | price_annual |

**Webhook Events Handled**:
- `checkout.session.completed` - New subscription
- `customer.subscription.updated` - Plan change
- `customer.subscription.deleted` - Cancellation
- `invoice.payment_failed` - Failed payment

**Checkout Flow**:
```
User clicks "Subscribe"
     |
     v
App creates Stripe Checkout Session
     |
     v
Redirect to Stripe-hosted checkout
     |
     v
User completes payment
     |
     v
Stripe webhook fires (checkout.session.completed)
     |
     v
Edge function updates user subscription status
     |
     v
App grants full access
```

### 5. Email Layer (SendGrid/Mailgun)

**Purpose**: Trial conversion emails and notifications

**Email Sequence**:
| Day | Email Type | Subject |
|-----|------------|---------|
| 0 | Welcome | Welcome to Biotech Radar |
| 3 | Value | 3 Catalysts You Almost Missed |
| 5 | Social Proof | How Traders Use Catalyst Data |
| 6 | Urgency | Your Trial Ends Tomorrow |
| 7 | Last Chance | Trial Expired - 20% Off Today |
| 9 | Follow-up | Still Trading Blind? |
| 14 | Win-back | Come Back for 30% Off |

---

## Data Flow Diagrams

### User Registration Flow
```
1. User lands on app
2. Clicks "Start Free Trial"
3. Enters email
4. Supabase Auth sends confirmation
5. User confirms email
6. User record created with trial_start_date = NOW()
7. Trial ends trial_start_date + 7 days
8. Full access for 7 days
```

### Daily Data Refresh Flow
```
6:00 AM UTC - Supabase Edge Function triggers

1. Fetch ClinicalTrials.gov API
   - GET /studies?filter.advanced=AREA[Phase](Phase2+OR+Phase3)
   - Next 10 pages (1000 studies max)

2. Parse response
   - Extract: NCT_ID, sponsor, phase, indication, completion_date

3. Ticker mapping (for each sponsor)
   - Check manual_overrides dictionary
   - If no match: fuzzy match against biotech_tickers table
   - Score > 80 = match

4. Stock enrichment (for matched tickers)
   - yfinance: market_cap, current_price, price_change_30d
   - Filter: market_cap < 5,000,000,000

5. Database upsert
   - ON CONFLICT (nct_id) DO UPDATE
   - Update price data, completion date

6. Log completion
   - Record: timestamp, rows_processed, errors
```

---

## Security Architecture

### Authentication
- Supabase Auth (email/password)
- JWT tokens for API access
- Session management via Supabase client

### Authorization
- Row Level Security (RLS) on all tables
- Free users: limited to 10 catalyst rows
- Subscribers: full access
- No direct database access from frontend

### Data Protection
- All data encrypted at rest (Supabase)
- TLS 1.3 for data in transit
- No PII stored beyond email
- Stripe handles all payment data (PCI compliant)

---

## Scalability Considerations

### Current (Free Tier) Limits
| Resource | Limit | Expected Usage |
|----------|-------|----------------|
| Supabase Database | 500 MB | ~15-20 MB |
| Supabase Edge Function Invocations | 500K/month | ~1K/month |
| Streamlit Cloud | Unlimited (community) | Low traffic |
| SendGrid | 100 emails/day | ~20/day |

### Scaling Triggers
- **100 users**: Consider paid Supabase ($25/month)
- **500 users**: Add Redis caching layer
- **1000 users**: Consider dedicated hosting
- **10,000 users**: Microservices architecture

---

## Monitoring & Observability

### Health Checks
- `/health` endpoint on Streamlit app
- Supabase dashboard for database health
- Stripe dashboard for payment health

### Metrics to Track
- Daily active users
- Trial signups
- Trial-to-paid conversion rate
- API response times
- Data sync success rate

### Alerting
- Email on Edge Function failures
- Slack integration (future)
- Supabase logs for debugging

---

## Disaster Recovery

### Backup Strategy
- Supabase automatic daily backups
- Manual CSV exports of critical data
- Git history for code

### Recovery Plan
1. Database restore from Supabase backup
2. Redeploy Edge Functions from Git
3. Verify Stripe webhook connectivity
4. Test subscription status sync

---

## Technology Stack Summary

| Layer | Technology | Cost |
|-------|------------|------|
| Frontend | Streamlit Cloud | Free |
| Database | Supabase (PostgreSQL) | Free |
| Auth | Supabase Auth | Free |
| Automation | Supabase Edge Functions | Free |
| Payments | Stripe | 2.9% + $0.30/txn |
| Email | SendGrid | Free (100/day) |
| Data Source | ClinicalTrials.gov API | Free |
| Stock Data | yfinance | Free |

**Total Monthly Cost (100 users)**: ~$0 + Stripe fees

---

**Last Updated**: 2024-12-30
**Architecture Version**: 2.0 (Supabase-based)
