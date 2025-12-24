-- ============================================================================
-- Biotech Catalyst Radar - Database Indexes
-- ============================================================================
-- This migration creates indexes to optimize query performance.
--
-- Index Strategy:
--   1. Primary lookups: email, stripe_customer_id, nct_id (unique)
--   2. Filtering: subscription status, completion dates, trial dates
--   3. Joins: Foreign key columns (user_id, catalyst_id)
--   4. Analytics: event types, timestamps
--
-- Author: Claude Code
-- Created: 2025-12-24
-- ============================================================================

-- ============================================================================
-- USERS TABLE INDEXES
-- ============================================================================

-- Fast email lookup for login (already unique, but explicit index helps)
CREATE INDEX idx_users_email ON users(email);

-- Lookup users by Stripe customer ID (webhook processing)
CREATE INDEX idx_users_stripe_customer_id ON users(stripe_customer_id);

-- Find users with active trials
CREATE INDEX idx_users_trial_end_date ON users(trial_end_date)
WHERE trial_end_date IS NOT NULL;

-- Filter by signup source for cohort analysis
CREATE INDEX idx_users_signup_source ON users(signup_source)
WHERE signup_source IS NOT NULL;

-- Find recently active users
CREATE INDEX idx_users_last_login_at ON users(last_login_at DESC);

-- ============================================================================
-- SUBSCRIPTIONS TABLE INDEXES
-- ============================================================================

-- Find subscriptions by user (frequent join)
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);

-- Filter active/canceled subscriptions (dashboard queries)
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Lookup by Stripe subscription ID (webhook processing)
CREATE INDEX idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id);

-- Find subscriptions ending soon (churn prevention)
CREATE INDEX idx_subscriptions_current_period_end ON subscriptions(current_period_end)
WHERE status = 'active';

-- Filter by plan type (revenue analytics)
CREATE INDEX idx_subscriptions_plan_id ON subscriptions(plan_id);

-- ============================================================================
-- CATALYSTS TABLE INDEXES
-- ============================================================================

-- Unique lookup by NCT ID (UPSERT operations)
CREATE UNIQUE INDEX idx_catalysts_nct_id ON catalysts(nct_id);

-- Filter by ticker symbol (user searches, stock pages)
CREATE INDEX idx_catalysts_ticker ON catalysts(ticker)
WHERE ticker IS NOT NULL;

-- Sort by completion date (upcoming catalysts)
CREATE INDEX idx_catalysts_completion_date ON catalysts(completion_date DESC)
WHERE completion_date IS NOT NULL;

-- Filter by phase (Phase 2 vs Phase 3)
CREATE INDEX idx_catalysts_phase ON catalysts(phase);

-- Find catalysts by sponsor
CREATE INDEX idx_catalysts_sponsor ON catalysts(sponsor);

-- Filter by market cap (small-cap filter: <$5B)
CREATE INDEX idx_catalysts_market_cap ON catalysts(market_cap)
WHERE market_cap IS NOT NULL;

-- Find pending enrichment jobs
CREATE INDEX idx_catalysts_enrichment_status ON catalysts(enrichment_status)
WHERE enrichment_status = 'pending';

-- Composite index for main dashboard query:
-- "Show Phase 2/3 catalysts with tickers, sorted by completion date"
CREATE INDEX idx_catalysts_dashboard ON catalysts(completion_date DESC, phase, ticker)
WHERE ticker IS NOT NULL AND completion_date IS NOT NULL;

-- ============================================================================
-- CATALYST_HISTORY TABLE INDEXES
-- ============================================================================

-- Find all snapshots for a catalyst (price chart queries)
CREATE INDEX idx_catalyst_history_catalyst_id ON catalyst_history(catalyst_id, snapshot_date DESC);

-- Find snapshots by date (daily report generation)
CREATE INDEX idx_catalyst_history_snapshot_date ON catalyst_history(snapshot_date DESC);

-- Composite unique constraint already defined in schema, but add comment
COMMENT ON INDEX unique_catalyst_snapshot IS 'Ensures only one snapshot per catalyst per day';

-- ============================================================================
-- ANALYTICS_EVENTS TABLE INDEXES
-- ============================================================================

