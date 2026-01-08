# Phase 4: Growth - Deployment Guide

> Complete deployment guide for Chat Agent + Proactive Alerts

## Overview

Phase 4 implements two major features:
1. **Chat Agent** - Natural language catalyst discovery
2. **Proactive Alerts** - Automated saved search monitoring with multi-channel notifications

**Timeline**: 1-2 weeks
**Status**: Ready for deployment
**Infrastructure**: Supabase (free tier) + Streamlit Cloud (free tier)

---

## Prerequisites

### Required Accounts
- [x] Supabase account (free tier)
- [x] Streamlit Cloud account (free tier)
- [x] SendGrid account (free tier - 100 emails/day)
- [ ] Twilio account (optional - Pro tier SMS)
- [ ] Slack workspace (optional - Pro tier notifications)

### Required Tools
```bash
# Install Supabase CLI
npm install -g supabase

# Install Streamlit
pip install streamlit

# Verify versions
supabase --version  # Should be 1.x+
streamlit version   # Should be 1.28+
```

---

## Part 1: Deploy Chat Agent

### 1.1 Verify Database Schema

The chat agent uses existing `catalysts` table. Verify it exists:

```sql
-- Run in Supabase SQL Editor
SELECT COUNT(*) FROM catalysts;
SELECT DISTINCT phase FROM catalysts;
SELECT DISTINCT therapeutic_area FROM catalysts WHERE therapeutic_area IS NOT NULL;
```

Expected:
- `catalysts` table exists
- Contains Phase 2/3 trials
- Has `ticker`, `market_cap`, `completion_date` columns

### 1.2 Test Chat Agent Locally

```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar

# Set environment variables
export SUPABASE_URL=https://xxxxx.supabase.co
export SUPABASE_ANON_KEY=your_anon_key

# Run chat page
streamlit run src/pages/chat.py
```

**Test queries:**
1. "Phase 3 oncology under $2B"
2. "trials next 60 days"
3. "neurology catalysts"
4. "Phase 2 rare disease under $1B"

Expected behavior:
- Query is parsed correctly
- Filters are applied to database
- Results are displayed as cards
- Action buttons work (Details, Watch, Alert)

### 1.3 Deploy to Streamlit Cloud

1. **Push code to GitHub:**
```bash
git add src/pages/chat.py src/ui/chat_agent.py src/agents/catalyst_agent.py
git commit -m "Add chat agent for Phase 4"
git push origin main
```

2. **Deploy via Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect GitHub repository
   - Set main file: `src/app.py`
   - Add secrets in "Advanced settings":
     ```toml
     SUPABASE_URL = "https://xxxxx.supabase.co"
     SUPABASE_ANON_KEY = "your_anon_key"
     ```
   - Click "Deploy"

3. **Verify deployment:**
   - Navigate to `/pages/chat.py` page
   - Test all example queries
   - Verify results load correctly

---

## Part 2: Deploy Proactive Alerts

### 2.1 Deploy Database Migrations

The alerts system requires additional tables:

```bash
# Run migration for saved_searches table
supabase db push
```

Or manually via SQL Editor:

```sql
-- Create saved_searches table
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    query_params JSONB NOT NULL,
    notification_channels JSONB DEFAULT '["email"]',
    active BOOLEAN DEFAULT TRUE,
    last_checked TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saved_searches_user ON saved_searches(user_id);
CREATE INDEX idx_saved_searches_active ON saved_searches(active) WHERE active = TRUE;

-- Create alert_notifications table
CREATE TABLE alert_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    saved_search_id UUID REFERENCES saved_searches(id) ON DELETE SET NULL,
    catalyst_id UUID REFERENCES catalysts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channels_used JSONB,
    alert_content JSONB,
    notification_sent_at TIMESTAMP DEFAULT NOW(),
    user_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP
);

CREATE INDEX idx_alert_notifications_user ON alert_notifications(user_id);
CREATE INDEX idx_alert_notifications_catalyst ON alert_notifications(catalyst_id);

-- Create notification_preferences table
CREATE TABLE notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    max_alerts_per_day INTEGER DEFAULT 10,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    user_timezone VARCHAR(50) DEFAULT 'America/New_York',
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    slack_enabled BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20),
    slack_webhook_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.2 Deploy Supabase Edge Function

```bash
# Deploy check-alerts function
supabase functions deploy check-alerts

