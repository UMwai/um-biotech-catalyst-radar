"""ClinicalTrials.gov API v2 scraper for Phase 2/3 trials.

Enhanced for Phase 2 MVP with:
- Trial design scoring (LLM-assessed quality)
- Better date precision handling
- Therapeutic area classification
- Integration with SQLite database
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)


# Trial design scoring prompt for LLM
TRIAL_DESIGN_SCORING_PROMPT = """
You are a clinical trials expert evaluating trial design quality.

Score this trial from 0-100 based on these criteria:
- Randomization (0-20 points)
- Blinding: Double-blind > Single-blind > Open-label (0-20 points)
- Control arm: Placebo-controlled > Active comparator > No control (0-20 points)
- Primary endpoint clarity and clinical relevance (0-20 points)
- Sample size adequacy for the indication (0-20 points)

Trial Information:
- Title: {title}
- Phase: {phase}
- Design: {design_info}
- Primary Outcome: {primary_outcome}
- Enrollment: {enrollment}
- Conditions: {conditions}

Respond in JSON format:
{{
    "score": <0-100>,
    "design_type": "double-blind|single-blind|open-label",
    "control_type": "placebo|active-comparator|none",
    "notes": "brief explanation of score",
    "strengths": ["list of design strengths"],
    "weaknesses": ["list of design weaknesses"]
}}

