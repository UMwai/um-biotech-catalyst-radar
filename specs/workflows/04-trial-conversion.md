# n8n Workflow: Trial Conversion Automation

## Overview

Automated email sequence that nurtures free trial users toward paid conversion over 7 days, then continues re-engagement for 14 days post-trial.

**Trigger**: Cron (hourly)
**Duration**: ~2-5 minutes per run
**Dependencies**: PostgreSQL, SendGrid/Mailgun

---

## Email Sequence Timeline

```
Day 0: User signs up
  ↓
Day 1: Welcome Email + Onboarding
  ↓
Day 3: Feature Highlight (Price Charts)
  ↓
Day 5: Social Proof / Use Case
  ↓
Day 6: Trial Expiring Soon (24hr warning)
  ↓
Day 7: Trial Expired → Paywall
  ↓
Day 9: Reminder (Limited-time offer - optional)
  ↓
Day 14: Final Re-engagement
```

---

## Workflow Diagram

```
┌──────────────┐
│ Cron Trigger │
│ Every hour   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│ PostgreSQL: Get Trial Users         │
│ WHERE trial_end_date IS NOT NULL    │
│ AND subscription_id IS NULL         │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Function: Calculate Trial Day       │
│ day = DATEDIFF(now, trial_start)    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Switch: Route by Trial Day          │
│ ├─ Day 1                             │
│ ├─ Day 3                             │
│ ├─ Day 5                             │
│ ├─ Day 6                             │
│ ├─ Day 7                             │
│ ├─ Day 9                             │
│ └─ Day 14                            │
└──────┬──────────────────────────────┘
       │
       ▼ (each branch)
┌─────────────────────────────────────┐
│ Filter: Email Not Sent Yet          │
│ Check email_log for this email_type │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ SendGrid: Send Email                │
│ Use template_id for this day        │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ PostgreSQL: Log Email Sent          │
│ INSERT INTO email_log               │
└─────────────────────────────────────┘
```

---

## n8n Node Configuration

### Node 1: Cron Trigger

**Type**: `Schedule Trigger`

**Configuration**:
```json
{
  "rule": {
    "interval": [
      {
        "field": "cronExpression",
        "expression": "0 * * * *"
      }
    ]
  },
  "timezone": "UTC"
}
```

**Output**: Triggers every hour on the hour

---

### Node 2: PostgreSQL - Get Trial Users

**Type**: `PostgreSQL`

**Operation**: `Execute Query`

**Query**:
```sql
SELECT
  u.id AS user_id,
  u.email,
  u.trial_start_date,
  u.trial_end_date,
  EXTRACT(DAY FROM (NOW() - u.trial_start_date)) AS trial_day,
  u.created_at
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
WHERE
  u.trial_start_date IS NOT NULL
  AND s.id IS NULL -- No active subscription
  AND u.trial_start_date >= NOW() - INTERVAL '14 days' -- Within 14 days of trial start
ORDER BY u.trial_start_date DESC;
```

**Output**: List of trial users with their trial day

---

### Node 3: Function - Calculate Trial Day

**Type**: `Code`

**Language**: JavaScript

**Code**:
```javascript
const items = [];

for (const item of $input.all()) {
  const trialStartDate = new Date(item.json.trial_start_date);
  const now = new Date();
  const diffTime = Math.abs(now - trialStartDate);
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  items.push({
    json: {
      ...item.json,
      trial_day: diffDays,
      trial_day_exact: diffTime / (1000 * 60 * 60 * 24),
      days_remaining: 7 - diffDays
    }
  });
}

return items;
```

**Output**: Users with calculated `trial_day` field

---

### Node 4: Switch - Route by Trial Day

**Type**: `Switch`

**Mode**: Rules

**Rules**:
```json
{
  "rules": {
    "rules": [
      {
        "name": "Day 1",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 1
            }
          ]
        }
      },
      {
        "name": "Day 3",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 3
            }
          ]
        }
      },
      {
        "name": "Day 5",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 5
            }
          ]
        }
      },
      {
        "name": "Day 6",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 6
            }
          ]
        }
      },
      {
        "name": "Day 7",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 7
            }
          ]
        }
      },
      {
        "name": "Day 9",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 9
            }
          ]
        }
      },
      {
        "name": "Day 14",
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.trial_day }}",
              "operation": "equals",
              "value2": 14
            }
          ]
        }
      }
    ]
  }
}
```

---

### Node 5a-5g: Filter - Email Not Sent

**Type**: `IF` (one per branch)