# Set environment variables
supabase secrets set SENDGRID_API_KEY=your_sendgrid_key
supabase secrets set TWILIO_ACCOUNT_SID=your_twilio_sid
supabase secrets set TWILIO_AUTH_TOKEN=your_twilio_token
supabase secrets set TWILIO_FROM_NUMBER=+1234567890
```

### 2.3 Test Edge Function

```bash
# Invoke manually
supabase functions invoke check-alerts

# Or via curl
curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "success": true,
  "searches_checked": 3,
  "matches_found": 2,
  "notifications_sent": 2,
  "errors": 0,
  "timestamp": "2025-12-30T14:00:00.000Z"
}
```

### 2.4 Schedule Daily Cron Job

Enable `pg_cron` extension:
1. Go to **Database → Extensions** in Supabase Dashboard
2. Enable "pg_cron"

Create cron job (via SQL Editor):

```sql
-- Run daily at 9 AM ET (14:00 UTC)
SELECT cron.schedule(
    'check-alerts-daily',
    '0 14 * * *',
    $$
    SELECT net.http_post(
        url := 'https://xxxxx.supabase.co/functions/v1/check-alerts',
        headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
    );
    $$
);

-- Verify cron job created
SELECT * FROM cron.job;
```

### 2.5 Create Helper Database Functions

```sql
-- Function to check if user can receive alert
CREATE OR REPLACE FUNCTION can_receive_alert(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_max_alerts INTEGER;
    v_alerts_today INTEGER;
BEGIN
    -- Get user's max alerts per day
    SELECT max_alerts_per_day INTO v_max_alerts
    FROM notification_preferences
    WHERE user_id = p_user_id;

    -- Default to 10 if not set
    v_max_alerts := COALESCE(v_max_alerts, 10);

    -- Count alerts sent today
    SELECT COUNT(*) INTO v_alerts_today
    FROM alert_notifications
    WHERE user_id = p_user_id
      AND notification_sent_at >= CURRENT_DATE;

    RETURN v_alerts_today < v_max_alerts;
END;
$$ LANGUAGE plpgsql;

-- Function to check if user is in quiet hours
CREATE OR REPLACE FUNCTION is_quiet_hours(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_quiet_start TIME;
    v_quiet_end TIME;
    v_timezone VARCHAR(50);
    v_current_time TIME;
BEGIN
    -- Get user's quiet hours settings
    SELECT quiet_hours_start, quiet_hours_end, user_timezone
    INTO v_quiet_start, v_quiet_end, v_timezone
    FROM notification_preferences
    WHERE user_id = p_user_id;

    -- If quiet hours not set, return false
    IF v_quiet_start IS NULL OR v_quiet_end IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Get current time in user's timezone
    v_current_time := (NOW() AT TIME ZONE v_timezone)::TIME;

    -- Check if current time is within quiet hours
    IF v_quiet_start <= v_quiet_end THEN
        RETURN v_current_time >= v_quiet_start AND v_current_time <= v_quiet_end;
    ELSE
        -- Handle overnight quiet hours (e.g., 22:00 - 06:00)
        RETURN v_current_time >= v_quiet_start OR v_current_time <= v_quiet_end;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get user tier
CREATE OR REPLACE FUNCTION get_user_tier(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_tier TEXT;
BEGIN
    SELECT
        CASE
            WHEN s.status = 'active' AND s.stripe_price_id LIKE '%pro%' THEN 'pro'
            WHEN s.status = 'active' THEN 'starter'
            WHEN s.status = 'trialing' THEN 'trial'
            ELSE 'free'
        END INTO v_tier
    FROM subscriptions s
    WHERE s.user_id = p_user_id
      AND s.status IN ('active', 'trialing')
    ORDER BY s.created_at DESC
    LIMIT 1;

    RETURN COALESCE(v_tier, 'free');
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old alert notifications (90 days retention)
CREATE OR REPLACE FUNCTION delete_old_alert_notifications()
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM alert_notifications
    WHERE notification_sent_at < NOW() - INTERVAL '90 days';

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### 2.6 Deploy Alerts UI

The UI is already implemented in `src/pages/alerts.py`. Update Streamlit Cloud:

```bash
git add src/pages/alerts.py src/ui/saved_searches.py
git commit -m "Add proactive alerts UI for Phase 4"
git push origin main
```

Streamlit Cloud will auto-redeploy.

### 2.7 Configure SendGrid

1. **Create SendGrid account:** https://sendgrid.com (free tier: 100 emails/day)

2. **Create API key:**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: `biotech-catalyst-radar-alerts`
   - Permissions: "Full Access"
   - Copy key (shown only once!)

3. **Verify sender email:**
   - Go to Settings → Sender Authentication
   - Verify a single sender: `alerts@yourdomain.com`
   - Follow email verification steps

4. **Add to Supabase secrets:**
```bash
supabase secrets set SENDGRID_API_KEY=SG.xxxxx
```

5. **Test email sending:**
```bash
# Create a test saved search via UI
# Wait for cron job or manually trigger function
# Check SendGrid Activity Feed for sent emails
```

---

## Part 3: End-to-End Testing

### 3.1 Test Chat Agent

**Manual test cases:**

| Test Case | Query | Expected Result |
|-----------|-------|-----------------|
| 1. Phase filter | "Phase 3 trials" | Only Phase 3 catalysts |
| 2. Therapeutic area | "oncology catalysts" | Only oncology trials |
| 3. Market cap | "under $2B" | Only <$2B market cap |
| 4. Combined | "Phase 3 oncology under $2B" | All filters applied |
| 5. Timeframe | "next 60 days" | Only trials within 60 days |
| 6. No results | "Phase 5 trials" | No results message with suggestions |

**Acceptance criteria:**
- [ ] All queries parse correctly
- [ ] Results match filters
- [ ] Response time <500ms (90th percentile)
- [ ] Catalyst cards render correctly
- [ ] Action buttons clickable
- [ ] Mobile-responsive (test on 360px screen)

### 3.2 Test Proactive Alerts

**Test workflow:**

1. **Create test user:**
```sql
INSERT INTO users (email, created_at)
VALUES ('test@example.com', NOW())
RETURNING id;
-- Copy user ID
```

2. **Create saved search:**
```sql
INSERT INTO saved_searches (user_id, name, query_params, notification_channels, active)
VALUES (
    'user-uuid-here',
    'Test Search - Oncology',
    '{"phase": "Phase 3", "therapeutic_area": "oncology", "max_market_cap": 2000000000}',
    '["email"]',
    true
);
```

3. **Insert test catalyst:**
```sql
INSERT INTO catalysts (
    nct_id, sponsor, ticker, phase, indication,
    completion_date, market_cap, current_price, created_at
)
VALUES (
    'NCT99999999',
    'Test Pharma Inc.',
    'TEST',
    'Phase 3',
    'Advanced oncology treatment',
    '2026-06-30',
    1500000000,
    25.50,
    NOW()
);
```

4. **Trigger alert check:**
```bash
curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

5. **Verify email sent:**
   - Check SendGrid Activity Feed
   - Verify `test@example.com` received email
   - Email should contain catalyst details

6. **Check database logging:**
```sql
SELECT * FROM alert_notifications
WHERE user_id = 'user-uuid-here'
ORDER BY notification_sent_at DESC
LIMIT 1;
```

**Acceptance criteria:**
- [ ] Alert is sent within 5 minutes
- [ ] Email contains correct catalyst data
- [ ] No duplicate alerts sent
- [ ] Alert logged in `alert_notifications` table
- [ ] `saved_searches.last_checked` updated

### 3.3 Test Saved Search UI

1. Navigate to `/pages/alerts.py`
2. Click "New Search"
3. Fill form:
   - Name: "My Test Search"
   - Phase: "Phase 3"
   - Therapeutic area: "oncology"
   - Max market cap: $2B
   - Channels: Email only
4. Click "Create Search"
5. Verify search appears in list
6. Click "Test" button
7. Verify results match criteria
8. Click "Pause" button
9. Verify status changes to paused
10. Click "Delete" button
11. Verify search is removed

**Acceptance criteria:**
- [ ] Create search works
- [ ] Edit search works
- [ ] Test search shows accurate results
- [ ] Pause/resume toggle works
- [ ] Delete removes search
- [ ] Form validation prevents empty names

---

## Part 4: Production Monitoring

### 4.1 Monitor Edge Function Runs

```sql
-- View recent function runs
SELECT
    function_name,
    started_at,
    completed_at,
    items_processed,
    status
FROM edge_function_runs
WHERE function_name = 'check-alerts'
ORDER BY started_at DESC
LIMIT 10;

-- Check success rate
SELECT
    status,
    COUNT(*) as count
FROM edge_function_runs
WHERE function_name = 'check-alerts'
  AND started_at >= NOW() - INTERVAL '7 days'
GROUP BY status;
```

### 4.2 Monitor Alert Delivery

```sql
-- Daily alert volume
SELECT
    DATE(notification_sent_at) as date,
    COUNT(*) as alerts_sent,
    COUNT(DISTINCT user_id) as unique_users
FROM alert_notifications
WHERE notification_sent_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(notification_sent_at)
ORDER BY date DESC;

-- Channel usage
SELECT
    channels_used,
    COUNT(*) as count
FROM alert_notifications
WHERE notification_sent_at >= NOW() - INTERVAL '7 days'
GROUP BY channels_used;

-- Top searches triggering alerts
SELECT
    ss.name,
    COUNT(an.id) as alert_count
FROM saved_searches ss
LEFT JOIN alert_notifications an ON ss.id = an.saved_search_id
WHERE an.notification_sent_at >= NOW() - INTERVAL '7 days'
GROUP BY ss.id, ss.name
ORDER BY alert_count DESC
LIMIT 10;
```

### 4.3 Monitor Chat Agent Usage

Add analytics tracking (optional):

```sql
-- Create analytics table
CREATE TABLE chat_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query_text TEXT,
    filters_parsed JSONB,
    results_count INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- View popular queries
SELECT
    query_text,
    COUNT(*) as query_count,
    AVG(results_count) as avg_results,
    AVG(response_time_ms) as avg_response_time
FROM chat_queries
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY query_text
ORDER BY query_count DESC
LIMIT 20;
```

---

## Part 5: Cost Optimization (Free Tier)

### 5.1 Database Storage (<500MB)

```sql
-- Check current database size
SELECT
    pg_size_pretty(pg_database_size(current_database())) as total_size;

-- Size by table
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.' || tablename) DESC;
```

**Optimization strategies:**
- Keep catalysts table <100k rows (trim old trials)
- Auto-delete alert_notifications >90 days
- Compress indication text (remove duplicates)

### 5.2 Edge Function Invocations (<2M/month)

**Current usage estimate:**
- Daily sync: 1/day × 30 days = 30 invocations
- Check alerts: 1/day × 30 days = 30 invocations
- Manual triggers: ~10/month
- **Total**: ~70/month (0.0035% of free tier limit)

### 5.3 SendGrid Email Limit (100/day)

**Projected usage:**
- 10 users × 3 saved searches × 0.5 new matches/day = 15 emails/day
- Well within free tier limit

**If exceeding:**
- Implement daily digest mode (batch alerts)
- Upgrade to SendGrid Essentials ($20/month for 50k emails)

---

## Part 6: Rollback Procedures

### 6.1 Rollback Edge Function

```bash
# List function versions
supabase functions list-versions check-alerts

# Rollback to previous version
supabase functions rollback check-alerts --version X
```

### 6.2 Rollback Database Migration

```bash
# Revert to previous migration
supabase db reset --version 20251224_initial_schema
```

### 6.3 Disable Alerts (Emergency)

```sql
-- Pause all saved searches
UPDATE saved_searches SET active = FALSE;

-- Disable cron job
SELECT cron.unschedule('check-alerts-daily');
```

---

## Success Criteria (Phase 4 Complete)

### Chat Agent
- [x] Code implemented (`src/agents/catalyst_agent.py`, `src/ui/chat_agent.py`, `src/pages/chat.py`)
- [ ] Deployed to Streamlit Cloud
- [ ] 80%+ query parsing success rate
- [ ] <500ms response time (90th percentile)
- [ ] Mobile-responsive UI
- [ ] Accessible via navigation menu

### Proactive Alerts
- [x] Database schema deployed (`saved_searches`, `alert_notifications`, `notification_preferences`)
- [x] Supabase Edge Function deployed (`check-alerts`)
- [ ] Cron job scheduled (daily at 9 AM ET)
- [ ] SendGrid integration working
- [ ] Email delivery rate >99%
- [ ] Alert deduplication working
- [ ] UI for managing saved searches deployed

### Production Readiness
- [ ] All tests passing
- [ ] Monitoring queries running
- [ ] Database size <100MB
- [ ] Edge Function invocations <1000/month
- [ ] Zero errors in last 7 days
- [ ] User documentation updated

---

## Next Steps (Post-Deployment)

1. **Week 1-2**: Monitor metrics, fix bugs
2. **Week 3-4**: Gather user feedback, optimize query parsing
3. **Month 2**: Add SMS/Slack for Pro tier
4. **Month 3**: Launch Reddit distribution campaign (Phase 4 marketing)

---

**Last Updated**: 2025-12-30
**Owner**: Dev Team
**Status**: Ready for Deployment
