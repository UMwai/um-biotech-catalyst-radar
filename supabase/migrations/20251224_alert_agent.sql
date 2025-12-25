-- ============================================
-- BIOTECH CATALYST RADAR - ALERT AGENT
-- Proactive monitoring & notification system
-- ============================================

-- ============================================
-- 1. SAVED SEARCHES TABLE
-- ============================================

CREATE TABLE public.saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Search configuration
    name TEXT NOT NULL, -- e.g., "Oncology under $500M"
    query_params JSONB NOT NULL, -- {therapeutic_area, max_market_cap, phase, etc.}

    -- Notification settings
    notification_channels TEXT[] NOT NULL DEFAULT ARRAY['email']::TEXT[], -- email, sms, slack

    -- Monitoring metadata
    last_checked TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_saved_searches_user_id ON public.saved_searches(user_id);
CREATE INDEX idx_saved_searches_active ON public.saved_searches(user_id, active) WHERE active = TRUE;
CREATE INDEX idx_saved_searches_last_checked ON public.saved_searches(last_checked) WHERE active = TRUE;

-- Row Level Security
ALTER TABLE public.saved_searches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own saved searches" ON public.saved_searches
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own saved searches" ON public.saved_searches
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own saved searches" ON public.saved_searches
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own saved searches" ON public.saved_searches
    FOR DELETE USING (auth.uid() = user_id);

COMMENT ON TABLE public.saved_searches IS 'User-defined search filters with automatic monitoring';

-- ============================================
-- 2. ALERT NOTIFICATIONS TABLE
-- ============================================

CREATE TABLE public.alert_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    saved_search_id UUID NOT NULL REFERENCES public.saved_searches(id) ON DELETE CASCADE,
    catalyst_id UUID NOT NULL REFERENCES public.catalysts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Notification details
    notification_sent_at TIMESTAMPTZ DEFAULT NOW(),
    channels_used TEXT[] NOT NULL,

    -- User interaction
    user_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,

    -- Alert content (cached for display)
    alert_content JSONB, -- {catalyst_name, ticker, completion_date, etc.}

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_alert_notifications_search_id ON public.alert_notifications(saved_search_id);
CREATE INDEX idx_alert_notifications_catalyst_id ON public.alert_notifications(catalyst_id);
CREATE INDEX idx_alert_notifications_user_id ON public.alert_notifications(user_id);
CREATE INDEX idx_alert_notifications_sent_at ON public.alert_notifications(notification_sent_at DESC);
CREATE UNIQUE INDEX idx_alert_notifications_dedup ON public.alert_notifications(saved_search_id, catalyst_id);

-- Row Level Security
ALTER TABLE public.alert_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own alert notifications" ON public.alert_notifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own alert acknowledgments" ON public.alert_notifications
    FOR UPDATE USING (auth.uid() = user_id);

COMMENT ON TABLE public.alert_notifications IS 'Log of sent alerts with deduplication';

-- ============================================
-- 3. USER NOTIFICATION PREFERENCES
-- ============================================

CREATE TABLE public.notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Rate limiting
    max_alerts_per_day INTEGER DEFAULT 10,

    -- Quiet hours (UTC timezone stored, converted in app)
    quiet_hours_start TIME, -- e.g., '22:00:00' for 10 PM
    quiet_hours_end TIME,   -- e.g., '08:00:00' for 8 AM
    user_timezone TEXT DEFAULT 'America/New_York', -- IANA timezone

    -- Channel preferences
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE, -- Pro tier only
    slack_enabled BOOLEAN DEFAULT FALSE, -- Pro tier only

    -- Contact details
    phone_number TEXT, -- For SMS notifications
    slack_webhook_url TEXT, -- For Slack notifications

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own notification preferences" ON public.notification_preferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences" ON public.notification_preferences
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences" ON public.notification_preferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

COMMENT ON TABLE public.notification_preferences IS 'User notification settings and rate limits';

-- ============================================
-- 4. HELPER FUNCTIONS
-- ============================================

