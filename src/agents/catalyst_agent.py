"""
Rule-based catalyst query agent.

This agent uses keyword matching and pattern recognition to understand
natural language queries about biotech catalysts. No LLM is used - all
responses are deterministic and based on simple rules.

Examples:
    - "Phase 3 oncology under $2B"
    - "trials next 60 days"
    - "neurology catalysts"
    - "rare disease under $1B in Q1 2025"
"""

import re
from datetime import datetime
from typing import Dict, List, Any
import logging

from ..utils.db import get_catalysts

logger = logging.getLogger(__name__)


class CatalystAgent:
    """Rule-based agent for querying catalyst database.

    This agent parses natural language queries using keyword matching
    and returns structured responses with catalyst data.
    """

    # Therapeutic area keywords mapping
    THERAPEUTIC_AREAS = {
        "oncology": [
            "oncology",
            "cancer",
            "tumor",
            "carcinoma",
            "melanoma",
            "leukemia",
            "lymphoma",
        ],
        "neurology": [
            "neurology",
            "neurological",
            "alzheimer",
            "parkinson",
            "multiple sclerosis",
            "ms",
            "epilepsy",
        ],
        "rare disease": ["rare disease", "orphan", "rare disorder"],
        "cardiology": ["cardiology", "cardiovascular", "heart", "cardiac"],
        "immunology": ["immunology", "immune", "autoimmune", "rheumatoid"],
        "infectious disease": [
            "infectious",
            "virus",
            "viral",
            "bacterial",
            "covid",
            "hiv",
        ],
        "metabolic": ["metabolic", "diabetes", "obesity", "nash", "nafld"],
        "respiratory": ["respiratory", "asthma", "copd", "pulmonary"],
        "dermatology": [
            "dermatology",
            "skin",
            "psoriasis",
            "eczema",
            "atopic dermatitis",
        ],
    }

    # Market cap keywords
    MARKET_CAP_PATTERNS = [
        (r"under\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
        (r"below\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
        (r"less than\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
        (r"<\s*\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
    ]

    # Phase keywords
    PHASE_PATTERNS = {
        "phase 2": ["phase 2", "phase ii", "p2"],
        "phase 3": ["phase 3", "phase iii", "p3"],
    }

    # Timeframe keywords
    TIMEFRAME_PATTERNS = [
        (r"next\s+(\d+)\s+days?", lambda m: int(m.group(1))),
        (r"within\s+(\d+)\s+days?", lambda m: int(m.group(1))),
        (r"(\d+)\s+days?", lambda m: int(m.group(1))),
        (r"q1\s+(\d{4})", lambda m: ("q1", int(m.group(1)))),
        (r"q2\s+(\d{4})", lambda m: ("q2", int(m.group(1)))),
        (r"q3\s+(\d{4})", lambda m: ("q3", int(m.group(1)))),
        (r"q4\s+(\d{4})", lambda m: ("q4", int(m.group(1)))),
        (
            r"january|february|march|april|may|june|july|august|september|october|november|december",
            "month",
        ),
    ]

    def __init__(self):
        """Initialize the catalyst agent."""
        self.default_limit = 50  # Max results to return

    def parse_query(self, user_message: str) -> Dict[str, Any]:
        """Extract filters from natural language query.

        Uses keyword matching to identify:
        - Therapeutic areas (oncology, neurology, etc.)
        - Market cap thresholds (under $2B, below $5B)
        - Phase (Phase 2, Phase 3)
        - Timeframe (next 60 days, Q1 2025)

        Args:
            user_message: User's natural language query

        Returns:
            Dictionary with extracted filters:
            {
                "therapeutic_area": str or None,
                "max_market_cap": int or None,
                "phase": str or None,
                "days_ahead": int or None,
                "quarter": tuple(quarter, year) or None
            }
        """
        query_lower = user_message.lower()
        filters = {
            "therapeutic_area": None,
            "max_market_cap": None,
            "phase": None,
            "days_ahead": None,
            "quarter": None,
        }

        # Extract therapeutic area
        for area, keywords in self.THERAPEUTIC_AREAS.items():
            if any(keyword in query_lower for keyword in keywords):
                filters["therapeutic_area"] = area
                break

        # Extract market cap threshold
        for pattern, extractor in self.MARKET_CAP_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                filters["max_market_cap"] = int(extractor(match))
                break

        # Extract phase
        for phase, keywords in self.PHASE_PATTERNS.items():
            if any(keyword in query_lower for keyword in keywords):
                filters["phase"] = phase.title()  # "Phase 2" or "Phase 3"
                break

        # Extract timeframe
        for pattern, extractor in self.TIMEFRAME_PATTERNS:
            if isinstance(pattern, str):
                # Month pattern
                if pattern in query_lower:
                    # For simplicity, treat month queries as 90 days
                    filters["days_ahead"] = 90
                    break
            else:
                match = re.search(pattern, query_lower)
                if match:
                    result = extractor(match)
                    if isinstance(result, tuple):
                        # Quarter pattern
                        filters["quarter"] = result
                    else:
                        # Days pattern
                        filters["days_ahead"] = result
                    break

        logger.info(f"Parsed query: {user_message} -> {filters}")
        return filters

    def query_database(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query catalyst database with extracted filters.

        Args:
            filters: Dictionary of filters from parse_query()

        Returns:
            List of catalyst dictionaries matching the filters
        """
        try:
            # Get catalysts from database
            phase = filters.get("phase")
            max_market_cap = filters.get("max_market_cap")

            catalysts = get_catalysts(
                phase=phase,
                max_market_cap=max_market_cap,
                min_ticker_confidence=80,
                limit=self.default_limit,
            )

            # Apply additional filtering not supported by get_catalysts
            filtered_catalysts = []

            for catalyst in catalysts:
                # Filter by therapeutic area (keyword match in indication)
                therapeutic_area = filters.get("therapeutic_area")
                if therapeutic_area:
                    indication = (catalyst.get("indication") or "").lower()
                    keywords = self.THERAPEUTIC_AREAS.get(therapeutic_area, [])
                    if not any(keyword in indication for keyword in keywords):
                        continue

                # Filter by timeframe
                days_ahead = filters.get("days_ahead")
                quarter = filters.get("quarter")

                if days_ahead is not None or quarter is not None:
                    completion_date = catalyst.get("completion_date")
                    if not completion_date:
                        continue

                    if days_ahead is not None:
                        # Check if within specified days
                        days_until = (completion_date - datetime.now()).days
                        if days_until < 0 or days_until > days_ahead:
                            continue

                    if quarter is not None:
                        # Check if in specified quarter
                        q, year = quarter
                        quarter_num = int(q[1])  # Extract number from "q1"

                        # Quarter date ranges
                        quarter_ranges = {
                            1: (1, 3),
                            2: (4, 6),
                            3: (7, 9),
                            4: (10, 12),
                        }
                        start_month, end_month = quarter_ranges[quarter_num]

                        if not (
                            completion_date.year == year
                            and start_month <= completion_date.month <= end_month
                        ):
                            continue

                filtered_catalysts.append(catalyst)

            logger.info(f"Found {len(filtered_catalysts)} catalysts matching filters")
            return filtered_catalysts

        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise

    def format_response(
        self, catalysts: List[Dict[str, Any]], user_query: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure response for chat UI.

        Args:
            catalysts: List of catalyst dictionaries from database
            user_query: Original user query
            filters: Parsed filters from parse_query()

        Returns:
            Structured response dictionary:
            {
                "type": "catalyst_list",
                "message": str (summary message),
                "data": list (catalyst data),
                "actions": list (available actions per catalyst)
            }
        """
        # Build summary message
        if not catalysts:
            message = self._format_no_results_message(filters)
            return {"type": "no_results", "message": message, "data": [], "actions": []}

        # Build success message
        message = self._format_success_message(catalysts, filters)

        # Define available actions for each catalyst
        actions = [
            {"icon": "📊", "label": "Details", "action": "view_details"},
            {"icon": "⭐", "label": "Watch", "action": "add_to_watchlist"},
            {"icon": "🔔", "label": "Alert", "action": "set_alert"},
        ]

        return {
            "type": "catalyst_list",
            "message": message,
            "data": catalysts[:20],  # Limit to 20 for display
            "actions": actions,
            "total_count": len(catalysts),
        }

    def _format_success_message(
        self, catalysts: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> str:
        """Format success message based on filters.

        Args:
            catalysts: List of found catalysts
            filters: Applied filters

        Returns:
            Human-readable success message
        """
        count = len(catalysts)
        parts = []

        # Add filter descriptions
        if filters.get("phase"):
            parts.append(f"**{filters['phase']}**")

        if filters.get("therapeutic_area"):
            area = filters["therapeutic_area"].title()
            parts.append(f"**{area}**")

        if filters.get("max_market_cap"):
            cap_b = filters["max_market_cap"] / 1e9
            parts.append(f"under **${cap_b:.1f}B** market cap")

        if filters.get("days_ahead"):
            parts.append(f"in the next **{filters['days_ahead']} days**")

        if filters.get("quarter"):
            q, year = filters["quarter"]
            parts.append(f"in **{q.upper()} {year}**")

        # Build message
        if parts:
            filter_desc = " ".join(parts)
            message = f"Found **{count} catalysts** matching {filter_desc}"
        else:
            message = f"Found **{count} upcoming catalysts**"

        if count > 20:
            message += " (showing top 20)"

        return message

    def _format_no_results_message(self, filters: Dict[str, Any]) -> str:
        """Format no results message with suggestions.

        Args:
            filters: Applied filters

        Returns:
            Human-readable no results message with suggestions
        """
        message = "No catalysts found matching your criteria.\n\n"
        message += "**Try:**\n"
        message += "- Broadening your market cap threshold\n"
        message += "- Expanding the timeframe\n"
        message += "- Searching for a different therapeutic area\n"
        message += "- Removing Phase filters\n\n"
        message += "**Example queries:**\n"
        message += "- `Phase 3 oncology under $5B`\n"
        message += "- `trials next 90 days`\n"
        message += "- `neurology catalysts`"

        return message

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """Main entry point: parse query, fetch data, format response.

        This is the primary method to call from the UI.

        Args:
            user_message: User's natural language query

        Returns:
            Structured response ready for UI rendering

        Raises:
            Exception: If database query fails
        """
        try:
            # Step 1: Parse the query
            filters = self.parse_query(user_message)

            # Step 2: Query the database
            catalysts = self.query_database(filters)

            # Step 3: Format the response
            response = self.format_response(catalysts, user_message, filters)

            return response

        except Exception as e:
            logger.error(f"Error processing query '{user_message}': {e}")
            return {
                "type": "error",
                "message": f"Sorry, I encountered an error processing your request. Please try again or simplify your query.\n\nError: {str(e)}",
                "data": [],
                "actions": [],
            }
