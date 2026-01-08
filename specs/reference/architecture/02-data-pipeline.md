# n8n Workflow: Daily Catalyst Scrape

## Overview

Automated workflow that scrapes ClinicalTrials.gov daily for Phase 2/3 trials, stores data in PostgreSQL, and triggers downstream enrichment workflows.

**Trigger**: Cron (daily at 6:00 AM UTC)
**Duration**: ~5-10 minutes
**Dependencies**: PostgreSQL, ClinicalTrials.gov API v2

---

## Workflow Diagram

```
┌──────────────┐
│ Cron Trigger │
│ 6:00 AM UTC  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│ HTTP Request             │
│ GET ClinicalTrials.gov   │
│ Query: Phase 2/3 trials  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Function: Parse Trials   │
│ Extract: NCT, sponsor,   │
│ phase, completion_date   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Filter: Remove invalid   │
│ - No completion date     │
│ - Completion > 3 months  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Loop: For each trial     │
│ ┌────────────────────┐   │
│ │ PostgreSQL: UPSERT │   │
│ │ (ON CONFLICT UPDATE)│  │
│ └────────────────────┘   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ PostgreSQL: Log run      │
│ INSERT workflow_runs     │
│ (timestamp, count)       │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Webhook: Trigger         │
│ ticker enrichment        │
│ workflow                 │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Slack/Email: Notify      │
│ "Scraped N trials"       │
└──────────────────────────┘
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
        "expression": "0 6 * * *"
      }
    ]
  },
  "timezone": "UTC"
}
```

**Output**: Triggers workflow daily at 6 AM UTC

---

### Node 2: HTTP Request - Fetch Trials

**Type**: `HTTP Request`

**Configuration**:
```json
{
  "method": "GET",
  "url": "https://clinicaltrials.gov/api/v2/studies",
  "qs": {
    "query.cond": "",
    "query.term": "",
    "filter.overallStatus": "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION",
    "filter.phase": "PHASE2|PHASE3",
    "pageSize": 100,
    "format": "json"
  },
  "options": {
    "timeout": 30000,
    "retry": {
      "maxRetries": 3,
      "retryDelay": 5000
    }
  }
}
```

**Response** (sample):
```json
{
  "studies": [
    {
      "protocolSection": {
        "identificationModule": {
          "nctId": "NCT05123456",
          "orgStudyIdInfo": {
            "id": "STUDY-2024-001"
          }
        },
        "sponsorCollaboratorsModule": {
          "leadSponsor": {
            "name": "Moderna, Inc."
          }
        },
        "designModule": {
          "phases": ["PHASE3"]
        },
        "statusModule": {
          "overallStatus": "RECRUITING",
          "primaryCompletionDateStruct": {
            "date": "2025-06-30"
          }
        },
        "conditionsModule": {
          "conditions": ["COVID-19", "SARS-CoV-2"]
        }
      }
    }
  ],
  "nextPageToken": "eyJ..."
}
```

---

### Node 3: Function - Parse Trials

**Type**: `Code`

**Language**: JavaScript

**Code**:
```javascript
const items = [];
const studies = $input.all()[0].json.studies || [];

for (const study of studies) {
  const protocol = study.protocolSection;

  // Extract fields with fallbacks
  const nctId = protocol.identificationModule?.nctId;
  const sponsor = protocol.sponsorCollaboratorsModule?.leadSponsor?.name || 'Unknown';
  const phases = protocol.designModule?.phases || [];
  const phase = phases.length > 0 ? phases[0] : 'UNKNOWN';
  const completionDate = protocol.statusModule?.primaryCompletionDateStruct?.date;
  const indication = (protocol.conditionsModule?.conditions || []).join(', ');
  const status = protocol.statusModule?.overallStatus;

  // Skip if missing critical data
  if (!nctId || !completionDate) {
    continue;
  }

  items.push({
    json: {
      nct_id: nctId,
      sponsor: sponsor,
      phase: phase,
      completion_date: completionDate,
      indication: indication,
      status: status,
      scraped_at: new Date().toISOString()
    }
  });
}

return items;
```

**Output**: Array of parsed trial objects

---

### Node 4: Filter - Remove Invalid Trials

**Type**: `Filter`

**Conditions**:
```json
{
  "conditions": {
    "combinator": "and",
    "conditions": [
      {
        "leftValue": "={{ $json.completion_date }}",
        "rightValue": "",
        "operator": "notEmpty"
      },
      {
        "leftValue": "={{ new Date($json.completion_date) }}",
        "rightValue": "={{ new Date(Date.now() + 90 * 24 * 60 * 60 * 1000) }}",
        "operator": "smallerOrEquals"
      },
      {
        "leftValue": "={{ new Date($json.completion_date) }}",
        "rightValue": "={{ new Date() }}",
        "operator": "largerOrEquals"
      }
    ]
  }
}
```

**Logic**: Keep only trials completing within next 90 days

---

### Node 5: PostgreSQL - Upsert Catalysts

**Type**: `PostgreSQL`

**Operation**: `Execute Query`