**Configuration** (example for Day 1):
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{ $('Check Email Log - Day 1').item.json.count === 0 }}",
        "value2": true
      }
    ]
  }
}
```

**Connected to**: PostgreSQL query that checks:
```sql
SELECT COUNT(*) AS count
FROM email_log
WHERE user_id = $1
AND email_type = $2;
```

**Parameters**: `[user_id, 'trial_day_1']`

---

### Node 6a-6g: SendGrid - Send Email

**Type**: `SendGrid`

**Operation**: `Send Email`

**Configuration** (example for Day 1):
```json
{
  "fromEmail": "hello@biotech-radar.com",
  "fromName": "Biotech Radar",
  "toEmail": "={{ $json.email }}",
  "subject": "Welcome to Biotech Radar! 🧬",
  "templateId": "d-1234567890abcdef",
  "dynamicTemplateData": {
    "parameters": {
      "user_email": "={{ $json.email }}",
      "trial_end_date": "={{ $json.trial_end_date }}",
      "days_remaining": "={{ $json.days_remaining }}",
      "app_url": "={{ $env.APP_URL }}"
    }
  }
}
```

---

### Email Templates (SendGrid Dynamic Templates)

#### Day 1: Welcome Email

**Template ID**: `d-trial-day-1`

**Subject**: Welcome to Biotech Radar! 🧬

**Body**:
```html
<h1>Welcome to Biotech Radar!</h1>

<p>Hi there,</p>

<p>Thanks for starting your 7-day free trial. You now have access to:</p>

<ul>
  <li>✅ Phase 2/3 clinical trial catalysts</li>
  <li>✅ Small-cap biotech stocks (<$5B market cap)</li>
  <li>✅ 6-month price charts with catalyst overlays</li>
  <li>✅ Daily data updates</li>
</ul>

<p><strong>Your trial expires on: {{ trial_end_date }}</strong> ({{ days_remaining }} days)</p>

<p>
  <a href="{{ app_url }}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Start Browsing Catalysts →
  </a>
</p>

<hr>

<p><strong>Quick Tips:</strong></p>
<ol>
  <li>Filter by "Next 30 Days" to find imminent catalysts</li>
  <li>Click any ticker to see price charts</li>
  <li>Check back daily for new trials</li>
</ol>

<p>Questions? Just reply to this email.</p>

<p>— The Biotech Radar Team</p>
```

---

#### Day 3: Feature Highlight

**Template ID**: `d-trial-day-3`

**Subject**: See price run-ups before catalyst dates 📈

**Body**:
```html
<h1>Price Charts + Catalyst Overlays</h1>

<p>Hi {{ user_email }},</p>

<p>You're 3 days into your trial! Have you tried our <strong>price chart feature</strong>?</p>

<p>Click any ticker in the dashboard to see:</p>
<ul>
  <li>📊 6-month candlestick chart</li>
  <li>🔔 Catalyst date marked on the chart</li>
  <li>📈 30-day price change %</li>
</ul>

<img src="https://example.com/chart-example.png" alt="Price chart example" width="600">

<p><strong>Pro tip:</strong> Look for stocks with tight consolidation 2-4 weeks before catalyst dates.</p>

<p>
  <a href="{{ app_url }}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Browse Charts Now →
  </a>
</p>

<p>{{ days_remaining }} days left in your trial.</p>

<p>— Biotech Radar</p>
```

---

#### Day 5: Social Proof

**Template ID**: `d-trial-day-5`

**Subject**: How traders use Biotech Radar

**Body**:
```html
<h1>How Traders Use Biotech Radar</h1>

<p>Hi {{ user_email }},</p>

<p>With just <strong>{{ days_remaining }} days left</strong> in your trial, I wanted to share how other traders are using the platform:</p>

<blockquote style="border-left: 4px solid #007bff; padding-left: 16px; font-style: italic;">
  "I scan the dashboard every Monday for catalysts 30-45 days out, then watch for run-ups. Saved me hours of manual searching."
  <br>— Alex, Retail Trader
</blockquote>

<p><strong>Common strategies:</strong></p>
<ol>
  <li>Enter positions 3-4 weeks before catalyst date</li>
  <li>Exit 1-2 days before data release (to avoid binary risk)</li>
  <li>Focus on small caps with <$2B market cap (bigger % moves)</li>
</ol>

<p>Ready to subscribe? Lock in <strong>$29/month</strong> pricing:</p>

<p>
  <a href="{{ app_url }}/subscribe" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Subscribe Now →
  </a>
</p>

<p>Trial ends {{ trial_end_date }}.</p>

