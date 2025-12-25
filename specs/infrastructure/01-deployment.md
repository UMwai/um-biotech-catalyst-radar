# Infrastructure Spec: Deployment & Hosting

## Overview

Define hosting infrastructure for the Biotech Radar SaaS, including Streamlit app, PostgreSQL database, n8n workflows, and supporting services.

---

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Users (HTTPS)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             Streamlit Cloud (Frontend)                       │
│   - Free tier: 1GB RAM, 1 CPU                               │
│   - Custom domain: biotech-radar.com                        │
│   - Auto-deploy on git push                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ PostgreSQL connection
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          Supabase / Render PostgreSQL                        │
│   - Free tier: 500MB storage, 1GB RAM                       │
│   - Managed backups                                          │
│   - Connection pooling                                       │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Read/Write
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        n8n Cloud / Self-Hosted (Workflows)                   │
│   - Option 1: n8n Cloud ($20/mo)                            │
│   - Option 2: Railway/Render ($5/mo, Docker)                │
│   - 5 workflows (scrape, enrich, emails, webhooks)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ External APIs
                       │
        ┌──────────────┼──────────────┐
        │              │               │
        ▼              ▼               ▼
┌──────────────┐ ┌──────────┐ ┌─────────────────┐
│ClinicalTrials│ │ Stripe   │ │ SendGrid        │
│.gov API      │ │ Webhooks │ │ (emails)        │
└──────────────┘ └──────────┘ └─────────────────┘
```

---

## Service Stack

### 1. Frontend - Streamlit App

**Platform**: Streamlit Community Cloud (Free Tier)

**Specs**:
- 1 GB RAM
- 1 vCPU
- Auto-deploy from GitHub
- Custom domain support (free)

**Configuration**:
- **App URL**: `https://biotech-radar.streamlit.app` (free subdomain)
- **Custom domain**: `biotech-radar.com` (optional, configure DNS)
- **Git branch**: `main` (auto-deploy on push)
- **Python version**: 3.11
- **Secrets**: Managed via Streamlit Secrets Manager

**Streamlit Secrets** (`.streamlit/secrets.toml`):
```toml
[postgres]
host = "db.supabase.co"
port = 5432
database = "biotech_radar"
user = "postgres"
password = "***"

[stripe]
api_key = "sk_live_***"
webhook_secret = "whsec_***"
price_monthly = "price_***"
price_annual = "price_***"

[app]
env = "production"
debug = false
```

**Pros**:
- ✅ Free (no cost for MVP)
- ✅ Auto-deploy from GitHub
- ✅ HTTPS included
- ✅ Easy secrets management

**Cons**:
- ❌ Limited resources (1GB RAM)
- ❌ Sleeps after inactivity (free tier)
- ❌ No custom server-side logic beyond Streamlit

**Upgrade Path**: If Streamlit Cloud becomes limiting, migrate to:
- Railway ($5/mo for basic instance)
- Render ($7/mo for web service)
- AWS Lightsail ($5/mo for VPS)

---

### 2. Database - PostgreSQL

**Platform**: Supabase (Free Tier) or Render PostgreSQL

**Option A: Supabase (Recommended)**

**Specs**:
- 500 MB database storage
- 1 GB RAM
- Unlimited API requests (reasonable use)
- Automatic backups (7 days)
- Connection pooling (PgBouncer)

**Pros**:
- ✅ Free tier generous
- ✅ Built-in connection pooling
- ✅ RESTful API (bonus)
- ✅ Built-in Auth (if needed)
- ✅ Dashboard for SQL queries

**Cons**:
- ❌ 500MB storage limit (may need upgrade after 6 months)

**Upgrade Path**: $25/mo for 8GB database

**Setup**:
```bash
# Create Supabase project
# Copy connection string:
postgresql://postgres:[password]@db.supabase.co:5432/biotech_radar

# Run migrations
psql postgresql://postgres:[password]@db.supabase.co:5432/biotech_radar < migrations/001_initial.sql
```

---

**Option B: Render PostgreSQL**

**Specs**:
- Free tier: 256MB RAM, 1GB storage
- Auto-backups (manual restore)
- Connection pooling (paid tier only)

**Pros**:
- ✅ Free tier available
- ✅ Simple setup

