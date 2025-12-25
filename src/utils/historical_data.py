"""Historical statistics for clinical trials and run-up patterns.

This module provides hardcoded industry statistics for phase success rates
and run-up patterns. In future versions, this will be replaced with real
historical data from a database.

Sources:
- Phase success rates: BIO Clinical Development Success Rates 2006-2015
- Run-up patterns: Based on analysis of small-cap biotech price movements
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Optional


# Phase transition success rates by therapeutic area
# Source: BIO Clinical Development Success Rates 2006-2015
PHASE_SUCCESS_RATES = {
    "oncology": {
        "phase_2_to_3": 0.30,
        "phase_3_to_approval": 0.50,
        "overall_approval": 0.15,
    },
    "rare_disease": {
        "phase_2_to_3": 0.40,
        "phase_3_to_approval": 0.60,
        "overall_approval": 0.24,
    },
    "neurology": {
        "phase_2_to_3": 0.25,
        "phase_3_to_approval": 0.45,
        "overall_approval": 0.11,
    },
    "cardiovascular": {
        "phase_2_to_3": 0.35,
        "phase_3_to_approval": 0.55,
        "overall_approval": 0.19,
    },
    "immunology": {
        "phase_2_to_3": 0.38,
        "phase_3_to_approval": 0.58,
        "overall_approval": 0.22,
    },
    "infectious_disease": {
        "phase_2_to_3": 0.33,
        "phase_3_to_approval": 0.52,
        "overall_approval": 0.17,
    },
    "default": {
        "phase_2_to_3": 0.35,
        "phase_3_to_approval": 0.52,
        "overall_approval": 0.18,
    },
}

# Average price run-up patterns by market cap tier and time window
# Based on analysis of small-cap biotech price movements before catalysts
RUN_UP_PATTERNS = {
    "small_cap": {  # < $2B market cap
        "90_day": 0.35,  # 35% average run-up 90 days before catalyst
        "60_day": 0.28,  # 28% average run-up 60 days before catalyst
        "30_day": 0.15,  # 15% average run-up 30 days before catalyst
        "volatility": 0.45,  # 45% daily volatility
    },
    "mid_cap": {  # $2-5B market cap
        "90_day": 0.20,  # 20% average run-up 90 days before catalyst
        "60_day": 0.15,  # 15% average run-up 60 days before catalyst
        "30_day": 0.08,  # 8% average run-up 30 days before catalyst
        "volatility": 0.30,  # 30% daily volatility
    },
}

# Therapeutic area keywords for classification
THERAPEUTIC_AREA_KEYWORDS = {
    "oncology": ["cancer", "tumor", "carcinoma", "lymphoma", "leukemia", "melanoma", "oncology"],
    "rare_disease": ["rare", "orphan", "genetic disorder", "inherited"],
    "neurology": ["alzheimer", "parkinson", "epilepsy", "multiple sclerosis", "neuropathy", "neurology"],
    "cardiovascular": ["heart", "cardiac", "hypertension", "cardiovascular", "coronary"],
    "immunology": ["autoimmune", "rheumatoid", "lupus", "psoriasis", "crohn", "immunology"],
    "infectious_disease": ["hiv", "hepatitis", "tuberculosis", "covid", "virus", "bacterial infection"],
}


def get_success_rate(therapeutic_area: str, phase: str) -> float:
    """Get historical success rate for a therapeutic area and phase.

    Args:
        therapeutic_area: Therapeutic area (e.g., "oncology", "rare_disease")
        phase: Trial phase ("Phase 2", "Phase 3", or "approval")

    Returns:
        Success rate as a float between 0 and 1
    """
    area = therapeutic_area.lower().replace(" ", "_")
    if area not in PHASE_SUCCESS_RATES:
        area = "default"

    stats = PHASE_SUCCESS_RATES[area]

    if phase == "Phase 2":
        return stats["phase_2_to_3"]
    elif phase == "Phase 3":
        return stats["phase_3_to_approval"]
    elif phase.lower() == "approval":
        return stats["overall_approval"]
    else:
        return stats["phase_2_to_3"]


def get_run_up_estimate(market_cap: float, days_to_completion: int) -> float:
    """Get estimated run-up percentage based on market cap and timing.

    Args:
        market_cap: Market capitalization in dollars
        days_to_completion: Number of days until completion date

    Returns:
        Estimated run-up percentage as a float (e.g., 0.25 = 25%)
    """
    # Determine market cap tier
    if market_cap < 2_000_000_000:  # < $2B
        tier = "small_cap"
    else:  # $2-5B
        tier = "mid_cap"

    patterns = RUN_UP_PATTERNS[tier]

    # Select run-up based on time window
    if days_to_completion >= 90:
        return patterns["90_day"]
    elif days_to_completion >= 60:
        return patterns["60_day"]
    elif days_to_completion >= 30:
        return patterns["30_day"]
    else:
        # Linear interpolation for < 30 days
        return patterns["30_day"] * (days_to_completion / 30)


def get_optimal_entry_window(completion_date: date, market_cap: float) -> Dict[str, any]:
    """Calculate optimal entry timing for a catalyst trade.

    Args:
        completion_date: Expected trial completion date
        market_cap: Market capitalization in dollars

    Returns:
        Dictionary with entry window recommendations:
        {
            "optimal_entry_date": date,
            "optimal_days_before": int,
            "expected_run_up": float,
            "risk_level": str,
            "rationale": str
        }
    """
    # Determine market cap tier
    if market_cap < 2_000_000_000:  # < $2B
        tier = "small_cap"
        optimal_days = 60
        risk_level = "High"
        rationale = "Small caps have higher volatility but larger run-up potential"
    else:  # $2-5B
        tier = "mid_cap"
        optimal_days = 45
        risk_level = "Medium"
        rationale = "Mid caps have moderate volatility with consistent run-up patterns"

    optimal_date = completion_date - timedelta(days=optimal_days)
    expected_run_up = RUN_UP_PATTERNS[tier]["60_day"]

    return {
        "optimal_entry_date": optimal_date,
        "optimal_days_before": optimal_days,
        "expected_run_up": expected_run_up,
        "risk_level": risk_level,
        "rationale": rationale,
    }


def classify_therapeutic_area(condition: str) -> str:
    """Classify therapeutic area based on condition keywords.

    Args:
        condition: Condition/indication string

    Returns:
        Therapeutic area name (e.g., "oncology", "rare_disease")
        Returns "default" if no match found
    """
    if not condition:
        return "default"

    condition_lower = condition.lower()

    for area, keywords in THERAPEUTIC_AREA_KEYWORDS.items():
        if any(keyword in condition_lower for keyword in keywords):
            return area

    return "default"


def get_therapeutic_area_stats(therapeutic_area: str) -> Dict[str, any]:
    """Get comprehensive statistics for a therapeutic area.

    Args:
        therapeutic_area: Therapeutic area name

    Returns:
        Dictionary with all statistics for the area
    """
    area = therapeutic_area.lower().replace(" ", "_")
    if area not in PHASE_SUCCESS_RATES:
        area = "default"

    stats = PHASE_SUCCESS_RATES[area]

    return {
        "area": therapeutic_area,
        "phase_2_success": stats["phase_2_to_3"],
        "phase_3_success": stats["phase_3_to_approval"],
        "overall_approval": stats["overall_approval"],
        "source": "BIO Clinical Development Success Rates 2006-2015",
    }


def format_success_rate(rate: float) -> str:
    """Format success rate as percentage string.

    Args:
        rate: Success rate as float (0-1)

    Returns:
        Formatted string (e.g., "35%")
    """
    return f"{int(rate * 100)}%"


def format_run_up(run_up: float) -> str:
    """Format run-up estimate as percentage string.

    Args:
        run_up: Run-up as float (0-1)

    Returns:
        Formatted string (e.g., "+28%")
    """
    return f"+{int(run_up * 100)}%"
