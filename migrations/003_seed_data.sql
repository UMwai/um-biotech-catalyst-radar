-- ============================================================================
-- Biotech Catalyst Radar - Seed Data (Development/Testing Only)
-- ============================================================================
-- This migration inserts sample data for local development and testing.
--
-- WARNING: DO NOT run this in production!
--
-- Contents:
--   - 3 test users (free trial, active subscriber, expired trial)
--   - 2 test subscriptions
--   - 10 sample catalysts from real NCT IDs
--   - Sample analytics events
--   - Sample email log entries
--
-- Author: Claude Code
-- Created: 2025-12-24
-- ============================================================================

-- ============================================================================
-- TEST USERS
-- ============================================================================

-- User 1: Active trial user (3 days into trial)
INSERT INTO users (id, email, password_hash, created_at, trial_start_date, trial_end_date, onboarding_completed, signup_source)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'trial.user@example.com',
    '$2b$12$KIXxLVZ5yFJ5y5Y5Y5Y5YOu8xGqJ5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Ye', -- password: 'testpass123'
    NOW() - INTERVAL '3 days',
    NOW() - INTERVAL '3 days',
    NOW() + INTERVAL '4 days',
    TRUE,
    'organic'
);

-- User 2: Active paying subscriber
INSERT INTO users (id, email, password_hash, created_at, trial_start_date, trial_end_date, stripe_customer_id, onboarding_completed, signup_source, last_login_at)
VALUES (
    '00000000-0000-0000-0000-000000000002'::uuid,
    'paying.user@example.com',
    '$2b$12$KIXxLVZ5yFJ5y5Y5Y5Y5YOu8xGqJ5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Ye',
    NOW() - INTERVAL '30 days',
    NOW() - INTERVAL '30 days',
    NOW() - INTERVAL '23 days',
    'cus_test_123456789',
    TRUE,
    'referral',
    NOW() - INTERVAL '2 hours'
);

-- User 3: Expired trial, not converted
INSERT INTO users (id, email, password_hash, created_at, trial_start_date, trial_end_date, onboarding_completed, signup_source)
VALUES (
    '00000000-0000-0000-0000-000000000003'::uuid,
    'expired.trial@example.com',
    '$2b$12$KIXxLVZ5yFJ5y5Y5Y5Y5YOu8xGqJ5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Ye',
    NOW() - INTERVAL '14 days',
    NOW() - INTERVAL '14 days',
    NOW() - INTERVAL '7 days',
    FALSE,
    'paid_ad'
);

-- ============================================================================
-- TEST SUBSCRIPTIONS
-- ============================================================================

-- Subscription for paying user (monthly plan)
INSERT INTO subscriptions (id, user_id, stripe_subscription_id, stripe_product_id, status, plan_id, plan_interval, plan_amount, current_period_start, current_period_end)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000002'::uuid,
    'sub_test_123456789',
    'prod_test_monthly',
    'active',
    'monthly_29',
    'month',
    2900, -- $29.00
    NOW() - INTERVAL '15 days',
    NOW() + INTERVAL '15 days'
);

-- Canceled subscription example (for testing churn)
INSERT INTO subscriptions (id, user_id, stripe_subscription_id, stripe_product_id, status, plan_id, plan_interval, plan_amount, current_period_start, current_period_end, cancel_at_period_end, canceled_at)
VALUES (
    '00000000-0000-0000-0000-000000000002'::uuid,
    '00000000-0000-0000-0000-000000000001'::uuid,
    'sub_test_canceled',
    'prod_test_monthly',
    'canceled',
    'monthly_29',
    'month',
    2900,
    NOW() - INTERVAL '45 days',
    NOW() - INTERVAL '15 days',
    TRUE,
    NOW() - INTERVAL '20 days'
);

-- ============================================================================
-- SAMPLE CATALYSTS
-- ============================================================================
-- These are real NCT IDs from ClinicalTrials.gov (for testing purposes)
-- Market data is fictional but realistic
-- ============================================================================

-- Catalyst 1: Phase 3 Oncology trial
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000001'::uuid,
    'NCT05123456',
    'Acme Therapeutics',
    'A Phase 3 Study of ACM-123 in Patients With Advanced Non-Small Cell Lung Cancer',
    'Phase 3',
    'Non-Small Cell Lung Cancer',
    NOW() + INTERVAL '45 days',
    'ACMT',
    95,
    'Acme Therapeutics Inc.',
    3200000000, -- $3.2B market cap
    24.50,
    12.3,
    'enriched'
);

