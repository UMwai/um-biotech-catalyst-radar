# Alert Agent System - Implementation Guide

## Overview

The Alert Agent is a proactive notification system that monitors saved searches and automatically alerts users when new catalysts matching their criteria are added to the database.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Alert Agent System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Supabase   │    │ Edge Function │    │ Notification │  │
│  │   Database   │◄───│ check-alerts  │───►│   Services   │  │
│  │              │    │  (Daily Cron) │    │ Email/SMS/   │  │
│  │ saved_       │    └──────────────┘    │  Slack       │  │
│  │ searches     │                         └──────────────┘  │
│  │              │                                            │
│  │ alert_       │    ┌──────────────┐                       │
│  │ notifications│◄───│ Python Agent │                       │
│  │              │    │ AlertAgent   │                       │
│  │ notification_│    └──────────────┘                       │
│  │ preferences  │                                            │
│  └──────────────┘    ┌──────────────┐                       │
│                      │ Streamlit UI │                       │
│                      │ /alerts      │                       │
│                      └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Tables Created

#### 1. `saved_searches`
Stores user-defined search criteria with notification settings.

```sql
- id: UUID (primary key)
- user_id: UUID (references auth.users)
- name: TEXT (user-friendly name)
- query_params: JSONB (filter criteria)
- notification_channels: TEXT[] (email, sms, slack)
- last_checked: TIMESTAMPTZ
- active: BOOLEAN
- created_at, updated_at: TIMESTAMPTZ
```

**Query Parameters Format:**
```json
{
  "phase": "Phase 3",
  "therapeutic_area": "oncology",
  "max_market_cap": 5000000000,
  "min_market_cap": 500000000,
  "min_enrollment": 100,
  "completion_date_start": "2025-01-01",
  "completion_date_end": "2025-12-31"
}
```

#### 2. `alert_notifications`
Log of sent notifications with deduplication.

```sql
- id: UUID (primary key)
- saved_search_id: UUID (references saved_searches)
- catalyst_id: UUID (references catalysts)
- user_id: UUID (references auth.users)
- notification_sent_at: TIMESTAMPTZ
- channels_used: TEXT[]
- user_acknowledged: BOOLEAN
- acknowledged_at: TIMESTAMPTZ
- alert_content: JSONB (cached alert data)
```

**Unique constraint:** `(saved_search_id, catalyst_id)` - prevents duplicate alerts

#### 3. `notification_preferences`
User notification settings and rate limits.

```sql
- user_id: UUID (primary key)
- max_alerts_per_day: INTEGER (default 10)
- quiet_hours_start, quiet_hours_end: TIME
- user_timezone: TEXT (IANA timezone)
- email_enabled: BOOLEAN
- sms_enabled: BOOLEAN (Pro tier only)
- slack_enabled: BOOLEAN (Pro tier only)
- phone_number: TEXT
- slack_webhook_url: TEXT
```

## Components

### 1. Database Migration

**File:** `supabase/migrations/20251224_alert_agent.sql`

Creates all tables, indexes, RLS policies, and helper functions.

**Key Functions:**
- `can_receive_alert(user_id)`: Check daily rate limit
- `is_quiet_hours(user_id)`: Check if within quiet hours
- `get_user_tier(user_id)`: Returns 'free', 'trial', or 'pro'
- `check_saved_search_limit()`: Trigger to enforce tier limits (3 for free/trial, unlimited for pro)

**Deploy:**
```bash
psql $DATABASE_URL -f supabase/migrations/20251224_alert_agent.sql
```

### 2. Python Alert Agent

**File:** `src/agents/alert_agent.py`

Main monitoring agent with notification logic.

**Key Methods:**
- `check_saved_searches()`: Main entry point, processes all active searches
- `find_new_matches(query_params, last_checked)`: Query catalysts matching criteria
- `send_notification(user_id, catalyst, channels)`: Multi-channel notification dispatch
- `format_alert_message(catalyst, search_name)`: Format alert content

**Usage:**
```python
from src.agents import AlertAgent

agent = AlertAgent()
results = agent.check_saved_searches()
print(f"Sent {results['notifications_sent']} notifications")
```

**Environment Variables Required:**
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Email (required)
SENDGRID_API_KEY=SG.xxx

# SMS (Pro tier, optional)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_FROM_NUMBER=+12025551234

# Slack (Pro tier, optional - webhook set per-user)
```

### 3. Supabase Edge Function

**File:** `supabase/functions/check-alerts/index.ts`

Serverless function that runs on a schedule to check alerts.

**Deploy:**
```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Deploy function
supabase functions deploy check-alerts

