# Alert Agent System - Implementation Summary

## Overview

A complete proactive alert notification system has been implemented for the Biotech Catalyst Radar. The system monitors user-defined saved searches and automatically pushes notifications (email, SMS, Slack) when new catalysts matching their criteria are added.

## Files Created

### 1. Database Migration
**File:** `/home/user/um-biotech-catalyst-radar/supabase/migrations/20251224_alert_agent.sql`
- **Size:** ~15 KB
- **Tables Created:**
  - `saved_searches` - User-defined search filters with notification settings
  - `alert_notifications` - Log of sent alerts with deduplication
  - `notification_preferences` - User settings (rate limits, quiet hours, channels)
- **Functions Created:**
  - `can_receive_alert(user_id)` - Check daily rate limit
  - `is_quiet_hours(user_id)` - Check if within quiet hours
  - `get_user_tier(user_id)` - Returns user tier (free/trial/pro)
  - `delete_old_alert_notifications()` - Cleanup function
- **Features:**
  - Row Level Security (RLS) enabled on all tables
  - Automatic tier limit enforcement (3 searches for free/trial, unlimited for pro)
  - Unique constraint to prevent duplicate alerts
  - Indexed for performance

### 2. Python Alert Agent
**File:** `/home/user/um-biotech-catalyst-radar/src/agents/alert_agent.py`
- **Size:** ~25 KB
- **Class:** `AlertAgent`
- **Key Methods:**
  - `check_saved_searches()` - Main entry point, processes all active searches
  - `find_new_matches(query_params, last_checked)` - Query catalysts with filters
  - `send_notification(user_id, catalyst, channels)` - Multi-channel dispatch
  - `format_alert_message(catalyst, search_name)` - Format alert content
  - `_send_email()`, `_send_sms()`, `_send_slack()` - Channel-specific senders
- **Features:**
  - Deduplication logic
  - Rate limiting checks
  - Quiet hours validation
  - Tier-based channel restrictions
  - Retry logic and error handling

### 3. Supabase Edge Function
**File:** `/home/user/um-biotech-catalyst-radar/supabase/functions/check-alerts/index.ts`
- **Size:** ~19 KB
- **Purpose:** Serverless function for scheduled alert checking
- **Features:**
  - Runs daily at 9 AM ET (14:00 UTC) via cron
  - Fetches active saved searches
  - Queries catalysts for new matches
  - Sends notifications via SendGrid/Twilio/Slack
  - Updates last_checked timestamps
  - Logs execution to `edge_function_runs` table
  - Cleanup of old alert notifications

### 4. Saved Searches UI Component
**File:** `/home/user/um-biotech-catalyst-radar/src/ui/saved_searches.py`
- **Size:** ~16 KB
- **Function:** `render_saved_searches(user_id)`
- **Features:**
  - List view with search cards
  - Create/edit/delete modals
  - Test search functionality (preview results)
  - Pause/resume toggle
  - Match count display (last 7 days)
  - Notification channel icons (📧 📱 💬)
  - Tier limit display
  - Human-readable query parameters

### 5. Alerts Page (Streamlit)
**File:** `/home/user/um-biotech-catalyst-radar/src/pages/alerts.py`
- **Size:** ~12 KB
- **URL:** `/alerts`
- **Three Tabs:**
  1. **My Saved Searches** - Manage saved searches
  2. **Alert History** - View past notifications with acknowledgment
  3. **Settings** - Configure notification preferences
- **Features:**
  - Quick start wizard for first-time users
  - Tier-based feature display
  - Upgrade CTA for free/trial users
  - Alert acknowledgment (mark as read)
  - Summary metrics (total alerts, today, unread)

### 6. Documentation
**File:** `/home/user/um-biotech-catalyst-radar/ALERT_AGENT_GUIDE.md`
- **Size:** ~15 KB
- **Contents:**
  - Architecture diagram
  - Database schema details
  - Component descriptions
  - End-to-end alert flow
  - Deployment instructions
  - Testing guide
  - Troubleshooting
  - Security considerations

### 7. Test Suite
**File:** `/home/user/um-biotech-catalyst-radar/tests/test_alert_agent.py`
- **Size:** ~8 KB
- **Test Coverage:**
  - Alert message formatting
  - Search filtering logic
  - Deduplication detection
  - Email sending (mocked)
  - Tier retrieval
  - Integration tests (requires live Supabase)

## Database Schema

### Table: `saved_searches`
```sql
Columns:
- id (UUID, PK)
- user_id (UUID, FK → auth.users)
- name (TEXT) - e.g., "Oncology under $500M"
- query_params (JSONB) - Filter criteria
- notification_channels (TEXT[]) - ['email', 'sms', 'slack']
- last_checked (TIMESTAMPTZ)
- active (BOOLEAN)
- created_at, updated_at (TIMESTAMPTZ)

Indexes:
- idx_saved_searches_user_id
- idx_saved_searches_active (partial index where active = TRUE)

RLS Policies:
- Users can view/insert/update/delete own searches only
```

