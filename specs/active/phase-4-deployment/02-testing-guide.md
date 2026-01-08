# Testing Guide - Phase 4

Quick reference for testing Chat Agent and Proactive Alerts features.

## Prerequisites

```bash
# Set environment variables
export SUPABASE_URL=https://xxxxx.supabase.co
export SUPABASE_ANON_KEY=your_anon_key
export SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Install dependencies
pip install -r requirements.txt
```

---

## Test 1: Chat Agent (Local)

### Run Locally

```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar
streamlit run src/pages/chat.py
```

### Test Queries

| Query | Expected Behavior |
|-------|-------------------|
| "Phase 3 oncology under $2B" | Filters: phase=3, area=oncology, cap<2B |
| "trials next 60 days" | Filters: completion_days_max=60 |
| "neurology catalysts" | Filters: therapeutic_area=neurology |
| "Phase 2 rare disease under $1B" | Filters: phase=2, area=rare disease, cap<1B |
| "oncology next 30 days" | Filters: area=oncology, days=30 |
| "Phase 5 trials" | No results (invalid phase) |

### Verify

- [ ] Query is parsed into structured filters
- [ ] Database is queried correctly
- [ ] Results displayed as catalyst cards
- [ ] Action buttons (Details, Watch, Alert) clickable
- [ ] Chat history persists during session
- [ ] Clear history button works
- [ ] Example query buttons work
- [ ] Mobile responsive (test at 360px width)

---

## Test 2: Catalyst Agent (Unit Tests)

```bash
# Run agent unit tests
pytest tests/test_agent.py -v

# Test query parsing
python -c "
from src.agents.catalyst_agent import CatalystAgent
agent = CatalystAgent()

# Test case 1: Phase filter
filters = agent.parse_query('Phase 3 oncology under \$2B')
print(f'Parsed filters: {filters}')
assert filters['phase'] == 'Phase 3'
assert filters['therapeutic_area'] == 'oncology'
assert filters['max_market_cap'] == 2_000_000_000
print('✅ Test 1 passed')

# Test case 2: Timeframe
filters = agent.parse_query('trials next 60 days')
print(f'Parsed filters: {filters}')
assert filters['days_ahead'] == 60
print('✅ Test 2 passed')
"
```

---

## Test 3: Proactive Alerts (Integration)

### 3.1 Create Test Data

```sql
-- Create test user
INSERT INTO users (id, email, created_at)
VALUES ('123e4567-e89b-12d3-a456-426614174000', 'test@example.com', NOW())
ON CONFLICT (id) DO NOTHING;

-- Create test catalyst
INSERT INTO catalysts (
    id, nct_id, sponsor, ticker, phase, indication,
    completion_date, market_cap, current_price, created_at
)
VALUES (
    'cat-123', 'NCT99999999', 'Test Pharma Inc.', 'TEST',
    'Phase 3', 'Advanced oncology treatment',
    '2026-06-30', 1500000000, 25.50, NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Create saved search
INSERT INTO saved_searches (
    user_id, name, query_params, notification_channels, active
)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'Test Search - Oncology',
    '{"phase": "Phase 3", "therapeutic_area": "oncology", "max_market_cap": 2000000000}',
    '["email"]',
    true
);
```

### 3.2 Test Alert Agent (Python)

```bash
# Test alert agent directly
python -c "
import os
os.environ['SUPABASE_URL'] = 'https://xxxxx.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'your_service_key'

from src.agents.alert_agent import AlertAgent

agent = AlertAgent()
results = agent.check_saved_searches()
print(f'Results: {results}')
assert results['searches_checked'] > 0
print('✅ Alert agent test passed')
"
```

### 3.3 Test Edge Function

```bash
# Invoke function manually
curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "success": true,
#   "searches_checked": 1,
#   "matches_found": 1,
#   "notifications_sent": 1,
#   "errors": 0
# }
```

### 3.4 Verify Alert Sent