# Set secrets
supabase secrets set SENDGRID_API_KEY=your-key
supabase secrets set TWILIO_ACCOUNT_SID=your-sid
supabase secrets set TWILIO_AUTH_TOKEN=your-token
supabase secrets set TWILIO_FROM_NUMBER=+1234567890
```

**Schedule (Cron):**
```sql
-- Run daily at 9 AM ET (14:00 UTC)
SELECT cron.schedule(
  'check-alerts-daily',
  '0 14 * * *',
  $$
  SELECT net.http_post(
    url := 'https://your-project.supabase.co/functions/v1/check-alerts',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
  );
  $$
);
```

**Test Manually:**
```bash
curl -X POST https://your-project.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### 4. Streamlit UI Components

#### Saved Searches Management
**File:** `src/ui/saved_searches.py`

- List view with search cards
- Create/edit/delete modals
- Test search functionality
- Pause/resume toggle
- Match count display

#### Alerts Page
**File:** `src/pages/alerts.py`

Three tabs:
1. **My Saved Searches** - Manage saved searches
2. **Alert History** - View past notifications
3. **Settings** - Configure notification preferences

**Access:**
```
https://your-app.streamlit.app/alerts
```

## Alert Flow (End-to-End)

### 1. User Creates Saved Search

```
User → Streamlit UI → Supabase
```

1. User navigates to `/alerts` page
2. Clicks "New Search"
3. Fills out search criteria:
   - Name: "Oncology under $500M"
   - Phase: Phase 3
   - Therapeutic Area: oncology
   - Max Market Cap: $500M
   - Channels: Email + Slack (if Pro)
4. Submits form
5. Supabase inserts row into `saved_searches` table
6. Trigger checks user tier limit (3 for free, unlimited for pro)

### 2. Daily Monitoring (Scheduled)

```
Cron Trigger → Edge Function → Supabase
```

1. **9 AM ET daily**, cron trigger fires
2. Edge Function `check-alerts` executes
3. Fetches all active saved searches from database
4. For each search:
   - Queries `catalysts` table with search filters
   - Filters by `created_at > last_checked` (only new catalysts)
   - Checks for duplicates in `alert_notifications`
   - Checks user rate limits (`can_receive_alert()`)
   - Checks quiet hours (`is_quiet_hours()`)

### 3. Notification Dispatch

```
Edge Function → SendGrid/Twilio/Slack → User
```

For each new match:

1. **Format alert message** with catalyst details
2. **Get user tier** to determine allowed channels
3. **Send via each channel:**
   - **Email** (all tiers): SendGrid API
   - **SMS** (Pro only): Twilio API
   - **Slack** (Pro only): Webhook POST
4. **Log notification** to `alert_notifications` table
5. **Update** `last_checked` timestamp on saved search

### 4. User Receives & Acknowledges

```
Email/SMS/Slack → User → Streamlit UI
```

1. User receives notification via chosen channel(s)
2. Clicks link to view details
3. Navigates to `/alerts` → "Alert History" tab
4. Sees unread notifications (🔔 icon)
5. Clicks "Mark as Read" to acknowledge
6. Notification updates: `user_acknowledged = TRUE`

## Tier Restrictions

| Feature | Free Tier | Trial Tier | Pro Tier |
|---------|-----------|------------|----------|
| Saved Searches | 3 | 3 | Unlimited |
| Email Alerts | ✅ | ✅ | ✅ |
| SMS Alerts | ❌ | ❌ | ✅ |
| Slack Alerts | ❌ | ❌ | ✅ |
| Max Alerts/Day | 10 | 10 | 50 |

## Testing

### Create Test User & Search

```sql
-- Create test user (via Supabase Auth)
-- Get user_id from auth.users table

-- Insert test saved search
INSERT INTO saved_searches (user_id, name, query_params, notification_channels, active)
VALUES (
  'USER_UUID_HERE',
  'Test Search - Oncology',
  '{"phase": "Phase 3", "therapeutic_area": "oncology", "max_market_cap": 5000000000}'::jsonb,
  ARRAY['email']::TEXT[],
  TRUE
);

-- Insert test catalyst (if needed)
INSERT INTO catalysts (nct_id, sponsor, ticker, phase, indication, completion_date, market_cap, current_price, ticker_confidence)
VALUES (
  'NCT99999999',
  'Test Pharma Inc.',
  'TPHR',
  'Phase 3',
  'Oncology - Lung Cancer',
  '2025-06-01',
  2500000000,
  45.50,
  95
);
```

### Test Alert Agent Locally

```bash
# Set environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-key
export SENDGRID_API_KEY=your-key

# Run agent
cd src/agents
python alert_agent.py
```

Expected output:
```json
{
  "searches_checked": 1,
  "matches_found": 1,
  "notifications_sent": 1,
  "errors": 0
}
```

### Test Edge Function

