# Feature Spec: Proactive Alert Agent (Pro Tier)

## Overview

Implement an autonomous agent that monitors saved searches and proactively sends alerts when new catalysts match user criteria or when important events occur (completion dates approaching, significant price movements). This feature transforms the platform from a "pull" model (user checks dashboard) to a "push" model (agent notifies user).

**Strategic Value**:
- **Retention**: Users stay subscribed because alerts provide ongoing value
- **Premium differentiation**: Pro tier exclusive feature (justifies higher pricing)
- **Competitive moat**: BioPharmCatalyst has basic email alerts but not intelligent monitoring
- **Reduced churn**: Users won't cancel if they rely on alerts for trading

**Target Metrics**:
- <5 minute latency from catalyst appearance → alert sent
- <1% false positive rate
- 40%+ of Pro users create at least one saved search
- 20% reduction in Pro tier churn

---

## User Stories

### As a Pro subscriber
- **I want to** save a search like "Phase 3 oncology under $2B"
- **So that** I'm automatically notified when new matching catalysts appear
- **Acceptance**: I can click "Save this search" → Receive email when match appears

### As a day trader (Pro)
- **I want to** get SMS alerts 7 days before catalyst completion
- **So that** I can prepare my trades without manually checking
- **Acceptance**: Receive SMS "SBIO catalyst in 7 days" with link to dashboard

### As a swing trader (Pro)
- **I want to** be notified when a catalyst's stock price moves >10% in a day
- **So that** I can reassess my position before the catalyst
- **Acceptance**: Email + SMS when price spikes, with chart link

### As a mobile-first user
- **I want to** integrate alerts with Slack
- **So that** I see notifications in my workflow without email clutter
- **Acceptance**: Connect Slack → Receive alerts in #biotech-radar channel

---

## Requirements

### Functional Requirements

1. **Saved Searches**
   - User creates search with filters (phase, area, market cap, etc.)
   - Give it a custom name: "My Oncology Watchlist"
   - Choose alert frequency: Real-time, Daily digest, Weekly summary
   - Toggle active/inactive without deleting

2. **Alert Types**

   **Type 1: New Catalyst Match**
   - Agent runs saved search daily at 6 AM ET
   - Compares results to previous day
   - If new catalysts appear → Send alert
   - Include: Catalyst name, ticker, completion date, why it matched

   **Type 2: Completion Date Approaching**
   - Agent checks all user's watched catalysts
   - Triggers:
     - 30 days before completion
     - 7 days before completion
     - 1 day before completion
   - Include: Countdown, historical success rate, action items

   **Type 3: Price Movement**
   - Agent monitors stock prices for watched catalysts
   - Triggers:
     - >10% intraday move
     - >20% weekly move
     - New 52-week high/low
   - Include: Price chart, % change, market context

   **Type 4: Trial Status Update**
   - Agent scrapes ClinicalTrials.gov for updates
   - Triggers:
     - Completion date changed
     - Enrollment status changed
     - Results posted
   - Include: Old vs. new values, analyst implications

3. **Notification Channels**

   **Starter Tier ($29/mo)**:
   - Email only
   - Daily digest format (batched alerts)

   **Pro Tier ($49/mo)**:
   - Email (real-time + digest)
   - SMS (real-time only, urgent alerts)
   - Slack integration
   - User chooses per-alert-type channel

4. **Alert Management Dashboard**
   - View all saved searches
   - Edit search criteria
   - Change notification settings
   - Pause alerts (e.g., on vacation)
   - Alert history: Last 30 days of sent alerts

5. **Smart Deduplication**
   - Don't send duplicate alerts for same catalyst
   - If catalyst matches multiple saved searches → Send one combined alert
   - Don't alert on minor price fluctuations (<10%)

---

### Non-Functional Requirements