-- Catalyst 2: Phase 2/3 Rare Disease
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000002'::uuid,
    'NCT05234567',
    'BioGen Pharma',
    'Phase 2/3 Trial of BG-456 for Treatment of Duchenne Muscular Dystrophy',
    'Phase 2/Phase 3',
    'Duchenne Muscular Dystrophy',
    NOW() + INTERVAL '60 days',
    'BGPH',
    88,
    'BioGen Pharma Corporation',
    1800000000, -- $1.8B market cap
    15.75,
    -5.2,
    'enriched'
);

-- Catalyst 3: Phase 2 Neurology
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000003'::uuid,
    'NCT05345678',
    'NeuroTech Solutions',
    'Study of NT-789 in Patients With Early-Stage Alzheimers Disease',
    'Phase 2',
    'Alzheimer Disease',
    NOW() + INTERVAL '90 days',
    'NTCH',
    92,
    'NeuroTech Solutions Inc.',
    2500000000, -- $2.5B market cap
    32.10,
    8.7,
    'enriched'
);

-- Catalyst 4: Phase 3 Cardiology (no ticker yet - pending enrichment)
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000004'::uuid,
    'NCT05456789',
    'CardioVascular Innovations LLC',
    'Phase 3 Trial of CV-321 for Heart Failure With Reduced Ejection Fraction',
    'Phase 3',
    'Heart Failure',
    NOW() + INTERVAL '120 days',
    'pending'
);

-- Catalyst 5: Phase 2 Immunology
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000005'::uuid,
    'NCT05567890',
    'ImmunoGen Therapeutics',
    'Phase 2 Study of IG-654 in Rheumatoid Arthritis',
    'Phase 2',
    'Rheumatoid Arthritis',
    NOW() + INTERVAL '75 days',
    'IMGN',
    85,
    'ImmunoGen Therapeutics Inc.',
    950000000, -- $950M market cap
    8.25,
    18.5,
    'enriched'
);

-- Catalyst 6: Phase 3 Infectious Disease
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000006'::uuid,
    'NCT05678901',
    'VaxTech Biopharma',
    'Phase 3 Trial of VT-999 Vaccine for Drug-Resistant Tuberculosis',
    'Phase 3',
    'Tuberculosis',
    NOW() + INTERVAL '30 days',
    'VAXT',
    90,
    'VaxTech Biopharma Inc.',
    4100000000, -- $4.1B market cap
    56.80,
    3.2,
    'enriched'
);

-- Catalyst 7: Phase 2 Metabolic Disease
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000007'::uuid,
    'NCT05789012',
    'MetaboCure Inc',
    'Phase 2 Study of MC-147 in Type 2 Diabetes Mellitus',
    'Phase 2',
    'Type 2 Diabetes Mellitus',
    NOW() + INTERVAL '105 days',
    'MTBC',
    87,
    'MetaboCure Inc.',
    1250000000, -- $1.25B market cap
    11.40,
    -2.1,
    'enriched'
);

-- Catalyst 8: Phase 3 Ophthalmology (small cap)
INSERT INTO catalysts (id, nct_id, sponsor, official_title, phase, indication, completion_date, ticker, ticker_confidence_score, company_name, market_cap, current_price, pct_change_30d, enrichment_status)
VALUES (
    '10000000-0000-0000-0000-000000000008'::uuid,
    'NCT05890123',
    'Visionary Pharma',
    'Phase 3 Trial of VP-258 for Age-Related Macular Degeneration',
    'Phase 3',
    'Macular Degeneration',
    NOW() + INTERVAL '50 days',
    'VISP',
    93,
    'Visionary Pharma Corporation',
    680000000, -- $680M market cap (small cap!)
    5.95,
    25.8,
    'enriched'
);

-- ============================================================================
-- CATALYST HISTORY (Price snapshots)
-- ============================================================================

-- Add 7 days of historical data for Catalyst 1
INSERT INTO catalyst_history (catalyst_id, snapshot_date, market_cap, current_price, pct_change_30d, days_until_completion)
SELECT
    '10000000-0000-0000-0000-000000000001'::uuid,
    (NOW() - INTERVAL '1 day' * i)::DATE,
    3200000000 + (i * 10000000), -- Slight variation
    24.50 + (i * 0.25),
    12.3 - (i * 0.5),
    45 + i
FROM generate_series(0, 6) AS i;

-- Add 7 days of historical data for Catalyst 2
INSERT INTO catalyst_history (catalyst_id, snapshot_date, market_cap, current_price, pct_change_30d, days_until_completion)
SELECT
    '10000000-0000-0000-0000-000000000002'::uuid,
    (NOW() - INTERVAL '1 day' * i)::DATE,
    1800000000 - (i * 5000000),
    15.75 - (i * 0.15),
    -5.2 - (i * 0.3),
    60 + i
FROM generate_series(0, 6) AS i;

-- ============================================================================
-- ANALYTICS EVENTS
-- ============================================================================