**Cons**:
- ❌ Smaller free tier than Supabase
- ❌ No connection pooling on free tier

**Pricing**: $7/mo for basic, $20/mo for standard

---

### 3. Workflow Engine - n8n

**Platform**: Self-hosted (Docker on Railway/Render) or n8n Cloud

**Option A: n8n Cloud (Recommended for Speed)**

**Specs**:
- $20/month (Starter plan)
- 2,500 executions/month
- 5-minute execution timeout
- Managed hosting (no DevOps)

**Pros**:
- ✅ Zero DevOps (managed)
- ✅ Auto-updates
- ✅ Built-in monitoring
- ✅ Fast setup (<1 hour)

**Cons**:
- ❌ $20/month cost
- ❌ Execution limits (2,500/mo)

**Upgrade Path**: $50/mo for Pro (10K executions)

---

**Option B: Self-Hosted (Railway) - Best for Cost**

**Platform**: Railway.app or Render.com

**Specs**:
- Docker container
- 512MB RAM, 0.5 vCPU (Railway: $5/mo)
- Persistent storage for workflows (1GB)

**Docker Compose**:
```yaml
version: '3'
services:
  n8n:
    image: n8nio/n8n:latest
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=n8n.railway.app
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.railway.app/
      - GENERIC_TIMEZONE=America/New_York
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=${POSTGRES_HOST}
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

**Deployment** (Railway):
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add PostgreSQL
railway add

# Deploy n8n
railway up
```

**Pros**:
- ✅ $5/month (vs $20 for n8n Cloud)
- ✅ Full control
- ✅ No execution limits

**Cons**:
- ❌ Requires Docker knowledge
- ❌ Manual updates
- ❌ Self-managed monitoring

---

### 4. Email Service - SendGrid

**Platform**: SendGrid (Free Tier)

**Specs**:
- 100 emails/day (free tier)
- Transactional + marketing emails
- Email templates
- Analytics (open rates, click rates)

**Pricing**:
- Free: 100 emails/day
- $19.95/mo: 50K emails/month (when you scale)

**Setup**:
```bash
# Create SendGrid account
# Generate API key
# Add to Streamlit secrets:
[sendgrid]
api_key = "SG.***"
from_email = "hello@biotech-radar.com"
```

**Alternative**: Mailgun (200 emails/day free)

---

### 5. Monitoring & Logging

**Platform**: BetterStack (Free Tier)

**Features**:
- Uptime monitoring (every 30 seconds)
- Status page
- Incident alerts (email, Slack)
- Log aggregation (5GB/month free)

**Setup**:
```bash
# Add monitoring endpoints:
- https://biotech-radar.streamlit.app (frontend)
- https://n8n.railway.app (n8n workflows)
- https://db.supabase.co (database connection)

# Configure alerts:
- Email: dev@example.com
- Slack: #alerts channel
```

**Alternative**: UptimeRobot (free, 50 monitors)

---

## Cost Breakdown

### MVP (Free Tier - Month 1)

| Service | Plan | Cost |
|---------|------|------|
| Streamlit Cloud | Free | $0 |
| Supabase PostgreSQL | Free | $0 |
| n8n (self-hosted Railway) | Hobby | $5 |
| SendGrid | Free (100/day) | $0 |
| BetterStack | Free | $0 |
| Stripe | Pay-as-you-go | 2.9% + $0.30 per transaction |
| **Total** | | **$5/month + Stripe fees** |

---

### Production (Scalable - Month 3+)

| Service | Plan | Cost |
|---------|------|------|
| Streamlit Cloud or Railway | Paid | $7-20 |
| Supabase PostgreSQL | Pro | $25 |
| n8n Cloud | Starter | $20 |
| SendGrid | Essentials | $20 (50K emails) |
| BetterStack | Team | $0-10 |
| Stripe | Pay-as-you-go | 2.9% + $0.30 |
| **Total** | | **$72-95/month + Stripe fees** |

**Note**: At 100 paying customers ($2,900 MRR), infrastructure is only 3% of revenue.

---

## Deployment Workflow

### Initial Setup (Week 1)

1. **Create Supabase project**
   - Sign up at supabase.com
   - Create new project
   - Copy connection string
   - Run database migrations

