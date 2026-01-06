#!/usr/bin/env python3
"""Daily data refresh script for GitHub Actions cron.

Per spec Section 5.4:
- Frequency: Daily
- Timing: Non-peak hours (overnight US, e.g., 2-4 AM ET)

This script:
1. Syncs FDA calendar data
2. Downloads and parses SEC filings for top biotechs
3. Refreshes ClinicalTrials.gov data with design scoring
4. Generates proactive daily feed
5. (Optional) Sends email digests at 7 AM ET

Usage:
    python scripts/daily_refresh.py              # Full refresh
    python scripts/daily_refresh.py --feed-only  # Just regenerate feed
    python scripts/daily_refresh.py --email      # Run email digest job
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Top biotech tickers to refresh (Phase 2 MVP - top 100)
# This list would be dynamically generated in production
TOP_BIOTECH_TICKERS = [
    "ACAD", "SAVA", "AXSM", "IMVT", "RXRX",
    "MRNA", "BNTX", "NVAX", "SGEN", "ALNY",
    "INCY", "EXEL", "BMRN", "SRPT", "RARE",
    "BLUE", "CRSP", "EDIT", "NTLA", "BEAM",
    "IONS", "HZNP", "UTHR", "NBIX", "PCVX",
    "RCUS", "RVNC", "ZNTL", "ALLO", "ARWR",
    "APLS", "LEGN", "VERV", "RLAY", "KRYS",
    "ADPT", "FATE", "ABCL", "ARVN", "SWTX",
    "DAWN", "TGTX", "MGNX", "XNCR", "KYMR",
    "YMAB", "REPL", "MIRM", "DCPH", "MNKD",
]


def sync_fda_data(db) -> int:
    """Sync FDA calendar events to database."""
    logger.info("Starting FDA data sync...")
    try:
        from data.fda_scraper import sync_fda_to_database
        count = sync_fda_to_database(db)
        logger.info(f"FDA sync complete: {count} events")
        return count
    except Exception as e:
        logger.error(f"FDA sync failed: {e}")
        return 0


def sync_sec_data(db, tickers: list[str]) -> int:
    """Sync SEC filings for specified tickers."""
    logger.info(f"Starting SEC data sync for {len(tickers)} tickers...")
    try:
        from data.sec_ingestor import sync_sec_to_database
        count = sync_sec_to_database(db, tickers)
        logger.info(f"SEC sync complete: {count} filings processed")
        return count
    except Exception as e:
        logger.error(f"SEC sync failed: {e}")
        return 0


def sync_ctgov_data(db, months_ahead: int = 6) -> int:
    """Sync ClinicalTrials.gov data."""
    logger.info(f"Starting CTgov sync (looking {months_ahead} months ahead)...")
    try:
        from data.scraper import sync_ctgov_to_database
        count = sync_ctgov_to_database(db, months_ahead=months_ahead, score_designs=False)
        logger.info(f"CTgov sync complete: {count} trials")
        return count
    except Exception as e:
        logger.error(f"CTgov sync failed: {e}")
        return 0


def generate_daily_feed(db) -> int:
    """Generate proactive daily feed."""
    logger.info("Generating daily feed...")
    try:
        from data.feed_generator import FeedGenerator

        generator = FeedGenerator(db=db)
        use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
        insights = generator.generate_feed(days_ahead=90, limit=15, use_llm=use_llm)
        saved = generator.save_feed_to_db(insights)
        logger.info(f"Feed generation complete: {saved} insights")
        return saved
    except Exception as e:
        logger.error(f"Feed generation failed: {e}")
        return 0


def run_email_digests(db) -> dict:
    """Send email digests to all users."""
    logger.info("Starting email digest job...")
    try:
        from utils.email_digest import run_daily_digest_job
        results = run_daily_digest_job(db)
        logger.info(f"Email digest complete: {results}")
        return results
    except Exception as e:
        logger.error(f"Email digest failed: {e}")
        return {"sent": 0, "failed": 0, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Daily data refresh script")
    parser.add_argument("--feed-only", action="store_true", help="Only regenerate feed")
    parser.add_argument("--email", action="store_true", help="Run email digest job")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to refresh")
    parser.add_argument("--months", type=int, default=6, help="Months ahead for CTgov")
    args = parser.parse_args()

    start_time = datetime.now()
    logger.info(f"=== Daily Refresh Started at {start_time.isoformat()} ===")

    # Initialize database
    try:
        from utils.sqlite_db import get_db
        db = get_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    results = {
        "fda_events": 0,
        "sec_filings": 0,
        "ctgov_trials": 0,
        "catalysts": 0,
        "feed_insights": 0,
        "emails": {"sent": 0, "failed": 0},
    }

    # Run email digest only
    if args.email:
        results["emails"] = run_email_digests(db)
        logger.info("Email digest job complete")
        return

    # Feed only mode
    if args.feed_only:
        results["feed_insights"] = generate_daily_feed(db)
        logger.info("Feed-only refresh complete")
        _print_summary(results, start_time)
        return

    # Full refresh
    tickers = args.tickers or TOP_BIOTECH_TICKERS

    # 1. FDA Calendar
    results["fda_events"] = sync_fda_data(db)

    # 2. SEC Filings (limited to save time)
    sec_tickers = tickers[:20]  # Process top 20 for MVP
    results["sec_filings"] = sync_sec_data(db, sec_tickers)

    # 3. ClinicalTrials.gov
    results["ctgov_trials"] = sync_ctgov_data(db, months_ahead=args.months)

    # 4. Aggregate catalysts into unified table
    logger.info("Aggregating catalysts...")
    results["catalysts"] = db.aggregate_catalysts()

    # 5. Generate Feed
    results["feed_insights"] = generate_daily_feed(db)

    # Print summary
    _print_summary(results, start_time)


def _print_summary(results: dict, start_time: datetime) -> None:
    """Print refresh summary."""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("DAILY REFRESH SUMMARY")
    logger.info("=" * 60)
    logger.info(f"FDA Events Synced:     {results.get('fda_events', 0)}")
    logger.info(f"SEC Filings Processed: {results.get('sec_filings', 0)}")
    logger.info(f"CTgov Trials Synced:   {results.get('ctgov_trials', 0)}")
    logger.info(f"Catalysts Aggregated:  {results.get('catalysts', 0)}")
    logger.info(f"Feed Insights Created: {results.get('feed_insights', 0)}")
    logger.info(f"Emails Sent:          {results.get('emails', {}).get('sent', 0)}")
    logger.info("-" * 60)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Completed at: {end_time.isoformat()}")
    logger.info("=" * 60)

    # Check for MVP criteria
    total_catalysts = results.get("ctgov_trials", 0) + results.get("fda_events", 0)
    if total_catalysts >= 500:
        logger.info("✅ MVP Criteria: ≥500 catalysts in database")
    else:
        logger.warning(f"⚠️ MVP Criteria: Need ≥500 catalysts (have {total_catalysts})")

    if results.get("feed_insights", 0) >= 10:
        logger.info("✅ MVP Criteria: Daily feed generates 10+ insights")
    else:
        logger.warning(f"⚠️ MVP Criteria: Need 10+ insights (have {results.get('feed_insights', 0)})")


if __name__ == "__main__":
    main()