-- Function to check if user can receive more alerts today
CREATE OR REPLACE FUNCTION can_receive_alert(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    alerts_today INTEGER;
    max_allowed INTEGER;
BEGIN
    -- Get max alerts allowed
    SELECT COALESCE(max_alerts_per_day, 10)
    INTO max_allowed
    FROM public.notification_preferences
    WHERE user_id = p_user_id;

    -- If no preferences, use default
    IF max_allowed IS NULL THEN
        max_allowed := 10;
    END IF;

    -- Count alerts sent today
    SELECT COUNT(*)
    INTO alerts_today
    FROM public.alert_notifications
    WHERE user_id = p_user_id
    AND notification_sent_at >= CURRENT_DATE;

    RETURN alerts_today < max_allowed;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION can_receive_alert IS 'Check if user has not exceeded daily alert limit';

-- Function to check if within quiet hours
CREATE OR REPLACE FUNCTION is_quiet_hours(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    prefs RECORD;
    user_time TIME;
BEGIN
    -- Get user preferences
    SELECT quiet_hours_start, quiet_hours_end, user_timezone
    INTO prefs
    FROM public.notification_preferences
    WHERE user_id = p_user_id;

    -- If no quiet hours set, always allow
    IF prefs.quiet_hours_start IS NULL OR prefs.quiet_hours_end IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Convert current UTC time to user's timezone
    -- Note: This is simplified; in production use pg_timezone extension
    user_time := CURRENT_TIME;

    -- Check if current time is in quiet hours
    IF prefs.quiet_hours_start < prefs.quiet_hours_end THEN
        -- Normal range (e.g., 22:00-08:00 next day)
        RETURN user_time >= prefs.quiet_hours_start AND user_time < prefs.quiet_hours_end;
    ELSE
        -- Overnight range (e.g., 22:00-08:00)
        RETURN user_time >= prefs.quiet_hours_start OR user_time < prefs.quiet_hours_end;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_quiet_hours IS 'Check if current time is within user quiet hours';

-- Function to get user tier (for channel restrictions)
CREATE OR REPLACE FUNCTION get_user_tier(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    has_subscription BOOLEAN;
    trial_active BOOLEAN;
BEGIN
    -- Check for active subscription
    SELECT EXISTS(
        SELECT 1 FROM public.subscriptions
        WHERE user_id = p_user_id AND status = 'active'
    ) INTO has_subscription;

    IF has_subscription THEN
        RETURN 'pro';
    END IF;

    -- Check for active trial
    SELECT EXISTS(
        SELECT 1 FROM public.users
        WHERE id = p_user_id AND trial_end_date > NOW()
    ) INTO trial_active;

    IF trial_active THEN
        RETURN 'trial';
    END IF;

    RETURN 'free';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_user_tier IS 'Returns user tier: pro, trial, or free';

-- Function to enforce saved search limits by tier
CREATE OR REPLACE FUNCTION check_saved_search_limit()
RETURNS TRIGGER AS $$
DECLARE
    user_tier TEXT;
    search_count INTEGER;
    max_searches INTEGER;
BEGIN
    user_tier := get_user_tier(NEW.user_id);

    -- Set limits by tier
    IF user_tier = 'pro' THEN
        max_searches := 999999; -- Unlimited
    ELSE
        max_searches := 3; -- Free/trial tier
    END IF;

    -- Count existing searches
    SELECT COUNT(*)
    INTO search_count
    FROM public.saved_searches
    WHERE user_id = NEW.user_id AND active = TRUE;

    -- Check limit
    IF search_count >= max_searches THEN
        RAISE EXCEPTION 'Maximum saved searches limit reached (% for % tier). Upgrade to Pro for unlimited searches.',
            max_searches, user_tier;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce saved search limits
CREATE TRIGGER enforce_saved_search_limit
    BEFORE INSERT ON public.saved_searches
    FOR EACH ROW EXECUTE FUNCTION check_saved_search_limit();

-- ============================================
-- 5. AUTO-UPDATE TRIGGERS
-- ============================================

CREATE TRIGGER saved_searches_updated_at
    BEFORE UPDATE ON public.saved_searches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER notification_preferences_updated_at
    BEFORE UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================
-- 6. CLEANUP FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION delete_old_alert_notifications()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete alert notifications older than 90 days
    DELETE FROM public.alert_notifications
    WHERE notification_sent_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_alert_notifications IS 'Delete alert notifications older than 90 days';

-- ============================================
-- 7. VIEWS FOR COMMON QUERIES
-- ============================================

CREATE VIEW user_alert_summary AS
SELECT
    u.id AS user_id,
    u.email,
    COUNT(DISTINCT ss.id) AS active_searches,
    COUNT(an.id) FILTER (WHERE an.notification_sent_at >= CURRENT_DATE) AS alerts_today,
    COUNT(an.id) FILTER (WHERE an.notification_sent_at >= NOW() - INTERVAL '7 days') AS alerts_last_7_days,
    COUNT(an.id) FILTER (WHERE an.user_acknowledged = FALSE) AS unacknowledged_alerts,
    np.max_alerts_per_day,
    get_user_tier(u.id) AS user_tier
FROM public.users u
LEFT JOIN public.saved_searches ss ON u.id = ss.user_id AND ss.active = TRUE
LEFT JOIN public.alert_notifications an ON u.id = an.user_id
LEFT JOIN public.notification_preferences np ON u.id = np.user_id
GROUP BY u.id, u.email, np.max_alerts_per_day;

COMMENT ON VIEW user_alert_summary IS 'Summary of alert activity per user';

-- ============================================
-- 8. GRANT PERMISSIONS
-- ============================================

-- Authenticated users can manage their own data
GRANT SELECT, INSERT, UPDATE, DELETE ON public.saved_searches TO authenticated;
GRANT SELECT, UPDATE ON public.alert_notifications TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.notification_preferences TO authenticated;

-- Service role has full access (for Edge Functions)
GRANT ALL ON public.saved_searches TO service_role;
GRANT ALL ON public.alert_notifications TO service_role;
GRANT ALL ON public.notification_preferences TO service_role;

-- ============================================
-- 9. SAMPLE DATA (for testing)
-- ============================================

-- Insert default notification preferences for test user
-- (User ID will be set after auth user is created)

-- ============================================
-- COMPLETION MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '✅ Alert Agent schema deployed successfully';
    RAISE NOTICE '🔔 Created tables: saved_searches, alert_notifications, notification_preferences';
    RAISE NOTICE '🔒 Row Level Security enabled on all tables';
    RAISE NOTICE '📊 Tier limits: Free/Trial = 3 searches, Pro = unlimited';
    RAISE NOTICE '📧 Channels: Email (all tiers), SMS/Slack (Pro only)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Deploy check-alerts Edge Function';
    RAISE NOTICE '2. Set up cron trigger for daily checks (9 AM ET = 14:00 UTC)';
    RAISE NOTICE '3. Configure SendGrid/Twilio/Slack API keys';
    RAISE NOTICE '4. Test with sample saved search';
END $$;
