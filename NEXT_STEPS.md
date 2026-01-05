# Next Steps - Phase 4 Deployment

**Date**: 2025-12-30
**Current Status**: 95% Complete - Code Ready for Deployment
**Estimated Time to Production**: 8-12 hours

---

## Quick Start (For Immediate Deployment)

### Step 1: Deploy Supabase (2-3 hours)

```bash
# 1. Login to Supabase
supabase login

# 2. Link to your project
supabase link --project-ref your-project-ref

# 3. Deploy database migrations
supabase db push

# 4. Deploy Edge Functions
supabase functions deploy daily-sync
supabase functions deploy check-alerts

# 5. Set environment secrets
supabase secrets set SENDGRID_API_KEY=your-key
supabase secrets set TWILIO_ACCOUNT_SID=your-sid
supabase secrets set TWILIO_AUTH_TOKEN=your-token
supabase secrets set TWILIO_FROM_NUMBER=+1234567890
```

Full instructions: `/Users/waiyang/Desktop/repo/um-biotech-catalyst-radar/docs/PHASE_4_DEPLOYMENT.md`

### Step 2: Deploy Streamlit Cloud (30 minutes)

```bash
# 1. Push code to GitHub
git add .
git commit -m "Phase 4: Add chat agent and proactive alerts"
git push origin main

# 2. Deploy via Streamlit Cloud Dashboard
# - Go to https://share.streamlit.io
# - Click "New app"
# - Select repository: um-biotech-catalyst-radar
# - Set main file: src/app.py
# - Add secrets:
#   SUPABASE_URL = "https://xxxxx.supabase.co"
#   SUPABASE_ANON_KEY = "your_anon_key"
```

### Step 3: Test End-to-End (4-6 hours)

Follow: `/Users/waiyang/Desktop/repo/um-biotech-catalyst-radar/docs/TESTING_GUIDE.md`

**Key tests:**
1. Chat agent queries (6 test cases)
2. Saved search creation
3. Alert notification delivery
4. Mobile responsiveness

---

## Critical Files for Deployment

### Configuration
- `.env` - Environment variables (local testing)
- `supabase/config.toml` - Supabase project configuration

### Database
- `supabase/migrations/20251224_initial_schema.sql` - Initial schema
- New tables needed:
  - `saved_searches`
  - `alert_notifications`
  - `notification_preferences`

### Edge Functions
- `supabase/functions/daily-sync/index.ts` - Daily catalyst sync
- `supabase/functions/check-alerts/index.ts` - Alert monitoring

### Frontend
- `src/app.py` - Main dashboard (updated with navigation)
- `src/pages/chat.py` - Chat agent page
- `src/pages/alerts.py` - Alert management page
- `src/agents/catalyst_agent.py` - Query parser
- `src/agents/alert_agent.py` - Alert monitoring logic

---

## Pre-Deployment Checklist

### Supabase
- [ ] Project created (free tier)
- [ ] Database password saved securely
- [ ] Project URL and keys copied
- [ ] SendGrid API key obtained
- [ ] Twilio credentials obtained (optional)

### GitHub
- [ ] Repository accessible
- [ ] Latest code pushed to main branch
- [ ] No sensitive data in repository (.env in .gitignore)

### Streamlit Cloud
- [ ] Account created
- [ ] GitHub repository connected
- [ ] Secrets configured

---

## Post-Deployment Verification

### 1. Verify Database

```sql
-- Check tables exist
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
-- Expected: catalysts, saved_searches, alert_notifications, notification_preferences

-- Check catalysts data
SELECT COUNT(*) FROM catalysts;
-- Expected: >0 (data from daily-sync)

-- Check Edge Function logs
SELECT * FROM edge_function_runs ORDER BY started_at DESC LIMIT 5;
-- Expected: Recent successful runs
```

### 2. Verify Edge Functions

```bash
# Test daily-sync
curl -X POST https://xxxxx.supabase.co/functions/v1/daily-sync \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Expected response:
# {"success": true, "trials_fetched": 150, ...}

# Test check-alerts
curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Expected response:
# {"success": true, "searches_checked": 0, ...}
```

### 3. Verify Streamlit App

1. Navigate to app URL
2. Check all pages load:
   - Dashboard (main page)
   - Chat (/pages/chat.py)
   - Alerts (/pages/alerts.py)
   - Subscribe (/pages/subscribe.py)
3. Test chat agent with example query
4. Test navigation between pages