<p>— Biotech Radar</p>
```

---

#### Day 6: Trial Expiring Soon

**Template ID**: `d-trial-day-6`

**Subject**: ⏰ Your trial expires tomorrow

**Body**:
```html
<h1>Your Trial Expires Tomorrow</h1>

<p>Hi {{ user_email }},</p>

<p><strong>Just a heads up:</strong> Your free trial ends in 24 hours.</p>

<p>After tomorrow, you'll need a paid subscription to access:</p>
<ul>
  <li>Full catalyst dashboard</li>
  <li>Price charts</li>
  <li>Daily data updates</li>
</ul>

<p>Subscribe now to keep access:</p>

<p>
  <a href="{{ app_url }}/subscribe?plan=monthly" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-right: 8px;">
    $29/month →
  </a>
  <a href="{{ app_url }}/subscribe?plan=annual" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    $232/year (Save 33%) →
  </a>
</p>

<p><em>Trial ends: {{ trial_end_date }}</em></p>

<p>— Biotech Radar</p>
```

---

#### Day 7: Trial Expired

**Template ID**: `d-trial-day-7`

**Subject**: Your trial has expired

**Body**:
```html
<h1>Your Trial Has Expired</h1>

<p>Hi {{ user_email }},</p>

<p>Your 7-day free trial has ended. To continue accessing biotech catalyst data, subscribe below:</p>

<p>
  <a href="{{ app_url }}/subscribe?plan=monthly" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-right: 8px;">
    Subscribe - $29/month →
  </a>
  <a href="{{ app_url }}/subscribe?plan=annual" style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Subscribe - $232/year →
  </a>
</p>

<p>Questions? Reply to this email.</p>

<p>— Biotech Radar</p>
```

---

#### Day 9: Reminder (Optional)

**Template ID**: `d-trial-day-9`

**Subject**: Still interested in catalyst tracking?

**Body**:
```html
<h1>Still Interested?</h1>

<p>Hi {{ user_email }},</p>

<p>I noticed you haven't subscribed yet. Is there anything holding you back?</p>

<p>Common questions:</p>
<ul>
  <li><strong>Is the data accurate?</strong> Yes, sourced directly from ClinicalTrials.gov</li>
  <li><strong>Can I cancel anytime?</strong> Absolutely, no long-term commitment</li>
  <li><strong>Is there a money-back guarantee?</strong> Contact us within 7 days for a refund</li>
</ul>

<p>Ready to subscribe?</p>

<p>
  <a href="{{ app_url }}/subscribe" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Get Started →
  </a>
</p>

<p>— Biotech Radar</p>
```

---

#### Day 14: Final Re-engagement

**Template ID**: `d-trial-day-14`

**Subject**: We miss you!

**Body**:
```html
<h1>We Miss You!</h1>

<p>Hi {{ user_email }},</p>

<p>It's been 2 weeks since your trial ended. If you're still interested in tracking biotech catalysts, we'd love to have you back.</p>

<p>
  <a href="{{ app_url }}/subscribe" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
    Subscribe Now →
  </a>
</p>

<p>Not interested? No problem — just ignore this email.</p>

<p>— Biotech Radar</p>
```

---

### Node 7: PostgreSQL - Log Email Sent

**Type**: `PostgreSQL`

**Operation**: `Execute Query`

**Query**:
```sql
INSERT INTO email_log (
  user_id,
  email_type,
  sent_at
)
VALUES ($1, $2, NOW());
```

**Parameters**:
```json
{
  "parameters": [
    "={{ $json.user_id }}",
    "=trial_day_{{ $('Switch').outputIndex }}"
  ]
}
```

---

## Testing Plan

### Local Testing

1. **Create test user** with trial_start_date = NOW() - 1 day
2. **Run workflow manually**
3. **Verify**: Day 1 email sent
4. **Check**: `email_log` table has entry

### Integration Testing

1. **Create users for each day** (1, 3, 5, 6, 7, 9, 14)
2. **Run workflow**
3. **Verify**: Each user gets correct email
4. **Run again**: No duplicate emails sent

---

## Success Criteria

- [ ] Emails sent within 1 hour of trial day milestone
- [ ] No duplicate emails for same user + day
- [ ] Open rate >20% (tracked via SendGrid)
- [ ] Click-through rate >5%
- [ ] Trial → paid conversion rate >10%

---

## Monitoring

Track in `analytics_events` table:
- `email_sent` (type, user_id)
- `email_opened` (via SendGrid webhook)
- `email_clicked` (via SendGrid webhook)
- `trial_converted` (when subscription created)

---

**Last Updated**: 2025-12-24
**Status**: 📝 Spec Draft
**Implementation Target**: Week 5-6