**Query**:
```sql
INSERT INTO catalysts (
  nct_id,
  sponsor,
  phase,
  indication,
  completion_date,
  data_refreshed_at,
  created_at
)
VALUES (
  $1, $2, $3, $4, $5, NOW(), NOW()
)
ON CONFLICT (nct_id)
DO UPDATE SET
  sponsor = EXCLUDED.sponsor,
  phase = EXCLUDED.phase,
  indication = EXCLUDED.indication,
  completion_date = EXCLUDED.completion_date,
  data_refreshed_at = NOW()
RETURNING *;
```

**Parameters** (n8n expression):
```json
{
  "parameters": [
    "={{ $json.nct_id }}",
    "={{ $json.sponsor }}",
    "={{ $json.phase }}",
    "={{ $json.indication }}",
    "={{ $json.completion_date }}"
  ]
}
```

**Settings**:
- Execute once per item: `true`
- Continue on fail: `false`

---

### Node 6: Aggregate Results

**Type**: `Aggregate`

**Configuration**:
```json
{
  "aggregate": "aggregateAllItemData",
  "include": "allFieldsIncludeNoFields"
}
```

**Purpose**: Combine all items into one for summary

---

### Node 7: PostgreSQL - Log Workflow Run

**Type**: `PostgreSQL`

**Operation**: `Execute Query`

**Query**:
```sql
INSERT INTO workflow_runs (
  workflow_name,
  started_at,
  completed_at,
  items_processed,
  status
)
VALUES (
  'daily_catalyst_scrape',
  $1,
  NOW(),
  $2,
  'success'
);
```

**Parameters**:
```json
{
  "parameters": [
    "={{ $('Cron Trigger').item.json.time }}",
    "={{ $('Aggregate Results').item.json.length }}"
  ]
}
```

---

### Node 8: Webhook - Trigger Enrichment

**Type**: `HTTP Request`

**Configuration**:
```json
{
  "method": "POST",
  "url": "{{ $env.N8N_WEBHOOK_BASE_URL }}/webhook/ticker-enrichment",
  "bodyParameters": {
    "parameters": [
      {
        "name": "trigger_source",
        "value": "daily_scrape"
      },
      {
        "name": "catalysts_count",
        "value": "={{ $('Aggregate Results').item.json.length }}"
      }
    ]
  }
}
```

---

### Node 9: Slack Notification (Optional)

**Type**: `Slack`

**Operation**: `Send Message`

**Configuration**:
```json
{
  "channel": "#biotech-radar-alerts",
  "text": "✅ Daily catalyst scrape complete: {{ $('Aggregate Results').item.json.length }} trials updated",
  "attachments": [
    {
      "color": "good",
      "fields": [
        {
          "title": "Workflow",
          "value": "daily_catalyst_scrape",
          "short": true
        },
        {
          "title": "Duration",
          "value": "={{ $runIndex === 0 ? 'N/A' : Math.round(($now() - $('Cron Trigger').item.json.time) / 1000) + 's' }}",
          "short": true
        }
      ]
    }
  ]
}
```

---

### Error Handling

**Node 10: On Error - Log Failure**

**Type**: `PostgreSQL` (connected to error output of Node 2)

**Query**:
```sql
INSERT INTO workflow_runs (
  workflow_name,
  started_at,
  completed_at,
  items_processed,
  status,
  error_message
)
VALUES (
  'daily_catalyst_scrape',
  $1,
  NOW(),
  0,
  'failed',
  $2
);
```

**Parameters**:
```json
{
  "parameters": [
    "={{ $('Cron Trigger').item.json.time }}",
    "={{ $json.error.message }}"
  ]
}
```

---

**Node 11: On Error - Send Alert**

**Type**: `Send Email` or `Slack`

**Configuration**:
```json
{
  "to": "dev@example.com",
  "subject": "🚨 Daily Catalyst Scrape Failed",
  "text": "Workflow failed at: {{ $now() }}\nError: {{ $json.error.message }}"
}
```

---

## Database Tables

### catalysts Table

Already defined in `architecture/02-target-architecture.md`

### workflow_runs Table (New)

```sql
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    items_processed INTEGER DEFAULT 0,
    status VARCHAR(50), -- success, failed, partial
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workflow_runs_name ON workflow_runs(workflow_name);
CREATE INDEX idx_workflow_runs_started_at ON workflow_runs(started_at DESC);
```

**Purpose**: Track workflow execution history for monitoring

---

## Environment Variables (n8n)

Add to n8n environment:

```bash
# PostgreSQL Connection
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_DB=biotech_radar
POSTGRES_USER=n8n_user
POSTGRES_PASSWORD=***

# ClinicalTrials.gov (no auth needed)
CLINICALTRIALS_API_BASE=https://clinicaltrials.gov/api/v2

# n8n Webhooks
N8N_WEBHOOK_BASE_URL=https://n8n.example.com

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/***
```

---

## Testing Plan

### Local Testing (n8n Desktop/Docker)