2. **Deploy n8n**
   - Railway: `railway init && railway up`
   - Import workflows from JSON
   - Connect to PostgreSQL
   - Test daily scrape workflow

3. **Deploy Streamlit app**
   - Push code to GitHub `main` branch
   - Connect Streamlit Cloud to repo
   - Add secrets in Streamlit UI
   - Test app at `*.streamlit.app`

4. **Configure Stripe**
   - Create products (Monthly, Annual)
   - Copy price IDs to Streamlit secrets
   - Set up webhook endpoint: `https://n8n.railway.app/webhook/stripe`
   - Test in Stripe test mode

5. **Set up SendGrid**
   - Create account
   - Verify sender email
   - Create email templates
   - Add API key to n8n

---

### CI/CD Pipeline

**GitHub Actions** (`.github/workflows/deploy.yml`):
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/

      - name: Deploy to Streamlit
        run: echo "Auto-deploys via Streamlit Cloud"

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {"text": "Deployed to production ✅"}
```

---

## Database Migrations

**Tool**: Alembic or simple SQL files

**Migration files** (`migrations/`):
```
001_initial.sql
002_add_email_log.sql
003_add_analytics_events.sql
```

**Run migrations**:
```bash
psql $DATABASE_URL < migrations/001_initial.sql
```

---

## Backup Strategy

### Database Backups

**Supabase**: Automatic daily backups (7-day retention)

**Manual backups** (weekly):
```bash
# Dump database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Upload to S3 or Google Drive
aws s3 cp backup_*.sql s3://biotech-radar-backups/
```

### n8n Workflows

**Export workflows** (monthly):
```bash
# Export all workflows as JSON
curl -u admin:password https://n8n.railway.app/api/v1/workflows > workflows_backup.json

# Commit to Git
git add workflows_backup.json && git commit -m "backup: n8n workflows"
```

---

## Security Checklist

- [ ] All secrets in environment variables (never in code)
- [ ] Database uses strong password (20+ chars)
- [ ] Stripe webhook signature verification enabled
- [ ] n8n protected with basic auth
- [ ] PostgreSQL only accessible from whitelisted IPs
- [ ] HTTPS enforced on all services
- [ ] SendGrid API key rotated quarterly

---

## Monitoring & Alerts

### Health Checks

**BetterStack monitors**:
- Streamlit app: `GET /` (expect 200)
- n8n: `GET /healthz` (expect 200)
- Database: Connection test (every 5 min)

### Alerts

**Trigger alerts on**:
- Streamlit app down >3 minutes
- Database connection failures
- n8n workflow failures (via email log)
- Disk space >80% (database)

**Notification channels**:
- Email: dev@example.com
- Slack: #alerts

---

## Rollout Plan

### Week 1: Infrastructure Setup
- [ ] Create Supabase project
- [ ] Deploy n8n (Railway)
- [ ] Deploy Streamlit app
- [ ] Run database migrations
- [ ] Test end-to-end

### Week 2: Integration
- [ ] Connect n8n to PostgreSQL
- [ ] Import workflows
- [ ] Configure Stripe webhooks
- [ ] Set up SendGrid templates

### Week 3: Testing
- [ ] Load test (simulate 100 users)
- [ ] Test workflows (scrape, emails, webhooks)
- [ ] Verify backups
- [ ] Security audit

### Week 4: Production Launch
- [ ] Custom domain (biotech-radar.com)
- [ ] Switch Stripe to live mode
- [ ] Monitor first 7 days
- [ ] Invite beta users

---

## Scaling Considerations

**At 100 users**:
- Streamlit Cloud may need upgrade ($20/mo)
- Database: Upgrade to Pro ($25/mo)
- n8n: Self-hosted is fine

**At 500 users**:
- Migrate to Railway/Render ($20-50/mo)
- Database: Scale to 4GB RAM ($50/mo)
- n8n: n8n Cloud Pro ($50/mo)

**At 1,000+ users**:
- Consider dedicated VPS (AWS/GCP)
- Load balancer + multiple app instances
- Database: Read replicas
- CDN for static assets

---

**Last Updated**: 2025-12-24
**Status**: 📝 Spec Draft - Ready for Implementation
**Owner**: DevOps Team
**Implementation Target**: Week 1-2
