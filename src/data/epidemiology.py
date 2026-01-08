"""Epidemiology Data Layer.

Per spec Phase 3 Section 2.6:
- Fetch patient population data from public sources
- No commercial data licensing required
- Sources: GBD, CDC WONDER, WHO GHO, PubMed extraction
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Epidemiology data sources configuration
EPIDEMIOLOGY_SOURCES = {
    "gbd": {
        "name": "Global Burden of Disease",
        "url": "https://ghdx.healthdata.org/",
        "cost": "Free",
        "coverage": "Comprehensive, academic format",
        "priority": 1,
    },
    "cdc_wonder": {
        "name": "CDC WONDER",
        "url": "https://wonder.cdc.gov/",
        "cost": "Free",
        "coverage": "US-focused, major indications",
        "priority": 2,
    },
    "who_gho": {
        "name": "WHO Global Health Observatory",
        "url": "https://www.who.int/data/gho",
        "cost": "Free",
        "coverage": "Global, patchy on rare diseases",
        "priority": 3,
    },
    "pubmed_extraction": {
        "name": "PubMed + LLM",
        "cost": "Compute only",
        "coverage": "Gap-filling for rare diseases",
        "priority": 4,
    },
    "ctgov_enrollment": {
        "name": "ClinicalTrials.gov Enrollment",
        "cost": "Free",
        "coverage": "Sanity check / proxy",
        "priority": 5,
    },
}


# Static prevalence data (US estimates) for MVP
# In production, would fetch from APIs
US_PREVALENCE_DATA = {
    # Oncology
    "breast cancer": {
        "prevalence": 3_800_000,
        "incidence": 297_000,
        "source": "American Cancer Society 2024",
    },
    "lung cancer": {
        "prevalence": 650_000,
        "incidence": 238_000,
        "source": "American Cancer Society 2024",
    },
    "prostate cancer": {
        "prevalence": 3_300_000,
        "incidence": 288_000,
        "source": "American Cancer Society 2024",
    },
    "colorectal cancer": {
        "prevalence": 1_500_000,
        "incidence": 153_000,
        "source": "American Cancer Society 2024",
    },
    "melanoma": {
        "prevalence": 1_300_000,
        "incidence": 100_000,
        "source": "American Cancer Society 2024",
    },

    # Neurology
    "alzheimer": {
        "prevalence": 6_700_000,
        "incidence": 500_000,
        "source": "Alzheimer's Association 2024",
    },
    "parkinson": {
        "prevalence": 1_000_000,
        "incidence": 90_000,
        "source": "Parkinson's Foundation 2024",
    },
    "multiple sclerosis": {
        "prevalence": 1_000_000,
        "incidence": 10_000,
        "source": "National MS Society 2024",
    },
    "epilepsy": {
        "prevalence": 3_400_000,
        "incidence": 150_000,
        "source": "Epilepsy Foundation 2024",
    },

    # Metabolic
    "type 2 diabetes": {
        "prevalence": 37_300_000,
        "incidence": 1_500_000,
        "source": "CDC Diabetes Statistics 2024",
    },
    "type 1 diabetes": {
        "prevalence": 1_900_000,
        "incidence": 64_000,
        "source": "CDC Diabetes Statistics 2024",
    },
    "obesity": {
        "prevalence": 100_000_000,
        "incidence": None,
        "source": "CDC NHANES 2024",
    },
    "nash": {
        "prevalence": 16_500_000,
        "incidence": 1_000_000,
        "source": "AASLD Guidelines 2024",
    },

    # Immunology/Inflammatory
    "rheumatoid arthritis": {
        "prevalence": 1_500_000,
        "incidence": 41_000,
        "source": "Arthritis Foundation 2024",
    },
    "psoriasis": {
        "prevalence": 7_500_000,
        "incidence": 250_000,
        "source": "NPF 2024",
    },
    "psoriatic arthritis": {
        "prevalence": 2_000_000,
        "incidence": 50_000,
        "source": "NPF 2024",
    },
    "crohn's disease": {
        "prevalence": 780_000,
        "incidence": 33_000,
        "source": "CCFA 2024",
    },
    "ulcerative colitis": {
        "prevalence": 910_000,
        "incidence": 38_000,
        "source": "CCFA 2024",
    },
    "lupus": {
        "prevalence": 1_500_000,
        "incidence": 16_000,
        "source": "Lupus Foundation 2024",
    },

    # Cardiovascular
    "heart failure": {
        "prevalence": 6_700_000,
        "incidence": 960_000,
        "source": "AHA Heart Disease Statistics 2024",
    },
    "atrial fibrillation": {
        "prevalence": 6_000_000,
        "incidence": 450_000,
        "source": "AHA Heart Disease Statistics 2024",
    },
    "hypertension": {
        "prevalence": 119_000_000,
        "incidence": None,
        "source": "AHA Heart Disease Statistics 2024",
    },

    # Psychiatry
    "major depression": {
        "prevalence": 21_000_000,
        "incidence": 8_000_000,
        "source": "NIMH 2024",
    },
    "schizophrenia": {
        "prevalence": 2_800_000,
        "incidence": 100_000,
        "source": "NIMH 2024",
    },
    "bipolar disorder": {
        "prevalence": 7_000_000,
        "incidence": 500_000,
        "source": "NIMH 2024",
    },
    "anxiety disorders": {
        "prevalence": 40_000_000,
        "incidence": None,
        "source": "NIMH 2024",
    },

    # Rare diseases (examples)
    "huntington's disease": {
        "prevalence": 41_000,
        "incidence": 3_000,
        "source": "HDSA 2024",
    },
    "amyotrophic lateral sclerosis": {
        "prevalence": 31_000,
        "incidence": 5_000,
        "source": "ALS Association 2024",
    },
    "cystic fibrosis": {
        "prevalence": 40_000,
        "incidence": 1_000,
        "source": "CF Foundation 2024",
    },
    "sickle cell disease": {
        "prevalence": 100_000,
        "incidence": 3_000,
        "source": "CDC 2024",
    },
    "duchenne muscular dystrophy": {
        "prevalence": 16_000,
        "incidence": 400,
        "source": "Parent Project MD 2024",
    },
    "rett syndrome": {
        "prevalence": 15_000,
        "incidence": 400,
        "source": "IRSF 2024",
    },
}


class EpidemiologyFetcher:
    """Fetches patient population data from various sources."""

    def __init__(self):
        """Initialize epidemiology fetcher."""
        self._cache: Dict[str, Dict] = {}

    def get_prevalence(
        self,
        indication: str,
        country: str = "US",
    ) -> Dict[str, Any]:
        """Get prevalence data for an indication.

        Args:
            indication: Disease/condition name
            country: Country code (currently only US supported)

        Returns:
            Dict with prevalence, incidence, source
        """
        # Check cache
        cache_key = f"{indication.lower()}_{country}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try static data first
        result = self._lookup_static(indication)

        if result:
            self._cache[cache_key] = result
            return result

        # Try LLM extraction from PubMed (if API key available)
        if os.getenv("ANTHROPIC_API_KEY"):
            result = self._extract_from_literature(indication)
            if result:
                self._cache[cache_key] = result
                return result

        # Fallback to heuristic
        result = self._estimate_heuristic(indication)
        self._cache[cache_key] = result
        return result

    def _lookup_static(self, indication: str) -> Optional[Dict[str, Any]]:
        """Look up indication in static prevalence data."""
        indication_lower = indication.lower()

        # Direct match
        if indication_lower in US_PREVALENCE_DATA:
            data = US_PREVALENCE_DATA[indication_lower]
            return {
                "prevalence": data["prevalence"],
                "incidence": data.get("incidence"),
                "source": data["source"],
                "method": "static_database",
                "confidence": "high",
            }

        # Partial match
        for key, data in US_PREVALENCE_DATA.items():
            if key in indication_lower or indication_lower in key:
                return {
                    "prevalence": data["prevalence"],
                    "incidence": data.get("incidence"),
                    "source": data["source"],
                    "method": "static_database_partial",
                    "matched_key": key,
                    "confidence": "medium",
                }

        return None

    def _extract_from_literature(self, indication: str) -> Optional[Dict[str, Any]]:
        """Extract prevalence from literature using LLM.

        Would search PubMed and extract from abstracts.
        For MVP, returns None to fall back to heuristic.
        """
        # TODO: Implement PubMed search + LLM extraction
        # This would:
        # 1. Search PubMed for "indication epidemiology prevalence United States"
        # 2. Get top 5 abstracts
        # 3. Use LLM to extract prevalence figures
        # 4. Cross-validate across sources
        return None

    def _estimate_heuristic(self, indication: str) -> Dict[str, Any]:
        """Estimate prevalence using heuristics.

        Falls back to category-based estimates when no specific data.
        """
        indication_lower = indication.lower()

        # Category detection
        if any(kw in indication_lower for kw in ["cancer", "carcinoma", "tumor", "lymphoma", "leukemia"]):
            return {
                "prevalence": 500_000,
                "source": "Heuristic estimate (oncology category)",
                "method": "heuristic",
                "confidence": "low",
            }

        if any(kw in indication_lower for kw in ["rare", "orphan", "syndrome", "dystrophy"]):
            return {
                "prevalence": 30_000,
                "source": "Heuristic estimate (rare disease category)",
                "method": "heuristic",
                "confidence": "low",
            }

        if any(kw in indication_lower for kw in ["neuro", "brain", "cognitive"]):
            return {
                "prevalence": 1_000_000,
                "source": "Heuristic estimate (neurology category)",
                "method": "heuristic",
                "confidence": "low",
            }

        # Default
        return {
            "prevalence": 500_000,
            "source": "Heuristic default estimate",
            "method": "heuristic",
            "confidence": "very_low",
        }

    def get_enrollment_proxy(
        self,
        indication: str,
    ) -> Optional[Dict[str, Any]]:
        """Use ClinicalTrials.gov enrollment as prevalence proxy.

        Useful for rare diseases where enrollment represents
        significant portion of patient population.
        """
        try:
            from data.scraper import ClinicalTrialsScraper

            scraper = ClinicalTrialsScraper(months_ahead=24)
            trials = scraper.fetch_trials()

            # Filter by indication
            indication_lower = indication.lower()
            relevant_trials = []

            for _, trial in trials.iterrows():
                conditions = trial.get("condition", "")
                if indication_lower in conditions.lower():
                    enrollment = trial.get("enrollment_count", 0)
                    if enrollment and enrollment > 0:
                        relevant_trials.append(enrollment)

            if relevant_trials:
                avg_enrollment = sum(relevant_trials) / len(relevant_trials)
                # Multiply by factor to estimate population
                # (trials typically enroll 0.1-1% of patients)
                estimated_prevalence = avg_enrollment * 500

                return {
                    "prevalence": estimated_prevalence,
                    "source": f"ClinicalTrials.gov ({len(relevant_trials)} trials)",
                    "method": "enrollment_proxy",
                    "avg_enrollment": avg_enrollment,
                    "confidence": "low",
                }

        except Exception as e:
            logger.warning(f"Enrollment proxy failed: {e}")

        return None

    def list_sources(self) -> List[Dict[str, Any]]:
        """List available epidemiology data sources."""
        return [
            {
                "id": source_id,
                **source_info,
            }
            for source_id, source_info in EPIDEMIOLOGY_SOURCES.items()
        ]

    def get_data_quality_score(self, result: Dict[str, Any]) -> float:
        """Score data quality based on source and method.

        Args:
            result: Prevalence result dict

        Returns:
            Score from 0-100
        """
        method = result.get("method", "unknown")
        confidence = result.get("confidence", "unknown")

        # Base score by method
        method_scores = {
            "static_database": 90,
            "static_database_partial": 70,
            "literature_extraction": 60,
            "enrollment_proxy": 40,
            "heuristic": 20,
            "unknown": 10,
        }

        base_score = method_scores.get(method, 10)

        # Adjust by confidence
        confidence_multipliers = {
            "high": 1.0,
            "medium": 0.8,
            "low": 0.6,
            "very_low": 0.4,
        }

        multiplier = confidence_multipliers.get(confidence, 0.5)

        return base_score * multiplier


# Singleton instance
_fetcher_instance: Optional[EpidemiologyFetcher] = None


def get_epidemiology_fetcher() -> EpidemiologyFetcher:
    """Get singleton fetcher instance."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = EpidemiologyFetcher()
    return _fetcher_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test epidemiology fetcher
    fetcher = get_epidemiology_fetcher()

    test_indications = [
        "Alzheimer's disease",
        "Breast cancer",
        "Rett syndrome",
        "Obesity",
        "Unknown rare syndrome",
    ]

    for indication in test_indications:
        result = fetcher.get_prevalence(indication)
        quality = fetcher.get_data_quality_score(result)
        print(f"\n{indication}:")
        print(f"  Prevalence: {result['prevalence']:,}")
        print(f"  Source: {result['source']}")
        print(f"  Quality Score: {quality:.0f}/100")