-- Filter events by user (user profile, cohort analysis)
CREATE INDEX idx_analytics_events_user_id ON analytics_events(user_id)
WHERE user_id IS NOT NULL;

-- Filter by event type (conversion funnel analysis)
CREATE INDEX idx_analytics_events_event_type ON analytics_events(event_type);

-- Filter by event category (engagement, conversion, retention)
CREATE INDEX idx_analytics_events_event_category ON analytics_events(event_category)
WHERE event_category IS NOT NULL;

-- Time-based analytics queries
CREATE INDEX idx_analytics_events_created_at ON analytics_events(created_at DESC);

-- GIN index for JSONB metadata queries (e.g., find events with specific catalyst_id)
CREATE INDEX idx_analytics_events_metadata ON analytics_events USING GIN (event_metadata);

-- Composite index for funnel queries: "Show signup -> trial -> conversion by date"
CREATE INDEX idx_analytics_events_funnel ON analytics_events(event_type, created_at DESC);

-- ============================================================================
-- EMAIL_LOG TABLE INDEXES
-- ============================================================================

-- Find all emails sent to a user
CREATE INDEX idx_email_log_user_id ON email_log(user_id);

-- Filter by email type (trial_day_3, payment_success, etc.)
CREATE INDEX idx_email_log_email_type ON email_log(email_type);

-- Filter by campaign (trial_conversion, transactional, digest)
CREATE INDEX idx_email_log_email_campaign ON email_log(email_campaign)
WHERE email_campaign IS NOT NULL;

-- Find emails sent in a time range (reporting)
CREATE INDEX idx_email_log_sent_at ON email_log(sent_at DESC);

-- Find unopened emails (re-engagement campaigns)
CREATE INDEX idx_email_log_unopened ON email_log(sent_at DESC)
WHERE opened_at IS NULL AND delivered_at IS NOT NULL;

-- Email engagement rate queries
CREATE INDEX idx_email_log_engagement ON email_log(email_type, opened_at)
WHERE opened_at IS NOT NULL;

-- ============================================================================
-- WORKFLOW_RUNS TABLE INDEXES
-- ============================================================================

-- Find runs by workflow ID (monitoring dashboard)
CREATE INDEX idx_workflow_runs_workflow_id ON workflow_runs(workflow_id, started_at DESC);

-- Find failed runs (alerting, debugging)
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status, started_at DESC)
WHERE status IN ('error', 'running');

-- Lookup by n8n execution ID (debugging)
CREATE INDEX idx_workflow_runs_execution_id ON workflow_runs(execution_id)
WHERE execution_id IS NOT NULL;

-- Find recent runs (monitoring)
CREATE INDEX idx_workflow_runs_started_at ON workflow_runs(started_at DESC);

-- GIN index for metadata searches
CREATE INDEX idx_workflow_runs_metadata ON workflow_runs USING GIN (execution_metadata);

-- ============================================================================
-- PARTIAL INDEXES FOR COMMON FILTERS
-- ============================================================================

-- Active users only (exclude deleted/inactive accounts)
CREATE INDEX idx_users_active ON users(id, email, created_at)
WHERE is_active = TRUE;

-- Paying customers only (exclude trial users)
CREATE INDEX idx_subscriptions_paying ON subscriptions(user_id, current_period_end)
WHERE status = 'active';

-- High-confidence ticker mappings only (>80 score)
CREATE INDEX idx_catalysts_high_confidence ON catalysts(ticker, completion_date)
WHERE ticker_confidence_score >= 80;

-- Small-cap catalysts only (<$5B market cap)
CREATE INDEX idx_catalysts_small_cap ON catalysts(market_cap, completion_date)
WHERE market_cap < 5000000000 AND market_cap IS NOT NULL;

-- ============================================================================
-- MAINTENANCE NOTES
-- ============================================================================

-- Analyze tables after bulk imports to update statistics
-- Run: ANALYZE users, subscriptions, catalysts, catalyst_history, analytics_events, email_log, workflow_runs;

-- Monitor index usage:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- ORDER BY idx_scan ASC;

-- Drop unused indexes if idx_scan is consistently 0 after 30 days

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
