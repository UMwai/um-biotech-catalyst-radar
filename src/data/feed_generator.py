"""Proactive Daily Feed Generator.

Generates AI-curated insights for the dashboard based on:
- Days to catalyst
- Cash runway
- Trial quality score
- Catalyst materiality (catalyst value / enterprise value)

Per spec Section 4.1:
- Generates "AI Picks Today" on dashboard load
- Top 3 featured, rest available for paid users
- Each insight includes headline, date, source citation

Algorithm:
    Score = f(days_to_catalyst, cash_runway, trial_quality, materiality)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Insight generation prompt for LLM
INSIGHT_GENERATION_PROMPT = """
You are a biotech analyst generating a concise investment insight.

Company: {ticker} ({company_name})
Catalyst: {catalyst_type} on {catalyst_date} ({days_until} days away)
Indication: {indication}
Drug: {drug_name}
Cash Runway: {cash_runway} months
Trial Design Score: {design_score}/100
Market Cap: ${market_cap}B

Generate a brief, actionable insight (1-2 sentences) highlighting:
1. Why this catalyst matters
2. Key risk/opportunity

Format:
{{
    "headline": "TICKER: One-line summary (max 80 chars)",
    "body": "2-3 sentence explanation with specific data points",
    "conviction_score": <50-100 based on setup quality>,
    "key_factors": ["factor1", "factor2", "factor3"]
}}

