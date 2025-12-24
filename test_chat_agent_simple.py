"""
Simple test script for chat agent query parsing (no database required).

Run this to verify the agent's query parsing works correctly.
"""

import re
from datetime import datetime


# Copied parsing logic from CatalystAgent for testing
THERAPEUTIC_AREAS = {
    "oncology": ["oncology", "cancer", "tumor", "carcinoma", "melanoma", "leukemia", "lymphoma"],
    "neurology": ["neurology", "neurological", "alzheimer", "parkinson", "multiple sclerosis", "ms", "epilepsy"],
    "rare disease": ["rare disease", "orphan", "rare disorder"],
    "cardiology": ["cardiology", "cardiovascular", "heart", "cardiac"],
    "immunology": ["immunology", "immune", "autoimmune", "rheumatoid"],
    "infectious disease": ["infectious", "virus", "viral", "bacterial", "covid", "hiv"],
    "metabolic": ["metabolic", "diabetes", "obesity", "nash", "nafld"],
    "respiratory": ["respiratory", "asthma", "copd", "pulmonary"],
    "dermatology": ["dermatology", "skin", "psoriasis", "eczema", "atopic dermatitis"],
}

MARKET_CAP_PATTERNS = [
    (r"under\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
    (r"below\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
    (r"less than\s+\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
    (r"<\s*\$?(\d+\.?\d*)\s*b(illion)?", lambda m: float(m.group(1)) * 1e9),
]

PHASE_PATTERNS = {
    "phase 2": ["phase 2", "phase ii", "p2"],
    "phase 3": ["phase 3", "phase iii", "p3"],
}

TIMEFRAME_PATTERNS = [
    (r"next\s+(\d+)\s+days?", lambda m: int(m.group(1))),
    (r"within\s+(\d+)\s+days?", lambda m: int(m.group(1))),
    (r"(\d+)\s+days?", lambda m: int(m.group(1))),
    (r"q1\s+(\d{4})", lambda m: ("q1", int(m.group(1)))),
    (r"q2\s+(\d{4})", lambda m: ("q2", int(m.group(1)))),
    (r"q3\s+(\d{4})", lambda m: ("q3", int(m.group(1)))),
    (r"q4\s+(\d{4})", lambda m: ("q4", int(m.group(1)))),
]


def parse_query(user_message):
    """Parse query and extract filters."""
    query_lower = user_message.lower()
    filters = {
        "therapeutic_area": None,
        "max_market_cap": None,
        "phase": None,
        "days_ahead": None,
        "quarter": None,
    }

    # Extract therapeutic area
    for area, keywords in THERAPEUTIC_AREAS.items():
        if any(keyword in query_lower for keyword in keywords):
            filters["therapeutic_area"] = area
            break

    # Extract market cap threshold
    for pattern, extractor in MARKET_CAP_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            filters["max_market_cap"] = int(extractor(match))
            break

    # Extract phase
    for phase, keywords in PHASE_PATTERNS.items():
        if any(keyword in query_lower for keyword in keywords):
            filters["phase"] = phase.title()
            break

    # Extract timeframe
    for pattern, extractor in TIMEFRAME_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            result = extractor(match)
            if isinstance(result, tuple):
                filters["quarter"] = result
            else:
                filters["days_ahead"] = result
            break

    return filters


def test_query_parsing():
    """Test various query patterns."""
    test_cases = [
        ("Phase 3 oncology under $2B", {
            "therapeutic_area": "oncology",
            "phase": "Phase 3",
            "max_market_cap": 2000000000,
        }),
        ("trials next 60 days", {
            "days_ahead": 60,
        }),
        ("neurology catalysts", {
            "therapeutic_area": "neurology",
        }),
        ("Phase 2 rare disease under $1B", {
            "therapeutic_area": "rare disease",
            "phase": "Phase 2",
            "max_market_cap": 1000000000,
        }),
        ("infectious disease next 30 days", {
            "therapeutic_area": "infectious disease",
            "days_ahead": 30,
        }),
        ("cardiology under $5B in Q1 2025", {
            "therapeutic_area": "cardiology",
            "max_market_cap": 5000000000,
            "quarter": ("q1", 2025),
        }),
    ]

    print("=" * 80)
    print("CATALYST AGENT QUERY PARSING TEST")
    print("=" * 80)
    print()

    all_passed = True

    for query, expected_filters in test_cases:
        print(f"Query: '{query}'")
        print("-" * 80)

        filters = parse_query(query)

        # Check each expected filter
        passed = True
        for key, expected_value in expected_filters.items():
            actual_value = filters.get(key)
            if actual_value != expected_value:
                print(f"  ❌ FAILED: {key}")
                print(f"     Expected: {expected_value}")
                print(f"     Got: {actual_value}")
                passed = False
                all_passed = False
            else:
                print(f"  ✅ {key}: {actual_value}")

        # Show filters that should be None
        for key in filters:
            if key not in expected_filters and filters[key] is not None:
                print(f"  ⚠️  Unexpected: {key} = {filters[key]}")

        if passed:
            print(f"  🎉 PASSED")

        print()

    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)


if __name__ == "__main__":
    test_query_parsing()