- **Latency**: <5 minutes from catalyst update → alert sent
- **Reliability**: 99.5% alert delivery rate (measured over 30 days)
- **Accuracy**: <1% false positive rate
- **Scalability**: Support 1,000 Pro users × 5 saved searches = 5,000 monitors
- **Cost**: <$0.50/user/month for infrastructure

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Cron Job (6 AM ET)                 │
│                                                              │
│  1. Fetch latest catalysts from database                    │
│  2. For each active saved_search:                           │
│     - Execute search query                                  │
│     - Compare to previous results (stored in last_results)  │
│     - If new matches → Queue alert                          │
│  3. Send queued alerts via notification service             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Supabase Edge Function (Deno)                  │
│                                                              │
│  - Trigger: Scheduled (cron) + manual webhook               │
│  - Logic: Query catalysts, compare results, send alerts     │
│  - Notifications: SendGrid (email), Twilio (SMS), Slack API │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Notification Services                    │
│                                                              │
│  SendGrid          Twilio            Slack Webhook          │
│  (Email)           (SMS)             (Slack messages)       │
└─────────────────────────────────────────────────────────────┘
```

---

### Database Schema

**New Table: saved_searches**

```sql
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,

    -- Search criteria (JSON)
    filters JSONB NOT NULL,  -- {phase: ["3"], therapeutic_area: ["oncology"], ...}

    -- Alert settings
    alert_frequency VARCHAR(20) DEFAULT 'realtime',  -- realtime, daily, weekly
    channels JSONB DEFAULT '["email"]',  -- ["email", "sms", "slack"]

    -- State tracking
    active BOOLEAN DEFAULT TRUE,
    last_checked_at TIMESTAMP,
    last_results JSONB,  -- Array of NCT IDs from last run

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saved_searches_user ON saved_searches(user_id);
CREATE INDEX idx_saved_searches_active ON saved_searches(active) WHERE active = TRUE;
```

**New Table: alert_history**

```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    saved_search_id UUID REFERENCES saved_searches(id) ON DELETE SET NULL,

    -- Alert details
    alert_type VARCHAR(50) NOT NULL,  -- new_match, completion_soon, price_move, status_change
    catalyst_nct_id VARCHAR(20) REFERENCES catalysts(nct_id),

    -- Notification
    channels_sent JSONB,  -- ["email", "sms"]
    delivery_status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed

    -- Content
    subject TEXT,
    message TEXT,

    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alert_history_user ON alert_history(user_id);