```bash
# Deploy
supabase functions deploy check-alerts

# Test
curl -X POST https://your-project.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json"
```

## Monitoring & Logs

### View Function Execution Logs

```sql
SELECT * FROM edge_function_runs
WHERE function_name = 'check-alerts'
ORDER BY started_at DESC
LIMIT 10;
```

### View Alert Statistics

```sql
-- Alerts sent per user in last 30 days
SELECT user_id, COUNT(*) as alert_count
FROM alert_notifications
WHERE notification_sent_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id
ORDER BY alert_count DESC;

-- Most active saved searches
SELECT ss.name, COUNT(an.id) as alert_count
FROM saved_searches ss
LEFT JOIN alert_notifications an ON ss.id = an.saved_search_id
WHERE an.notification_sent_at >= NOW() - INTERVAL '30 days'
GROUP BY ss.id, ss.name
ORDER BY alert_count DESC;
```

### View User Alert Summary

```sql
SELECT * FROM user_alert_summary
WHERE user_id = 'USER_UUID_HERE';
```

## Error Handling

### Rate Limiting
- Users cannot receive more than `max_alerts_per_day` (default: 10)
- Checked via `can_receive_alert()` function before sending
- Resets daily at midnight UTC

### Quiet Hours
- No notifications sent during user's quiet hours
- Timezone-aware (converts UTC to user timezone)
- Checked via `is_quiet_hours()` function

### Deduplication
- Unique index on `(saved_search_id, catalyst_id)` prevents duplicates
- Edge Function checks for existing notification before sending

### Retry Logic
- Edge Function continues processing other searches if one fails
- Errors logged to `edge_function_runs` table
- Status: 'success', 'partial' (some errors), or 'failed'

## Cleanup & Maintenance

### Automatic Cleanup (Built-in)

```sql
-- Delete old alert notifications (>90 days)
SELECT delete_old_alert_notifications();

-- Scheduled via Edge Function daily
```

### Manual Cleanup

```sql
-- Delete inactive searches (not checked in 90 days)
DELETE FROM saved_searches
WHERE active = FALSE
AND last_checked < NOW() - INTERVAL '90 days';

-- Archive old notifications
-- (Consider moving to cold storage instead of deleting)
```

## Security Considerations

1. **Row Level Security (RLS)**: All tables have RLS enabled
   - Users can only see their own saved searches
   - Users can only see their own alert notifications
   - Users can only update their own preferences

2. **API Keys**: Stored as Supabase secrets, never exposed to client
   - SendGrid API key
   - Twilio credentials
   - Service role key (Edge Function only)

3. **Rate Limiting**: Prevents abuse
   - Max searches per tier (3 for free, unlimited for pro)
   - Max alerts per day (configurable, default 10)

4. **Input Validation**: All user inputs sanitized
   - Query params validated before execution
   - Phone numbers validated for E.164 format
   - Webhook URLs validated for HTTPS

## Troubleshooting

### No alerts received

1. Check saved search is **active**: `SELECT * FROM saved_searches WHERE id = 'SEARCH_ID'`
2. Check rate limit not exceeded: `SELECT can_receive_alert('USER_ID')`
3. Check not in quiet hours: `SELECT is_quiet_hours('USER_ID')`
4. Check Edge Function logs: `SELECT * FROM edge_function_runs WHERE function_name = 'check-alerts'`
5. Check notification preferences: `SELECT * FROM notification_preferences WHERE user_id = 'USER_ID'`

### Duplicate alerts

- Should be prevented by unique index on `(saved_search_id, catalyst_id)`
- If duplicates occur, check Edge Function execution logs for errors

### Email not sending

1. Check SendGrid API key is valid
2. Check SendGrid sender email is verified
3. Check user email exists in `users` table
4. Check Edge Function logs for SendGrid API errors

### SMS not sending (Pro tier)

1. Check Twilio credentials are valid
2. Check user has phone number in `notification_preferences`
3. Check phone number is in E.164 format (+1234567890)
4. Check Twilio account has sufficient balance

## Future Enhancements

- [ ] Push notifications (web push API)
- [ ] Discord/Telegram integration
- [ ] Custom alert templates
- [ ] Digest mode (daily/weekly summary)
- [ ] Alert preview/testing before saving
- [ ] Smart scheduling (optimal time based on user activity)
- [ ] Alert analytics dashboard
- [ ] Export alert history to CSV
- [ ] Webhook callbacks for custom integrations
- [ ] Machine learning for alert relevance scoring

## Support

For issues or questions:
- Check logs: `edge_function_runs`, `analytics_events`
- Review RLS policies: Ensure user has proper permissions
- Test locally: Use Python agent for debugging
- Contact support: support@biotechcatalyst.app
