# Scrape Trials

Scrape clinical trials from ClinicalTrials.gov API v2.

## Task: $ARGUMENTS

## Agent Configuration

Use the Task tool with `subagent_type="data-pipeline-engineer"`:

```
Fetch Phase 2/3 clinical trials with upcoming completion dates.

## Data Pipeline
1. Query ClinicalTrials.gov API v2
2. Filter for Phase 2 and Phase 3 trials
3. Focus on trials completing in next 3 months
4. Extract: NCT ID, Sponsor, Phase, Completion Date, Indication
5. Save to data/cached_catalysts.json
```

## Commands
```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar
python -c "from src.data.scraper import ClinicalTrialsScraper; s = ClinicalTrialsScraper(); print(s.fetch_trials())"
```

## Key Files
- `src/data/scraper.py` - ClinicalTrials.gov API client
- `data/cached_catalysts.json` - Cached results
- `data/biotech_tickers.csv` - Reference ticker list

## Automation
GitHub Actions runs daily at 6 AM UTC:
`.github/workflows/daily_scrape.yml`

## Example Usage
- `/scrape-trials` - Run full scrape
- `/scrape-trials --phase 3 only`
- `/scrape-trials --months-ahead 6`
