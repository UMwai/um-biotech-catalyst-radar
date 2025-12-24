# Supabase Deployment Guide - Free Tier

> **Complete guide** to deploy Biotech Catalyst Radar on Supabase free tier

## Prerequisites

- Supabase account (free): https://supabase.com/dashboard
- Supabase CLI: `npm install -g supabase`
- Git installed
- Node.js 18+ (for Edge Functions)

---

## Step 1: Create Supabase Project

### Via Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Fill in details:
   - **Name**: `biotech-catalyst-radar`
   - **Database Password**: Generate strong password (save it!)
   - **Region**: Choose closest to your users (e.g., `us-east-1`)
   - **Pricing Plan**: Free

4. Wait ~2 minutes for project to initialize

### Get Project Credentials

Once project is ready, go to **Settings → API**:

```bash
# Copy these values:
Project URL: https://xxxxx.supabase.co
Anon/Public Key: eyJhbG...
Service Role Key: eyJhbG... (keep secret!)
Project Ref: xxxxx
```

---

## Step 2: Deploy Database Schema

### Option A: Via Supabase Dashboard (Easiest)

1. Go to **SQL Editor** in Supabase Dashboard
2. Click "New Query"
3. Copy entire contents of `supabase/migrations/20251224_initial_schema.sql`
4. Paste into query editor
5. Click "Run" (or press Cmd/Ctrl + Enter)
6. Wait for success message

### Option B: Via Supabase CLI

```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref xxxxx

# Run migration
supabase db push

# Verify tables created
supabase db inspect
```

### Verify Schema

```sql
-- Run this in SQL Editor to verify:
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Expected output:
-- catalysts, users, subscriptions, email_log, analytics_events, edge_function_runs
```

---

## Step 3: Deploy Edge Function (Daily Sync)

### Install Dependencies

```bash
# Navigate to project root
cd /home/user/um-biotech-catalyst-radar

# Ensure Supabase CLI is installed
npm install -g supabase
```

### Deploy Function

```bash
# Deploy the daily-sync function
supabase functions deploy daily-sync

# Set secrets (environment variables)
supabase secrets set SUPABASE_URL=https://xxxxx.supabase.co
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Test Function Manually

```bash
# Invoke function via CLI
supabase functions invoke daily-sync

# Or via curl:
curl -X POST https://xxxxx.supabase.co/functions/v1/daily-sync \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "success": true,
  "trials_fetched": 150,
  "trials_filtered": 87,
  "tickers_mapped": 45,
  "small_caps": 38,
  "timestamp": "2025-12-24T06:00:00.000Z"
}
```

---

## Step 4: Schedule Daily Sync (Cron)

### Enable pg_cron Extension

1. Go to **Database → Extensions** in Supabase Dashboard
2. Search for "pg_cron"
3. Click "Enable"

### Create Cron Job

Go to **SQL Editor** and run:

```sql
-- Schedule daily sync at 6 AM UTC
SELECT cron.schedule(
    'daily-catalyst-sync',
    '0 6 * * *', -- Every day at 6 AM UTC (cron format)
    $$
    SELECT net.http_post(
        url := 'https://xxxxx.supabase.co/functions/v1/daily-sync',
        headers := jsonb_build_object(
            'Authorization',
            'Bearer YOUR_ANON_KEY',
            'Content-Type',
            'application/json'
        )
    ) as request_id;
    $$
);

-- Verify cron job created
SELECT * FROM cron.job;
```

### Monitor Cron Jobs

```sql
-- Check cron job runs
SELECT * FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 10;

-- Check edge function logs
SELECT * FROM public.edge_function_runs
ORDER BY started_at DESC
LIMIT 10;
```

---

## Step 5: Enable Authentication

### Configure Supabase Auth

1. Go to **Authentication → Providers** in dashboard
2. Enable "Email" provider
3. **Disable** "Confirm email" (for MVP, optional for production)
4. Save changes

### Configure Email Templates (Optional)

Go to **Authentication → Email Templates**:

- Customize "Confirm signup" email
- Customize "Magic Link" email
- Customize "Change Email Address" email

---

## Step 6: Update Streamlit App

### Install Supabase Client

```bash
# Add to requirements.txt
echo "supabase==2.3.4" >> requirements.txt

# Install
pip install supabase
```

### Update `src/utils/config.py`

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Supabase
    supabase_url: str
    supabase_anon_key: str

    # Stripe
    stripe_api_key: str
    stripe_price_monthly: str
    stripe_price_annual: str
    stripe_webhook_secret: str

    # App
    app_env: str
    debug: bool

    @classmethod
    def from_env(cls):
        return cls(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
            stripe_api_key=os.getenv("STRIPE_API_KEY"),
            stripe_price_monthly=os.getenv("STRIPE_PRICE_MONTHLY"),
            stripe_price_annual=os.getenv("STRIPE_PRICE_ANNUAL"),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
            app_env=os.getenv("APP_ENV", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
```

### Create Supabase Client