---

## Monitoring After Deployment

### Daily Checks (First Week)

```sql
-- 1. Check Edge Function runs
SELECT
    function_name,
    DATE(started_at) as date,
    COUNT(*) as runs,
    COUNT(*) FILTER (WHERE status = 'success') as successes
FROM edge_function_runs
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY function_name, DATE(started_at)
ORDER BY date DESC;

-- 2. Check alert delivery
SELECT
    DATE(notification_sent_at) as date,
    COUNT(*) as alerts_sent,
    COUNT(DISTINCT user_id) as unique_users
FROM alert_notifications
WHERE notification_sent_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(notification_sent_at)
ORDER BY date DESC;

-- 3. Check database size
SELECT pg_size_pretty(pg_database_size(current_database()));
```

### Weekly Metrics

- Chat agent usage: # of queries per day
- Saved searches created: # per week
- Alert delivery rate: % of alerts sent successfully
- Database growth: MB per week
- Edge Function cost: Invocations per month
- SendGrid usage: Emails sent per day

---

## Troubleshooting Common Issues

### Issue: Chat agent not loading

**Symptoms**: Page shows error or blank
**Solution**:
1. Check Streamlit logs for import errors
2. Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` in secrets
3. Test database connection:
   ```python
   from src.utils.db import get_catalysts
   catalysts = get_catalysts(limit=5)
   ```

### Issue: Alerts not sending

**Symptoms**: No emails received after creating saved search
**Solution**:
1. Check cron job is scheduled:
   ```sql
   SELECT * FROM cron.job WHERE jobname = 'check-alerts-daily';
   ```
2. Manually trigger Edge Function:
   ```bash
   curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
     -H "Authorization: Bearer YOUR_ANON_KEY"
   ```
3. Check SendGrid Activity Feed for delivery status
4. Verify `SENDGRID_API_KEY` is set:
   ```bash
   supabase secrets list
   ```

### Issue: Database size growing too fast

**Symptoms**: Database >100 MB
**Solution**:
1. Check table sizes:
   ```sql
   SELECT tablename, pg_size_pretty(pg_total_relation_size('public.' || tablename))
   FROM pg_tables WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size('public.' || tablename) DESC;
   ```
2. Delete old catalysts:
   ```sql
   DELETE FROM catalysts WHERE completion_date < NOW() - INTERVAL '90 days';
   ```
3. Delete old alerts:
   ```sql
   DELETE FROM alert_notifications WHERE notification_sent_at < NOW() - INTERVAL '90 days';
   ```

---

## Rollback Plan

If critical issues are found after deployment:

### 1. Disable Alerts (Immediate)

```sql
-- Pause all saved searches
UPDATE saved_searches SET active = FALSE;

-- Disable cron job
SELECT cron.unschedule('check-alerts-daily');
```

### 2. Revert Streamlit App (5 minutes)

```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Streamlit Cloud will auto-redeploy
```

### 3. Rollback Database (30 minutes)

```sql
-- Drop new tables
DROP TABLE IF EXISTS alert_notifications;
DROP TABLE IF EXISTS saved_searches;
DROP TABLE IF EXISTS notification_preferences;
```

---

## Feature Flags (Optional)

To enable gradual rollout, add feature flags:

```python
# src/utils/config.py
ENABLE_CHAT_AGENT = os.getenv("ENABLE_CHAT_AGENT", "true").lower() == "true"
ENABLE_PROACTIVE_ALERTS = os.getenv("ENABLE_PROACTIVE_ALERTS", "true").lower() == "true"

# src/app.py
if ENABLE_CHAT_AGENT:
    # Show chat button in navigation
    if st.button("💬 Chat", ...):
        st.switch_page("pages/chat.py")
```

Set in Streamlit Cloud secrets:
```toml
ENABLE_CHAT_AGENT = "true"
ENABLE_PROACTIVE_ALERTS = "false"  # Start with alerts disabled
```

---

## Success Metrics (Week 1 Targets)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Chat queries** | 50+ | Count queries in session logs |
| **Query success rate** | >80% | Manual review of failed queries |
| **Response time** | <500ms | Performance testing |
| **Saved searches created** | 10+ | `SELECT COUNT(*) FROM saved_searches` |
| **Alerts sent** | 20+ | `SELECT COUNT(*) FROM alert_notifications` |
| **Email delivery rate** | >95% | SendGrid Activity Feed |
| **Database size** | <50 MB | `SELECT pg_database_size(current_database())` |
| **Zero downtime** | 100% | Streamlit Cloud uptime monitoring |

---

## Launch Communication

### Internal Team

**Email to Dev Team:**
```
Subject: Phase 4 Deployed - Chat Agent + Proactive Alerts Live

