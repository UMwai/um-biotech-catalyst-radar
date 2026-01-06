-- ============================================================================
-- Biotech Catalyst Radar - Phase 2 MVP SQLite Schema
-- ============================================================================
-- This migration extends the schema with Phase 2 MVP tables:
--   - fda_events: FDA calendar events (PDUFA, AdCom, approvals)
--   - sec_filings: SEC 8-K/10-K filings with extracted data
--   - clinical_trials: Enhanced CTgov data with design scoring
--   - insights: AI-generated proactive feed items
--   - email_digests: Digest email tracking
--
-- For local development with SQLite. Production uses Supabase (Postgres).
-- ============================================================================

-- ============================================================================
-- COMPANIES TABLE (master list)
-- ============================================================================
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    market_cap_usd REAL,
    enterprise_value_usd REAL,
    sector TEXT DEFAULT 'Biotech',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CATALYSTS TABLE (the core data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS catalysts_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    catalyst_type TEXT NOT NULL,  -- 'PDUFA', 'Phase2_Readout', 'Phase3_Readout', 'AdCom', 'CRL_Response'
    catalyst_date DATE,
    catalyst_date_precision TEXT,  -- 'exact', 'month', 'quarter', 'half', 'year'
    indication TEXT,
    drug_name TEXT,
    trial_phase TEXT,  -- 'Phase1', 'Phase2', 'Phase3', 'NDA', 'BLA'
    trial_nct_id TEXT,
    source TEXT NOT NULL,  -- 'FDA', 'SEC_8K', 'CTgov', 'Manual'
    source_reference TEXT,  -- 'ACAD_2025_10K, pg 42'
    confidence_score REAL,  -- 0-1, from LLM extraction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- FDA EVENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS fda_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    event_type TEXT NOT NULL,  -- 'PDUFA', 'AdCom', 'CRL', 'Approval', 'RTF'
    event_date DATE,
    drug_name TEXT,
    indication TEXT,
    source_url TEXT,
    raw_text TEXT,  -- Original scraped text for reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SEC FILINGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS sec_filings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    filing_type TEXT NOT NULL,  -- '10-K', '10-Q', '8-K'
    filing_date DATE NOT NULL,
    accession_number TEXT UNIQUE,
    file_path TEXT,  -- local path to downloaded filing
    -- Extracted financial data
    cash_runway_months REAL,
    monthly_burn_rate_usd REAL,
    cash_position_usd REAL,
    -- Extraction metadata
    extracted_at TIMESTAMP,
    extraction_model TEXT,  -- 'claude-haiku-4.5', 'gemini-flash', etc.
    extraction_confidence REAL,  -- 0-1
    raw_text TEXT,  -- for re-processing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CLINICAL TRIALS TABLE (enhanced from CTgov)
-- ============================================================================
CREATE TABLE IF NOT EXISTS clinical_trials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    nct_id TEXT UNIQUE NOT NULL,
    title TEXT,
    phase TEXT,
    status TEXT,  -- 'Recruiting', 'Active', 'Completed', 'Terminated'
    conditions TEXT,  -- JSON array
    interventions TEXT,  -- JSON array
    primary_completion_date DATE,
    study_completion_date DATE,
    enrollment_count INTEGER,
    -- LLM-assessed trial design quality
    trial_design_score REAL,  -- 0-100
    trial_design_notes TEXT,  -- 'Double-blind, placebo-controlled'
    design_scoring_model TEXT,
    -- Sponsor/Company mapping
    sponsor_name TEXT,
    sponsor_ticker TEXT,
    ticker_confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INSIGHTS TABLE (proactive feed)
-- ============================================================================
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    catalyst_id INTEGER,  -- References catalysts_v2(id)
    insight_type TEXT NOT NULL,  -- 'opportunity', 'red_flag', 'update'
    headline TEXT NOT NULL,  -- 'ACAD: Phase 3 readout in 14 days'
    body TEXT,  -- Extended explanation
    conviction_score REAL,  -- 0-100
    factors TEXT,  -- JSON: {"days_to_catalyst": 14, "cash_runway": 18, ...}
    source_citations TEXT,  -- JSON array of source references
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by TEXT,  -- Model that generated this insight
    expires_at TIMESTAMP,  -- After catalyst date
    is_active INTEGER DEFAULT 1  -- SQLite boolean
);

-- ============================================================================
-- USERS TABLE (simplified for local dev)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users_local (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    stripe_customer_id TEXT,
    subscription_status TEXT DEFAULT 'free',  -- 'free', 'active', 'cancelled'
    subscription_tier TEXT DEFAULT 'free',  -- 'free', 'paid'
    watchlist TEXT,  -- JSON array of tickers
    preferences TEXT,  -- JSON: notification settings, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- ============================================================================
-- EMAIL DIGESTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS email_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users_local(id),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    insight_ids TEXT,  -- JSON array of insight IDs included
    status TEXT  -- 'sent', 'failed', 'bounced'
);

-- ============================================================================
-- CHAT HISTORY TABLE (for session memory)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER REFERENCES users_local(id),
    role TEXT NOT NULL,  -- 'user', 'assistant'
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON: model used, tokens, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_catalysts_v2_date ON catalysts_v2(catalyst_date);
CREATE INDEX IF NOT EXISTS idx_catalysts_v2_company ON catalysts_v2(company_id);
CREATE INDEX IF NOT EXISTS idx_insights_active ON insights(is_active, generated_at);
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_fda_events_date ON fda_events(event_date);
CREATE INDEX IF NOT EXISTS idx_sec_filings_date ON sec_filings(filing_date);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_nct ON clinical_trials(nct_id);
CREATE INDEX IF NOT EXISTS idx_clinical_trials_completion ON clinical_trials(primary_completion_date);
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
