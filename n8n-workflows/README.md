# n8n Workflows for Biotech Radar

This directory contains n8n workflow JSON files for automating key operations in the Biotech Radar SaaS platform.

## Workflows Overview

| Workflow | File | Purpose | Trigger |
|----------|------|---------|---------|
| **Daily Catalyst Scrape** | `01-daily-catalyst-scrape.json` | Scrapes ClinicalTrials.gov for Phase 2/3 trials and stores them in PostgreSQL | Cron (6 AM UTC daily) |
| **Trial Conversion** | `04-trial-conversion.json` | Sends automated email sequence to trial users over 14 days | Cron (hourly) |
| **Stripe Webhooks** | `05-stripe-webhooks.json` | Handles Stripe webhook events for subscription management | Webhook (on-demand) |

---

## Prerequisites

### 1. n8n Installation

You need a running n8n instance. Options:

- **Cloud**: [n8n Cloud](https://n8n.io/cloud/) (recommended for production)
- **Self-hosted Docker**:
  ```bash
  docker run -it --rm \
    --name n8n \
    -p 5678:5678 \
    -e N8N_BASIC_AUTH_ACTIVE=true \
    -e N8N_BASIC_AUTH_USER=admin \
    -e N8N_BASIC_AUTH_PASSWORD=yourpassword \
    -v ~/.n8n:/home/node/.n8n \
    n8nio/n8n
  ```
- **npm**: `npm install n8n -g && n8n start`

### 2. PostgreSQL Database

Ensure your PostgreSQL database has the required tables:

```sql
-- Catalysts table (for workflow 01)
CREATE TABLE catalysts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nct_id VARCHAR(50) UNIQUE NOT NULL,
    sponsor VARCHAR(255),
    phase VARCHAR(50),
    indication TEXT,
    completion_date DATE,
    data_refreshed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workflow runs tracking (for workflow 01)
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    items_processed INTEGER DEFAULT 0,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Users table (for workflows 04 & 05)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255),
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions table (for workflow 05)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50),
    plan_type VARCHAR(50),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Email log (for workflow 04)
CREATE TABLE email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    email_type VARCHAR(100),
    sent_at TIMESTAMP DEFAULT NOW()
);

-- Webhook events log (for workflow 05)
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100),
    event_data JSONB,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_catalysts_completion_date ON catalysts(completion_date);
CREATE INDEX idx_workflow_runs_name ON workflow_runs(workflow_name);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_email_log_user_id ON email_log(user_id);
CREATE INDEX idx_webhook_events_type ON webhook_events(event_type);
```

### 3. External Services

- **SendGrid** or **SMTP** for email sending
- **Slack** (optional) for notifications
- **Stripe** account with webhook secret

---

## Environment Variables

Configure these in n8n (Settings → Environments):

```bash
# PostgreSQL
POSTGRES_HOST=your-db-host.com
POSTGRES_PORT=5432
POSTGRES_DB=biotech_radar
POSTGRES_USER=n8n_user
POSTGRES_PASSWORD=your-secure-password

# ClinicalTrials.gov API
CLINICALTRIALS_API_BASE=https://clinicaltrials.gov/api/v2

# n8n Webhooks
N8N_WEBHOOK_BASE_URL=https://your-n8n-instance.com

# Application URLs
APP_URL=https://biotech-radar.streamlit.app

# Stripe
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PRICE_MONTHLY=price_monthly_id
STRIPE_PRICE_ANNUAL=price_annual_id

# Email (SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## Importing Workflows

### Method 1: n8n UI (Recommended)

1. Open n8n web interface
2. Click **Workflows** in the left sidebar
3. Click **Add workflow** → **Import from file**
4. Select one of the JSON files from this directory
5. Click **Import**
6. Repeat for each workflow

### Method 2: CLI

```bash
# Copy workflows to n8n directory
cp n8n-workflows/*.json ~/.n8n/workflows/

# Restart n8n
docker restart n8n
# or
systemctl restart n8n
```

### Method 3: API

```bash
# Import via n8n API
curl -X POST http://localhost:5678/rest/workflows \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/01-daily-catalyst-scrape.json
```

---

## Workflow Configuration

### 1. Daily Catalyst Scrape (`01-daily-catalyst-scrape.json`)

**Setup Steps**:

1. Import the workflow
2. Configure PostgreSQL credentials:
   - Click on any PostgreSQL node
   - Create new credential: "PostgreSQL - Biotech Radar"
   - Enter connection details
3. Configure Slack credentials (optional):
   - Click "Slack Notification" node
   - Add Slack API credential or webhook URL
4. Test the workflow:
   - Click "Execute Workflow" button
   - Verify data appears in `catalysts` table
5. Activate the workflow (toggle in top-right)

**Testing**:

```sql
-- Verify data was scraped
SELECT * FROM catalysts ORDER BY data_refreshed_at DESC LIMIT 10;

-- Check workflow runs
SELECT * FROM workflow_runs WHERE workflow_name = 'daily_catalyst_scrape';
```

---

### 2. Trial Conversion (`04-trial-conversion.json`)

**Setup Steps**:

1. Import the workflow
2. Configure PostgreSQL credentials (reuse from workflow 01)
3. Configure SendGrid/SMTP credentials:
   - Click on any "SendGrid" node
   - Create new SMTP credential
   - Enter SendGrid API key details
4. Update email templates if needed (each SendGrid node has HTML content)
5. Test with a test user:
   ```sql
   -- Create test user
   INSERT INTO users (email, trial_start_date, trial_end_date)
   VALUES ('test@example.com', NOW() - INTERVAL '1 day', NOW() + INTERVAL '6 days');
   ```
6. Execute workflow manually
7. Verify email was sent (check email_log table)
8. Activate the workflow

**Testing**:

```sql
-- Create test users for each trial day
INSERT INTO users (email, trial_start_date, trial_end_date) VALUES
  ('day1@test.com', NOW() - INTERVAL '1 day', NOW() + INTERVAL '6 days'),
  ('day3@test.com', NOW() - INTERVAL '3 days', NOW() + INTERVAL '4 days'),
  ('day7@test.com', NOW() - INTERVAL '7 days', NOW()),
  ('day14@test.com', NOW() - INTERVAL '14 days', NOW() - INTERVAL '7 days');

-- Verify emails sent
SELECT * FROM email_log ORDER BY sent_at DESC;
```

---

### 3. Stripe Webhooks (`05-stripe-webhooks.json`)

**Setup Steps**:

1. Import the workflow
2. Configure PostgreSQL credentials (reuse from workflow 01)
3. Configure SendGrid/SMTP credentials (reuse from workflow 04)
4. Activate the workflow
5. Get the webhook URL:
   - Open the workflow
   - Click on "Webhook Trigger" node
   - Copy the "Production URL" (e.g., `https://your-n8n.com/webhook/stripe-webhooks`)
6. Configure Stripe webhook:
   - Go to [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks)
   - Click "Add endpoint"
   - Paste the webhook URL
   - Select events:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Click "Add endpoint"
   - Copy the "Signing secret" (starts with `whsec_`)
7. Update environment variable `STRIPE_WEBHOOK_SECRET` with the signing secret
8. Test the webhook:
   - Use Stripe CLI: `stripe trigger customer.subscription.created`
   - Or create a test subscription in Stripe Dashboard

**Testing with Stripe CLI**:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe
# or download from https://stripe.com/docs/stripe-cli

# Login to Stripe
stripe login

# Test webhook events
stripe trigger customer.subscription.created
stripe trigger invoice.payment_succeeded
stripe trigger invoice.payment_failed

# Verify in database
SELECT * FROM subscriptions ORDER BY created_at DESC;
SELECT * FROM webhook_events ORDER BY processed_at DESC;
```

---

## Monitoring & Troubleshooting

### View Workflow Executions

1. Go to n8n UI → **Executions**
2. Filter by workflow name
3. Click on any execution to see detailed logs

### Common Issues

#### Workflow 01: Daily Catalyst Scrape

**Issue**: No trials fetched

- **Solution**: Check ClinicalTrials.gov API status, verify query parameters

**Issue**: PostgreSQL connection error

- **Solution**: Verify credentials, check firewall rules, ensure database is accessible

#### Workflow 04: Trial Conversion

**Issue**: Emails not sending

- **Solution**: Verify SMTP credentials, check SendGrid API key, review email logs

**Issue**: Duplicate emails sent

- **Solution**: Check `email_log` table, ensure deduplication logic is working

#### Workflow 05: Stripe Webhooks

**Issue**: Signature verification failed

- **Solution**: Verify `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard, check webhook payload

**Issue**: Webhook not triggering

- **Solution**: Verify webhook URL is correct, check Stripe Dashboard webhook logs, ensure workflow is active

### Database Queries for Monitoring

```sql
-- Check recent workflow runs
SELECT * FROM workflow_runs ORDER BY started_at DESC LIMIT 10;

-- Check recent emails sent
SELECT el.*, u.email
FROM email_log el
JOIN users u ON el.user_id = u.id
ORDER BY el.sent_at DESC LIMIT 20;

-- Check subscription status
SELECT
  u.email,
  s.status,
  s.plan_type,
  s.current_period_end
FROM subscriptions s
JOIN users u ON s.user_id = u.id
ORDER BY s.created_at DESC;

-- Check webhook events
SELECT
  event_type,
  COUNT(*) as count,
  MAX(processed_at) as last_processed
FROM webhook_events
GROUP BY event_type
ORDER BY last_processed DESC;
```

---

## Security Best Practices

1. **Never commit credentials**: Keep `.env` files out of version control
2. **Use environment variables**: Store all secrets in n8n environment variables
3. **Verify webhook signatures**: Workflow 05 includes signature verification
4. **Limit database permissions**: Create a dedicated `n8n_user` with minimal permissions
5. **Enable HTTPS**: Always use HTTPS for webhook endpoints
6. **Rotate secrets regularly**: Update Stripe webhook secrets and API keys periodically

---

## Rollout Checklist

### Week 1: Testing

- [ ] Import all workflows
- [ ] Configure credentials
- [ ] Test each workflow manually
- [ ] Verify database updates
- [ ] Check email delivery
- [ ] Test Stripe webhooks with test mode

### Week 2: Staging

- [ ] Deploy to staging n8n instance
- [ ] Run workflows daily for 7 days
- [ ] Monitor logs for errors
- [ ] Verify no duplicate data
- [ ] Test webhook reliability

### Week 3: Production

- [ ] Deploy to production n8n
- [ ] Activate workflows
- [ ] Configure Stripe production webhooks
- [ ] Monitor first 3 executions
- [ ] Set up alerts for failures

---

## Support & Maintenance

### Workflow Updates

To update a workflow:

1. Make changes in n8n UI
2. Export workflow: Workflow → Download
3. Replace JSON file in this directory
4. Commit to version control

### Backup Workflows

```bash
# Export all workflows
n8n export:workflow --all --output=./backups/

# Restore from backup
n8n import:workflow --input=./backups/workflow.json
```

### Monitoring Alerts

Set up alerts for:

- Workflow failures (check `workflow_runs.status = 'failed'`)
- High email bounce rates
- Payment failures (webhook events)
- API rate limits

---

## Resources

- [n8n Documentation](https://docs.n8n.io/)
- [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [SendGrid SMTP Setup](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)

---

## Contributing

To contribute workflow improvements:

1. Test changes in development n8n instance
2. Export updated workflow JSON
3. Update this README if adding new environment variables
4. Create pull request with description of changes

---

**Last Updated**: 2025-12-24
**Maintained by**: Biotech Radar Development Team
**Support**: dev@biotech-radar.com