1. **Manual trigger**: Click "Execute Workflow" in n8n UI
2. **Verify outputs**:
   - [ ] HTTP Request returns trials JSON
   - [ ] Function parses trials correctly
   - [ ] Filter removes trials >90 days out
   - [ ] PostgreSQL UPSERT works (check with SQL query)
   - [ ] Webhook triggers enrichment workflow

### Integration Testing

1. **End-to-end test**:
   - [ ] Trigger workflow manually
   - [ ] Verify trials in database: `SELECT * FROM catalysts ORDER BY data_refreshed_at DESC LIMIT 10;`
   - [ ] Check enrichment workflow was triggered
   - [ ] Verify Slack notification received

2. **Error scenarios**:
   - [ ] ClinicalTrials.gov API down (use offline mock)
   - [ ] Invalid JSON response (test with malformed data)
   - [ ] Database connection failure

### Production Testing

1. **Dry run** in production (test mode):
   - [ ] Run workflow at 5:30 AM UTC (before scheduled time)
   - [ ] Verify no duplicate data in database
   - [ ] Check logs for errors

2. **Monitor first 7 days**:
   - [ ] Workflow runs successfully every day
   - [ ] No duplicates in `catalysts` table
   - [ ] Enrichment workflow triggered each time

---

## Success Criteria

- [ ] Workflow completes in <10 minutes
- [ ] Fetches 80-150 trials daily
- [ ] Zero duplicate `nct_id` in database
- [ ] 100% uptime over 7 days
- [ ] Error notifications delivered <5 min after failure

---

## Monitoring & Alerts

### Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Execution Time** | <10 min | >15 min |
| **Trials Fetched** | 80-150 | <50 or >200 |
| **Success Rate** | 100% | <95% over 7 days |
| **Database Errors** | 0 | >1 per day |

### Alerts

1. **Workflow Failure**: Email + Slack within 5 min
2. **Low Data Volume**: If <50 trials, send warning
3. **High Latency**: If >15 min, investigate API issues

---

## Rollout Plan

### Week 1: Development
- [ ] Build workflow in n8n test instance
- [ ] Test with mock data
- [ ] Verify database schema

### Week 2: Staging
- [ ] Deploy to n8n staging environment
- [ ] Run daily for 7 days
- [ ] Monitor logs and database

### Week 3: Production
- [ ] Deploy to production n8n
- [ ] Schedule cron for 6 AM UTC
- [ ] Monitor first 3 runs closely
- [ ] Disable old GitHub Actions workflow after 7 successful runs

---

## Migration from GitHub Actions

**Old**: `.github/workflows/daily_scrape.yml`
**New**: n8n workflow (this spec)

**Cutover Plan**:
1. Run n8n workflow in parallel for 7 days
2. Compare results (should be identical)
3. Disable GitHub Actions workflow
4. Delete workflow file from repo

---

## Future Enhancements

- [ ] Add pagination support (fetch >100 trials per run)
- [ ] Implement incremental updates (only changed trials)
- [ ] Add data quality checks (validate sponsor names, dates)
- [ ] Parallelize API calls (fetch multiple pages concurrently)
- [ ] Cache API responses (avoid re-fetching same data)

---

## References

- [ClinicalTrials.gov API v2 Docs](https://clinicaltrials.gov/data-api/api)
- [n8n Documentation](https://docs.n8n.io/)
- [n8n Cron Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.cron/)
- [PostgreSQL Upsert (ON CONFLICT)](https://www.postgresql.org/docs/current/sql-insert.html)

---

## Implementation Status

**Status**: ✅ **IMPLEMENTED**
**Implementation Date**: 2025-12-24
**Implementation Summary**: Complete n8n workflow JSON ready for import

### Files Created
- ✅ `n8n-workflows/01-daily-catalyst-scrape.json` (13 KB)
- ✅ `n8n-workflows/README.md` - Complete setup guide

### Workflow Features
- ✅ Cron trigger (6 AM UTC daily)
- ✅ HTTP Request to ClinicalTrials.gov API v2
- ✅ JavaScript function to parse trials
- ✅ Filter trials (Phase 2/3, next 90 days)
- ✅ PostgreSQL UPSERT (handles duplicates)
- ✅ Workflow execution logging
- ✅ Downstream webhook trigger (ticker enrichment)
- ✅ Slack notifications
- ✅ Error handling with database logging
- ✅ Email alerts on failure

### Nodes Implemented
- 11 total nodes (including error handling)
- Valid n8n v1.0+ JSON format
- All environment variables as placeholders
- Detailed node descriptions

### Next Steps
1. Set up n8n instance (Cloud or self-hosted)
2. Import workflow JSON via n8n UI
3. Configure PostgreSQL credentials
4. Configure Slack webhook (optional)
5. Test manual execution
6. Activate cron trigger
7. Monitor for 7 days

### Documentation
- Complete setup instructions in `n8n-workflows/README.md`
- Testing procedures included
- Troubleshooting guide

---

**Last Updated**: 2025-12-24
**Status**: ✅ **IMPLEMENTED & READY FOR DEPLOYMENT**
**Owner**: Development Team
**Implementation Date**: Week 1 (ahead of schedule)