### Table: `alert_notifications`
```sql
Columns:
- id (UUID, PK)
- saved_search_id (UUID, FK → saved_searches)
- catalyst_id (UUID, FK → catalysts)
- user_id (UUID, FK → auth.users)
- notification_sent_at (TIMESTAMPTZ)
- channels_used (TEXT[])
- user_acknowledged (BOOLEAN)
- acknowledged_at (TIMESTAMPTZ)
- alert_content (JSONB) - Cached alert data

Indexes:
- idx_alert_notifications_search_id
- idx_alert_notifications_catalyst_id
- idx_alert_notifications_user_id
- idx_alert_notifications_sent_at
- UNIQUE idx_alert_notifications_dedup (saved_search_id, catalyst_id)

RLS Policies:
- Users can view own notifications
- Users can update own acknowledgments
```

### Table: `notification_preferences`
```sql
Columns:
- user_id (UUID, PK, FK → auth.users)
- max_alerts_per_day (INTEGER, default 10)
- quiet_hours_start, quiet_hours_end (TIME)
- user_timezone (TEXT, IANA timezone)
- email_enabled (BOOLEAN)
- sms_enabled (BOOLEAN, Pro only)
- slack_enabled (BOOLEAN, Pro only)
- phone_number (TEXT)
- slack_webhook_url (TEXT)
- created_at, updated_at (TIMESTAMPTZ)

RLS Policies:
- Users can view/update own preferences
```

## Alert Flow (End-to-End)

### 1. User Creates Saved Search
```
User → Streamlit UI (/alerts) → Supabase → saved_searches table
```

1. User navigates to `/alerts` page
2. Clicks "New Search" button
3. Fills out search form:
   - Name: "Oncology under $500M"
   - Phase: Phase 3
   - Therapeutic Area: oncology
   - Max Market Cap: $500M
   - Channels: Email + Slack (if Pro)
4. Form submits to Supabase
5. Insert triggers tier limit check:
   - Free/Trial: Max 3 searches
   - Pro: Unlimited
6. Search saved with `active = TRUE`

### 2. Daily Monitoring (Automated)
```
Cron (9 AM ET) → Edge Function → Query Catalysts → Send Notifications
```

**Every day at 9 AM ET (14:00 UTC):**

1. Supabase cron trigger fires
2. Edge Function `check-alerts` executes
3. Fetches all active saved searches: `SELECT * FROM saved_searches WHERE active = TRUE`
4. For each search:
   - Builds query with filters (phase, therapeutic_area, market_cap, etc.)
   - Adds filter: `created_at > last_checked` (only new catalysts)
   - Executes query against `catalysts` table
   - For each match:
     - Checks if already notified: `SELECT FROM alert_notifications WHERE saved_search_id = X AND catalyst_id = Y`
     - Checks rate limit: `can_receive_alert(user_id)` → counts alerts sent today
     - Checks quiet hours: `is_quiet_hours(user_id)` → checks user timezone
     - If all checks pass → send notification
5. Updates `last_checked` timestamp on search

### 3. Notification Dispatch
```
Edge Function → SendGrid/Twilio/Slack APIs → User receives alert
```

**For each catalyst match:**

1. **Format Alert:**
   - Ticker: BTCH
   - Phase: Phase 3
   - Catalyst Date: 2025-06-15
   - Days Until: 45 days
   - Market Cap: $2.50B
   - Current Price: $45.50
   - Indication: Oncology - Lung Cancer

2. **Get User Tier:**
   - `get_user_tier(user_id)` returns 'free', 'trial', or 'pro'

3. **Send via Channels:**
   - **Email (all tiers):**
     - SendGrid API
     - Formatted HTML email with catalyst details
     - Link to dashboard and ClinicalTrials.gov
   - **SMS (Pro only):**
     - Twilio API
     - 160-char message: "🚀 New Catalyst: BTCH (Phase 3) - 2025-06-15. View: https://biotechcatalyst.app"
     - Requires phone number in preferences
   - **Slack (Pro only):**
     - Webhook POST
     - Rich message with blocks (header, fields, buttons)
     - Requires webhook URL in preferences

4. **Log Notification:**
   - Insert into `alert_notifications` table
   - Includes: search_id, catalyst_id, user_id, channels_used, alert_content
   - Unique constraint prevents duplicates

### 4. User Receives & Acknowledges
```
Email/SMS/Slack → User → Streamlit UI → Mark as Read
```

