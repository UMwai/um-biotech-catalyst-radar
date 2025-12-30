"""ClinicalTrials.gov API v2 scraper for Phase 2/3 trials."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import requests


class ClinicalTrialsScraper:
    """Fetch Phase 2/3 clinical trials with upcoming completion dates."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    # Target phases for biotech run-ups
    TARGET_PHASES = {"PHASE2", "PHASE3"}

    # Active trial statuses
    ACTIVE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}

    def __init__(self, months_ahead: int = 3, max_pages: int = 10):
        self.months_ahead = months_ahead
        self.max_pages = max_pages

    def fetch_trials(self) -> pd.DataFrame:
        """Fetch Phase 2/3 trials completing in the next N months.

        Uses pagination to fetch enough data, then filters locally.
        This is more reliable than complex query syntax.

        Returns:
            DataFrame with columns: nct_id, sponsor, phase, title, completion_date, condition
        """
        today = datetime.now()
        cutoff_date = today + timedelta(days=self.months_ahead * 30)

        all_studies = []
        next_page_token = None

        for page in range(self.max_pages):
            studies, next_page_token = self._fetch_page(next_page_token)
            all_studies.extend(studies)

            if not next_page_token:
                break

        # Parse and filter
        df = self._parse_studies(all_studies)

        if df.empty:
            return df

        # Filter by phase
        df = df[df["phase"].isin(["Phase 2", "Phase 3"])]

        # Filter by status (already active)
        df = df[df["status"].isin(self.ACTIVE_STATUSES)]

        # Filter by completion date (next N months)
        df = df[(df["completion_date"] >= today) & (df["completion_date"] <= cutoff_date)]

        # Sort by completion date
        df = df.sort_values("completion_date").reset_index(drop=True)

        return df

    def _fetch_page(self, page_token: Optional[str] = None) -> tuple[List[Dict], Optional[str]]:
        """Fetch a single page of results."""
        params = {
            "format": "json",
            "pageSize": 1000,
            # Filter for active trials only - reduces dataset significantly
            "filter.overallStatus": "RECRUITING|ACTIVE_NOT_RECRUITING|ENROLLING_BY_INVITATION",
        }

        if page_token:
            params["pageToken"] = page_token

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"Warning: API request failed: {e}")
            return [], None

        studies = data.get("studies", [])
        next_token = data.get("nextPageToken")

        return studies, next_token

    def _parse_studies(self, studies: List[Dict]) -> pd.DataFrame:
        """Parse raw API studies into DataFrame."""
        records = []

        for study in studies:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            status_module = protocol.get("statusModule", {})
            conditions_module = protocol.get("conditionsModule", {})

            lead_sponsor = sponsor_module.get("leadSponsor", {})
            completion_info = status_module.get("primaryCompletionDateStruct", {})
            phases = design_module.get("phases", [])

            # Skip if no phases or not Phase 2/3
            if not any(p in self.TARGET_PHASES for p in phases):
                continue

            records.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "sponsor": lead_sponsor.get("name", ""),
                    "sponsor_class": lead_sponsor.get("class", ""),
                    "phase": self._extract_phase(phases),
                    "status": status_module.get("overallStatus", ""),
                    "completion_date": completion_info.get("date", ""),
                    "condition": ", ".join(conditions_module.get("conditions", [])[:3]),
                }
            )

        df = pd.DataFrame(records)

        if not df.empty:
            df["completion_date"] = pd.to_datetime(df["completion_date"], errors="coerce")
            df = df.dropna(subset=["completion_date"])

        return df

    @staticmethod
    def _extract_phase(phases: List[str]) -> str:
        """Extract highest phase from list."""
        if "PHASE3" in phases:
            return "Phase 3"
        if "PHASE2" in phases:
            return "Phase 2"
        return "Unknown"


# Quick test
if __name__ == "__main__":
    scraper = ClinicalTrialsScraper(months_ahead=3, max_pages=5)
    df = scraper.fetch_trials()
    print(f"Found {len(df)} Phase 2/3 trials with upcoming catalysts")
    if not df.empty:
        print("\nTop 15 upcoming catalysts:")
        print(
            df[["nct_id", "sponsor", "phase", "completion_date", "condition"]].head(15).to_string()
        )
