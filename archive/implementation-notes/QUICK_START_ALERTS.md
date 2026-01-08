# Alert Agent - Quick Start Guide

## For Developers

### 1. Deploy Database Migration
```bash
psql $DATABASE_URL -f supabase/migrations/20251224_alert_agent.sql
```

### 2. Deploy Edge Function
```bash
supabase functions deploy check-alerts
supabase secrets set SENDGRID_API_KEY=your-key
supabase secrets set TWILIO_ACCOUNT_SID=your-sid
supabase secrets set TWILIO_AUTH_TOKEN=your-token
supabase secrets set TWILIO_FROM_NUMBER=+12025551234
```

### 3. Schedule Cron Job
Via Supabase Dashboard > Database > Cron:
```sql
SELECT cron.schedule(
  'check-alerts-daily',
  '0 14 * * *',
  $$SELECT net.http_post(
    url := 'https://YOUR-PROJECT.supabase.co/functions/v1/check-alerts',
    headers := '{"Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb
  );$$
);
```

### 4. Test Locally
```bash
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-key
export SENDGRID_API_KEY=your-key

cd src/agents
python alert_agent.py
```

## For Users

### Create Your First Alert

1. Navigate to `/alerts` page
2. Click "New Search"
3. Fill out:
   - Name: "Oncology under $500M"
   - Phase: Phase 3
   - Therapeutic Area: oncology
   - Max Market Cap: $500M
   - Channels: Email (+ SMS/Slack if Pro)
4. Submit
5. You'll be notified daily at 9 AM ET when new matches appear

### Manage Alerts

- **Pause:** Temporarily stop notifications
- **Edit:** Change search criteria or channels
- **Test:** Preview matching catalysts
- **Delete:** Remove saved search

### Notification Settings

Go to Settings tab:
- Set quiet hours (no notifications during sleep)
- Set max alerts per day (prevent overload)
- Configure SMS/Slack (Pro tier only)

## Files Created

```
supabase/migrations/20251224_alert_agent.sql         - Database schema
supabase/functions/check-alerts/index.ts             - Edge Function
src/agents/alert_agent.py                            - Python agent
src/ui/saved_searches.py                             - UI component
src/pages/alerts.py                                  - Streamlit page
tests/test_alert_agent.py                            - Test suite
ALERT_AGENT_GUIDE.md                                 - Full documentation
ALERT_SYSTEM_SUMMARY.md                              - Implementation summary
```

## Support

See full documentation: `ALERT_AGENT_GUIDE.md`