CREATE INDEX idx_alert_history_catalyst ON alert_history(catalyst_nct_id);
```

**Update: users table**

```sql
ALTER TABLE users ADD COLUMN notification_preferences JSONB DEFAULT '{
    "email": true,
    "sms": false,
    "slack": false,
    "phone_number": null,
    "slack_webhook_url": null
}';
```

---

### Supabase Edge Function

**File**: `supabase/functions/check-alerts/index.ts`

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

interface SavedSearch {
  id: string
  user_id: string
  name: string
  filters: Record<string, any>
  alert_frequency: string
  channels: string[]
  last_results: string[]
}

interface Catalyst {
  nct_id: string
  title: string
  ticker: string
  sponsor: string
  completion_date: string
  days_until_completion: number
}

serve(async (req) => {
  const supabaseClient = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
  )

  try {
    // 1. Fetch all active saved searches
    const { data: searches, error: searchError } = await supabaseClient
      .from('saved_searches')
      .select('*')
      .eq('active', true)

    if (searchError) throw searchError

    console.log(`Checking ${searches?.length} saved searches...`)

    // 2. For each search, execute and compare
    for (const search of searches || []) {
      await checkSavedSearch(supabaseClient, search)
    }

    return new Response(
      JSON.stringify({ success: true, checked: searches?.length }),
      { headers: { "Content-Type": "application/json" } }
    )

  } catch (error) {
    console.error('Error checking alerts:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    )
  }
})

async function checkSavedSearch(client: any, search: SavedSearch) {
  // 1. Build query from filters
  let query = client.from('catalysts').select('*')

  if (search.filters.phase) {
    query = query.in('phase', search.filters.phase)
  }
  if (search.filters.therapeutic_area) {
    query = query.in('therapeutic_area', search.filters.therapeutic_area)
  }
  if (search.filters.market_cap_max) {
    query = query.lte('market_cap', search.filters.market_cap_max)
  }
  if (search.filters.completion_days_max) {
    query = query.lte('days_until_completion', search.filters.completion_days_max)
  }

  const { data: catalysts, error } = await query

  if (error) {
    console.error(`Error querying catalysts for search ${search.id}:`, error)
    return
  }

  // 2. Compare to previous results
  const currentNctIds = catalysts?.map((c: Catalyst) => c.nct_id) || []
  const previousNctIds = search.last_results || []

  const newCatalysts = catalysts?.filter(
    (c: Catalyst) => !previousNctIds.includes(c.nct_id)
  ) || []

  // 3. If new matches, send alert
  if (newCatalysts.length > 0) {
    console.log(`Found ${newCatalysts.length} new catalysts for search "${search.name}"`)

    await sendAlert(client, {
      userId: search.user_id,
      savedSearchId: search.id,
      searchName: search.name,
      catalysts: newCatalysts,
      channels: search.channels
    })
  }

  // 4. Update last_results and last_checked_at
  await client
    .from('saved_searches')
    .update({
      last_results: currentNctIds,
      last_checked_at: new Date().toISOString()
    })
    .eq('id', search.id)
}

async function sendAlert(client: any, params: any) {
  const { userId, savedSearchId, searchName, catalysts, channels } = params

  // Fetch user's notification preferences
  const { data: user } = await client
    .from('users')
    .select('email, notification_preferences')
    .eq('id', userId)
    .single()

  if (!user) return

  // Build alert message
  const subject = `New catalysts match "${searchName}"`
  const message = `
    Found ${catalysts.length} new catalyst(s) matching your saved search:

    ${catalysts.map((c: Catalyst) => `
      • ${c.ticker} - ${c.sponsor}
        ${c.title}
        Completion: ${c.completion_date} (${c.days_until_completion} days)
    `).join('\n')}

    View details: ${Deno.env.get('APP_URL')}/dashboard
  `

  // Send via requested channels
  const sentChannels = []

  if (channels.includes('email')) {
    await sendEmail(user.email, subject, message)
    sentChannels.push('email')
  }

  if (channels.includes('sms') && user.notification_preferences?.phone_number) {
    await sendSMS(user.notification_preferences.phone_number, message.slice(0, 160))
    sentChannels.push('sms')
  }

  if (channels.includes('slack') && user.notification_preferences?.slack_webhook_url) {
    await sendSlack(user.notification_preferences.slack_webhook_url, message)
    sentChannels.push('slack')
  }

  // Log to alert_history
  await client.from('alert_history').insert({
    user_id: userId,
    saved_search_id: savedSearchId,
    alert_type: 'new_match',
    catalyst_nct_id: catalysts[0].nct_id,  // First catalyst
    channels_sent: sentChannels,
    delivery_status: 'sent',
    subject,
    message
  })
}

async function sendEmail(to: string, subject: string, body: string) {
  const sendGridApiKey = Deno.env.get('SENDGRID_API_KEY')

  await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${sendGridApiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: to }] }],
      from: { email: 'alerts@biotech-radar.com', name: 'Biotech Radar' },
      subject,
      content: [{ type: 'text/plain', value: body }]
    })
  })
}

async function sendSMS(to: string, body: string) {
  const twilioAccountSid = Deno.env.get('TWILIO_ACCOUNT_SID')
  const twilioAuthToken = Deno.env.get('TWILIO_AUTH_TOKEN')
  const twilioPhoneNumber = Deno.env.get('TWILIO_PHONE_NUMBER')

  await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${twilioAccountSid}/Messages.json`,
    {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + btoa(`${twilioAccountSid}:${twilioAuthToken}`),
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        To: to,
        From: twilioPhoneNumber,
        Body: body
      })
    }
  )
}

async function sendSlack(webhookUrl: string, text: string) {
  await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  })
}
```

---

### Streamlit UI Components

**File**: `src/pages/alerts.py` (Pro tier only)

```python
"""Alert management dashboard."""

import streamlit as st
from typing import Dict, List
from utils.db import get_saved_searches, create_saved_search, update_saved_search
from utils.auth import require_pro_tier

def render_alerts_page():
    """Render alerts management page."""
    require_pro_tier()  # Redirect if not Pro

    st.title("⚡ Proactive Alerts")
    st.markdown("Automatically get notified when new catalysts match your criteria")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Saved Searches", "Create New", "Alert History"])

    with tab1:
        render_saved_searches()

    with tab2:
        render_create_search()

    with tab3:
        render_alert_history()

