"""Fuzzy match sponsor names to stock tickers."""

from pathlib import Path

import pandas as pd
from thefuzz import fuzz, process


class TickerMapper:
    """Map clinical trial sponsor names to NASDAQ biotech tickers."""

    # Manual overrides for common mappings that fuzzy matching gets wrong
    MANUAL_MAPPINGS = {
        "Pfizer": "PFE",
        "Eli Lilly and Company": "LLY",
        "Eli Lilly": "LLY",
        "Johnson & Johnson": "JNJ",
        "Merck Sharp & Dohme": "MRK",
        "Merck & Co.": "MRK",
        "AbbVie": "ABBV",
        "Bristol-Myers Squibb": "BMY",
        "AstraZeneca": "AZN",
        "Novartis": "NVS",
        "Roche": "RHHBY",
        "Genentech": "RHHBY",
        "Sanofi": "SNY",
        "Amgen": "AMGN",
        "Gilead Sciences": "GILD",
        "Regeneron Pharmaceuticals": "REGN",
        "Biogen": "BIIB",
        "Vertex Pharmaceuticals": "VRTX",
        "Moderna": "MRNA",
        "BioNTech": "BNTX",
    }

    def __init__(self, reference_csv: str | Path | None = None):
        """Initialize with reference ticker data.

        Args:
            reference_csv: Path to CSV with columns [ticker, company_name]
                          If None, uses built-in NASDAQ biotech list.
        """
        self.reference_df = self._load_reference(reference_csv)
        self._build_lookup()

    # Default reference file path (relative to this file)
    DEFAULT_REFERENCE = Path(__file__).parent.parent.parent / "data" / "biotech_tickers.csv"

    def _load_reference(self, csv_path: str | Path | None) -> pd.DataFrame:
        """Load reference ticker data."""
        # Use provided path
        if csv_path and Path(csv_path).exists():
            return pd.read_csv(csv_path)

        # Use bundled reference file
        if self.DEFAULT_REFERENCE.exists():
            return pd.read_csv(self.DEFAULT_REFERENCE)

        # Fallback: empty DataFrame (will rely on manual mappings only)
        return pd.DataFrame(columns=["ticker", "company_name"])

    def _build_lookup(self) -> None:
        """Build lookup structures for fast matching."""
        self.name_to_ticker: dict[str, str] = {}
        self.ticker_choices: list[str] = []

        for _, row in self.reference_df.iterrows():
            name = str(row.get("company_name", "")).strip()
            ticker = str(row.get("ticker", "")).strip().upper()
            if name and ticker:
                self.name_to_ticker[name.lower()] = ticker
                self.ticker_choices.append(name)

    def map_sponsor_to_ticker(
        self, sponsor_name: str, min_score: int = 80
    ) -> tuple[str | None, int]:
        """Map a sponsor name to a stock ticker.

        Args:
            sponsor_name: Company name from ClinicalTrials.gov
            min_score: Minimum fuzzy match score (0-100) to accept

        Returns:
            Tuple of (ticker or None, match_score)
        """
        if not sponsor_name:
            return None, 0

        # Check manual mappings first
        for known_name, ticker in self.MANUAL_MAPPINGS.items():
            if known_name.lower() in sponsor_name.lower():
                return ticker, 100

        # Check exact match
        sponsor_lower = sponsor_name.lower().strip()
        if sponsor_lower in self.name_to_ticker:
            return self.name_to_ticker[sponsor_lower], 100

        # Fuzzy match
        if not self.ticker_choices:
            return None, 0

        result = process.extractOne(
            sponsor_name, self.ticker_choices, scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= min_score:
            matched_name = result[0]
            ticker = self.name_to_ticker.get(matched_name.lower())
            return ticker, result[1]

        return None, 0

    def map_all(
        self, df: pd.DataFrame, sponsor_col: str = "sponsor"
    ) -> pd.DataFrame:
        """Map all sponsors in a DataFrame to tickers.

        Args:
            df: DataFrame with sponsor column
            sponsor_col: Name of the sponsor column

        Returns:
            DataFrame with added 'ticker' and 'match_score' columns
        """
        results = df[sponsor_col].apply(self.map_sponsor_to_ticker)
        df = df.copy()
        df["ticker"] = results.apply(lambda x: x[0])
        df["match_score"] = results.apply(lambda x: x[1])
        return df