JSON Response:
"""


class FeedGenerator:
    """Generate proactive daily feed of AI-curated opportunities."""

    # Scoring weights
    WEIGHTS = {
        "days_to_catalyst": 0.30,  # Closer = higher score
        "cash_runway": 0.20,       # More runway = higher score
        "trial_quality": 0.25,     # Higher design score = higher score
        "materiality": 0.25,       # Higher signal strength = higher score
    }

    def __init__(self, db=None):
        """Initialize feed generator.

        Args:
            db: SQLiteDB instance (optional, will create if not provided)
        """
        self.db = db

    def _get_db(self):
        """Lazy load database connection."""
        if self.db is None:
            from utils.sqlite_db import get_db
            self.db = get_db()
        return self.db

    def calculate_opportunity_score(
        self,
        days_to_catalyst: int,
        cash_runway_months: Optional[float],
        trial_design_score: Optional[float],
        market_cap_usd: Optional[float],
    ) -> float:
        """Calculate composite opportunity score.

        Args:
            days_to_catalyst: Days until catalyst event
            cash_runway_months: Company's cash runway in months
            trial_design_score: Trial design quality (0-100)
            market_cap_usd: Company market cap

        Returns:
            Score from 0-100
        """
        scores = {}

        # Days to catalyst scoring (closer is better, peak around 14-30 days)
        if days_to_catalyst <= 0:
            scores["days"] = 0
        elif days_to_catalyst <= 14:
            scores["days"] = 100  # Imminent catalyst
        elif days_to_catalyst <= 30:
            scores["days"] = 90
        elif days_to_catalyst <= 60:
            scores["days"] = 70
        elif days_to_catalyst <= 90:
            scores["days"] = 50
        else:
            scores["days"] = max(0, 50 - (days_to_catalyst - 90) / 3)

        # Cash runway scoring (want 6-24 months ideally)
        if cash_runway_months is None:
            scores["runway"] = 50  # Unknown, use neutral
        elif cash_runway_months < 6:
            scores["runway"] = 30  # High dilution risk
        elif cash_runway_months < 12:
            scores["runway"] = 60
        elif cash_runway_months < 24:
            scores["runway"] = 90  # Ideal range
        else:
            scores["runway"] = 80  # Plenty of runway

        # Trial design scoring
        if trial_design_score is None:
            scores["trial"] = 50
        else:
            scores["trial"] = trial_design_score

        # Materiality scoring (smaller caps = more binary, more interesting)
        if market_cap_usd is None:
            scores["materiality"] = 50
        else:
            market_cap_b = market_cap_usd / 1e9
            if market_cap_b < 0.5:
                scores["materiality"] = 95  # Micro-cap, very binary
            elif market_cap_b < 1:
                scores["materiality"] = 85
            elif market_cap_b < 2:
                scores["materiality"] = 75
            elif market_cap_b < 5:
                scores["materiality"] = 60
            else:
                scores["materiality"] = 40

        # Weighted composite
        composite = (
            scores["days"] * self.WEIGHTS["days_to_catalyst"]
            + scores["runway"] * self.WEIGHTS["cash_runway"]
            + scores["trial"] * self.WEIGHTS["trial_quality"]
            + scores["materiality"] * self.WEIGHTS["materiality"]
        )

        return round(composite, 1)

    def generate_feed(
        self,
        days_ahead: int = 90,
        limit: int = 10,
        use_llm: bool = False,
    ) -> List[Dict[str, Any]]:
        """Generate daily feed of top opportunities.

        Args:
            days_ahead: How far ahead to look for catalysts
            limit: Number of insights to generate
            use_llm: Whether to use LLM for insight text

        Returns:
            List of insight dicts sorted by conviction score
        """
        db = self._get_db()
        insights = []

        # Get upcoming catalysts from all sources
        catalysts = self._aggregate_catalysts(db, days_ahead)

        if not catalysts:
            logger.warning("No catalysts found for feed generation")
            return []

        # Score and rank
        for catalyst in catalysts:
            days_until = catalyst.get("days_until", 90)
            score = self.calculate_opportunity_score(
                days_to_catalyst=days_until,
                cash_runway_months=catalyst.get("cash_runway_months"),
                trial_design_score=catalyst.get("design_score"),
                market_cap_usd=catalyst.get("market_cap_usd"),
            )

            insight = {
                "ticker": catalyst.get("ticker"),
                "company_name": catalyst.get("company_name"),
                "catalyst_type": catalyst.get("catalyst_type"),
                "catalyst_date": catalyst.get("catalyst_date"),
                "days_until": days_until,
                "indication": catalyst.get("indication"),
                "drug_name": catalyst.get("drug_name"),
                "conviction_score": score,
                "market_cap_usd": catalyst.get("market_cap_usd"),
                "cash_runway_months": catalyst.get("cash_runway_months"),
                "design_score": catalyst.get("design_score"),
                "source": catalyst.get("source"),
                "source_reference": catalyst.get("source_reference"),
            }

            # Generate headline and body
            if use_llm:
                insight.update(self._generate_llm_insight(insight))
            else:
                insight.update(self._generate_rule_based_insight(insight))

            insights.append(insight)

        # Sort by conviction score and return top N
        insights.sort(key=lambda x: x["conviction_score"], reverse=True)

        return insights[:limit]

    def _aggregate_catalysts(
        self, db, days_ahead: int
    ) -> List[Dict[str, Any]]:
        """Aggregate catalysts from all sources."""
        catalysts = []
        today = datetime.now().date()

        # 1. FDA events
        try:
            fda_events = db.get_upcoming_fda_events(days_ahead=days_ahead)
            for event in fda_events:
                event_date = event.get("event_date")
                if event_date:
                    if isinstance(event_date, str):
                        event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                    days_until = (event_date - today).days

                    catalysts.append({
                        "ticker": event.get("ticker"),
                        "company_name": event.get("company_name"),
                        "catalyst_type": event.get("event_type", "FDA"),
                        "catalyst_date": event_date,
                        "days_until": days_until,
                        "indication": event.get("indication"),
                        "drug_name": event.get("drug_name"),
                        "source": "FDA",
                        "source_reference": event.get("source_url"),
                        "market_cap_usd": event.get("market_cap_usd"),
                    })
        except Exception as e:
            logger.error(f"Failed to get FDA events: {e}")

        # 2. Clinical trials
        try:
            trials = db.get_upcoming_trials(days_ahead=days_ahead)
            for trial in trials:
                completion_date = trial.get("primary_completion_date")
                if completion_date:
                    if isinstance(completion_date, str):
                        completion_date = datetime.strptime(completion_date, "%Y-%m-%d").date()
                    days_until = (completion_date - today).days

                    phase = trial.get("phase", "Phase 2")
                    catalysts.append({
                        "ticker": trial.get("ticker") or trial.get("sponsor_ticker"),
                        "company_name": trial.get("company_name") or trial.get("sponsor_name"),
                        "catalyst_type": f"{phase} Readout",
                        "catalyst_date": completion_date,
                        "days_until": days_until,
                        "indication": ", ".join(trial.get("conditions", [])[:2]) if trial.get("conditions") else "",
                        "drug_name": trial.get("title", "")[:50],
                        "source": "ClinicalTrials.gov",
                        "source_reference": f"NCT: {trial.get('nct_id')}",
                        "design_score": trial.get("trial_design_score"),
                        "market_cap_usd": trial.get("market_cap_usd"),
                    })
        except Exception as e:
            logger.error(f"Failed to get clinical trials: {e}")

        # 3. Unified catalysts table (if populated)
        try:
            unified = db.get_all_catalysts(days_ahead=days_ahead)
            for cat in unified:
                catalyst_date = cat.get("catalyst_date")
                if catalyst_date:
                    if isinstance(catalyst_date, str):
                        catalyst_date = datetime.strptime(catalyst_date, "%Y-%m-%d").date()
                    days_until = (catalyst_date - today).days

                    catalysts.append({
                        "ticker": cat.get("ticker"),
                        "company_name": cat.get("company_name"),
                        "catalyst_type": cat.get("catalyst_type"),
                        "catalyst_date": catalyst_date,
                        "days_until": days_until,
                        "indication": cat.get("indication"),
                        "drug_name": cat.get("drug_name"),
                        "source": cat.get("source"),
                        "source_reference": cat.get("source_reference"),
                        "market_cap_usd": cat.get("market_cap_usd"),
                    })
        except Exception as e:
            logger.error(f"Failed to get unified catalysts: {e}")

        # Deduplicate by ticker + date
        seen = set()
        unique = []
        for cat in catalysts:
            key = (cat.get("ticker"), str(cat.get("catalyst_date")))
            if key not in seen and cat.get("ticker"):
                seen.add(key)
                unique.append(cat)

        return unique

    def _generate_rule_based_insight(self, catalyst: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insight headline and body using rules."""
        ticker = catalyst.get("ticker", "N/A")
        days = catalyst.get("days_until", 0)
        catalyst_type = catalyst.get("catalyst_type", "Catalyst")
        indication = catalyst.get("indication", "")
        score = catalyst.get("conviction_score", 50)

        # Generate headline
        if days <= 14:
            headline = f"{ticker}: {catalyst_type} in {days} days - HIGH URGENCY"
        elif days <= 30:
            headline = f"{ticker}: Near-term {catalyst_type} ({days}d)"
        else:
            headline = f"{ticker}: {catalyst_type} in {days} days"

        # Generate body based on score
        if score >= 80:
            body = f"High-conviction setup. {catalyst_type} approaching for {indication}. "
            body += "Strong trial design and adequate cash runway support thesis."
        elif score >= 60:
            body = f"Interesting opportunity. {catalyst_type} expected in {days} days. "
            body += "Monitor for position sizing based on risk tolerance."
        else:
            body = f"{catalyst_type} upcoming. Consider as part of diversified biotech basket. "
            body += "Some risk factors present - review financials."

        # Source citation
        source_ref = catalyst.get("source_reference", catalyst.get("source", "Internal"))

        return {
            "headline": headline[:100],
            "body": body,
            "source_citations": [source_ref],
            "insight_type": "opportunity" if score >= 60 else "update",
        }

    def _generate_llm_insight(self, catalyst: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insight using LLM."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._generate_rule_based_insight(catalyst)

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            market_cap_str = f"{catalyst.get('market_cap_usd', 0) / 1e9:.2f}" if catalyst.get('market_cap_usd') else "Unknown"
            runway_str = str(catalyst.get('cash_runway_months', 'Unknown'))

            prompt = INSIGHT_GENERATION_PROMPT.format(
                ticker=catalyst.get("ticker", "N/A"),
                company_name=catalyst.get("company_name", "Unknown"),
                catalyst_type=catalyst.get("catalyst_type", "Catalyst"),
                catalyst_date=catalyst.get("catalyst_date", "Unknown"),
                days_until=catalyst.get("days_until", 0),
                indication=catalyst.get("indication", "Unspecified"),
                drug_name=catalyst.get("drug_name", "Unknown"),
                cash_runway=runway_str,
                design_score=catalyst.get("design_score", 50),
                market_cap=market_cap_str,
            )

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )

            import re
            response_text = response.content[0].text
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "headline": result.get("headline", catalyst.get("ticker", "")),
                    "body": result.get("body", ""),
                    "conviction_score": result.get("conviction_score", catalyst.get("conviction_score")),
                    "key_factors": result.get("key_factors", []),
                    "insight_type": "opportunity",
                    "source_citations": [catalyst.get("source_reference", "")],
                }

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")

        return self._generate_rule_based_insight(catalyst)

    def save_feed_to_db(self, insights: List[Dict[str, Any]]) -> int:
        """Save generated insights to database.

        Args:
            insights: List of insight dicts from generate_feed()

        Returns:
            Number of insights saved
        """
        db = self._get_db()
        saved = 0

        for insight in insights:
            try:
                ticker = insight.get("ticker")
                if not ticker:
                    continue

                # Get or create company
                company = db.get_company_by_ticker(ticker)
                if not company:
                    company_id = db.upsert_company(
                        ticker,
                        insight.get("company_name", f"{ticker} Inc."),
                        market_cap_usd=insight.get("market_cap_usd"),
                    )
                else:
                    company_id = company["id"]

                # Calculate expiry (after catalyst date)
                catalyst_date = insight.get("catalyst_date")
                expires_at = None
                if catalyst_date:
                    if isinstance(catalyst_date, str):
                        catalyst_date = datetime.strptime(catalyst_date, "%Y-%m-%d")
                    expires_at = catalyst_date + timedelta(days=7)

                # Insert insight
                db.insert_insight(
                    company_id=company_id,
                    insight_type=insight.get("insight_type", "opportunity"),
                    headline=insight.get("headline", ""),
                    body=insight.get("body", ""),
                    conviction_score=insight.get("conviction_score"),
                    factors={
                        "days_until": insight.get("days_until"),
                        "cash_runway": insight.get("cash_runway_months"),
                        "design_score": insight.get("design_score"),
                        "key_factors": insight.get("key_factors", []),
                    },
                    source_citations=insight.get("source_citations", []),
                    generated_by="feed_generator",
                    expires_at=expires_at,
                )
                saved += 1

            except Exception as e:
                logger.error(f"Failed to save insight for {insight.get('ticker')}: {e}")

        logger.info(f"Saved {saved} insights to database")
        return saved


def run_daily_feed_job() -> int:
    """Run the daily feed generation job.

    This is called by GitHub Actions cron at 5 AM ET.

    Returns:
        Number of insights generated
    """
    logger.info("Starting daily feed generation...")

    generator = FeedGenerator()

    # Generate feed (use LLM if API key available)
    use_llm = bool(os.getenv("ANTHROPIC_API_KEY"))
    insights = generator.generate_feed(
        days_ahead=90,
        limit=15,
        use_llm=use_llm,
    )

    # Save to database
    saved = generator.save_feed_to_db(insights)

    logger.info(f"Daily feed complete: {saved} insights generated")
    return saved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test feed generation
    generator = FeedGenerator()

    print("=== Generating Test Feed ===")
    insights = generator.generate_feed(days_ahead=90, limit=5, use_llm=False)

    for i, insight in enumerate(insights, 1):
        print(f"\n--- Insight #{i} (Score: {insight.get('conviction_score')}) ---")
        print(f"Headline: {insight.get('headline')}")
        print(f"Body: {insight.get('body')}")
        print(f"Catalyst: {insight.get('catalyst_type')} in {insight.get('days_until')} days")
        print(f"Source: {insight.get('source_citations')}")
