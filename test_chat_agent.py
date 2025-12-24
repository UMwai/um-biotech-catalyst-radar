"""
Test script for the chat agent functionality.

Run this to verify the agent's query parsing works correctly.
"""

import sys
sys.path.insert(0, 'src')

from agents import CatalystAgent


def test_query_parsing():
    """Test various query patterns."""
    agent = CatalystAgent()

    test_queries = [
        "Phase 3 oncology under $2B",
        "trials next 60 days",
        "neurology catalysts",
        "Phase 2 rare disease under $1B",
        "infectious disease next 30 days",
        "cardiology under $5B in Q1 2025",
    ]

    print("=" * 80)
    print("CATALYST AGENT QUERY PARSING TEST")
    print("=" * 80)
    print()

    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 80)

        filters = agent.parse_query(query)

        print(f"  Therapeutic Area: {filters.get('therapeutic_area') or 'None'}")
        print(f"  Phase: {filters.get('phase') or 'None'}")

        if filters.get('max_market_cap'):
            cap_b = filters['max_market_cap'] / 1e9
            print(f"  Max Market Cap: ${cap_b:.1f}B")
        else:
            print(f"  Max Market Cap: None")

        if filters.get('days_ahead'):
            print(f"  Days Ahead: {filters['days_ahead']}")
        else:
            print(f"  Days Ahead: None")

        if filters.get('quarter'):
            q, year = filters['quarter']
            print(f"  Quarter: {q.upper()} {year}")
        else:
            print(f"  Quarter: None")

        print()

    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_query_parsing()