JSON Response:
"""


class ClinicalTrialsScraper:
    """Fetch Phase 2/3 clinical trials with upcoming completion dates.

    Enhanced with trial design scoring for Phase 2 MVP.
    """

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    # Target phases for biotech run-ups
    TARGET_PHASES = {"PHASE2", "PHASE3"}

    # Active trial statuses
    ACTIVE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}

    # Therapeutic area keywords for classification
    THERAPEUTIC_AREAS = {
        "oncology": ["cancer", "tumor", "carcinoma", "leukemia", "lymphoma", "melanoma", "oncology"],
        "neurology": ["alzheimer", "parkinson", "multiple sclerosis", "epilepsy", "migraine", "neurological"],
        "cardiovascular": ["heart", "cardiac", "cardiovascular", "hypertension", "atherosclerosis"],
        "immunology": ["autoimmune", "rheumatoid", "lupus", "crohn", "ulcerative colitis", "psoriasis"],
        "infectious": ["hiv", "hepatitis", "covid", "influenza", "bacterial", "viral"],
        "metabolic": ["diabetes", "obesity", "metabolic", "lipid"],
        "respiratory": ["asthma", "copd", "pulmonary", "respiratory"],
        "rare_disease": ["rare", "orphan", "duchenne", "huntington", "cystic fibrosis"],
    }

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

        logger.info(f"Fetched {len(all_studies)} total studies from CTgov")

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

        logger.info(f"Filtered to {len(df)} Phase 2/3 trials within {self.months_ahead} months")

        return df

    def fetch_trials_enhanced(self, score_designs: bool = False) -> pd.DataFrame:
        """Fetch trials with enhanced data including design scoring.

        Args:
            score_designs: Whether to score trial designs with LLM (adds latency)

        Returns:
            Enhanced DataFrame with design scores and therapeutic areas
        """
        df = self.fetch_trials()

        if df.empty:
            return df

        # Add therapeutic area classification
        df["therapeutic_area"] = df["condition"].apply(self._classify_therapeutic_area)

        # Add date precision
        df["date_precision"] = "exact"  # Could be enhanced to detect "Q3 2025" etc.

        # Score designs if requested
        if score_designs:
            df = self._add_design_scores(df)

        return df

    def _fetch_page(self, page_token: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
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
            logger.warning(f"API request failed: {e}")
            return [], None

        studies = data.get("studies", [])
        next_token = data.get("nextPageToken")

        return studies, next_token

    def fetch_single_trial(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed data for a single trial.

        Args:
            nct_id: ClinicalTrials.gov NCT ID

        Returns:
            Full trial data dict or None if not found
        """
        url = f"{self.BASE_URL}/{nct_id}"
        try:
            response = requests.get(url, params={"format": "json"}, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch trial {nct_id}: {e}")

        return None

    def _parse_studies(self, studies: List[Dict]) -> pd.DataFrame:
        """Parse raw API studies into DataFrame with enhanced fields."""
        records = []

        for study in studies:
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            status_module = protocol.get("statusModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            outcomes_module = protocol.get("outcomesModule", {})
            eligibility_module = protocol.get("eligibilityModule", {})

            lead_sponsor = sponsor_module.get("leadSponsor", {})
            completion_info = status_module.get("primaryCompletionDateStruct", {})
            study_completion = status_module.get("studyCompletionDateStruct", {})
            phases = design_module.get("phases", [])

            # Skip if no phases or not Phase 2/3
            if not any(p in self.TARGET_PHASES for p in phases):
                continue

            # Extract design info
            design_info = design_module.get("designInfo", {})
            allocation = design_info.get("allocation", "")
            masking_info = design_info.get("maskingInfo", {})
            masking = masking_info.get("masking", "")

            # Primary outcomes
            primary_outcomes = outcomes_module.get("primaryOutcomes", [])
            primary_outcome_text = ""
            if primary_outcomes:
                primary_outcome_text = primary_outcomes[0].get("measure", "")

            # Enrollment
            enrollment_info = design_module.get("enrollmentInfo", {})
            enrollment_count = enrollment_info.get("count")

            # Interventions
            arms_module = protocol.get("armsInterventionsModule", {})
            interventions = arms_module.get("interventions", [])
            intervention_names = [i.get("name", "") for i in interventions[:3]]

            records.append(
                {
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "official_title": id_module.get("officialTitle", ""),
                    "sponsor": lead_sponsor.get("name", ""),
                    "sponsor_class": lead_sponsor.get("class", ""),
                    "phase": self._extract_phase(phases),
                    "status": status_module.get("overallStatus", ""),
                    "completion_date": completion_info.get("date", ""),
                    "study_completion_date": study_completion.get("date", ""),
                    "condition": ", ".join(conditions_module.get("conditions", [])[:3]),
                    "conditions_list": conditions_module.get("conditions", []),
                    # Design fields
                    "allocation": allocation,
                    "masking": masking,
                    "primary_outcome": primary_outcome_text,
                    "enrollment_count": enrollment_count,
                    "interventions": intervention_names,
                }
            )

        df = pd.DataFrame(records)

        if not df.empty:
            df["completion_date"] = pd.to_datetime(df["completion_date"], errors="coerce")
            df["study_completion_date"] = pd.to_datetime(df["study_completion_date"], errors="coerce")
            df = df.dropna(subset=["completion_date"])

        return df

    def _classify_therapeutic_area(self, condition_text: str) -> str:
        """Classify trial into therapeutic area based on condition text."""
        condition_lower = condition_text.lower()

        for area, keywords in self.THERAPEUTIC_AREAS.items():
            if any(kw in condition_lower for kw in keywords):
                return area

        return "other"

    def _add_design_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add LLM-based trial design scores."""
        # Check for LLM availability
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            # Use heuristic scoring
            df["design_score"] = df.apply(self._heuristic_design_score, axis=1)
            df["design_notes"] = "Heuristic scoring (no LLM)"
            df["scoring_model"] = "heuristic"
            return df

        # LLM scoring (for first N trials to avoid cost)
        max_llm_scores = 50
        scores = []
        notes = []

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            for idx, row in df.head(max_llm_scores).iterrows():
                try:
                    prompt = TRIAL_DESIGN_SCORING_PROMPT.format(
                        title=row.get("title", ""),
                        phase=row.get("phase", ""),
                        design_info=f"Allocation: {row.get('allocation', 'Unknown')}, Masking: {row.get('masking', 'Unknown')}",
                        primary_outcome=row.get("primary_outcome", "Not specified"),
                        enrollment=row.get("enrollment_count", "Unknown"),
                        conditions=row.get("condition", ""),
                    )

                    response = client.messages.create(
                        model="claude-3-5-haiku-20241022",
                        max_tokens=512,
                        messages=[{"role": "user", "content": prompt}],
                    )

                    response_text = response.content[0].text
                    json_match = re.search(r"\{[\s\S]*\}", response_text)
                    if json_match:
                        result = json.loads(json_match.group())
                        scores.append(result.get("score", 50))
                        notes.append(result.get("notes", ""))
                    else:
                        scores.append(self._heuristic_design_score(row))
                        notes.append("LLM parse failed, used heuristic")

                except Exception as e:
                    logger.warning(f"Design scoring failed for {row.get('nct_id')}: {e}")
                    scores.append(self._heuristic_design_score(row))
                    notes.append("Error, used heuristic")

        except ImportError:
            # Fall back to heuristic for all
            pass

        # Apply scores
        if scores:
            df.loc[df.head(max_llm_scores).index, "design_score"] = scores
            df.loc[df.head(max_llm_scores).index, "design_notes"] = notes
            df.loc[df.head(max_llm_scores).index, "scoring_model"] = "claude-haiku"

        # Heuristic for remaining
        remaining_mask = df["design_score"].isna() if "design_score" in df.columns else pd.Series([True] * len(df))
        if remaining_mask.any():
            df.loc[remaining_mask, "design_score"] = df.loc[remaining_mask].apply(self._heuristic_design_score, axis=1)
            df.loc[remaining_mask, "design_notes"] = "Heuristic scoring"
            df.loc[remaining_mask, "scoring_model"] = "heuristic"

        return df

    def _heuristic_design_score(self, row: pd.Series) -> int:
        """Calculate heuristic design score based on available fields."""
        score = 50  # Base score

        # Phase bonus
        if row.get("phase") == "Phase 3":
            score += 10

        # Masking bonus
        masking = str(row.get("masking", "")).lower()
        if "double" in masking:
            score += 15
        elif "single" in masking:
            score += 8

        # Allocation bonus
        allocation = str(row.get("allocation", "")).lower()
        if "randomized" in allocation:
            score += 10

        # Enrollment size bonus
        enrollment = row.get("enrollment_count")
        if enrollment:
            if enrollment >= 500:
                score += 10
            elif enrollment >= 100:
                score += 5

        return min(100, max(0, score))

    @staticmethod
    def _extract_phase(phases: List[str]) -> str:
        """Extract highest phase from list."""
        if "PHASE3" in phases:
            return "Phase 3"
        if "PHASE2" in phases:
            return "Phase 2"
        return "Unknown"


def sync_ctgov_to_database(db, months_ahead: int = 6, score_designs: bool = False) -> int:
    """Sync ClinicalTrials.gov data to database.

    Args:
        db: SQLiteDB instance
        months_ahead: How many months ahead to look for trials
        score_designs: Whether to score trial designs with LLM

    Returns:
        Number of trials synced
    """
    from data.ticker_mapper import TickerMapper

    scraper = ClinicalTrialsScraper(months_ahead=months_ahead, max_pages=10)
    mapper = TickerMapper()

    df = scraper.fetch_trials_enhanced(score_designs=score_designs)

    if df.empty:
        logger.warning("No trials fetched from CTgov")
        return 0

    # Map sponsors to tickers
    df = mapper.map_all(df)

    synced = 0
    for _, row in df.iterrows():
        try:
            # Handle company
            ticker = row.get("ticker")
            company_id = None

            if ticker:
                company = db.get_company_by_ticker(ticker)
                if not company:
                    company_id = db.upsert_company(ticker, row.get("sponsor", f"{ticker} Inc."))
                else:
                    company_id = company["id"]

            # Insert trial
            db.upsert_clinical_trial(
                nct_id=row.get("nct_id"),
                title=row.get("title"),
                phase=row.get("phase"),
                status=row.get("status"),
                conditions=row.get("conditions_list", []),
                interventions=row.get("interventions", []),
                primary_completion_date=row.get("completion_date"),
                study_completion_date=row.get("study_completion_date"),
                enrollment_count=row.get("enrollment_count"),
                sponsor_name=row.get("sponsor"),
                sponsor_ticker=ticker,
                ticker_confidence=row.get("fuzzy_score"),
                trial_design_score=row.get("design_score"),
                trial_design_notes=row.get("design_notes"),
                design_scoring_model=row.get("scoring_model"),
                company_id=company_id,
            )
            synced += 1

        except Exception as e:
            logger.error(f"Failed to sync trial {row.get('nct_id')}: {e}")

    logger.info(f"Synced {synced} trials to database")
    return synced


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scraper = ClinicalTrialsScraper(months_ahead=3, max_pages=5)
    df = scraper.fetch_trials_enhanced(score_designs=False)

    print(f"Found {len(df)} Phase 2/3 trials with upcoming catalysts")

    if not df.empty:
        print("\nTop 15 upcoming catalysts:")
        display_cols = ["nct_id", "sponsor", "phase", "completion_date", "condition", "therapeutic_area"]
        print(df[display_cols].head(15).to_string())

        print("\nTherapeutic area distribution:")
        print(df["therapeutic_area"].value_counts())
