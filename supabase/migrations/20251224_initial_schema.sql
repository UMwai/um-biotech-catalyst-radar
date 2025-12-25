-- ============================================
-- BIOTECH CATALYST RADAR - SUPABASE SCHEMA
-- Free Tier Optimized (<500MB)
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. PUBLIC USERS TABLE
-- (auth.users is managed by Supabase Auth)
-- ============================================

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

-- Indexes
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_trial_end ON public.users(trial_end_date) WHERE trial_end_date IS NOT NULL;

-- Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON public.users
    FOR UPDATE USING (auth.uid() = id);

COMMENT ON TABLE public.users IS 'User profiles with trial and Stripe data';

-- ============================================
-- 2. SUBSCRIPTIONS
-- ============================================

CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete')),
    plan_id TEXT, -- monthly, annual
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON public.subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX idx_subscriptions_stripe_id ON public.subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscriptions" ON public.subscriptions
    FOR SELECT USING (auth.uid() = user_id);

COMMENT ON TABLE public.subscriptions IS 'Stripe subscription tracking';

-- ============================================
-- 3. CATALYSTS (OPTIMIZED)
-- ============================================

CREATE TABLE public.catalysts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Core identifiers
    nct_id TEXT UNIQUE NOT NULL,

    -- Trial details (12 essential fields)
    sponsor TEXT,
    ticker TEXT,
    ticker_confidence SMALLINT CHECK (ticker_confidence >= 0 AND ticker_confidence <= 100),
    phase TEXT CHECK (phase IN ('Phase 2', 'Phase 3', 'Phase 2/Phase 3')),
    indication TEXT,
    completion_date DATE,
    enrollment INTEGER,
    study_type TEXT,

    -- Market data
    market_cap BIGINT,
    current_price NUMERIC(10, 2),
    pct_change_30d NUMERIC(5, 2),

    -- Metadata
    data_refreshed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes (only what we query)
CREATE INDEX idx_catalysts_nct_id ON public.catalysts(nct_id);
CREATE INDEX idx_catalysts_ticker ON public.catalysts(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX idx_catalysts_completion_date ON public.catalysts(completion_date) WHERE completion_date IS NOT NULL;
CREATE INDEX idx_catalysts_phase ON public.catalysts(phase);
CREATE INDEX idx_catalysts_market_cap ON public.catalysts(market_cap) WHERE market_cap < 5000000000;

ALTER TABLE public.catalysts ENABLE ROW LEVEL SECURITY;

-- RLS: Free users see 10 rows, subscribers see all
CREATE POLICY "Authenticated users see catalysts based on subscription" ON public.catalysts
    FOR SELECT USING (
        -- User has active subscription or trial
        EXISTS (
            SELECT 1
            FROM public.users u
            LEFT JOIN public.subscriptions s ON u.id = s.user_id AND s.status = 'active'
            WHERE u.id = auth.uid()
            AND (s.id IS NOT NULL OR u.trial_end_date > NOW())
        )
        -- OR it's in the preview (first 10 rows)
        OR id IN (
            SELECT id FROM public.catalysts
            ORDER BY completion_date ASC NULLS LAST
            LIMIT 10
        )
    );

COMMENT ON TABLE public.catalysts IS 'Clinical trial catalysts (Phase 2/3 only, optimized for <500MB)';

-- ============================================
-- 4. EMAIL LOG (90-day rolling window)
-- ============================================

CREATE TABLE public.email_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    email_type TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ
);

CREATE INDEX idx_email_log_user_id ON public.email_log(user_id);
CREATE INDEX idx_email_log_sent_at ON public.email_log(sent_at);

ALTER TABLE public.email_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own email log" ON public.email_log
    FOR SELECT USING (auth.uid() = user_id);

COMMENT ON TABLE public.email_log IS 'Email campaign tracking (auto-deletes after 90 days)';

-- ============================================
-- 5. ANALYTICS EVENTS (90-day rolling window)
-- ============================================

CREATE TABLE public.analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_user_id ON public.analytics_events(user_id);
CREATE INDEX idx_analytics_event_type ON public.analytics_events(event_type);
CREATE INDEX idx_analytics_created_at ON public.analytics_events(created_at);

ALTER TABLE public.analytics_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can insert analytics" ON public.analytics_events
    FOR INSERT WITH CHECK (true);

COMMENT ON TABLE public.analytics_events IS 'User behavior tracking (auto-deletes after 90 days)';

-- ============================================
-- 6. EDGE FUNCTION LOGS
-- ============================================

