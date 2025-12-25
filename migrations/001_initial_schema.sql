-- ============================================================================
-- Biotech Catalyst Radar - Initial Database Schema
-- ============================================================================
-- This migration creates the core tables for the Biotech Run-Up Radar SaaS.
--
-- Tables:
--   - users: User accounts with trial and Stripe information
--   - subscriptions: Stripe subscription data
--   - catalysts: Clinical trial catalyst data (Phase 2/3)
--   - catalyst_history: Historical snapshots of catalyst data
--   - analytics_events: User behavior tracking
--   - email_log: Email campaign tracking
--   - workflow_runs: n8n workflow execution logs
--
-- Author: Claude Code
-- Created: 2025-12-24
-- ============================================================================

-- Enable UUID extension (PostgreSQL 13+)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
-- Stores user accounts with authentication and trial tracking.
-- Trial flow: New users get 7-day trial, then paywall activates.
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- bcrypt hash, NULL for OAuth users
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Trial management
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,

    -- Stripe integration
    stripe_customer_id VARCHAR(255) UNIQUE,

    -- User state
    onboarding_completed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,

    -- Metadata
    signup_source VARCHAR(100), -- organic, referral, paid_ad
    utm_campaign VARCHAR(100),
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100)
);

-- ============================================================================
-- SUBSCRIPTIONS TABLE
-- ============================================================================
-- Tracks Stripe subscription status for each user.
-- Updated via Stripe webhooks (handled by n8n workflow).
-- ============================================================================

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Stripe data
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_product_id VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- active, canceled, past_due, trialing, unpaid

    -- Plan details
    plan_id VARCHAR(100) NOT NULL, -- monthly_29, annual_232
    plan_interval VARCHAR(20), -- month, year
    plan_amount INTEGER, -- Amount in cents (2900 = $29.00)

    -- Billing cycle
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete'))
);

-- ============================================================================
-- CATALYSTS TABLE
-- ============================================================================
-- Stores clinical trial catalyst data from ClinicalTrials.gov.
-- Enriched with ticker symbols and stock market data.
-- Updated daily via n8n workflow.
-- ============================================================================

CREATE TABLE catalysts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ClinicalTrials.gov data
    nct_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., NCT12345678
    sponsor VARCHAR(255),
    official_title TEXT,
    brief_summary TEXT,

    -- Trial details
    phase VARCHAR(50), -- Phase 1, Phase 2, Phase 3, Phase 2/Phase 3
    indication TEXT, -- Disease/condition being treated
    primary_outcome TEXT,
    enrollment_count INTEGER,
    study_type VARCHAR(100), -- Interventional, Observational

    -- Timeline
    start_date DATE,
    completion_date DATE, -- Primary completion date (the catalyst!)
    estimated_completion BOOLEAN DEFAULT TRUE, -- True if completion_date is estimated

    -- Stock mapping (enriched data)
    ticker VARCHAR(10), -- NASDAQ ticker symbol
    ticker_confidence_score INTEGER, -- 0-100, fuzzy match confidence
    company_name VARCHAR(255), -- Mapped company name

    -- Market data (from yfinance)
    market_cap BIGINT, -- Market capitalization in USD
    current_price DECIMAL(10, 2), -- Current stock price
    pct_change_30d DECIMAL(5, 2), -- 30-day price change percentage
    volume_avg_30d BIGINT, -- 30-day average volume

    -- Data quality
    data_refreshed_at TIMESTAMP DEFAULT NOW(),
    enrichment_status VARCHAR(50) DEFAULT 'pending', -- pending, enriched, failed
    enrichment_error TEXT, -- Error message if enrichment failed

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_phase CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 2/Phase 3', 'Phase 1/Phase 2'))
);

-- ============================================================================
-- CATALYST_HISTORY TABLE
-- ============================================================================
-- Daily snapshots of catalyst market data for trend analysis.
-- Enables price movement charts and historical comparisons.
-- ============================================================================

