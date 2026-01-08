# Current Architecture - MVP State

## Overview

The current implementation is a **monolithic Streamlit application** with Python-based data processing and minimal automation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Streamlit Cloud (Free Tier)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           src/app.py (Main App)                    │    │
│  │  - Page rendering                                  │    │
│  │  - Session state management                        │    │
│  │  - In-memory caching (@st.cache_data, 1hr TTL)    │    │
│  └────────────────────────────────────────────────────┘    │
│                       │                                      │
│  ┌────────────────────┼────────────────────────────┐        │
│  │                    │                             │        │
│  │  ┌─────────────────▼──────┐  ┌─────────────────▼──────┐ │
│  │  │  UI Layer              │  │  Data Layer            │ │
│  │  │  - dashboard.py        │  │  - scraper.py          │ │
│  │  │  - charts.py           │  │  - ticker_mapper.py    │ │
│  │  │  - Plotly rendering    │  │  - enricher.py         │ │
│  │  └────────────────────────┘  └────────────────────────┘ │
│  │                                        │                  │
│  │  ┌─────────────────────────────────────┼────────────┐   │
│  │  │  Utils Layer                        │            │   │
│  │  │  - config.py (env vars)             │            │   │
│  │  │  - stripe_gate.py (MVP stub)        │            │   │
│  │  └─────────────────────────────────────┘            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ HTTP API calls
                       │
        ┌──────────────┼──────────────┐
        │              │               │
        ▼              ▼               ▼
┌──────────────┐ ┌──────────┐ ┌─────────────────┐
│ClinicalTrials│ │ yfinance │ │ Stripe API      │
│.gov API v2   │ │ (Yahoo)  │ │ (not integrated)│
└──────────────┘ └──────────┘ └─────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               GitHub Actions (Daily Cron)                    │
│                                                              │
│  Workflow: .github/workflows/daily_scrape.yml               │
│  - Runs: 6:00 AM UTC daily                                  │
│  - Executes: scripts/generate_report.py                     │
│  - Outputs: docs/catalyst_report.html (committed to repo)   │
│  - Side effect: data/latest_catalysts.csv updated           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   File System (Git Repo)                     │
│                                                              │
│  data/                                                       │
│  ├── biotech_tickers.csv      (manual curation)            │
│  ├── latest_catalysts.csv     (generated daily)            │
│  └── catalyst_report.csv      (generated daily)            │
│                                                              │
│  docs/                                                       │
│  └── catalyst_report.html     (generated daily)            │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend - Streamlit App

**Technology**: Streamlit (Python web framework)

**Location**: `src/app.py`, `src/ui/`

**Responsibilities**:
- Render interactive dashboard
- Handle user filters (phase, date range)
- Display paywall (currently session-based)
- Generate price charts with Plotly

**State Management**:
- `st.session_state` for demo mode flag
- `@st.cache_data(ttl=3600)` for data loading (1-hour cache)

**Limitations**:
- No persistent user sessions across browser restarts
- No user authentication (session-only demo toggle)
- Data reloads every hour even if unchanged
- No user-specific data (no database)

---

### 2. Data Pipeline

#### A. ClinicalTrials.gov Scraper

**File**: `src/data/scraper.py`

**Process**:
1. Query ClinicalTrials.gov API v2
2. Filter for Phase 2/3 trials
3. Filter for trials completing in next 3 months
4. Extract: NCT ID, sponsor, phase, completion date, indication
5. Return pandas DataFrame

**API Endpoint**: `https://clinicaltrials.gov/api/v2/studies`

**Limitations**:
- No pagination (capped at 10 pages)
- No retry logic on failures
- No incremental updates (full refresh every time)
- Synchronous blocking calls

---

#### B. Ticker Mapper

**File**: `src/data/ticker_mapper.py`

**Process**:
1. Check manual overrides dictionary (20+ pharma companies)
2. If not found, fuzzy match against `biotech_tickers.csv`
3. Use `thefuzz` library (token_sort_ratio algorithm)
4. Require minimum score of 80
5. Return matched ticker or NaN

**Data Source**: `data/biotech_tickers.csv` (60+ tickers, manually curated)

**Limitations**:
- Manual mappings hardcoded in Python file
- No confidence scoring in output
- No logging of unmatched sponsors
- CSV file manually maintained

---

#### C. Stock Enricher

**File**: `src/data/enricher.py`

**Process**:
1. For each ticker, call yfinance API
2. Fetch market cap, current price, 30-day % change
3. Fetch 6-month price history for charts
4. Filter out tickers with market cap >$5B
5. Return enriched DataFrame

**Data Source**: yfinance (Yahoo Finance scraper)