-- User 1 (trial user) events
INSERT INTO analytics_events (user_id, event_type, event_category, event_metadata, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000001'::uuid, 'signup', 'conversion', '{"source": "homepage"}', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'trial_start', 'conversion', '{"trial_days": 7}', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'page_view', 'engagement', '{"page": "dashboard"}', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'view_catalyst', 'engagement', '{"catalyst_id": "10000000-0000-0000-0000-000000000001"}', NOW() - INTERVAL '2 days'),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'view_catalyst', 'engagement', '{"catalyst_id": "10000000-0000-0000-0000-000000000002"}', NOW() - INTERVAL '1 day');

-- User 2 (paying user) events
INSERT INTO analytics_events (user_id, event_type, event_category, event_metadata, created_at)
VALUES
    ('00000000-0000-0000-0000-000000000002'::uuid, 'signup', 'conversion', '{"source": "referral", "referrer": "john@example.com"}', NOW() - INTERVAL '30 days'),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'trial_start', 'conversion', '{"trial_days": 7}', NOW() - INTERVAL '30 days'),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'subscribe', 'conversion', '{"plan": "monthly_29", "amount": 2900}', NOW() - INTERVAL '23 days'),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'page_view', 'engagement', '{"page": "dashboard"}', NOW() - INTERVAL '2 hours');

-- ============================================================================
-- EMAIL LOG
-- ============================================================================

-- Trial user emails
INSERT INTO email_log (user_id, email_type, email_campaign, subject, sent_at, delivered_at, opened_at)
VALUES
    ('00000000-0000-0000-0000-000000000001'::uuid, 'welcome', 'trial_conversion', 'Welcome to Biotech Run-Up Radar!', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000001'::uuid, 'trial_day_3', 'trial_conversion', 'Discover Phase 3 Catalysts 📊', NOW() - INTERVAL '12 hours', NOW() - INTERVAL '12 hours', NOW() - INTERVAL '10 hours');

-- Paying user emails
INSERT INTO email_log (user_id, email_type, email_campaign, subject, sent_at, delivered_at, opened_at, clicked_at)
VALUES
    ('00000000-0000-0000-0000-000000000002'::uuid, 'welcome', 'trial_conversion', 'Welcome to Biotech Run-Up Radar!', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days'),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'payment_success', 'transactional', 'Payment Confirmed - Subscription Active', NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days', NOW() - INTERVAL '23 days', NULL),
    ('00000000-0000-0000-0000-000000000002'::uuid, 'weekly_digest', 'digest', 'Top 5 Upcoming Catalysts This Week', NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days', NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days');

-- ============================================================================
-- WORKFLOW RUNS
-- ============================================================================

-- Successful daily scrape run
INSERT INTO workflow_runs (workflow_id, workflow_name, execution_id, status, started_at, completed_at, duration_seconds, records_processed)
VALUES (
    'daily_scrape',
    'Daily Catalyst Scrape',
    'exec_20251224_060000',
    'success',
    NOW() - INTERVAL '6 hours',
    NOW() - INTERVAL '5 hours 55 minutes',
    300,
    45
);

-- Successful enrichment run
INSERT INTO workflow_runs (workflow_id, workflow_name, execution_id, status, started_at, completed_at, duration_seconds, records_processed)
VALUES (
    'ticker_enrichment',
    'Ticker Enrichment',
    'exec_20251224_061000',
    'success',
    NOW() - INTERVAL '5 hours 50 minutes',
    NOW() - INTERVAL '5 hours 45 minutes',
    120,
    8
);

-- Failed run example (for testing error handling)
INSERT INTO workflow_runs (workflow_id, workflow_name, execution_id, status, started_at, completed_at, duration_seconds, records_processed, records_failed, error_message)
VALUES (
    'ticker_enrichment',
    'Ticker Enrichment',
    'exec_20251223_060000',
    'error',
    NOW() - INTERVAL '1 day 6 hours',
    NOW() - INTERVAL '1 day 5 hours 58 minutes',
    45,
    3,
    2,
    'yfinance API rate limit exceeded'
);

-- ============================================================================
-- SEED DATA SUMMARY
-- ============================================================================

SELECT 'Seed data inserted successfully!' AS status;
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS subscription_count FROM subscriptions;
SELECT COUNT(*) AS catalyst_count FROM catalysts;
SELECT COUNT(*) AS catalyst_history_count FROM catalyst_history;
SELECT COUNT(*) AS analytics_event_count FROM analytics_events;
SELECT COUNT(*) AS email_log_count FROM email_log;
SELECT COUNT(*) AS workflow_run_count FROM workflow_runs;

-- ============================================================================
-- END OF SEED DATA MIGRATION
-- ============================================================================
