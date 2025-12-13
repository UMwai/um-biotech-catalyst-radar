# Refresh Data

Refresh all data: scrape trials, map tickers, enrich with stock data.

## Task: $ARGUMENTS

## Full Pipeline

```python
# 1. Scrape clinical trials
from src.data.scraper import ClinicalTrialsScraper
trials = ClinicalTrialsScraper().fetch_trials()

# 2. Map sponsors to tickers
from src.data.ticker_mapper import TickerMapper
mapped = TickerMapper().map_all(trials)

# 3. Enrich with stock data (yfinance)
from src.data.enricher import StockEnricher
enriched = StockEnricher().enrich(mapped)

# 4. Filter small caps (<$5B market cap)
filtered = enriched[enriched['market_cap'] < 5e9]

# 5. Save to cache
filtered.to_json('data/cached_catalysts.json')
```

## Commands
```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar
python -c "
from src.data.scraper import ClinicalTrialsScraper
from src.data.ticker_mapper import TickerMapper
from src.data.enricher import StockEnricher

trials = ClinicalTrialsScraper().fetch_trials()
mapped = TickerMapper().map_all(trials)
enriched = StockEnricher().enrich(mapped)
enriched.to_json('data/cached_catalysts.json')
print(f'Refreshed {len(enriched)} catalysts')
"
```

## Key Files
- `src/data/scraper.py` - ClinicalTrials API
- `src/data/ticker_mapper.py` - Sponsor→ticker
- `src/data/enricher.py` - yfinance enrichment

## Schedule
Automated via GitHub Actions: Daily 6 AM UTC

## Example Usage
- `/refresh-data` - Full pipeline
- `/refresh-data --skip-scrape` - Only enrich existing
