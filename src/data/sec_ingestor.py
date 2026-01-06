"""SEC Ingestor for fetching and parsing 10-K/10-Q/8-K filings.

This module handles:
- Downloading SEC filings via sec-edgar-downloader
- Extracting financial data (cash runway, burn rate) using LLM
- Parsing 8-K material events for catalyst information
- Storing extracted data in the database

Per spec Section 2.2:
- 10-K/10-Q: Cash runway, monthly burn rate, debt covenants
- 8-K Item 1.01: Material agreements (partnerships, licensing)
- 8-K Item 7.01: Pipeline updates, timeline changes
- 8-K Item 8.01: Clinical readouts, FDA meetings
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from sec_edgar_downloader import Downloader

logger = logging.getLogger(__name__)


# LLM extraction prompts
SEC_FINANCIAL_EXTRACTION_PROMPT = """
You are a financial analyst extracting key metrics from SEC filings for biotech companies.

Given the following text from a {filing_type} filing for {ticker}, extract:

1. **Cash Position**: Current cash and cash equivalents in USD
2. **Cash Runway**: How many months of cash runway the company has
3. **Monthly Burn Rate**: Estimated monthly operating expenses in USD
4. **Debt/Financing Risks**: Any mentioned debt covenants or financing concerns
5. **Key Dates**: Any PDUFA dates, clinical trial readouts, or regulatory milestones mentioned

Format your response as JSON:
{{
    "cash_position_usd": <number or null>,
    "cash_runway_months": <number or null>,
    "monthly_burn_rate_usd": <number or null>,
    "debt_concerns": "<string or null>",
    "key_dates": [
        {{"date": "YYYY-MM-DD", "event": "description", "drug": "drug_name"}}
    ],
    "confidence": <0.0-1.0>
}}

FILING TEXT:
{text}

JSON Response:
"""

SEC_8K_EXTRACTION_PROMPT = """
You are analyzing an 8-K filing to identify material biotech events.

For {ticker}, extract any of these events from the filing:
- Item 1.01: Material agreements (partnerships, licensing deals)
- Item 7.01: Pipeline updates, timeline changes
- Item 8.01: Clinical readouts, FDA meetings, trial results

Format your response as JSON:
{{
    "events": [
        {{
            "item": "1.01|7.01|8.01",
            "event_type": "partnership|trial_update|fda_meeting|clinical_readout",
            "description": "brief description",
            "drug_name": "if mentioned",
            "date": "YYYY-MM-DD if mentioned",
            "is_material": true|false
        }}
    ],
    "summary": "one-sentence summary of the filing"
}}

FILING TEXT:
{text}