1. User receives notification via chosen channel(s)
2. Opens email/SMS/Slack and sees alert details
3. Clicks link to view full details
4. Navigates to `/alerts` → "Alert History" tab
5. Sees list of notifications:
   - Unread: 🔔 icon
   - Read: ✅ icon
6. Clicks "Mark as Read" button
7. Updates: `user_acknowledged = TRUE, acknowledged_at = NOW()`

## Tier-Based Features

| Feature | Free Tier | Trial Tier | Pro Tier |
|---------|-----------|------------|----------|
| **Saved Searches** | 3 max | 3 max | Unlimited |
| **Email Alerts** | ✅ Yes | ✅ Yes | ✅ Yes |
| **SMS Alerts** | ❌ No | ❌ No | ✅ Yes |
| **Slack Alerts** | ❌ No | ❌ No | ✅ Yes |
| **Max Alerts/Day** | 10 | 10 | 50 (configurable) |
| **Quiet Hours** | ✅ Yes | ✅ Yes | ✅ Yes |

**Enforcement:**
- Tier limits enforced by trigger on `saved_searches` table
- Channel restrictions enforced in Edge Function (checks user tier before sending)
- Rate limits enforced by `can_receive_alert()` function

## Deployment Checklist

### 1. Database Setup
```bash
# Run migration
psql $DATABASE_URL -f supabase/migrations/20251224_alert_agent.sql

# Verify tables created
psql $DATABASE_URL -c "\dt+ saved_searches alert_notifications notification_preferences"

# Test functions
psql $DATABASE_URL -c "SELECT get_user_tier('USER_UUID_HERE')"
```

### 2. Edge Function Deployment
```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref your-project-ref

# Deploy function
supabase functions deploy check-alerts

# Set secrets
supabase secrets set SENDGRID_API_KEY=SG.your-key
supabase secrets set TWILIO_ACCOUNT_SID=ACyour-sid
supabase secrets set TWILIO_AUTH_TOKEN=your-token
supabase secrets set TWILIO_FROM_NUMBER=+12025551234
```

### 3. Schedule Cron Job
```sql
-- Via Supabase Dashboard > Database > Cron
SELECT cron.schedule(
  'check-alerts-daily',
  '0 14 * * *', -- 9 AM ET = 14:00 UTC
  $$
  SELECT net.http_post(
    url := 'https://YOUR-PROJECT.supabase.co/functions/v1/check-alerts',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
  );
  $$
);
```

### 4. Environment Variables (Python Agent)
```bash
# For local testing
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
export SENDGRID_API_KEY=SG.your-key
export TWILIO_ACCOUNT_SID=ACyour-sid
export TWILIO_AUTH_TOKEN=your-token
export TWILIO_FROM_NUMBER=+12025551234
```

### 5. Test End-to-End
```bash
# Create test user and saved search (via SQL or UI)

# Manually trigger Edge Function
curl -X POST https://YOUR-PROJECT.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Check logs
psql $DATABASE_URL -c "SELECT * FROM edge_function_runs WHERE function_name = 'check-alerts' ORDER BY started_at DESC LIMIT 1"

# Verify alert sent
psql $DATABASE_URL -c "SELECT * FROM alert_notifications ORDER BY notification_sent_at DESC LIMIT 5"
```

## Testing with Mock Data

### Create Test User (via Supabase Auth)
```sql
-- After user signs up via Supabase Auth, get their UUID
SELECT id, email FROM auth.users WHERE email = 'test@example.com';
-- Copy the UUID
```

### Create Test Saved Search
```sql
INSERT INTO saved_searches (
  user_id,
  name,
  query_params,
  notification_channels,
  active
) VALUES (
  'USER_UUID_HERE',
  'Test Search - Oncology Phase 3',
  '{
    "phase": "Phase 3",
    "therapeutic_area": "oncology",
    "max_market_cap": 5000000000
  }'::jsonb,
  ARRAY['email']::TEXT[],
  TRUE
);
```

### Create Test Catalyst
```sql
INSERT INTO catalysts (
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
  current_price
) VALUES (
  'NCT99999999',
  'Test Biotech Inc.',
  'TBTC',
  95,
  'Phase 3',
  'Oncology - Lung Cancer',
  '2025-06-15',
  450,
  'Interventional',
  2500000000,
  45.50
);
```

### Trigger Alert Check
```bash
# Via Edge Function
curl -X POST https://YOUR-PROJECT.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Or via Python Agent
cd src/agents
python alert_agent.py
```

### Verify Alert Sent
```sql
-- Check alert notifications
SELECT
  an.id,
  ss.name AS search_name,
  c.ticker,
  an.channels_used,
  an.notification_sent_at
FROM alert_notifications an
JOIN saved_searches ss ON an.saved_search_id = ss.id
JOIN catalysts c ON an.catalyst_id = c.id
ORDER BY an.notification_sent_at DESC
LIMIT 5;
```

