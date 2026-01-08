"""Natural Language Filter Parser.

Per spec Phase 3 Section 2.3:
- Allow users to filter dashboard using natural language queries
- Parse NL to structured JSON filters
- Apply filters to catalyst dataframe
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# NL Filter parsing prompt
NL_FILTER_PROMPT = """
Parse this natural language filter query into structured JSON.

Query: "{query}"

Return JSON matching this schema:
{{
    "indication": ["string"] or null,  // therapeutic areas
    "market_cap_max_usd": number or null,
    "market_cap_min_usd": number or null,
    "catalyst_window_days": [min, max] or null,
    "phase_filter": ["Phase2", "Phase3"] or null,
    "cash_runway_min_months": number or null,
    "trial_quality_min": number or null,  // 0-100
    "event_types": ["PDUFA", "Readout"] or null
}}

Examples:
- "obesity under $3B" -> {{"indication": ["obesity"], "market_cap_max_usd": 3000000000}}
- "Phase 3 readouts next 30 days" -> {{"phase_filter": ["Phase3"], "catalyst_window_days": [0, 30]}}
- "oncology with >18 months runway" -> {{"indication": ["oncology"], "cash_runway_min_months": 18}}
- "small caps under $2B in neurology" -> {{"indication": ["neurology"], "market_cap_max_usd": 2000000000}}

