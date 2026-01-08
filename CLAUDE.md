# CLAUDE.md

Guidance for Claude Code when working with the Biotech Run-Up Radar project.

## Project Overview

**Biotech Run-Up Radar** is a micro-SaaS dashboard tracking Phase 2/3 clinical trial catalysts for small-cap biotech stocks. Retail traders pay $29/month for a filtered list of upcoming data releases.

**Target**: 35 subscribers = $1,000 MRR

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run src/app.py
```

## Architecture

```
src/
├── app.py              # Streamlit entry point
├── data/
│   ├── scraper.py      # ClinicalTrials.gov API v2 client
│   ├── ticker_mapper.py # Fuzzy match sponsor → ticker
│   └── enricher.py     # yfinance market cap + price data
├── ui/
│   ├── dashboard.py    # Main table view
│   └── charts.py       # Plotly price charts
└── utils/
    ├── config.py       # Environment configuration
    └── stripe_gate.py  # Subscription paywall
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `streamlit run src/app.py` | Run the app locally |
| `pytest tests/` | Run tests |
| `ruff check src/` | Lint code |
| `ruff format src/` | Format code |

## Data Flow

1. **Scraper** fetches Phase 2/3 trials from ClinicalTrials.gov API v2
2. **TickerMapper** fuzzy matches sponsor names to NASDAQ tickers
3. **StockEnricher** adds market cap + price data via yfinance
4. **Dashboard** renders filtered table with paywall for premium content

## Critical Thresholds

| Metric | Value | Rationale |
|--------|-------|-----------|
| Max Market Cap | $5B | Small caps have run-up dynamics |
| Min Fuzzy Score | 80 | Balance precision/recall |
| Cache TTL | 1 hour | Balance freshness/API limits |
| Free Preview | 10 rows | Show value before paywall |

## Agent Delegation

- **Gemini**: Use for planning, code review, large analysis tasks
- **Codex**: Use for implementation, file changes, shell commands

## Development Principles

1. **Simplicity first** - This is a specialized spreadsheet with a paywall
2. **Accuracy over completeness** - Wrong tickers destroy trust
3. **Manual verification OK** - Automate 80%, manually verify top 100 mappings
4. **No over-engineering** - MVP now, iterate based on user feedback

## Known Challenges

| Challenge | Solution |
|-----------|----------|
| Sponsor → Ticker mapping | Manual mappings for top 20 pharma + fuzzy match |
| API rate limits | Cache aggressively, daily refresh via GitHub Actions |
| Incomplete trial dates | Filter out missing completion dates |

## Testing Strategy

- Unit tests for `TickerMapper` (critical for accuracy)
- Integration tests for `ClinicalTrialsScraper`
- Manual QA of top 50 results before launch

## Environment Variables

```
STRIPE_API_KEY     - Stripe secret key
STRIPE_PRICE_ID    - Subscription price ID
STRIPE_WEBHOOK_SECRET - Webhook signing secret
APP_ENV            - development | production
DEBUG              - true | false
```

## Deployment

- **Hosting**: Streamlit Community Cloud (free tier)
- **Data refresh**: GitHub Actions daily cron
- **Secrets**: Streamlit Secrets Manager

## Related Docs

### Project Specs
- **Current status**: `specs/STATUS.md`
- **Roadmap**: `specs/ROADMAP.md`
- **Active work**: `specs/active/phase-4-deployment/`
- **What's next**: `specs/planned/phase-5-growth/`
- **Architecture**: `specs/reference/architecture/`

### External
- ClinicalTrials.gov API: https://clinicaltrials.gov/data-api/api
- Streamlit docs: https://docs.streamlit.io
- yfinance: https://github.com/ranaroussi/yfinance