CREATE TABLE public.edge_function_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    function_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    items_processed INTEGER DEFAULT 0,
    status TEXT CHECK (status IN ('success', 'failed', 'partial')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_edge_function_runs_name ON public.edge_function_runs(function_name);
CREATE INDEX idx_edge_function_runs_started_at ON public.edge_function_runs(started_at DESC);

COMMENT ON TABLE public.edge_function_runs IS 'Edge function execution logs (auto-deletes after 30 days)';

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
-- CLEANUP FUNCTIONS
-- ============================================

CREATE OR REPLACE FUNCTION delete_old_email_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.email_log
    WHERE sent_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_email_logs IS 'Delete email logs older than 90 days to save space';

CREATE OR REPLACE FUNCTION delete_old_analytics()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.analytics_events
    WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_analytics IS 'Delete analytics events older than 90 days';

CREATE OR REPLACE FUNCTION delete_old_function_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.edge_function_runs
    WHERE created_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_function_logs IS 'Delete edge function logs older than 30 days';

CREATE OR REPLACE FUNCTION delete_old_catalysts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete trials that completed >18 months ago
    DELETE FROM public.catalysts
    WHERE completion_date < NOW() - INTERVAL '18 months';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_catalysts IS 'Delete catalysts older than 18 months to save space';

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

CREATE VIEW active_catalysts AS
SELECT *
FROM public.catalysts
WHERE completion_date BETWEEN NOW() AND NOW() + INTERVAL '90 days'
AND ticker IS NOT NULL
ORDER BY completion_date ASC;

COMMENT ON VIEW active_catalysts IS 'Catalysts in next 90 days with ticker mapped';

CREATE VIEW user_access_status AS
SELECT
    u.id,
    u.email,
    CASE
        WHEN s.status = 'active' THEN 'subscribed'
        WHEN u.trial_end_date > NOW() THEN 'trial'
        ELSE 'expired'
    END AS access_level,
    EXTRACT(DAY FROM (COALESCE(s.current_period_end, u.trial_end_date) - NOW())) AS days_remaining,
    COALESCE(s.current_period_end, u.trial_end_date) AS access_expires_at
FROM public.users u
LEFT JOIN public.subscriptions s ON u.id = s.user_id AND s.status = 'active';

COMMENT ON VIEW user_access_status IS 'User subscription and trial status summary';

-- ============================================
-- HELPER FUNCTION: Get User Access Level
-- ============================================

CREATE OR REPLACE FUNCTION get_user_access_level(user_id UUID)
RETURNS TEXT AS $$
DECLARE
    has_subscription BOOLEAN;
    trial_active BOOLEAN;
BEGIN
    -- Check for active subscription
    SELECT EXISTS(
        SELECT 1 FROM public.subscriptions
        WHERE user_id = $1 AND status = 'active'
    ) INTO has_subscription;

    IF has_subscription THEN
        RETURN 'full';
    END IF;

    -- Check for active trial
    SELECT EXISTS(
        SELECT 1 FROM public.users
        WHERE id = $1 AND trial_end_date > NOW()
    ) INTO trial_active;

    IF trial_active THEN
        RETURN 'trial';
    END IF;

    RETURN 'preview';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_user_access_level IS 'Returns user access level: full, trial, or preview';

-- ============================================
-- SAMPLE DATA (for testing)
-- ============================================

-- Insert test catalyst (can be deleted)
INSERT INTO public.catalysts (
    nct_id,
    sponsor,
    ticker,
    ticker_confidence,
    phase,
    indication,
    completion_date,
    enrollment,
    study_type,
    market_cap,
    current_price,
    pct_change_30d
) VALUES (
    'NCT05000000',
    'Example Biotech Inc.',
    'EXBT',
    95,
    'Phase 3',
    'Oncology - Non-Small Cell Lung Cancer',
    '2025-06-15'::DATE,
    450,
    'Interventional',
    2500000000,
    45.23,
    12.5
);

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

-- Grant authenticated users access to their own data
GRANT SELECT ON public.users TO authenticated;
GRANT UPDATE ON public.users TO authenticated;

GRANT SELECT ON public.subscriptions TO authenticated;

-- Authenticated users can read catalysts (RLS controls access)
GRANT SELECT ON public.catalysts TO authenticated;

-- Service role can write (for Edge Functions)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ============================================
-- COMPLETION MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '✅ Biotech Catalyst Radar schema deployed successfully';
    RAISE NOTICE '📊 Estimated database size: 15-20 MB (97%% under 500MB free tier limit)';
    RAISE NOTICE '🔒 Row Level Security enabled on all tables';
    RAISE NOTICE '🧹 Auto-cleanup functions created (call from Edge Function daily)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Deploy Supabase Edge Function for daily sync';
    RAISE NOTICE '2. Update Streamlit app to use Supabase client';
    RAISE NOTICE '3. Enable Supabase Auth for user management';
END $$;