Return ONLY valid JSON, no explanation.
"""


class NLFilterParser:
    """Parses natural language queries into structured filters."""

    # Common indication keywords
    INDICATION_KEYWORDS = {
        "oncology": ["oncology", "cancer", "tumor", "carcinoma", "lymphoma", "leukemia"],
        "neurology": ["neuro", "alzheimer", "parkinson", "epilepsy", "ms", "multiple sclerosis"],
        "cardiology": ["cardio", "heart", "cardiovascular", "hypertension"],
        "immunology": ["immuno", "autoimmune", "inflammation", "arthritis"],
        "obesity": ["obesity", "weight", "metabolic"],
        "diabetes": ["diabetes", "diabetic", "glucose", "insulin"],
        "rare_disease": ["rare", "orphan"],
        "respiratory": ["respiratory", "lung", "asthma", "copd"],
        "dermatology": ["derm", "skin", "psoriasis", "eczema"],
        "ophthalmology": ["eye", "vision", "retina", "macular"],
    }

    def __init__(self):
        """Initialize the filter parser."""
        self._llm_available = bool(os.getenv("ANTHROPIC_API_KEY"))

    def parse_query(self, query: str) -> Dict[str, Any]:
        """Convert NL query to structured filter.

        Args:
            query: Natural language filter query

        Returns:
            Structured filter dict
        """
        if self._llm_available:
            try:
                return self._parse_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM parsing failed, falling back to heuristic: {e}")

        return self._parse_heuristic(query)

    def _parse_with_llm(self, query: str) -> Dict[str, Any]:
        """Parse query using LLM."""
        import anthropic

        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": NL_FILTER_PROMPT.format(query=query),
            }],
        )

        response_text = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```" in response_text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
            if match:
                response_text = match.group(1)

        return json.loads(response_text)

    def _parse_heuristic(self, query: str) -> Dict[str, Any]:
        """Parse query using heuristics (fallback when no LLM).

        Args:
            query: Natural language query

        Returns:
            Structured filter dict
        """
        filters: Dict[str, Any] = {}
        query_lower = query.lower()

        # Parse indication
        for indication, keywords in self.INDICATION_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                filters.setdefault("indication", []).append(indication)

        # Parse market cap
        # Patterns: "under $3B", "below $2B", "<$5B", "small cap", "micro cap"
        market_cap_match = re.search(
            r"(?:under|below|<|less than)\s*\$?(\d+(?:\.\d+)?)\s*([BMK])?",
            query,
            re.IGNORECASE,
        )
        if market_cap_match:
            value = float(market_cap_match.group(1))
            multiplier = {"B": 1e9, "M": 1e6, "K": 1e3}.get(
                (market_cap_match.group(2) or "B").upper(), 1e9
            )
            filters["market_cap_max_usd"] = value * multiplier

        if "small cap" in query_lower:
            filters.setdefault("market_cap_max_usd", 2e9)
        if "micro cap" in query_lower:
            filters.setdefault("market_cap_max_usd", 300e6)

        # Parse phase
        if "phase 3" in query_lower or "phase3" in query_lower or "p3" in query_lower:
            filters.setdefault("phase_filter", []).append("Phase3")
        if "phase 2" in query_lower or "phase2" in query_lower or "p2" in query_lower:
            filters.setdefault("phase_filter", []).append("Phase2")

        # Parse time window
        # Patterns: "next 30 days", "within 2 weeks", "this month"
        days_match = re.search(r"(?:next|within)\s*(\d+)\s*days?", query_lower)
        if days_match:
            filters["catalyst_window_days"] = [0, int(days_match.group(1))]

        weeks_match = re.search(r"(?:next|within)\s*(\d+)\s*weeks?", query_lower)
        if weeks_match:
            filters["catalyst_window_days"] = [0, int(weeks_match.group(1)) * 7]

        if "this month" in query_lower:
            filters["catalyst_window_days"] = [0, 30]
        if "this quarter" in query_lower:
            filters["catalyst_window_days"] = [0, 90]

        # Parse cash runway
        runway_match = re.search(
            r"(?:runway|cash)\s*(?:>|greater than|more than|at least)\s*(\d+)\s*months?",
            query_lower,
        )
        if runway_match:
            filters["cash_runway_min_months"] = int(runway_match.group(1))

        # Parse event types
        if "pdufa" in query_lower:
            filters.setdefault("event_types", []).append("PDUFA")
        if "readout" in query_lower:
            filters.setdefault("event_types", []).append("Readout")
        if "adcom" in query_lower:
            filters.setdefault("event_types", []).append("AdCom")

        return filters

    def apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply parsed filters to catalyst dataframe.

        Args:
            df: Catalyst dataframe
            filters: Parsed filter dict

        Returns:
            Filtered dataframe
        """
        if df.empty:
            return df

        result = df.copy()

        # Filter by indication
        if filters.get("indication"):
            indications = filters["indication"]
            indication_pattern = "|".join(indications)
            if "indication" in result.columns:
                result = result[
                    result["indication"].str.contains(
                        indication_pattern, case=False, na=False
                    )
                ]

        # Filter by market cap
        if filters.get("market_cap_max_usd") and "market_cap_usd" in result.columns:
            result = result[result["market_cap_usd"] <= filters["market_cap_max_usd"]]

        if filters.get("market_cap_min_usd") and "market_cap_usd" in result.columns:
            result = result[result["market_cap_usd"] >= filters["market_cap_min_usd"]]

        # Filter by phase
        if filters.get("phase_filter"):
            phases = filters["phase_filter"]
            if "trial_phase" in result.columns:
                result = result[result["trial_phase"].isin(phases)]
            elif "phase" in result.columns:
                result = result[result["phase"].isin(phases)]

        # Filter by catalyst window (days until)
        if filters.get("catalyst_window_days"):
            min_days, max_days = filters["catalyst_window_days"]
            if "days_until" in result.columns:
                result = result[
                    (result["days_until"] >= min_days) &
                    (result["days_until"] <= max_days)
                ]
            elif "catalyst_date" in result.columns:
                from datetime import datetime
                today = datetime.now().date()
                result["_days_until"] = pd.to_datetime(result["catalyst_date"]).dt.date.apply(
                    lambda d: (d - today).days if pd.notna(d) else None
                )
                result = result[
                    (result["_days_until"] >= min_days) &
                    (result["_days_until"] <= max_days)
                ]
                result = result.drop(columns=["_days_until"])

        # Filter by cash runway
        if filters.get("cash_runway_min_months") and "cash_runway_months" in result.columns:
            result = result[
                result["cash_runway_months"] >= filters["cash_runway_min_months"]
            ]

        # Filter by trial quality
        if filters.get("trial_quality_min") and "trial_design_score" in result.columns:
            result = result[
                result["trial_design_score"] >= filters["trial_quality_min"]
            ]

        # Filter by event types
        if filters.get("event_types"):
            event_types = filters["event_types"]
            if "catalyst_type" in result.columns:
                pattern = "|".join(event_types)
                result = result[
                    result["catalyst_type"].str.contains(pattern, case=False, na=False)
                ]

        return result

    def format_applied_filters(self, filters: Dict[str, Any]) -> str:
        """Format filters for display to user.

        Args:
            filters: Parsed filter dict

        Returns:
            Human-readable filter summary
        """
        parts = []

        if filters.get("indication"):
            parts.append(f"Indication: {', '.join(filters['indication'])}")

        if filters.get("market_cap_max_usd"):
            cap = filters["market_cap_max_usd"]
            if cap >= 1e9:
                parts.append(f"Market Cap: <${cap/1e9:.1f}B")
            else:
                parts.append(f"Market Cap: <${cap/1e6:.0f}M")

        if filters.get("phase_filter"):
            parts.append(f"Phase: {', '.join(filters['phase_filter'])}")

        if filters.get("catalyst_window_days"):
            min_d, max_d = filters["catalyst_window_days"]
            parts.append(f"Window: {min_d}-{max_d} days")

        if filters.get("cash_runway_min_months"):
            parts.append(f"Runway: >{filters['cash_runway_min_months']} months")

        if filters.get("event_types"):
            parts.append(f"Events: {', '.join(filters['event_types'])}")

        return " | ".join(parts) if parts else "No filters applied"


# Singleton instance
_parser_instance: Optional[NLFilterParser] = None


def get_nl_filter_parser() -> NLFilterParser:
    """Get singleton parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = NLFilterParser()
    return _parser_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test parsing
    parser = get_nl_filter_parser()

    test_queries = [
        "obesity under $3B",
        "Phase 3 readouts next 30 days",
        "oncology with >18 months runway",
        "small cap neuro plays",
        "PDUFA dates this quarter",
    ]

    for query in test_queries:
        filters = parser.parse_query(query)
        formatted = parser.format_applied_filters(filters)
        print(f"Query: {query}")
        print(f"Filters: {filters}")
        print(f"Display: {formatted}")
        print()
