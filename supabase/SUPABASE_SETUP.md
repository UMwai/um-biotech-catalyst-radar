# Supabase Infrastructure Setup - Free Tier Optimized

> **Goal**: Build production-ready Biotech Catalyst Radar on Supabase free tier (<500MB database)

## Overview

**Hybrid Architecture**: Sync ClinicalTrials.gov data into Supabase PostgreSQL nightly, serve fast queries to users.

**Why Supabase?**
- ✅ 500MB PostgreSQL database (free tier)
- ✅ Built-in Auth (no custom user management needed)
- ✅ Edge Functions (serverless, replaces n8n for data sync)
- ✅ Realtime subscriptions (optional)
- ✅ Automatic REST API generation
- ✅ Connection pooling (handles 50+ concurrent users)

---

## Optimized Schema Design

### Key Optimizations for 500MB Limit

1. **Flatten JSON**: Extract only 12-15 essential fields (not full JSON blobs)
2. **Smart filtering**: Only sync Phase 2/3 trials in specific therapeutic areas
3. **Rolling window**: Keep only trials from last 12 months + next 6 months
4. **No historical snapshots**: Single current state (not `catalyst_history`)
5. **Efficient indexes**: Only index what we query

### Estimated Data Size

```
Trials per year: ~20,000 Phase 2/3 worldwide
After filtering (small-cap biotech only): ~800 trials
After therapeutic area filter (Oncology, Rare Disease, etc.): ~500 trials
Rolling 18-month window: ~750 trials

Per trial storage: ~2 KB (flattened)
Total catalysts: 750 × 2 KB = 1.5 MB

Users (10,000): ~500 KB
Subscriptions: ~200 KB
Email logs (3 months): ~2 MB
Analytics events (3 months): ~5 MB

**Total: ~10 MB for MVP** (plenty of headroom!)
```

---

## Supabase-Optimized Schema

```sql
-- ============================================
-- SUPABASE SCHEMA (FREE TIER OPTIMIZED)
-- Estimated total: ~10-20 MB for 10K users
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. USERS (managed by Supabase Auth)
-- ============================================
-- Supabase creates auth.users automatically
-- We just need a public users table for trial/subscription data

CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    trial_converted BOOLEAN DEFAULT FALSE,
    stripe_customer_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_trial_end ON public.users(trial_end_date) WHERE trial_end_date IS NOT NULL;

-- RLS (Row Level Security)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON public.users
    FOR UPDATE USING (auth.uid() = id);

-- ============================================
-- 2. SUBSCRIPTIONS
-- ============================================
CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT NOT NULL, -- active, canceled, past_due, trialing
    plan_id TEXT, -- monthly, annual
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON public.subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions(status);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- 3. CATALYSTS (OPTIMIZED - Only essential fields)
-- ============================================
CREATE TABLE public.catalysts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Core identifiers
    nct_id TEXT UNIQUE NOT NULL,

    -- Trial details (12 essential fields only)
    sponsor TEXT,
    ticker TEXT, -- Mapped ticker symbol
    ticker_confidence SMALLINT, -- Fuzzy match score (0-100)
    phase TEXT, -- Phase 2, Phase 3, Phase 2/Phase 3
    indication TEXT, -- Disease/condition
    completion_date DATE,
    enrollment INTEGER, -- Patient count
    study_type TEXT, -- Interventional, Observational

    -- Market data (compact)
    market_cap BIGINT,
    current_price NUMERIC(10, 2),
    pct_change_30d NUMERIC(5, 2),

    -- Metadata
    data_refreshed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_phase CHECK (phase IN ('Phase 2', 'Phase 3', 'Phase 2/Phase 3')),
    CONSTRAINT valid_ticker_confidence CHECK (ticker_confidence >= 0 AND ticker_confidence <= 100)
);

-- Indexes (only what we query)
CREATE INDEX idx_catalysts_nct_id ON public.catalysts(nct_id);
CREATE INDEX idx_catalysts_ticker ON public.catalysts(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX idx_catalysts_completion_date ON public.catalysts(completion_date) WHERE completion_date IS NOT NULL;
CREATE INDEX idx_catalysts_phase ON public.catalysts(phase);
CREATE INDEX idx_catalysts_market_cap ON public.catalysts(market_cap) WHERE market_cap IS NOT NULL;

-- RLS
ALTER TABLE public.catalysts ENABLE ROW LEVEL SECURITY;

-- Free users: see 10 rows only
CREATE POLICY "Free users see limited catalysts" ON public.catalysts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users u
            LEFT JOIN public.subscriptions s ON u.id = s.user_id AND s.status = 'active'
            WHERE u.id = auth.uid()
            AND (
                s.id IS NOT NULL -- Has active subscription
                OR u.trial_end_date > NOW() -- Active trial
            )
        )
        OR id IN (
            SELECT id FROM public.catalysts
            ORDER BY completion_date ASC
            LIMIT 10
        )
    );

-- ============================================
-- 4. EMAIL LOG (Rolling 90-day window)
-- ============================================
CREATE TABLE public.email_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    email_type TEXT NOT NULL, -- trial_day_1, trial_day_3, etc.
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ
);

CREATE INDEX idx_email_log_user_id ON public.email_log(user_id);
CREATE INDEX idx_email_log_sent_at ON public.email_log(sent_at);

-- Auto-delete emails older than 90 days (keep size down)
CREATE OR REPLACE FUNCTION delete_old_email_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM public.email_log
    WHERE sent_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 5. ANALYTICS EVENTS (Rolling 90-day window)
-- ============================================
CREATE TABLE public.analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL, -- signup, trial_start, conversion, page_view, etc.
    event_metadata JSONB, -- Minimal metadata only
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_user_id ON public.analytics_events(user_id);
CREATE INDEX idx_analytics_event_type ON public.analytics_events(event_type);
CREATE INDEX idx_analytics_created_at ON public.analytics_events(created_at);

-- Auto-delete events older than 90 days
CREATE OR REPLACE FUNCTION delete_old_analytics()
RETURNS void AS $$
BEGIN
    DELETE FROM public.analytics_events
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. EDGE FUNCTION LOGS (Lightweight)
-- ============================================
CREATE TABLE public.edge_function_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    function_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    items_processed INTEGER DEFAULT 0,
    status TEXT, -- success, failed
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_edge_function_runs_name ON public.edge_function_runs(function_name);
CREATE INDEX idx_edge_function_runs_started_at ON public.edge_function_runs(started_at DESC);

-- Auto-delete logs older than 30 days
CREATE OR REPLACE FUNCTION delete_old_function_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM public.edge_function_runs
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- AUTO-UPDATE TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- CLEANUP SCHEDULER (Run daily via Edge Function)
-- ============================================
-- Call these from a scheduled Edge Function:
-- SELECT delete_old_email_logs();
-- SELECT delete_old_analytics();
-- SELECT delete_old_function_logs();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Active trials (next 90 days)
CREATE VIEW active_catalysts AS
SELECT *
FROM public.catalysts
WHERE completion_date BETWEEN NOW() AND NOW() + INTERVAL '90 days'
AND ticker IS NOT NULL
ORDER BY completion_date ASC;

-- User subscription status
CREATE VIEW user_access_status AS
SELECT
    u.id,
    u.email,
    CASE
        WHEN s.status = 'active' THEN 'subscribed'
        WHEN u.trial_end_date > NOW() THEN 'trial'
        ELSE 'expired'
    END AS access_level,
    COALESCE(s.current_period_end, u.trial_end_date) AS access_expires_at
FROM public.users u
LEFT JOIN public.subscriptions s ON u.id = s.user_id AND s.status = 'active';
```

