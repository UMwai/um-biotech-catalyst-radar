"""Enrich trial data with stock market data from yfinance."""

from typing import Optional

import pandas as pd
import yfinance as yf


class StockEnricher:
    """Add market cap and price data to trial records."""

    # Filter out large caps (they don't have the same run-up dynamics)
    MAX_MARKET_CAP = 5_000_000_000  # $5B

    def __init__(self, max_market_cap: float = MAX_MARKET_CAP):
        self.max_market_cap = max_market_cap

    def enrich(self, df: pd.DataFrame, ticker_col: str = "ticker") -> pd.DataFrame:
        """Add market cap and current price to DataFrame.

        Args:
            df: DataFrame with ticker column
            ticker_col: Name of the ticker column

        Returns:
            DataFrame with added 'market_cap', 'current_price', 'pct_change_30d' columns
        """
        df = df.copy()

        # Initialize new columns
        df["market_cap"] = None
        df["current_price"] = None
        df["pct_change_30d"] = None

        # Get unique tickers
        tickers = df[ticker_col].dropna().unique().tolist()

        if not tickers:
            return df

        # Batch fetch with yfinance
        ticker_data = self._fetch_batch(tickers)

        # Map back to DataFrame
        for idx, row in df.iterrows():
            ticker = row.get(ticker_col)
            if ticker and ticker in ticker_data:
                data = ticker_data[ticker]
                df.at[idx, "market_cap"] = data.get("market_cap")
                df.at[idx, "current_price"] = data.get("current_price")
                df.at[idx, "pct_change_30d"] = data.get("pct_change_30d")

        return df

    def _fetch_batch(self, tickers: list[str]) -> dict:
        """Fetch data for multiple tickers."""
        results = {}

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                # Get 30-day price change
                hist = stock.history(period="1mo")
                pct_change = None
                if len(hist) > 1:
                    pct_change = (
                        (hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                        / hist["Close"].iloc[0]
                        * 100
                    )

                results[ticker] = {
                    "market_cap": info.get("marketCap"),
                    "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "pct_change_30d": round(pct_change, 2) if pct_change else None,
                }
            except Exception:
                # Skip tickers that fail
                continue

        return results

    def filter_small_caps(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to only small-cap stocks.

        Args:
            df: DataFrame with market_cap column

        Returns:
            Filtered DataFrame with only stocks under max_market_cap
        """
        df = df.copy()

        # Keep rows where market_cap is under threshold or unknown
        mask = (df["market_cap"].isna()) | (df["market_cap"] <= self.max_market_cap)
        return df[mask]

    def get_price_history(
        self, ticker: str, period: str = "6mo"
    ) -> Optional[pd.DataFrame]:
        """Get price history for charting.

        Args:
            ticker: Stock ticker symbol
            period: yfinance period string (e.g., '6mo', '1y')

        Returns:
            DataFrame with Date, Open, High, Low, Close, Volume or None
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                return None
            hist = hist.reset_index()
            return hist[["Date", "Open", "High", "Low", "Close", "Volume"]]
        except Exception:
            return None
