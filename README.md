# Biotech Run-Up Radar

A micro-SaaS dashboard that tracks Phase 2/3 clinical trial catalysts for small-cap biotech stocks.

## The Problem

Biotech stocks often see a 20-50% "run-up" in the 2-6 weeks before major clinical trial results. Retail traders know this strategy works, but tracking thousands of trial dates on ClinicalTrials.gov is impossible.

## The Solution

A clean, filtered list of small-cap stocks with Phase 2/3 trials ending in the next 30-60 days.

**Price**: $19/month

## Tech Stack

- **Backend**: Python (Pandas for data processing)
- **Frontend**: Streamlit
- **Data Source**: ClinicalTrials.gov API v2
- **Payments**: Stripe

## Features

- Daily scrape of ClinicalTrials.gov
- Fuzzy matching of sponsor names to NASDAQ tickers
- Market cap filtering (<$5B small caps only)
- 6-month price chart with catalyst date overlay
- Stripe subscription gating

## Quick Start

```bash
# Clone
git clone https://github.com/UMwai/um-biotech-catalyst-radar.git
cd um-biotech-catalyst-radar

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
streamlit run src/app.py
```

## Project Structure

```
um-biotech-catalyst-radar/
├── src/
│   ├── app.py              # Streamlit main app
│   ├── data/
│   │   ├── scraper.py      # ClinicalTrials.gov API client
│   │   ├── ticker_mapper.py # Sponsor → Ticker fuzzy matching
│   │   └── enricher.py     # yfinance market cap + price data
│   ├── ui/
│   │   ├── dashboard.py    # Main dashboard view
│   │   └── charts.py       # Price charts with catalyst overlay
│   └── utils/
│       ├── config.py       # Environment/config management
│       └── stripe_gate.py  # Subscription gating logic
├── data/
│   └── nasdaq_biotech.csv  # Ticker reference data
├── tests/
├── .github/workflows/
│   └── daily_scrape.yml    # GitHub Actions daily data refresh
├── requirements.txt
└── README.md
```

## Development

```bash
# Run tests
pytest tests/

# Lint
ruff check src/

# Format
ruff format src/
```

## Deployment

Hosted on [Streamlit Community Cloud](https://share.streamlit.io/) (free tier).

## License

MIT