Team,

Phase 4 is now deployed to production:
- Chat agent: https://app.streamlit.io/chat
- Proactive alerts: https://app.streamlit.io/alerts

Please test and report any issues in #engineering-bugs Slack channel.

Key docs:
- Deployment guide: /docs/PHASE_4_DEPLOYMENT.md
- Testing guide: /docs/TESTING_GUIDE.md
- Status report: /PHASE_4_STATUS.md

Monitoring dashboard: [link to Supabase dashboard]

Thanks,
Dev Team Lead
```

### Beta Users (10-20 users)

**Email to Beta Users:**
```
Subject: New Feature: Chat with Biotech Catalyst Radar

Hi [Name],

We just launched two exciting features:

1. **Chat Agent**: Ask questions like "Phase 3 oncology under $2B" and get instant results
2. **Proactive Alerts**: Create saved searches and get notified when new catalysts match

Try it now: [app link]

We'd love your feedback! Reply to this email or fill out our 2-minute survey: [link]

Thanks for being an early supporter!

Best,
Biotech Catalyst Radar Team
```

### Reddit Post (r/Biotechplays)

**Title**: "I built a conversational AI to find biotech catalysts (free tool)"

**Post:**
```
Hey r/Biotechplays!

I built a free tool to track Phase 2/3 clinical trial catalysts for small-cap biotech stocks.

New feature: **Chat with the catalyst database** instead of manually filtering.

Examples:
- "Phase 3 oncology under $2B"
- "trials next 60 days"
- "neurology catalysts"

Also added **proactive alerts** - create a saved search and get notified when new matching catalysts appear.

Try it: [link]

Feedback welcome! This is 100% free and runs on open data from ClinicalTrials.gov.

[Screenshot of chat interface]
[GIF of creating a saved search]
```

---

## Timeline

### Week 1 (Jan 6-12, 2026)
- **Mon-Tue**: Deploy to Supabase + Streamlit Cloud
- **Wed-Thu**: End-to-end testing + bug fixes
- **Fri**: Invite 10 beta users
- **Sat-Sun**: Monitor usage, fix any issues

### Week 2 (Jan 13-19, 2026)
- **Mon**: Gather beta user feedback
- **Tue-Wed**: Implement quick fixes
- **Thu**: Prepare Reddit post (screenshot, GIF)
- **Fri**: Launch on r/Biotechplays (8 AM ET)
- **Sat-Sun**: Respond to comments, onboard new users

### Week 3 (Jan 20-26, 2026)
- **Daily**: Monitor metrics (signups, queries, alerts)
- **Mid-week**: Iterate based on user feedback
- **End-week**: Review success metrics

### Week 4 (Jan 27-Feb 2, 2026)
- **Assess**: Did we hit 80% query success rate? 40% saved search creation?
- **Plan**: Phase 5 features (API, SMS/Slack, advanced filters)
- **Document**: Case study for Reddit (results, learnings)

---

## Contact & Support

**Questions during deployment?**
- Supabase docs: https://supabase.com/docs
- Streamlit docs: https://docs.streamlit.io
- Project docs: `/Users/waiyang/Desktop/repo/um-biotech-catalyst-radar/docs/`

**Issues?**
- Create GitHub issue: [repository URL]
- Email: dev@biotechcatalyst.app (if configured)

**Monitoring:**
- Supabase dashboard: https://supabase.com/dashboard/project/[project-id]
- Streamlit logs: https://share.streamlit.io/[app-url]/logs
- SendGrid activity: https://app.sendgrid.com/email_activity

---

## Final Checklist

Before launching to public:

- [ ] All code deployed
- [ ] All tests passing
- [ ] Database populated with catalysts
- [ ] Edge Functions running on schedule
- [ ] SendGrid delivering emails
- [ ] Mobile responsive verified
- [ ] Beta users invited
- [ ] Monitoring dashboard set up
- [ ] Rollback plan documented
- [ ] Reddit post drafted
- [ ] Support email configured

**Ready to launch**: When all boxes checked ✅

---

**Last Updated**: 2025-12-30
**Next Review**: After Week 1 deployment
**Owner**: Dev Team Lead
