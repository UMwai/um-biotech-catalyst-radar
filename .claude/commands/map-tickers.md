# Map Tickers

Map clinical trial sponsors to stock ticker symbols.

## Task: $ARGUMENTS

## Mapping Strategy

### Priority Order
1. **Manual Overrides** (20+ common pharma)
   - Pfizer → PFE
   - Eli Lilly → LLY
   - Novartis → NVS

2. **Exact Match** against `biotech_tickers.csv`

3. **Fuzzy Match** (thefuzz library)
   - Algorithm: token_sort_ratio
   - Minimum score: 80
   - Levenshtein distance optimization

## Commands
```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar
python -c "from src.data.ticker_mapper import TickerMapper; m = TickerMapper(); print(m.map_all())"
```

## Key Files
- `src/data/ticker_mapper.py` - Fuzzy matching logic
- `data/biotech_tickers.csv` - 60+ biotech tickers

## Quality Checks
- Top 50 matches verified manually before launch
- Log unmatched sponsors for manual review
- Flag low-confidence matches (score 80-85)

## Example Usage
- `/map-tickers` - Run full mapping
- `/map-tickers "Moderna Inc"` - Test single sponsor
- `/map-tickers --review-unmatched`