**Limitations**:
- Sequential API calls (slow for large datasets)
- No error handling for delisted stocks
- No caching of price data
- yfinance is unofficially maintained (fragile)

---

### 3. Automation

#### GitHub Actions Workflow

**File**: `.github/workflows/daily_scrape.yml`

**Trigger**: Cron schedule (daily at 6:00 AM UTC)

**Process**:
```yaml
- Checkout repo
- Install Python dependencies
- Run scripts/generate_report.py
- Commit updated files to repo
- Push to main branch
```

**Outputs**:
- `data/latest_catalysts.csv`
- `data/catalyst_report.csv`
- `docs/catalyst_report.html`

**Limitations**:
- Runs on GitHub's servers (limited compute)
- No notifications on failure
- No retry logic
- Report committed to Git (repo bloat over time)

---

### 4. Data Storage

**Current State**: **File-based (CSV files in Git repo)**

**Files**:
- `data/biotech_tickers.csv` - Reference ticker list
- `data/latest_catalysts.csv` - Generated catalyst data
- `data/catalyst_report.csv` - Subset for report

**Limitations**:
- No database (can't query efficiently)
- No user data storage
- No subscription status persistence
- No historical data tracking
- Git history bloated with data commits

---

### 5. Monetization Layer

**Current State**: **MVP stub (session-based demo mode)**

**File**: `src/utils/stripe_gate.py`

**Function**: `check_subscription(email)`

**Current Logic**:
```python
def check_subscription(email=None):
    # Check session state for demo mode
    if st.session_state.get("is_subscribed", False):
        return True

    # TODO: Integrate with Stripe Customer Portal
    return False
```

**Limitations**:
- No real authentication
- No Stripe API integration
- No webhook handling
- No subscription status checking
- No trial period tracking

---

## Data Flow

### User Visit Flow

```
1. User visits Streamlit app
2. App checks cache (1hr TTL)
   - If cache hit: serve cached data
   - If cache miss:
     a. Scrape ClinicalTrials.gov
     b. Map sponsors → tickers
     c. Enrich with yfinance data
     d. Filter small caps
     e. Cache result
3. Render dashboard with filters
4. User applies filters (phase, date range)
5. Check subscription status (always returns False in production)
6. Show paywall if not subscribed
```

### Daily Refresh Flow

```
1. GitHub Actions cron triggers (6 AM UTC)
2. Run generate_report.py:
   a. Scrape trials
   b. Map tickers
   c. Enrich with stock data
   d. Generate HTML report
   e. Save CSVs
3. Commit files to repo
4. Push to main branch
5. Streamlit Cloud auto-deploys (if app.py changed)
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Streamlit | Latest |
| **Charting** | Plotly | Latest |
| **Data Processing** | Pandas | Latest |
| **HTTP Requests** | requests | Latest |
| **Stock Data** | yfinance | Latest |
| **Fuzzy Matching** | thefuzz | Latest |
| **Hosting** | Streamlit Community Cloud | Free |
| **Automation** | GitHub Actions | - |
| **Version Control** | Git + GitHub | - |
| **Payments** | Stripe (planned) | Not integrated |

---

## Pain Points & Limitations

### 1. No Real Monetization
- [ ] No user authentication
- [ ] No subscription tracking
- [ ] No payment processing
- [ ] No trial period enforcement

### 2. Poor Data Architecture
- [ ] File-based storage (no database)
- [ ] No incremental updates
- [ ] No historical tracking
- [ ] Git repo bloated with data

### 3. Fragile Automation
- [ ] No failure notifications
- [ ] No retry logic
- [ ] Sequential API calls (slow)
- [ ] yfinance dependency risk

### 4. Scalability Issues
- [ ] In-memory caching only (1hr TTL)
- [ ] No multi-user support
- [ ] Synchronous data pipeline
- [ ] Free tier limits (Streamlit Cloud)

### 5. Operational Blind Spots
- [ ] No monitoring/observability
- [ ] No error tracking
- [ ] No analytics
- [ ] No A/B testing capability

---

## What Works Well

✅ **Simple Architecture** - Easy to understand and modify
✅ **Free Hosting** - Streamlit Cloud free tier
✅ **Functional MVP** - Core data pipeline works
✅ **Automated Refresh** - GitHub Actions reliable
✅ **Good UX** - Streamlit provides clean UI

---

## Migration Path to Target Architecture

See: [02-target-architecture.md](./02-target-architecture.md)

**Key Changes Needed**:
1. Replace file storage → PostgreSQL
2. Replace GitHub Actions → n8n workflows
3. Add Stripe integration + webhooks
4. Add user authentication system
5. Add monitoring and observability
6. Implement proper caching strategy

---

**Last Updated**: 2025-12-24
**Status**: ✅ Documented
