-- Phase 3 Schema Additions
-- Run with: sqlite3 data/biotech_catalyst.db < migrations/005_phase3_schema.sql

-- 1. Extend users_local for memory
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE, using workaround
-- These columns may already exist, so we catch errors gracefully

-- 2. Chat sessions and messages
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users_local(id),
    session_id TEXT NOT NULL UNIQUE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON: extracted entities, citations used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Watchlist alerts
CREATE TABLE IF NOT EXISTS watchlist_alerts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users_local(id),
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- 'date_window', 'timeline_change', 'red_flag'
    trigger_event TEXT NOT NULL,  -- Description of what triggered
    catalyst_id INTEGER REFERENCES catalysts_v2(id),
    severity TEXT DEFAULT 'info',  -- 'info', 'warning', 'critical'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    delivered_via TEXT  -- 'in_app', 'email', 'both'
);

-- 4. Extraction verifications (dual-model)
CREATE TABLE IF NOT EXISTS extraction_verifications (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,  -- 'sec_filing', 'trial', 'fda_event'
    source_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    primary_model TEXT NOT NULL,  -- 'claude-haiku'
    primary_value TEXT,
    secondary_model TEXT NOT NULL,  -- 'gemini-flash'
    secondary_value TEXT,
    is_match BOOLEAN,
    confidence_score REAL,
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP,
    reviewed_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Backtest tracking
CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sample_size INTEGER,
    overall_accuracy REAL,
    sec_accuracy REAL,
    trial_accuracy REAL,
    fda_accuracy REAL,
    alert_sent BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES backtest_runs(id),
    source_type TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    original_value TEXT,
    reextracted_value TEXT,
    is_match BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON watchlist_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON watchlist_alerts(user_id, acknowledged_at);
CREATE INDEX IF NOT EXISTS idx_verifications_review ON extraction_verifications(needs_review);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON backtest_runs(run_date);
