"""Catalyst Aggregator to combine multiple data sources."""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from data.scraper import ClinicalTrialsScraper
from data.fda_scraper import FDAScraper
from data.ticker_mapper import TickerMapper

logger = logging.getLogger(__name__)

class CatalystAggregator:
    """Aggregates catalyst data from ClinicalTrials.gov and FDA sources."""

    def __init__(self, mapper: Optional[TickerMapper] = None):
        self.ct_scraper = ClinicalTrialsScraper(months_ahead=6)
        self.fda_scraper = FDAScraper()
        self.mapper = mapper or TickerMapper()

    def fetch_all_catalysts(self) -> pd.DataFrame:
        """Fetch and merge all catalysts."""
        # 1. Fetch Clinical Trials
        try:
            ct_df = self.ct_scraper.fetch_trials()
            # Map sponsors to tickers
            if not ct_df.empty:
                ct_df = self.mapper.map_all(ct_df)
                ct_df["source"] = "ClinicalTrials.gov"
                ct_df["catalyst_type"] = ct_df["phase"] + " Completion"
                # Ensure common columns
                ct_df["description"] = ct_df["title"]
        except Exception as e:
            logger.error(f"Error fetching clinical trials: {e}")
            ct_df = pd.DataFrame()

        # 2. Fetch FDA Data
        try:
            fda_df = self.fda_scraper.fetch_pdufa_dates()
            if not fda_df.empty:
                fda_df["source"] = "FDA"
                fda_df["phase"] = "Regulatory"
                # Build description from available columns
                event_type = fda_df.get("event_type", pd.Series(["PDUFA"] * len(fda_df)))
                drug_name = fda_df.get("drug", fda_df.get("drug_name", pd.Series([""] * len(fda_df))))
                fda_df["description"] = drug_name.astype(str) + " (" + event_type.astype(str) + ")"
                fda_df["catalyst_type"] = fda_df.get("event_type", "PDUFA")
                fda_df["catalyst_date"] = fda_df.get("event_date")
        except Exception as e:
            logger.error(f"Error fetching FDA data: {e}")
            fda_df = pd.DataFrame()

        # 3. Merge
        # Define common schema
        common_columns = ["ticker", "catalyst_date", "catalyst_type", "description", "source", "nct_id", "status", "phase"]
        
        # Standardize CT DF
        if not ct_df.empty:
            # fill missing
            for col in common_columns:
                if col not in ct_df.columns:
                    ct_df[col] = None
            ct_final = ct_df[common_columns]
        else:
            ct_final = pd.DataFrame(columns=common_columns)

        # Standardize FDA DF
        if not fda_df.empty:
            for col in common_columns:
                if col not in fda_df.columns:
                    fda_df[col] = None
            fda_final = fda_df[common_columns]
        else:
            fda_final = pd.DataFrame(columns=common_columns)

        combined = pd.concat([ct_final, fda_final], ignore_index=True)
        
        # Sort
        if not combined.empty:
            combined["catalyst_date"] = pd.to_datetime(combined["catalyst_date"], errors="coerce")
            combined = combined.sort_values("catalyst_date").reset_index(drop=True)

        return combined

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agg = CatalystAggregator()
    df = agg.fetch_all_catalysts()
    print(df.head())