```python
# src/utils/supabase_client.py
from supabase import create_client, Client
from .config import Config

_supabase_client: Client | None = None

def get_supabase_client() -> Client:
    """Get or create Supabase client (singleton)."""
    global _supabase_client

    if _supabase_client is None:
        config = Config.from_env()
        _supabase_client = create_client(
            config.supabase_url,
            config.supabase_anon_key
        )

    return _supabase_client
```

### Update Database Queries

Replace `src/utils/db.py` PostgreSQL calls with Supabase:

```python
# Before (PostgreSQL):
from .db import get_user

# After (Supabase):
from .supabase_client import get_supabase_client

def get_user(email: str):
    supabase = get_supabase_client()
    response = supabase.table('users').select('*').eq('email', email).execute()
    return response.data[0] if response.data else None
```

---

## Step 7: Configure Environment Variables

### Update `.env`

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG... # Keep secret!

# Stripe
STRIPE_API_KEY=sk_test_... # Test mode
STRIPE_PRICE_MONTHLY=price_...
STRIPE_PRICE_ANNUAL=price_...
STRIPE_WEBHOOK_SECRET=whsec_...

# App
APP_ENV=development
DEBUG=true
```

### For Streamlit Cloud

Go to **Streamlit Cloud → App Settings → Secrets**:

```toml
[supabase]
url = "https://xxxxx.supabase.co"
anon_key = "eyJhbG..."

[stripe]
api_key = "sk_live_..." # Production
price_monthly = "price_..."
price_annual = "price_..."
webhook_secret = "whsec_..."
```

---

## Step 8: Deploy to Streamlit Cloud

### Push to GitHub

```bash
git add .
git commit -m "feat: Integrate Supabase for data and auth"
git push origin main
```

### Deploy via Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Connect GitHub repository
4. Select:
   - **Repository**: `UMwai/um-biotech-catalyst-radar`
   - **Branch**: `main`
   - **Main file path**: `src/app.py`
5. Click "Deploy!"

---

## Step 9: Test End-to-End

### Test Data Sync

```bash
# Manually trigger Edge Function
curl -X POST https://xxxxx.supabase.co/functions/v1/daily-sync \
  -H "Authorization: Bearer YOUR_ANON_KEY"

# Check database
supabase db inspect
```

### Test User Signup

1. Visit your Streamlit app
2. Sign up with email
3. Verify user created in Supabase Dashboard → Authentication → Users

### Test Subscription

1. Use Stripe test card: `4242 4242 4242 4242`
2. Complete checkout
3. Verify subscription in Supabase Dashboard → Table Editor → subscriptions

---

## Database Monitoring

### Check Database Size

```sql
SELECT
    pg_size_pretty(pg_database_size(current_database())) AS db_size;

-- Expected: 15-20 MB (well under 500MB free tier limit)
```

### Monitor Table Sizes

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor Function Runs

```sql
SELECT
    function_name,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_runs,
    AVG(items_processed) AS avg_items,
    MAX(completed_at - started_at) AS max_duration
FROM edge_function_runs
GROUP BY function_name;
```

---

## Troubleshooting

### Edge Function Not Running

**Check logs**:
```bash
supabase functions logs daily-sync --limit 50
```

**Common issues**:
- Missing secrets: `supabase secrets list`
- Wrong permissions: Check RLS policies
- API rate limit: Add retry logic

### Database Too Large

**Current size**:
```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

**Solutions**:
1. Run cleanup functions manually:
   ```sql
   SELECT delete_old_catalysts();
   SELECT delete_old_email_logs();
   SELECT delete_old_analytics();
   ```

2. Reduce therapeutic area filter (fewer trials)

3. Shorten rolling window (12 months → 9 months)

### RLS Policies Not Working

**Debug RLS**:
```sql
-- Check current user
SELECT auth.uid(), auth.email();

-- Check policies
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- Disable RLS temporarily (for debugging only!)
ALTER TABLE public.catalysts DISABLE ROW LEVEL SECURITY;
```

---

## Cost Monitoring

**Supabase Free Tier Limits**:
- Database: 500 MB ✅ (we use ~15-20 MB)
- Bandwidth: 5 GB/month
- Edge Function Invocations: 500K/month
- Auth users: Unlimited

**Stay under limits**:
- Cache queries in Streamlit
- Use database views for common queries
- Auto-cleanup old data
- Compress JSONB metadata

---

## Production Checklist

- [ ] Database schema deployed
- [ ] Edge Function deployed and scheduled
- [ ] Supabase Auth enabled
- [ ] RLS policies tested
- [ ] Stripe integration working
- [ ] Streamlit app deployed
- [ ] Monitoring dashboard set up
- [ ] Backup strategy defined
- [ ] Environment variables secured

---

## Next Steps

1. **Week 1**: Deploy to Supabase + test with sample data
2. **Week 2**: Integrate Streamlit app with Supabase Auth
3. **Week 3**: Launch to beta users (10-20 people)
4. **Week 4**: Monitor metrics, iterate on UX

---

**Documentation**: See `SUPABASE_SETUP.md` for architecture details
**Support**: Supabase Discord - https://discord.supabase.com/
