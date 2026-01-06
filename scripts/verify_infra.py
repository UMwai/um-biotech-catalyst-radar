"""Verification script for Biotech Radar components."""

import logging
import sys
from datetime import datetime

# Add src to path
sys.path.append("src")

from data.fda_scraper import FDAScraper
from data.sec_ingestor import SECIngestor
from data.catalyst_aggregator import CatalystAggregator
from ui.components.chatbot import render_chatbot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_infrastructure():
    logger.info("Verifying Infrastructure...")
    
    # 1. FDA Scraper
    try:
        fda = FDAScraper()
        # Mock fetch (or real if implemented)
        df_fda = fda.fetch_pdufa_dates()
        logger.info(f"FDA Scraper returned {len(df_fda)} rows.")
    except Exception as e:
        logger.error(f"FDA Scraper failed: {e}")

    # 2. SEC Ingestor
    try:
        sec = SECIngestor()
        # Mock download (don't actually download to save time/bandwidth in test)
        logger.info("SEC Ingestor initialized.")
    except Exception as e:
        logger.error(f"SEC Ingestor failed: {e}")

    # 3. Catalyst Aggregator
    try:
        agg = CatalystAggregator()
        df_agg = agg.fetch_all_catalysts()
        logger.info(f"Aggregator returned {len(df_agg)} rows.")
        if not df_agg.empty:
            logger.info(f"Columns: {df_agg.columns.tolist()}")
            logger.info(f"Sample: \n{df_agg.head(2)}")
    except Exception as e:
        logger.error(f"Aggregator failed: {e}")

if __name__ == "__main__":
    verify_infrastructure()
    print("\nVerification Complete.")