CREATE TABLE catalyst_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catalyst_id UUID NOT NULL REFERENCES catalysts(id) ON DELETE CASCADE,

    -- Snapshot date
    snapshot_date DATE NOT NULL,

    -- Market data snapshot
    market_cap BIGINT,
    current_price DECIMAL(10, 2),
    pct_change_30d DECIMAL(5, 2),
    volume_avg_30d BIGINT,

    -- Days until completion (calculated field)
    days_until_completion INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure one snapshot per catalyst per day
    CONSTRAINT unique_catalyst_snapshot UNIQUE (catalyst_id, snapshot_date)
);

-- ============================================================================
-- ANALYTICS_EVENTS TABLE
-- ============================================================================
-- Tracks user behavior for product analytics and conversion optimization.
-- Event types: page_view, signup, trial_start, conversion, churn, etc.
-- ============================================================================

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User association (nullable for anonymous events)
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(100), -- Browser session ID

    -- Event details
    event_type VARCHAR(100) NOT NULL, -- signup, login, view_catalyst, subscribe, cancel
    event_category VARCHAR(50), -- engagement, conversion, retention

    -- Event metadata (flexible JSON)
    event_metadata JSONB, -- {catalyst_id: "uuid", source: "email_link", etc.}

    -- Context
    page_url TEXT,
    referrer_url TEXT,
    user_agent TEXT,
    ip_address VARCHAR(45), -- IPv6 compatible

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EMAIL_LOG TABLE
-- ============================================================================
-- Tracks all emails sent to users for deliverability and engagement analysis.
-- Updated by SendGrid webhooks (via n8n).
-- ============================================================================

CREATE TABLE email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User and campaign
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_type VARCHAR(100) NOT NULL, -- welcome, trial_day_3, payment_success, etc.
    email_campaign VARCHAR(100), -- trial_conversion, transactional, digest

    -- Email details
    subject VARCHAR(500),
    sendgrid_message_id VARCHAR(255),

    -- Engagement tracking
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    bounced_at TIMESTAMP,
    complained_at TIMESTAMP, -- Spam complaint

    -- Metadata
    email_metadata JSONB, -- Template variables, A/B test variant, etc.

    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- WORKFLOW_RUNS TABLE
-- ============================================================================
-- Logs n8n workflow executions for monitoring and debugging.
-- Written by n8n workflows at start/end of execution.
-- ============================================================================

CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Workflow identification
    workflow_id VARCHAR(100) NOT NULL, -- daily_scrape, ticker_enrichment, etc.
    workflow_name VARCHAR(255),
    execution_id VARCHAR(100), -- n8n execution ID

    -- Execution details
    status VARCHAR(50) NOT NULL, -- running, success, error
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER, -- Calculated: completed_at - started_at

    -- Results and errors
    records_processed INTEGER,
    records_failed INTEGER,
    error_message TEXT,
    execution_metadata JSONB, -- Detailed logs, parameters, etc.

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_workflow_status CHECK (status IN ('running', 'success', 'error', 'cancelled'))
);

-- ============================================================================
-- TRIGGERS
-- ============================================================================
-- Automatically update 'updated_at' timestamps on record updates.
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_catalysts_updated_at
    BEFORE UPDATE ON catalysts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================
-- Add descriptive comments to tables and critical columns.
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts with trial tracking and Stripe integration';
COMMENT ON COLUMN users.trial_end_date IS '7 days after signup, paywall activates when NOW() > trial_end_date';
COMMENT ON COLUMN users.stripe_customer_id IS 'Stripe customer ID, set when user first interacts with Stripe';

COMMENT ON TABLE subscriptions IS 'Stripe subscription data, updated via webhooks';
COMMENT ON COLUMN subscriptions.status IS 'Subscription status: active = paying customer, canceled = churned';

COMMENT ON TABLE catalysts IS 'Phase 2/3 clinical trial catalysts from ClinicalTrials.gov';
COMMENT ON COLUMN catalysts.completion_date IS 'Primary completion date - the catalyst event';
COMMENT ON COLUMN catalysts.ticker_confidence_score IS 'Fuzzy match score (0-100), >80 is high confidence';

COMMENT ON TABLE catalyst_history IS 'Daily snapshots of catalyst market data for trend analysis';

COMMENT ON TABLE analytics_events IS 'User behavior tracking for product analytics';

COMMENT ON TABLE email_log IS 'Email campaign tracking with engagement metrics';

COMMENT ON TABLE workflow_runs IS 'n8n workflow execution logs for monitoring';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
