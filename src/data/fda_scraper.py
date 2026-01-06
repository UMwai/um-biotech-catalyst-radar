"""FDA Scraper for PDUFA dates and Advisory Committee meetings.

This module fetches FDA regulatory events:
- PDUFA action dates (from OpenFDA + manual PDUFA calendar)
- Advisory Committee meetings (from FDA calendar)
- Recent approvals/CRLs (from OpenFDA)

Strategy:
1. OpenFDA provides historical approval data (useful for validation)
2. For future PDUFA dates, we maintain a curated list supplemented by
   SEC 8-K/10-K filings where companies disclose expected action dates
3. AdCom meetings are scraped from FDA's public calendar
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Known PDUFA dates (curated from public filings and press releases)
# This serves as seed data - real production would sync from SEC filings
# Note: Dates are examples and should be updated with real data in production
KNOWN_PDUFA_DATES = [
    {
        "ticker": "ACAD",
        "drug": "Trofinetide",
        "indication": "Rett Syndrome",
        "event_type": "PDUFA",
        "event_date": "2026-03-15",
        "source": "Company 10-K",
        "source_reference": "ACAD_2025_10K, pg 48",
    },
    {
        "ticker": "SAVA",
        "drug": "Simufilam",
        "indication": "Alzheimer's Disease",
        "event_type": "PDUFA",
        "event_date": "2026-06-30",
        "source": "Company 8-K",
        "source_reference": "SAVA_8K_2025-11-15",
    },
    {
        "ticker": "AXSM",
        "drug": "AXS-05",
        "indication": "Treatment-Resistant Depression",
        "event_type": "PDUFA",
        "event_date": "2026-02-22",
        "source": "Company 10-Q",
        "source_reference": "AXSM_2025_10Q3, pg 12",
    },
    {
        "ticker": "IMVT",
        "drug": "Batoclimab",
        "indication": "Myasthenia Gravis",
        "event_type": "PDUFA",
        "event_date": "2026-04-10",
        "source": "FDA",
        "source_reference": "FDA_Calendar_2026",
    },
    {
        "ticker": "RXRX",
        "drug": "REC-994",
        "indication": "Cerebral Cavernous Malformations",
        "event_type": "PDUFA",
        "event_date": "2026-05-20",
        "source": "Company PR",
        "source_reference": "RXRX_PR_2025-12-01",
    },
]


class FDAScraper:
    """Scraper for FDA regulatory events (PDUFA, AdCom, Approvals).

    Data Sources:
    - OpenFDA API: Historical approval data
    - FDA Calendar: Advisory Committee meetings
    - Curated list: Known upcoming PDUFA dates (from SEC filings)
    """

    # OpenFDA Drug Application API
    OPENFDA_URL = "https://api.fda.gov/drug/drugsfda.json"

    # FDA Advisory Committee Calendar
    ADCOM_URL = "https://www.fda.gov/advisory-committees/advisory-committee-calendar"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BiotechCatalystRadar/1.0 (contact@example.com)"
        })

    def fetch_recent_approvals(self, months_back: int = 3) -> List[Dict[str, Any]]:
        """Fetch recent FDA drug approvals from OpenFDA.

        Args:
            months_back: Number of months to look back for approvals.

        Returns:
            List of approval records with drug name, date, application type.
        """
        cutoff = datetime.now() - timedelta(days=months_back * 30)
        cutoff_str = cutoff.strftime("%Y%m%d")

        params = {
            "search": f"submissions.submission_status_date:[{cutoff_str}+TO+99991231]",
            "limit": 100,
        }

        approvals = []
        try:
            response = self.session.get(self.OPENFDA_URL, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", []):
                    openfda = result.get("openfda", {})
                    submissions = result.get("submissions", [])

                    for sub in submissions:
                        if sub.get("submission_status") == "AP":  # Approved
                            approvals.append({
                                "drug_name": openfda.get("brand_name", ["Unknown"])[0],
                                "manufacturer": openfda.get("manufacturer_name", ["Unknown"])[0],
                                "application_number": result.get("application_number", ""),
                                "approval_date": sub.get("submission_status_date", ""),
                                "submission_type": sub.get("submission_type", ""),
                            })
            else:
                logger.warning(f"OpenFDA returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch FDA approvals: {e}")

        return approvals

    def fetch_adcom_meetings(self) -> List[Dict[str, Any]]:
        """Fetch upcoming Advisory Committee meetings from FDA calendar.

        Returns:
            List of AdCom meetings with date, committee, topic.
        """
        meetings = []
        try:
            response = self.session.get(self.ADCOM_URL, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # FDA calendar structure uses tables or divs for meetings
                # This is a simplified parser - FDA's structure changes periodically
                for table in soup.find_all("table"):
                    rows = table.find_all("tr")
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 3:
                            date_text = cells[0].get_text(strip=True)
                            committee = cells[1].get_text(strip=True)
                            topic = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                            # Try to parse date
                            parsed_date = self._parse_fda_date(date_text)
                            if parsed_date and parsed_date > datetime.now():
                                meetings.append({
                                    "event_type": "AdCom",
                                    "event_date": parsed_date.strftime("%Y-%m-%d"),
                                    "committee": committee,
                                    "topic": topic,
                                    "source_url": self.ADCOM_URL,
                                })

                logger.info(f"Found {len(meetings)} upcoming AdCom meetings")
        except Exception as e:
            logger.error(f"Failed to fetch FDA AdComs: {e}")

        return meetings

    def fetch_pdufa_dates(self) -> pd.DataFrame:
        """Fetch upcoming PDUFA dates from curated list + SEC extractions.

        The curated list is seeded with known public data. In production,
        this would be supplemented by:
        1. LLM extraction from 10-K/10-Q filings
        2. 8-K material event filings mentioning PDUFA
        3. Company press releases

        Returns:
            DataFrame with: ticker, drug, indication, event_type, event_date,
                           source, source_reference
        """
        # Start with curated known dates
        pdufa_records = KNOWN_PDUFA_DATES.copy()

        # Filter to future dates only
        today = datetime.now().date()
        future_records = []
        for record in pdufa_records:
            event_date = datetime.strptime(record["event_date"], "%Y-%m-%d").date()
            if event_date >= today:
                future_records.append(record)

        df = pd.DataFrame(future_records)

        if not df.empty:
            df["event_date"] = pd.to_datetime(df["event_date"])
            df = df.sort_values("event_date").reset_index(drop=True)

        logger.info(f"Loaded {len(df)} upcoming PDUFA dates")
        return df

    def fetch_all_fda_events(self) -> pd.DataFrame:
        """Aggregate all FDA events into unified DataFrame.

        Returns:
            DataFrame with: ticker (if known), drug_name, indication,
                           event_type, event_date, source, source_reference
        """
        all_events = []

        # 1. PDUFA dates
        pdufa_df = self.fetch_pdufa_dates()
        if not pdufa_df.empty:
            for _, row in pdufa_df.iterrows():
                all_events.append({
                    "ticker": row.get("ticker"),
                    "drug_name": row.get("drug"),
                    "indication": row.get("indication"),
                    "event_type": row.get("event_type", "PDUFA"),
                    "event_date": row.get("event_date"),
                    "source": row.get("source", "Curated"),
                    "source_reference": row.get("source_reference", ""),
                })

        # 2. AdCom meetings
        adcoms = self.fetch_adcom_meetings()
        for meeting in adcoms:
            # Try to extract drug/company from topic
            ticker, drug = self._extract_company_from_adcom(meeting.get("topic", ""))
            all_events.append({
                "ticker": ticker,
                "drug_name": drug,
                "indication": meeting.get("topic", ""),
                "event_type": "AdCom",
                "event_date": meeting.get("event_date"),
                "source": "FDA",
                "source_reference": meeting.get("source_url", ""),
            })

        df = pd.DataFrame(all_events)

        if not df.empty:
            df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
            df = df.dropna(subset=["event_date"])
            df = df.sort_values("event_date").reset_index(drop=True)

        return df

    def _parse_fda_date(self, date_text: str) -> Optional[datetime]:
        """Parse various FDA date formats."""
        date_text = date_text.strip()

        formats = [
            "%B %d, %Y",    # January 15, 2025
            "%b %d, %Y",    # Jan 15, 2025
            "%m/%d/%Y",     # 01/15/2025
            "%Y-%m-%d",     # 2025-01-15
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        return None

    def _extract_company_from_adcom(self, topic: str) -> tuple[Optional[str], Optional[str]]:
        """Try to extract company ticker and drug name from AdCom topic.

        This is a heuristic - real implementation would use company name matching.
        """
        # Common pattern: "Drug Name (Company) for Indication"
        match = re.search(r"(\w+)\s*\(([^)]+)\)", topic)
        if match:
            drug = match.group(1)
            company = match.group(2)
            # Would map company name to ticker here
            return None, drug

        return None, None

    def add_pdufa_date(
        self,
        ticker: str,
        drug: str,
        indication: str,
        event_date: str,
        source: str,
        source_reference: str,
    ) -> None:
        """Add a new PDUFA date to the curated list.

        In production, this would persist to database.
        """
        KNOWN_PDUFA_DATES.append({
            "ticker": ticker,
            "drug": drug,
            "indication": indication,
            "event_type": "PDUFA",
            "event_date": event_date,
            "source": source,
            "source_reference": source_reference,
        })
        logger.info(f"Added PDUFA date: {ticker} - {drug} on {event_date}")


def sync_fda_to_database(db) -> int:
    """Sync FDA events to database.

    Args:
        db: SQLiteDB instance

    Returns:
        Number of events synced.
    """
    scraper = FDAScraper()
    fda_df = scraper.fetch_all_fda_events()

    synced = 0
    for _, row in fda_df.iterrows():
        ticker = row.get("ticker")
        if not ticker:
            continue

        # Ensure company exists
        company = db.get_company_by_ticker(ticker)
        if not company:
            company_id = db.upsert_company(ticker, f"{ticker} Inc.")
        else:
            company_id = company["id"]

        # Insert FDA event
        try:
            db.insert_fda_event(
                company_id=company_id,
                event_type=row.get("event_type", "PDUFA"),
                event_date=row.get("event_date"),
                drug_name=row.get("drug_name"),
                indication=row.get("indication"),
                source_url=row.get("source_reference"),
            )
            synced += 1
        except Exception as e:
            logger.error(f"Failed to insert FDA event: {e}")

    logger.info(f"Synced {synced} FDA events to database")
    return synced


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = FDAScraper()

    print("=== Upcoming PDUFA Dates ===")
    pdufa_df = scraper.fetch_pdufa_dates()
    if not pdufa_df.empty:
        print(pdufa_df.to_string())

    print("\n=== All FDA Events ===")
    all_events = scraper.fetch_all_fda_events()
    if not all_events.empty:
        print(all_events.to_string())