## Monitoring & Analytics

### View Alert Statistics
```sql
-- Alerts sent per user (last 30 days)
SELECT
  u.email,
  COUNT(an.id) AS total_alerts,
  COUNT(an.id) FILTER (WHERE an.user_acknowledged = FALSE) AS unread_alerts
FROM users u
LEFT JOIN alert_notifications an ON u.id = an.user_id
WHERE an.notification_sent_at >= NOW() - INTERVAL '30 days'
GROUP BY u.id, u.email
ORDER BY total_alerts DESC;

-- Most active saved searches
SELECT
  ss.name,
  COUNT(an.id) AS alert_count,
  COUNT(DISTINCT an.catalyst_id) AS unique_catalysts
FROM saved_searches ss
LEFT JOIN alert_notifications an ON ss.id = an.saved_search_id
WHERE an.notification_sent_at >= NOW() - INTERVAL '30 days'
GROUP BY ss.id, ss.name
ORDER BY alert_count DESC
LIMIT 10;

-- Edge Function execution history
SELECT
  function_name,
  started_at,
  completed_at,
  items_processed,
  status,
  error_message
FROM edge_function_runs
WHERE function_name = 'check-alerts'
ORDER BY started_at DESC
LIMIT 10;
```

## Security & Privacy

### Row Level Security (RLS)
- **Enabled on all tables**: Users can only access their own data
- **Service role bypass**: Edge Functions use service_role key to access all data
- **No direct user access**: Users cannot query other users' saved searches or alerts

### API Key Security
- **Supabase secrets**: All API keys stored as encrypted secrets
- **No client exposure**: API keys never sent to frontend
- **Environment variables**: Use `.env` files locally, never commit to git

### Rate Limiting
- **Per-user limits**: Default 10 alerts/day, configurable up to 50
- **Prevents abuse**: Protects against runaway notifications
- **Quiet hours**: Respects user sleep schedules

### Data Cleanup
- **90-day retention**: Alert notifications auto-deleted after 90 days
- **Saves storage**: Keeps database under free tier limits
- **GDPR compliance**: User can delete account and all related data cascades

## Troubleshooting

### No Alerts Received

**Check these in order:**

1. **Saved search active?**
   ```sql
   SELECT * FROM saved_searches WHERE user_id = 'USER_ID';
   ```

2. **Rate limit exceeded?**
   ```sql
   SELECT can_receive_alert('USER_ID');
   -- Should return TRUE
   ```

3. **Quiet hours?**
   ```sql
   SELECT is_quiet_hours('USER_ID');
   -- Should return FALSE
   ```

4. **Edge Function running?**
   ```sql
   SELECT * FROM edge_function_runs WHERE function_name = 'check-alerts' ORDER BY started_at DESC LIMIT 1;
   -- Check status = 'success'
   ```

5. **New catalysts matching criteria?**
   ```sql
   SELECT * FROM catalysts
   WHERE created_at > (SELECT last_checked FROM saved_searches WHERE id = 'SEARCH_ID')
   -- Should return rows
   ```

### Duplicate Alerts

- **Should not happen**: Unique index prevents duplicates
- **If it does**: Check Edge Function logs for errors
- **Fix**: Delete duplicates manually:
  ```sql
  DELETE FROM alert_notifications a
  USING alert_notifications b
  WHERE a.id > b.id
  AND a.saved_search_id = b.saved_search_id
  AND a.catalyst_id = b.catalyst_id;
  ```

### Email Not Sending

1. **SendGrid API key valid?** Check in Supabase secrets
2. **Sender email verified?** Verify in SendGrid dashboard
3. **User email exists?** Check `users` table
4. **Check Edge Function logs** for SendGrid API errors

## Next Steps

1. **Deploy to production**: Follow deployment checklist above
2. **Test with real users**: Create 2-3 test accounts with different tiers
3. **Monitor for 1 week**: Check Edge Function logs daily
4. **Adjust settings**: Tune rate limits, quiet hours based on feedback
5. **Add analytics**: Track alert open rates, click-through rates
6. **Consider enhancements**:
   - Push notifications (web push API)
   - Digest mode (daily/weekly summary instead of real-time)
   - Alert preview before saving search
   - Custom alert templates

## Support & Documentation

- **Full Guide:** `/home/user/um-biotech-catalyst-radar/ALERT_AGENT_GUIDE.md`
- **Test Suite:** `/home/user/um-biotech-catalyst-radar/tests/test_alert_agent.py`
- **API Docs:** See function docstrings in `src/agents/alert_agent.py`
- **Database Schema:** See migration file comments

---

**Implementation Status:** ✅ Complete and ready for deployment

All components have been implemented, tested, and documented. The system is production-ready pending deployment of the Edge Function and database migration.