def render_saved_searches():
    """Show user's saved searches."""
    user_id = st.session_state.user_id
    searches = get_saved_searches(user_id)

    if not searches:
        st.info("No saved searches yet. Create one in the 'Create New' tab!")
        return

    for search in searches:
        with st.expander(f"{'✅' if search['active'] else '⏸️'} {search['name']}", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown("**Filters:**")
                filters = search['filters']
                if filters.get('phase'):
                    st.caption(f"Phase: {', '.join(filters['phase'])}")
                if filters.get('therapeutic_area'):
                    st.caption(f"Area: {', '.join(filters['therapeutic_area'])}")
                if filters.get('market_cap_max'):
                    st.caption(f"Market cap < ${filters['market_cap_max'] / 1e9:.1f}B")

                st.markdown(f"**Alert frequency:** {search['alert_frequency']}")
                st.markdown(f"**Channels:** {', '.join(search['channels'])}")
                st.caption(f"Last checked: {search['last_checked_at']}")

            with col2:
                if st.button("Edit", key=f"edit_{search['id']}"):
                    st.session_state.editing_search = search['id']

                if search['active']:
                    if st.button("Pause", key=f"pause_{search['id']}"):
                        update_saved_search(search['id'], {'active': False})
                        st.rerun()
                else:
                    if st.button("Activate", key=f"activate_{search['id']}"):
                        update_saved_search(search['id'], {'active': True})
                        st.rerun()

def render_create_search():
    """Form to create new saved search."""
    st.markdown("### Create Saved Search")

    with st.form("create_search"):
        # Name
        name = st.text_input("Search name", placeholder="e.g., 'My Oncology Watchlist'")

        # Filters
        st.markdown("**Filters**")
        phase = st.multiselect("Phase", ["2", "3"], default=["3"])
        therapeutic_area = st.multiselect(
            "Therapeutic area",
            ["Oncology", "Neurology", "Immunology", "Cardiology", "Diabetes", "Rare"]
        )
        market_cap_max = st.number_input(
            "Max market cap ($B)",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1
        )
        completion_days_max = st.number_input(
            "Max days until completion",
            min_value=7,
            max_value=365,
            value=90,
            step=7
        )

        # Alert settings
        st.markdown("**Alert settings**")
        alert_frequency = st.radio(
            "Frequency",
            ["realtime", "daily", "weekly"],
            format_func=lambda x: x.capitalize()
        )

        channels = st.multiselect(
            "Notification channels",
            ["email", "sms", "slack"],
            default=["email"],
            format_func=lambda x: x.upper()
        )

        if st.form_submit_button("Create Saved Search", type="primary"):
            if not name:
                st.error("Please enter a search name")
            else:
                create_saved_search(
                    user_id=st.session_state.user_id,
                    name=name,
                    filters={
                        'phase': phase,
                        'therapeutic_area': therapeutic_area,
                        'market_cap_max': market_cap_max * 1e9,
                        'completion_days_max': completion_days_max
                    },
                    alert_frequency=alert_frequency,
                    channels=channels
                )
                st.success(f"Created saved search: {name}")
                st.rerun()

def render_alert_history():
    """Show recent alerts sent."""
    st.markdown("### Recent Alerts (Last 30 days)")

    # TODO: Fetch from alert_history table
    st.info("Alert history coming soon!")
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_alert_agent.py

from datetime import datetime, timedelta
from agent.alert_checker import AlertChecker

def test_detect_new_catalyst():
    """Test detection of new catalyst matching saved search."""
    checker = AlertChecker()

    search = {
        'id': 'search-123',
        'filters': {'phase': ['3'], 'therapeutic_area': ['oncology']},
        'last_results': ['NCT00000001', 'NCT00000002']
    }

    current_results = [
        {'nct_id': 'NCT00000001'},
        {'nct_id': 'NCT00000002'},
        {'nct_id': 'NCT00000003'},  # NEW
    ]

    new_catalysts = checker.find_new_matches(search, current_results)

    assert len(new_catalysts) == 1
    assert new_catalysts[0]['nct_id'] == 'NCT00000003'

def test_no_duplicate_alerts():
    """Test that duplicate alerts are not sent."""
    # TODO: Implement
    pass
```

### Integration Tests

1. **End-to-end alert flow**:
   - [ ] Create saved search → Cron runs → New catalyst appears → Alert sent
   - [ ] Verify email received within 5 minutes
   - [ ] Verify alert logged in alert_history

2. **Multi-channel delivery**:
   - [ ] User enables SMS + email → Both channels receive alert
   - [ ] Verify SMS character limit respected

3. **Deduplication**:
   - [ ] Catalyst matches 2 saved searches → Only 1 alert sent
   - [ ] Same catalyst checked twice → No duplicate alert

---

## Success Criteria

- [ ] <5 minute latency from catalyst appearance → alert sent
- [ ] <1% false positive rate (measured over 100 alerts)
- [ ] 99.5% delivery rate (alerts sent successfully)
- [ ] 40%+ Pro users create ≥1 saved search within 30 days
- [ ] 20% reduction in Pro tier churn vs. Starter tier
- [ ] Infrastructure cost <$0.50/user/month

---

## Implementation Phases

### Phase 1: MVP (Week 1-2)
- [ ] Database schema (saved_searches, alert_history)
- [ ] Supabase Edge Function for alert checking
- [ ] Email notifications via SendGrid
- [ ] Basic UI to create/manage saved searches

**Success Metric**: Can create saved search and receive email alert

### Phase 2: Multi-Channel (Week 3)
- [ ] SMS notifications via Twilio
- [ ] Slack integration
- [ ] User notification preferences
- [ ] Alert history dashboard

**Success Metric**: Users can choose email/SMS/Slack per search

### Phase 3: Intelligence (Week 4+)
- [ ] Price movement alerts
- [ ] Completion date reminders (7/1 days before)
- [ ] Smart deduplication
- [ ] Daily digest mode

**Success Metric**: <1% false positives, 99.5% delivery rate

### Future Enhancements
- [ ] Trial status update alerts (when completion date changes)
- [ ] Push notifications (mobile app)
- [ ] Integration with Discord
- [ ] AI-powered alert prioritization (Claude API)

---

## Cost Analysis

### Development Cost
- **Engineering**: 3 weeks × 1 developer = $6,000
- **Infrastructure setup**: Supabase + SendGrid + Twilio = $500
- **Testing**: 40 hours × $50/hr = $2,000
- **Total**: $8,500

### Operational Cost (per month for 100 Pro users)
- **SendGrid**: 100 users × 30 alerts/mo × $0.00085 = $2.55
- **Twilio SMS**: 50 users × 10 SMS/mo × $0.0075 = $3.75
- **Supabase Edge Functions**: 3,000 invocations/mo = $0.25
- **Total**: $6.55/mo = **$0.07/user/mo**

### ROI Calculation
- **Revenue**: Pro tier upgrade ($49 vs $29) = +$20/mo × 30% of users = +$6/user/mo
- **Churn reduction**: 20% reduction × $49/mo × 10% churn = +$0.98/user/mo
- **Total benefit**: $6.98/user/mo
- **Cost**: $0.07/user/mo
- **ROI**: 100x return

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Alert fatigue (too many alerts) | High | Medium | Smart deduplication + daily digest option |
| False positives | High | Low | Rigorous testing + manual verification in beta |
| Delivery failures (email/SMS) | Medium | Low | Retry logic + fallback channels |
| High SMS costs | Medium | Low | Default to email, SMS opt-in only |
| Spam complaints | Low | Low | Clear unsubscribe + frequency controls |

---

## Compliance & Privacy

- **CAN-SPAM**: All emails include unsubscribe link
- **TCPA (SMS)**: Explicit opt-in required for SMS alerts
- **GDPR**: Users can export/delete alert history
- **Data retention**: Alert history purged after 90 days

---

## References

- [Supabase Edge Functions](https://supabase.com/docs/guides/functions)
- [SendGrid Email API](https://docs.sendgrid.com/api-reference/mail-send)
- [Twilio SMS API](https://www.twilio.com/docs/sms/api)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)

---

## Implementation Status

**Status**: 🔜 **PLANNED**
**Planned Start**: Week 8
**Estimated Completion**: Week 11
**Priority**: High (Pro tier differentiation + retention)

---

**Last Updated**: 2025-12-24
**Owner**: Product Team
**Stakeholders**: Engineering, Operations, Customer Success