---

## Database Size Estimation

**Catalysts Table** (main storage):
```sql
-- Check current size
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Expected sizes**:
- 500 catalysts × 2 KB = **1 MB**
- 10,000 users × 0.5 KB = **5 MB**
- 3 months email logs = **2 MB**
- 3 months analytics = **5 MB**
- Indexes = **3 MB**
- **Total: ~15-20 MB** (well under 500MB!)

---

## Filtering Strategy (Stay Under 500MB)

### Option 1: Therapeutic Area Filter (Recommended)

Only sync trials in high-value therapeutic areas:

```sql
-- In Edge Function, filter API results:
const THERAPEUTIC_AREAS = [
  'Oncology',
  'Rare Diseases',
  'Neurology',
  'Immunology',
  'Cardiology'
];

// Only sync trials matching these conditions
```

### Option 2: Smart Cap Filter

```sql
-- Only sync trials for companies with:
-- - Market cap < $5B (small caps)
-- - Traded on NASDAQ/NYSE
-- - Phase 2 or Phase 3
```

### Option 3: AACT Database (Advanced)

Use the pre-processed AACT database:

1. Download AACT monthly dump (free)
2. Import only relevant tables: `studies`, `outcomes`, `sponsors`
3. Filter to your criteria
4. Load into Supabase

**AACT Tables to Import**:
- `studies` (core trial data)
- `sponsors` (company mapping)
- `outcomes` (results - optional)

**Skip AACT tables** (save space):
- `detailed_descriptions`
- `design_outcomes`
- `browse_conditions`
- Full XML dumps

---

## Auto-Cleanup Functions

**Keep database lean** with automatic cleanup:

```sql
-- Schedule via Supabase Edge Function (daily cron)

-- Delete trials older than 18 months
DELETE FROM public.catalysts
WHERE completion_date < NOW() - INTERVAL '18 months';

-- Delete old logs
SELECT delete_old_email_logs();
SELECT delete_old_analytics();
SELECT delete_old_function_logs();

-- Vacuum to reclaim space
VACUUM ANALYZE public.catalysts;
```

---

## Next Steps

1. **Deploy this schema** to Supabase
2. **Create Edge Function** for daily sync (see `supabase-edge-functions/daily-sync.ts`)
3. **Update Streamlit app** to use Supabase client
4. **Enable RLS policies** for security

---

**File**: `supabase/migrations/20251224_initial_schema.sql`
**Status**: ✅ Ready for deployment
**Estimated DB size**: 15-20 MB (97% under free tier limit)