```sql
-- Check alert notifications
SELECT
    an.*,
    ss.name as search_name,
    c.ticker,
    c.sponsor
FROM alert_notifications an
JOIN saved_searches ss ON an.saved_search_id = ss.id
JOIN catalysts c ON an.catalyst_id = c.id
WHERE an.user_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY an.notification_sent_at DESC
LIMIT 5;
```

### 3.5 Check SendGrid Activity

1. Go to https://sendgrid.com
2. Navigate to Activity Feed
3. Search for `test@example.com`
4. Verify email was delivered
5. Check email content matches catalyst data

---

## Test 4: Saved Searches UI

### Navigate to Alerts Page

```bash
streamlit run src/app.py
# Click "Alerts" in navigation menu
```

### Test Workflow

1. **Create Search:**
   - Click "New Search"
   - Fill form:
     - Name: "My Test Search"
     - Phase: "Phase 3"
     - Area: "oncology"
     - Max Cap: $2B
   - Click "Create Search"
   - Verify appears in list

2. **Test Search:**
   - Click "Test" button
   - Verify results match filters
   - Check result count is accurate

3. **Edit Search:**
   - Click "Edit"
   - Change max cap to $5B
   - Save changes
   - Verify updated in list

4. **Pause/Resume:**
   - Click "Pause"
   - Verify status changes to paused
   - Click "Resume"
   - Verify status changes to active

5. **Delete Search:**
   - Click "Delete"
   - Confirm deletion
   - Verify removed from list

---

## Test 5: Notification Settings

### Navigate to Settings Tab

1. Go to Alerts page → Settings tab
2. Configure preferences:
   - Max alerts: 10
   - Quiet hours: 22:00 - 06:00
   - Timezone: America/New_York
   - Enable email
   - Enable SMS (Pro only)
   - Add phone number
3. Click "Save Settings"
4. Verify settings persisted

### Verify Database

```sql
SELECT * FROM notification_preferences
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000';
```

---

## Test 6: Rate Limiting & Deduplication

### Test Rate Limit

```sql
-- Create 15 alerts (over limit of 10)
INSERT INTO alert_notifications (
    saved_search_id, catalyst_id, user_id,
    channels_used, notification_sent_at
)
SELECT
    (SELECT id FROM saved_searches LIMIT 1),
    (SELECT id FROM catalysts LIMIT 1),
    '123e4567-e89b-12d3-a456-426614174000',
    '["email"]',
    NOW()
FROM generate_series(1, 15);

-- Test can_receive_alert function
SELECT can_receive_alert('123e4567-e89b-12d3-a456-426614174000');
-- Should return FALSE (over limit)
```

### Test Deduplication

```bash
# Trigger alert check twice
curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Verify only one notification sent for same catalyst
```

```sql
SELECT
    catalyst_id,
    COUNT(*) as notification_count
FROM alert_notifications
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
  AND notification_sent_at >= NOW() - INTERVAL '1 hour'
GROUP BY catalyst_id
HAVING COUNT(*) > 1;

-- Should return 0 rows (no duplicates)
```

---

## Test 7: Multi-Channel Notifications

### Test Email

```bash
# Already tested in Test 3
```

### Test SMS (Pro Tier)

```bash
# 1. Upgrade test user to Pro tier
# 2. Add phone number in notification settings
# 3. Trigger alert

curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# 4. Verify SMS received via Twilio logs
```

### Test Slack (Pro Tier)

```bash
# 1. Create Slack webhook URL
# 2. Add to notification settings
# 3. Trigger alert
# 4. Verify message appears in Slack channel
```

---

## Test 8: Performance Benchmarks

### Chat Agent Response Time

