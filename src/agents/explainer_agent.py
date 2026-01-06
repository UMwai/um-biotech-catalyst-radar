"""Rule-based explainer agent for clinical trial catalysts.

This agent provides plain English explanations about trial implications
without requiring LLM API calls. Phase 1 uses pre-written templates and
data-driven responses based on historical statistics.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from utils.historical_data import (
    classify_therapeutic_area,
    format_run_up,
    format_success_rate,
    get_optimal_entry_window,
    get_run_up_estimate,
    get_success_rate,
    get_therapeutic_area_stats,
)


class ExplainerAgent:
    """Rule-based agent that explains trial implications in plain English."""

    # Disclaimer text for all explanations
    DISCLAIMER = "\n\n**Disclaimer:** This is educational information only, not financial advice. Always do your own research and consult a licensed financial advisor before making investment decisions."

    def explain_trial(self, catalyst: Dict[str, Any], question_type: str) -> str:
        """Generate explanation for a specific question about the catalyst.

        Args:
            catalyst: Dictionary containing trial data with keys:
                - ticker: Stock ticker symbol
                - phase: Trial phase ("Phase 2" or "Phase 3")
                - condition: Medical condition/indication
                - completion_date: Expected completion date
                - market_cap: Market capitalization
                - enrollment: Number of patients (optional)
                - sponsor: Company name
            question_type: Type of question being asked

        Returns:
            Plain English explanation (2-3 paragraphs)
        """
        handlers = {
            "what_does_trial_test": self._explain_trial_purpose,
            "why_completion_important": self._explain_catalyst_timing,
            "historical_success_rate": self._explain_success_rates,
            "market_cap_impact": self._explain_market_cap_impact,
            "enrollment_significance": self._explain_enrollment,
            "catalyst_timeline": self._explain_entry_timing,
        }

        handler = handlers.get(question_type)
        if not handler:
            return f"Unknown question type: {question_type}{self.DISCLAIMER}"

        explanation = handler(catalyst)
        return f"{explanation}{self.DISCLAIMER}"

    def _explain_trial_purpose(self, catalyst: Dict[str, Any]) -> str:
        """Explain what the trial is testing."""
        phase = catalyst.get("phase", "Unknown")
        condition = catalyst.get("condition", "unknown condition")
        ticker = catalyst.get("ticker", "this company")
        sponsor = catalyst.get("sponsor", ticker)

        if phase == "Phase 2":
            purpose = (
                f"This **{phase}** trial is testing whether {sponsor}'s treatment "
                f"for **{condition}** is safe and effective in a larger group of patients. "
                f"Phase 2 trials typically enroll 100-300 patients to determine optimal dosing, "
                f"identify side effects, and gather preliminary efficacy data."
            )
        elif phase == "Phase 3":
            purpose = (
                f"This **{phase}** trial is the final confirmation study for {sponsor}'s "
                f"treatment for **{condition}**. Phase 3 trials enroll hundreds to thousands "
                f"of patients to definitively prove the treatment works better than current "
                f"standard of care or placebo. Success here typically leads to FDA approval."
            )
        else:
            purpose = (
                f"This trial is testing {sponsor}'s treatment for **{condition}**. "
                f"The trial aims to gather data on safety and efficacy."
            )

        context = (
            f"\n\nFor biotech traders, {phase} data readouts are major catalysts because "
            f"they can validate years of research in a single announcement. Positive results "
            f"often trigger significant price movements as the market reprices the asset's "
            f"probability of eventual FDA approval."
        )

        return purpose + context

    def _explain_catalyst_timing(self, catalyst: Dict[str, Any]) -> str:
        """Explain why completion date matters for price movement."""
        completion_date = catalyst.get("completion_date")
        phase = catalyst.get("phase", "trial")
        ticker = catalyst.get("ticker", "the stock")

        if isinstance(completion_date, str):
            completion_date = datetime.fromisoformat(completion_date).date()
        elif isinstance(completion_date, datetime):
            completion_date = completion_date.date()

        days_until = (completion_date - date.today()).days if completion_date else 0

        timing_context = (
            f"The completion date ({completion_date.strftime('%B %d, %Y')}) marks when "
            f"{phase} trial results are expected to be announced - approximately **{days_until} days** "
            f"from now. This is the single most important date for {ticker} because it's when "
            f"the market will learn whether the drug works or fails."
        )

        pattern_context = (
            "\n\nHistorically, small-cap biotech stocks begin their 'run-up' 60-90 days before "
            "major catalyst dates as anticipation builds. Institutional investors and retail "
            "traders position themselves ahead of the announcement, driving price appreciation. "
            "The stock often peaks 1-2 weeks before the actual data release as late-stage "
            "momentum traders enter."
        )

        risk_note = (
            "\n\n**Critical timing insight:** If results are positive, the stock typically "
            "gaps up 50-200% within hours of the announcement. If results are negative or "
            "mixed, the stock can fall 30-70%. This binary outcome is why completion dates "
            "drive trading strategy."
        )

        return timing_context + pattern_context + risk_note

    def _explain_success_rates(self, catalyst: Dict[str, Any]) -> str:
        """Explain historical success rates for this trial type."""
        phase = catalyst.get("phase", "Unknown")
        condition = catalyst.get("condition", "")

        # Classify therapeutic area
        therapeutic_area = classify_therapeutic_area(condition)
        stats = get_therapeutic_area_stats(therapeutic_area)

        if phase == "Phase 2":
            success_rate = stats["phase_2_success"]
            rate_str = format_success_rate(success_rate)
            advancement = (
                f"Based on historical industry data, **{rate_str}** of {therapeutic_area.replace('_', ' ')} "
                f"Phase 2 trials successfully advance to Phase 3. This means roughly 1 in "
                f"{int(1 / success_rate)} Phase 2 programs make it to the next stage."
            )
        elif phase == "Phase 3":
            success_rate = stats["phase_3_success"]
            rate_str = format_success_rate(success_rate)
            advancement = (
                f"Based on historical industry data, **{rate_str}** of {therapeutic_area.replace('_', ' ')} "
                f"Phase 3 trials achieve their primary endpoints and lead to FDA approval. "
                f"This is significantly higher than Phase 2 success rates, making Phase 3 "
                f"readouts more predictable but still risky."
            )
        else:
            rate_str = "35%"
            advancement = (
                f"Historical success rates for this trial phase are approximately {rate_str}. "
                f"Success depends on trial design, endpoints, and therapeutic area."
            )

        context = (
            f"\n\n**Why this matters:** The {rate_str} historical success rate provides a baseline "
            f"probability for your risk assessment. However, individual trials can vary significantly "
            f"based on mechanism of action, endpoint selection, patient population, and competitive "
            f"landscape. Strong preclinical data, positive Phase 1 results, or a novel mechanism "
            f"can improve odds beyond historical averages."
        )

        source_note = f"\n\n*Data source: {stats['source']}*"

        return advancement + context + source_note

    def _explain_market_cap_impact(self, catalyst: Dict[str, Any]) -> str:
        """Explain how market cap affects volatility and run-up potential."""
        market_cap = catalyst.get("market_cap", 0)
        ticker = catalyst.get("ticker", "this stock")

        if market_cap < 500_000_000:  # < $500M
            tier = "micro-cap"
            volatility = "extremely high"
            run_up_potential = "100-300%"
            risk_desc = "highest risk but highest reward"
        elif market_cap < 2_000_000_000:  # < $2B
            tier = "small-cap"
            volatility = "high"
            run_up_potential = "30-100%"
            risk_desc = "high risk, high reward"
        else:  # $2-5B
            tier = "mid-cap"
            volatility = "moderate"
            run_up_potential = "15-40%"
            risk_desc = "moderate risk, moderate reward"

        market_cap_str = f"${market_cap / 1e9:.2f}B" if market_cap > 0 else "unknown"

        size_context = (
            f"With a market cap of **{market_cap_str}**, {ticker} is classified as a "
            f"**{tier}** biotech. This size category typically experiences **{volatility} volatility** "
            f"around catalyst events, with pre-announcement run-ups in the **{run_up_potential}** range "
            f"for promising trials."
        )

        mechanics = (
            "\n\n**Why size matters:** Smaller companies are more volatile because:\n"
            "1. Their entire valuation may depend on a single drug candidate\n"
            "2. Lower float means less liquidity and bigger price swings\n"
            "3. Institutional ownership is lower, giving retail traders more influence\n"
            "4. Options activity can create gamma squeezes near catalyst dates"
        )

        strategy = (
            f"\n\nFor {tier} biotechs, expect **{risk_desc}** dynamics. Position sizing "
            f"should account for the possibility of 50%+ single-day moves in either direction. "
            f"Many traders use smaller positions with wider stop-losses, or use options strategies "
            f"to define maximum risk."
        )

        return size_context + mechanics + strategy

    def _explain_enrollment(self, catalyst: Dict[str, Any]) -> str:
        """Explain what enrollment size means for trial quality."""
        enrollment = catalyst.get("enrollment")
        phase = catalyst.get("phase", "trial")
        catalyst.get("condition", "the condition")

        if not enrollment or enrollment == 0:
            return (
                f"Enrollment data is not available for this {phase}. Typical {phase} trials "
                f"enroll between 100-1000+ patients depending on the indication and statistical "
                f"requirements. Larger trials generally provide more definitive results but take "
                f"longer to complete and cost more to run."
            )

        # Determine if enrollment is typical for phase
        if phase == "Phase 2":
            typical_range = "100-300"
            if enrollment < 50:
                size_assessment = "smaller than typical"
                implications = "may be a proof-of-concept study with limited statistical power"
            elif enrollment < 100:
                size_assessment = "on the smaller end"
                implications = "suggests early efficacy exploration"
            elif enrollment <= 300:
                size_assessment = "typical size"
                implications = "provides adequate statistical power for dose-ranging"
            else:
                size_assessment = "larger than typical"
                implications = "may be a pivotal Phase 2 study designed for potential approval"
        else:  # Phase 3
            typical_range = "300-3000+"
            if enrollment < 200:
                size_assessment = "smaller than typical"
                implications = "may target a rare disease or have a very strong effect size"
            elif enrollment < 500:
                size_assessment = "on the smaller end"
                implications = "suggests either rare disease or well-powered endpoint"
            elif enrollment <= 1000:
                size_assessment = "typical size"
                implications = "standard pivotal trial sizing"
            else:
                size_assessment = "larger than typical"
                implications = "indicates complex endpoint or cardiovascular/oncology trial"

        enrollment_context = (
            f"This trial enrolled **{enrollment} patients**, which is **{size_assessment}** "
            f"for {phase} studies (typical range: {typical_range}). This {implications}."
        )

        quality_note = (
            "\n\n**Quality implications:** Larger enrollment generally means:\n"
            "1. Higher statistical confidence in results (less likely to be false positive/negative)\n"
            "2. Better ability to detect smaller treatment effects\n"
            "3. More comprehensive safety database\n"
            "4. Longer trial duration and higher costs\n\n"
            "However, enrollment size alone doesn't determine success - trial design, endpoint "
            "selection, and patient population matter just as much."
        )

        return enrollment_context + quality_note

    def _explain_entry_timing(self, catalyst: Dict[str, Any]) -> str:
        """Explain optimal entry timing based on run-up patterns."""
        completion_date = catalyst.get("completion_date")
        market_cap = catalyst.get("market_cap", 1_000_000_000)
        ticker = catalyst.get("ticker", "this stock")

        if isinstance(completion_date, str):
            completion_date = datetime.fromisoformat(completion_date).date()
        elif isinstance(completion_date, datetime):
            completion_date = completion_date.date()

        if not completion_date:
            return (
                "Optimal entry timing cannot be calculated without a completion date. "
                "Generally, small-cap biotech run-ups begin 60-90 days before catalyst dates."
            )

        days_until = (completion_date - date.today()).days
        entry_window = get_optimal_entry_window(completion_date, market_cap)
        run_up_estimate = get_run_up_estimate(market_cap, days_until)

        timing_reco = (
            f"Based on historical run-up patterns, the **optimal entry window** for {ticker} "
            f"is approximately **{entry_window['optimal_days_before']} days before** the "
            f"catalyst date, which would be around **{entry_window['optimal_entry_date'].strftime('%B %d, %Y')}**."
        )

        pattern_details = (
            f"\n\n**Historical pattern analysis:**\n"
            f"- Expected run-up from optimal entry: **{format_run_up(entry_window['expected_run_up'])}**\n"
            f"- Risk level: **{entry_window['risk_level']}**\n"
            f"- Current days until catalyst: **{days_until} days**\n"
            f"- Estimated remaining run-up potential: **{format_run_up(run_up_estimate)}**\n\n"
            f"*Rationale:* {entry_window['rationale']}"
        )

        strategy_note = (
            f"\n\n**Trading strategy considerations:**\n"
            f"1. **If entering now ({days_until} days out):** You're "
            f"{'early - expect choppy price action' if days_until > 90 else 'in the sweet spot' if days_until > 30 else 'late - most run-up may have occurred'}\n"
            f"2. **Stop-loss:** Consider 15-25% below entry for risk management\n"
            f"3. **Position sizing:** Use 2-5% of portfolio max for binary catalyst plays\n"
            f"4. **Exit strategy:** Many traders take profits 1-2 weeks before announcement to avoid binary event risk"
        )

        return timing_reco + pattern_details + strategy_note

    def get_historical_context(self, therapeutic_area: str, phase: str) -> Dict[str, Any]:
        """Fetch historical success rates for therapeutic area and phase.

        Args:
            therapeutic_area: Therapeutic area name
            phase: Trial phase ("Phase 2" or "Phase 3")

        Returns:
            Dictionary with historical statistics
        """
        stats = get_therapeutic_area_stats(therapeutic_area)
        success_rate = get_success_rate(therapeutic_area, phase)

        return {
            "therapeutic_area": therapeutic_area,
            "phase": phase,
            "success_rate": success_rate,
            "success_rate_formatted": format_success_rate(success_rate),
            "all_stats": stats,
        }

    def calculate_run_up_window(self, completion_date: date, market_cap: float) -> Dict[str, Any]:
        """Analyze optimal entry timing for a catalyst.

        Args:
            completion_date: Expected trial completion date
            market_cap: Market capitalization in dollars

        Returns:
            Dictionary with entry timing recommendations
        """
        return get_optimal_entry_window(completion_date, market_cap)

    def find_similar_catalysts(self, catalyst: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find comparable trials based on phase, therapeutic area, and market cap.

        Note: This is a placeholder for Phase 1. In Phase 2, this will query
        a historical catalyst database.

        Args:
            catalyst: Current catalyst data

        Returns:
            List of similar historical catalysts (empty for Phase 1)
        """
        # Phase 1: Return empty list with explanation
        # Phase 2: Will query Supabase for historical catalysts
        return []

    def get_available_questions(self) -> List[Dict[str, str]]:
        """Get list of available question types.

        Returns:
            List of dictionaries with question metadata
        """
        return [
            {
                "type": "what_does_trial_test",
                "label": "What does this trial test?",
                "icon": "💡",
                "category": "basics",
            },
            {
                "type": "why_completion_important",
                "label": "Why is the completion date important?",
                "icon": "📊",
                "category": "timing",
            },
            {
                "type": "historical_success_rate",
                "label": "What's the historical success rate?",
                "icon": "📈",
                "category": "statistics",
            },
            {
                "type": "market_cap_impact",
                "label": "How does market cap affect run-up?",
                "icon": "💰",
                "category": "risk",
            },
            {
                "type": "enrollment_significance",
                "label": "What does enrollment size mean?",
                "icon": "👥",
                "category": "quality",
            },
            {
                "type": "catalyst_timeline",
                "label": "When should I enter this trade?",
                "icon": "⏰",
                "category": "strategy",
            },
        ]