JSON Response:
"""


class SECIngestor:
    """Download and analyze SEC filings for biotech catalysts.

    Uses LLM extraction for:
    - Cash runway and burn rate from 10-K/10-Q
    - Material events from 8-K filings
    """

    def __init__(
        self,
        download_dir: str = "data/sec_filings",
        email: str = "biotechradar@example.com",
    ):
        """Initialize SEC ingestor.

        Args:
            download_dir: Directory to store downloaded filings.
            email: User agent email required by SEC EDGAR API.
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.email = email

        # Initialize downloader (SEC requires user agent with email)
        try:
            self.dl = Downloader("BiotechRadar", email, str(self.download_dir))
        except Exception as e:
            logger.warning(f"Failed to initialize SEC downloader: {e}")
            self.dl = None

    def download_filings(
        self,
        ticker: str,
        amount: int = 1,
        doc_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Path]]:
        """Download latest filings for a ticker.

        Args:
            ticker: Stock ticker symbol
            amount: Number of each filing type to download
            doc_types: List of filing types (default: ["10-K", "10-Q", "8-K"])

        Returns:
            Dict mapping doc_type to list of downloaded file paths
        """
        if self.dl is None:
            logger.error("SEC downloader not initialized")
            return {}

        if doc_types is None:
            doc_types = ["10-K", "10-Q", "8-K"]

        downloaded = {}
        for doc_type in doc_types:
            try:
                self.dl.get(doc_type, ticker, limit=amount)
                logger.info(f"Downloaded {amount} {doc_type}(s) for {ticker}")

                # Find downloaded files
                ticker_dir = self.download_dir / "sec-edgar-filings" / ticker / doc_type
                if ticker_dir.exists():
                    files = list(ticker_dir.glob("**/*.html")) + list(ticker_dir.glob("**/*.txt"))
                    downloaded[doc_type] = files
            except Exception as e:
                logger.error(f"Failed to download {doc_type} for {ticker}: {e}")
                downloaded[doc_type] = []

        return downloaded

    def get_latest_filing_text(
        self,
        ticker: str,
        doc_type: str = "10-Q",
    ) -> Tuple[Optional[str], Optional[str]]:
        """Read the local text of the latest downloaded filing.

        Returns:
            Tuple of (filing_text, accession_number)
        """
        ticker_dir = self.download_dir / "sec-edgar-filings" / ticker / doc_type
        if not ticker_dir.exists():
            return None, None

        # Find latest by sorting accession numbers
        filings = sorted([d for d in ticker_dir.iterdir() if d.is_dir()], reverse=True)
        if not filings:
            return None, None

        latest_filing = filings[0]
        accession = latest_filing.name

        # Read primary document
        for ext in ["*.html", "*.htm", "*.txt"]:
            files = list(latest_filing.glob(ext))
            if files:
                try:
                    with open(files[0], "r", encoding="utf-8", errors="ignore") as f:
                        return f.read(), accession
                except Exception as e:
                    logger.error(f"Failed to read {files[0]}: {e}")

        return None, accession

    def clean_filing_text(self, html_text: str, max_chars: int = 50000) -> str:
        """Clean HTML filing to plain text for LLM processing.

        Args:
            html_text: Raw HTML from SEC filing
            max_chars: Maximum characters to return (for LLM context limits)

        Returns:
            Cleaned plain text
        """
        soup = BeautifulSoup(html_text, "lxml")

        # Remove script and style elements
        for element in soup(["script", "style", "head"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator=" ", strip=True)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)

        # Truncate if needed
        if len(text) > max_chars:
            # Try to truncate at a sentence boundary
            text = text[:max_chars]
            last_period = text.rfind(".")
            if last_period > max_chars * 0.8:
                text = text[: last_period + 1]

        return text

    def extract_financials_heuristic(self, text: str) -> Dict[str, Any]:
        """Heuristic extraction of financial data (fallback when no LLM).

        This is a rule-based extraction for basic patterns.
        LLM extraction is preferred for accuracy.
        """
        result = {
            "cash_position_usd": None,
            "cash_runway_months": None,
            "monthly_burn_rate_usd": None,
            "key_dates": [],
            "confidence": 0.3,  # Low confidence for heuristic extraction
        }

        clean_text = self.clean_filing_text(text, max_chars=100000)

        # Cash position patterns
        cash_patterns = [
            r"cash.*?(?:and|,)?\s*cash\s*equivalents.*?\$\s*([\d,.]+)\s*(million|billion)?",
            r"\$\s*([\d,.]+)\s*(million|billion)?\s*(?:in|of)\s*cash",
        ]
        for pattern in cash_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1).replace(",", ""))
                multiplier = match.group(2)
                if multiplier:
                    if "billion" in multiplier.lower():
                        amount *= 1e9
                    elif "million" in multiplier.lower():
                        amount *= 1e6
                result["cash_position_usd"] = amount
                break

        # Cash runway patterns
        runway_patterns = [
            r"(?:sufficient|adequate|expect).*?(?:fund|finance).*?operations.*?(?:through|into|until)\s*(\w+\s*\d{4})",
            r"runway.*?(\d+)\s*months?",
            r"(\d+)\s*months?\s*(?:of)?\s*(?:cash\s*)?runway",
        ]
        for pattern in runway_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                runway_str = match.group(1)
                if runway_str.isdigit():
                    result["cash_runway_months"] = int(runway_str)
                else:
                    # Parse date like "Q2 2026" or "December 2025"
                    result["runway_date"] = runway_str
                break

        # PDUFA date patterns
        pdufa_pattern = r"PDUFA.*?(?:date|action).*?(\w+\s*\d{1,2}?,?\s*\d{4})"
        match = re.search(pdufa_pattern, clean_text, re.IGNORECASE)
        if match:
            result["key_dates"].append({
                "event": "PDUFA",
                "date_text": match.group(1),
            })

        return result

    def extract_financials_llm(
        self,
        text: str,
        ticker: str,
        filing_type: str,
        model: str = "haiku",
    ) -> Dict[str, Any]:
        """Extract financial data using LLM.

        Args:
            text: Cleaned filing text
            ticker: Company ticker
            filing_type: Type of filing (10-K, 10-Q)
            model: LLM model to use (haiku, sonnet, flash)

        Returns:
            Extracted financial data as dict
        """
        # Check for Anthropic API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("No ANTHROPIC_API_KEY found, using heuristic extraction")
            return self.extract_financials_heuristic(text)

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            # Prepare prompt
            prompt = SEC_FINANCIAL_EXTRACTION_PROMPT.format(
                filing_type=filing_type,
                ticker=ticker,
                text=self.clean_filing_text(text, max_chars=30000),
            )

            # Map model name to API model
            model_map = {
                "haiku": "claude-3-5-haiku-20241022",
                "sonnet": "claude-sonnet-4-20250514",
            }
            api_model = model_map.get(model, "claude-3-5-haiku-20241022")

            response = client.messages.create(
                model=api_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse JSON response
            response_text = response.content[0].text
            # Find JSON in response
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())

        except ImportError:
            logger.warning("anthropic package not installed, using heuristic extraction")
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")

        return self.extract_financials_heuristic(text)

    def extract_8k_events(
        self,
        text: str,
        ticker: str,
        model: str = "haiku",
    ) -> Dict[str, Any]:
        """Extract material events from 8-K filing.

        Args:
            text: 8-K filing text
            ticker: Company ticker
            model: LLM model to use

        Returns:
            Extracted events as dict
        """
        # Default response
        result = {"events": [], "summary": "Unable to parse 8-K"}

        # Check for LLM availability
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Heuristic 8-K parsing
            clean_text = self.clean_filing_text(text, max_chars=20000)

            # Look for item numbers
            items_found = []
            for item in ["1.01", "7.01", "8.01"]:
                if f"Item {item}" in clean_text:
                    items_found.append(item)

            if items_found:
                result["events"] = [{"item": item, "event_type": "unknown"} for item in items_found]
                result["summary"] = f"8-K contains Items: {', '.join(items_found)}"

            return result

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            prompt = SEC_8K_EXTRACTION_PROMPT.format(
                ticker=ticker,
                text=self.clean_filing_text(text, max_chars=20000),
            )

            model_map = {
                "haiku": "claude-3-5-haiku-20241022",
                "sonnet": "claude-sonnet-4-20250514",
            }
            api_model = model_map.get(model, "claude-3-5-haiku-20241022")

            response = client.messages.create(
                model=api_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            logger.error(f"8-K LLM extraction failed: {e}")

        return result

    def process_company(
        self,
        ticker: str,
        download: bool = True,
    ) -> Dict[str, Any]:
        """Process all filings for a company.

        Args:
            ticker: Company ticker
            download: Whether to download fresh filings

        Returns:
            Extracted data from all filing types
        """
        result = {
            "ticker": ticker,
            "financials": None,
            "events_8k": [],
            "errors": [],
        }

        if download:
            self.download_filings(ticker, amount=1)

        # Process 10-K/10-Q for financials
        for doc_type in ["10-K", "10-Q"]:
            text, accession = self.get_latest_filing_text(ticker, doc_type)
            if text:
                financials = self.extract_financials_llm(text, ticker, doc_type)
                if financials and financials.get("confidence", 0) > 0.2:
                    financials["filing_type"] = doc_type
                    financials["accession_number"] = accession
                    result["financials"] = financials
                    break  # Use most recent 10-K or 10-Q

        # Process 8-K for events
        text, accession = self.get_latest_filing_text(ticker, "8-K")
        if text:
            events = self.extract_8k_events(text, ticker)
            events["accession_number"] = accession
            result["events_8k"].append(events)

        return result


def sync_sec_to_database(db, tickers: List[str]) -> int:
    """Sync SEC filings to database for multiple tickers.

    Args:
        db: SQLiteDB instance
        tickers: List of ticker symbols to process

    Returns:
        Number of filings processed
    """
    ingestor = SECIngestor()
    processed = 0

    for ticker in tickers:
        try:
            # Ensure company exists
            company = db.get_company_by_ticker(ticker)
            if not company:
                company_id = db.upsert_company(ticker, f"{ticker} Inc.")
            else:
                company_id = company["id"]

            # Process filings
            result = ingestor.process_company(ticker, download=True)

            if result.get("financials"):
                fin = result["financials"]
                db.upsert_sec_filing(
                    company_id=company_id,
                    filing_type=fin.get("filing_type", "10-Q"),
                    filing_date=datetime.now().date(),  # Would extract actual date
                    accession_number=fin.get("accession_number", f"{ticker}_latest"),
                    cash_runway_months=fin.get("cash_runway_months"),
                    monthly_burn_rate_usd=fin.get("monthly_burn_rate_usd"),
                    cash_position_usd=fin.get("cash_position_usd"),
                    extraction_model="haiku",
                    extraction_confidence=fin.get("confidence", 0.5),
                )
                processed += 1

            logger.info(f"Processed SEC filings for {ticker}")

        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")

    return processed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    ingestor = SECIngestor()

    # Test with a ticker
    ticker = "ACAD"
    print(f"Processing {ticker}...")

    # Download (if needed)
    ingestor.download_filings(ticker, amount=1, doc_types=["10-Q"])

    # Read and extract
    text, accession = ingestor.get_latest_filing_text(ticker, "10-Q")
    if text:
        print(f"Found filing: {accession}")
        result = ingestor.extract_financials_heuristic(text)
        print(f"Extracted: {json.dumps(result, indent=2)}")