```python
import time
from src.agents.catalyst_agent import CatalystAgent

agent = CatalystAgent()
queries = [
    "Phase 3 oncology under $2B",
    "trials next 60 days",
    "neurology catalysts",
]

times = []
for query in queries:
    start = time.time()
    response = agent.process_query(query)
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)
    print(f"{query}: {elapsed:.2f}ms")

avg_time = sum(times) / len(times)
p90_time = sorted(times)[int(len(times) * 0.9)]

print(f"\nAverage: {avg_time:.2f}ms")
print(f"90th percentile: {p90_time:.2f}ms")

assert p90_time < 500, "Response time too slow!"
print("✅ Performance test passed")
```

### Alert Check Performance

```bash
# Time the edge function
time curl -X POST https://xxxxx.supabase.co/functions/v1/check-alerts \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Should complete in <5 seconds
```

---

## Test 9: Error Handling

### Test Invalid Queries

```python
from src.agents.catalyst_agent import CatalystAgent

agent = CatalystAgent()

# Test empty query
response = agent.process_query("")
assert response['type'] in ['no_results', 'error']

# Test nonsense query
response = agent.process_query("asdfghjkl")
assert 'message' in response

print("✅ Error handling test passed")
```

### Test Missing Database

```bash
# Unset database URL
unset SUPABASE_URL

# Run chat agent
streamlit run src/pages/chat.py

# Should show friendly error, not crash
```

---

## Test 10: Mobile Responsiveness

### Test Chat UI on Mobile

1. Open Chrome DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Set viewport to:
   - iPhone SE (375×667)
   - Galaxy S8+ (360×740)
   - iPad Air (820×1180)

4. Verify:
   - [ ] Chat input is tappable
   - [ ] Catalyst cards render correctly
   - [ ] Action buttons are tappable
   - [ ] Example query buttons are tappable
   - [ ] Navigation menu accessible
   - [ ] No horizontal scrolling
   - [ ] Text is readable (no overflow)

---

## Success Criteria Checklist

### Chat Agent
- [ ] All 6 test queries parse correctly
- [ ] Response time <500ms (90th percentile)
- [ ] Database queries execute successfully
- [ ] Results displayed as cards
- [ ] Mobile responsive
- [ ] Example queries work

### Proactive Alerts
- [ ] Edge function deploys successfully
- [ ] Alerts sent within 5 minutes
- [ ] Email delivery rate >95%
- [ ] No duplicate alerts
- [ ] Rate limiting works
- [ ] Quiet hours respected
- [ ] Database functions work

### UI
- [ ] Create search works
- [ ] Edit search works
- [ ] Test search works
- [ ] Pause/resume works
- [ ] Delete works
- [ ] Notification settings save
- [ ] Alert history displays

---

## Troubleshooting

### Chat Agent Not Loading

```bash
# Check imports
python -c "from src.agents.catalyst_agent import CatalystAgent; print('✅ Import OK')"

# Check database connection
python -c "
from src.utils.db import get_catalysts
catalysts = get_catalysts(limit=5)
print(f'✅ Database OK: {len(catalysts)} catalysts')
"
```

### Alerts Not Sending

```sql
-- Check saved searches
SELECT * FROM saved_searches WHERE active = TRUE;

-- Check recent catalysts
SELECT * FROM catalysts WHERE created_at >= NOW() - INTERVAL '1 day';

-- Check cron job
SELECT * FROM cron.job WHERE jobname = 'check-alerts-daily';

-- Check edge function logs
SELECT * FROM edge_function_runs
WHERE function_name = 'check-alerts'
ORDER BY started_at DESC LIMIT 5;
```

### Email Not Delivering

1. Check SendGrid Activity Feed
2. Verify sender email is verified
3. Check API key is set: `supabase secrets list`
4. Test SendGrid directly:
```bash
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer YOUR_SENDGRID_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "personalizations": [{"to": [{"email": "test@example.com"}]}],
    "from": {"email": "alerts@yourdomain.com"},
    "subject": "Test",
    "content": [{"type": "text/plain", "value": "Test"}]
  }'
```

---

**Last Updated**: 2025-12-30
