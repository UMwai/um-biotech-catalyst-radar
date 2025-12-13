"""ClinicalTrials.gov API v2 scraper for Phase 2/3 trials."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests


class ClinicalTrialsScraper:
    """Fetch Phase 2/3 clinical trials with upcoming completion dates."""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, months_ahead: int = 3):
        self.months_ahead = months_ahead

    def fetch_trials(self) -> pd.DataFrame:
        """Fetch Phase 2/3 trials completing in the next N months.

        Returns:
            DataFrame with columns: nct_id, sponsor, phase, title, completion_date, condition
        """
        today = datetime.now()
        end_date = today + timedelta(days=self.months_ahead * 30)

        # ClinicalTrials.gov API v2 query
        params = {
            "format": "json",
            "pageSize": 1000,
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
            "filter.phase": "PHASE2,PHASE3",
            "query.term": f"AREA[PrimaryCompletionDate]RANGE[{today.strftime('%Y-%m-%d')},{end_date.strftime('%Y-%m-%d')}]",
            "fields": "NCTId,BriefTitle,LeadSponsorName,Phase,PrimaryCompletionDate,Condition",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch from ClinicalTrials.gov: {e}") from e

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> pd.DataFrame:
        """Parse API response into DataFrame."""
        studies = data.get("studies", [])

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

            records.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "sponsor": lead_sponsor.get("name", ""),
                    "phase": self._extract_phase(design_module.get("phases", [])),
                    "completion_date": completion_info.get("date", ""),
                    "condition": ", ".join(conditions_module.get("conditions", [])[:3]),
                }
            )

        df = pd.DataFrame(records)

        # Parse and filter by date
        if not df.empty:
            df["completion_date"] = pd.to_datetime(df["completion_date"], errors="coerce")
            df = df.dropna(subset=["completion_date"])
            df = df.sort_values("completion_date")

        return df

    @staticmethod
    def _extract_phase(phases: list[str]) -> str:
        """Extract highest phase from list."""
        if "PHASE3" in phases:
            return "Phase 3"
        if "PHASE2" in phases:
            return "Phase 2"
        return "Unknown"
