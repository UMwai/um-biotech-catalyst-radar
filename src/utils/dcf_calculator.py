"""DCF First-Principles Valuation Model.

Per spec Phase 3 Section 2.6:
- Generate detailed valuations with full assumption transparency
- Free tier: back-of-envelope based on analyst estimates
- Paid tier: first-principles with epidemiology data
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Phase success probabilities by phase
PHASE_SUCCESS_PROBABILITIES = {
    "Phase1": 0.15,
    "Phase2": 0.30,
    "Phase3": 0.60,
    "NDA": 0.85,
    "Approved": 1.00,
}

# Default discount rate
DEFAULT_DISCOUNT_RATE = 0.10

# Years to peak sales
YEARS_TO_PEAK = 5


class DCFCalculator:
    """First-principles drug DCF valuation."""

    def __init__(self, db=None, epidemiology=None):
        """Initialize DCF calculator.

        Args:
            db: SQLiteDB instance
            epidemiology: Epidemiology data fetcher
        """
        self.db = db
        self.epidemiology = epidemiology
        self._init_db()

    def _init_db(self):
        """Lazy load database."""
        if self.db is None:
            try:
                from utils.sqlite_db import get_db
                self.db = get_db()
            except Exception as e:
                logger.warning(f"Could not initialize database: {e}")
                self.db = None

    def calculate_dcf(
        self,
        ticker: str,
        indication: str,
        tier: str = "free",
    ) -> Dict[str, Any]:
        """Generate DCF valuation.

        Args:
            ticker: Company ticker
            indication: Therapeutic indication
            tier: Pricing tier (free/paid)

        Returns:
            Valuation dict with assumptions exposed
        """
        if tier == "free":
            return self._back_of_envelope(ticker, indication)
        else:
            return self._first_principles(ticker, indication)

    def _back_of_envelope(self, ticker: str, indication: str) -> Dict[str, Any]:
        """Simple DCF for free tier based on analyst estimates.

        Uses analyst peak sales estimates from 10-K disclosures or
        comparable drugs to estimate NPV.
        """
        # Get analyst estimates (placeholder - would come from SEC filings)
        peak_sales = self._get_analyst_estimates(ticker, indication)

        # Get current phase
        phase = self._get_current_phase(ticker, indication)

        # Apply success probability
        prob = PHASE_SUCCESS_PROBABILITIES.get(phase, 0.30)

        # Discount to present value
        npv = peak_sales * prob / ((1 + DEFAULT_DISCOUNT_RATE) ** YEARS_TO_PEAK)

        return {
            "tier": "free",
            "method": "back_of_envelope",
            "ticker": ticker,
            "indication": indication,
            "peak_sales_estimate_usd": peak_sales,
            "current_phase": phase,
            "probability_of_success": prob,
            "discount_rate": DEFAULT_DISCOUNT_RATE,
            "years_to_peak": YEARS_TO_PEAK,
            "npv_usd": npv,
            "summary": (
                f"Est. peak sales: ${peak_sales/1e9:.1f}B (analyst consensus). "
                f"At {prob:.0%} PoS for {phase}, risk-adjusted NPV: ${npv/1e9:.2f}B"
            ),
            "assumptions_exposed": True,
            "editable_assumptions": [
                "peak_sales_estimate_usd",
                "probability_of_success",
                "discount_rate",
            ],
        }

    def _first_principles(self, ticker: str, indication: str) -> Dict[str, Any]:
        """Full DCF with epidemiology for paid tier.

        Builds valuation from patient population up.
        """
        # 1. Get patient population from epidemiology sources
        patient_pop = self._get_patient_population(indication)

        # 2. Build patient funnel
        funnel = {
            "total_patients": patient_pop,
            "diagnosed_rate": 0.70,
            "treated_rate": 0.50,
            "eligible_rate": 0.80,
            "market_share": 0.15,
        }

        # 3. Calculate addressable patients
        addressable = (
            patient_pop
            * funnel["diagnosed_rate"]
            * funnel["treated_rate"]
            * funnel["eligible_rate"]
            * funnel["market_share"]
        )

        # 4. Price assumption
        annual_price = self._estimate_price(indication)

        # 5. Peak sales
        peak_sales = addressable * annual_price

        # 6. Get phase and probability
        phase = self._get_current_phase(ticker, indication)
        phase_prob = PHASE_SUCCESS_PROBABILITIES.get(phase, 0.30)

        # 7. NPV calculation
        base_npv = self._calculate_npv(peak_sales, phase_prob, DEFAULT_DISCOUNT_RATE)

        # 8. Sensitivity analysis
        sensitivity = {
            "bear_case": {
                "market_share": 0.10,
                "price_discount": 0.8,
                "npv_usd": base_npv * 0.6,
            },
            "base_case": {
                "market_share": 0.15,
                "price_discount": 1.0,
                "npv_usd": base_npv,
            },
            "bull_case": {
                "market_share": 0.25,
                "price_discount": 1.2,
                "npv_usd": base_npv * 1.5,
            },
            "key_drivers": ["market_share", "annual_price", "probability_of_success"],
        }

        return {
            "tier": "paid",
            "method": "first_principles",
            "ticker": ticker,
            "indication": indication,

            # Epidemiology
            "patient_population": patient_pop,
            "patient_funnel": funnel,
            "addressable_patients": addressable,

            # Economics
            "annual_price_usd": annual_price,
            "peak_sales_usd": peak_sales,

            # Risk adjustment
            "current_phase": phase,
            "probability_of_success": phase_prob,
            "discount_rate": DEFAULT_DISCOUNT_RATE,
            "years_to_peak": YEARS_TO_PEAK,

            # Result
            "npv_usd": base_npv,

            # Sensitivity
            "sensitivity": sensitivity,

            # Transparency
            "assumptions_exposed": True,
            "editable_assumptions": [
                "diagnosed_rate",
                "treated_rate",
                "eligible_rate",
                "market_share",
                "annual_price_usd",
                "probability_of_success",
                "discount_rate",
            ],

            "summary": (
                f"From {patient_pop:,.0f} patients, {addressable:,.0f} addressable. "
                f"At ${annual_price:,.0f}/yr, peak sales ${peak_sales/1e9:.1f}B. "
                f"Risk-adjusted NPV: ${base_npv/1e9:.2f}B ({phase}, {phase_prob:.0%} PoS)"
            ),
        }

    def _get_analyst_estimates(
        self,
        ticker: str,
        indication: str,
    ) -> float:
        """Get analyst peak sales estimates.

        In production, would parse from SEC filings or analyst reports.
        For MVP, uses indication-based heuristics.
        """
        # Indication-based peak sales estimates (USD)
        INDICATION_PEAK_SALES = {
            "oncology": 3e9,
            "cancer": 3e9,
            "neurology": 2e9,
            "alzheimer": 5e9,
            "obesity": 8e9,
            "diabetes": 4e9,
            "rare_disease": 0.5e9,
            "immunology": 2.5e9,
            "default": 1.5e9,
        }

        indication_lower = indication.lower()
        for key, value in INDICATION_PEAK_SALES.items():
            if key in indication_lower:
                return value

        return INDICATION_PEAK_SALES["default"]

    def _get_current_phase(self, ticker: str, indication: str) -> str:
        """Get current development phase for ticker/indication.

        Args:
            ticker: Company ticker
            indication: Therapeutic indication

        Returns:
            Phase string (e.g., "Phase3")
        """
        if self.db is None:
            return "Phase2"  # Default assumption

        try:
            # Check clinical trials
            trials = self.db.get_upcoming_trials(days_ahead=365)
            for trial in trials:
                if trial.get("sponsor_ticker") == ticker:
                    # Check if indication matches
                    conditions = trial.get("conditions", [])
                    if isinstance(conditions, str):
                        import json
                        conditions = json.loads(conditions)

                    indication_lower = indication.lower()
                    for cond in conditions:
                        if indication_lower in cond.lower():
                            phase = trial.get("phase", "Phase2")
                            # Normalize phase format
                            if "3" in phase:
                                return "Phase3"
                            elif "2" in phase:
                                return "Phase2"
                            elif "1" in phase:
                                return "Phase1"

            # Check FDA events for NDA status
            fda_events = self.db.get_upcoming_fda_events(days_ahead=365)
            for event in fda_events:
                if event.get("ticker") == ticker:
                    if event.get("event_type") in ["PDUFA", "NDA"]:
                        return "NDA"

        except Exception as e:
            logger.error(f"Error getting phase: {e}")

        return "Phase2"  # Default

    def _get_patient_population(self, indication: str) -> float:
        """Get patient population for indication.

        In production, would fetch from epidemiology APIs.
        For MVP, uses US prevalence estimates.
        """
        # US prevalence estimates
        US_PREVALENCE = {
            "oncology": 2_000_000,
            "cancer": 2_000_000,
            "breast cancer": 280_000,
            "lung cancer": 230_000,
            "alzheimer": 6_700_000,
            "parkinson": 1_000_000,
            "obesity": 42_000_000,
            "diabetes": 34_000_000,
            "type 2 diabetes": 30_000_000,
            "rheumatoid arthritis": 1_500_000,
            "multiple sclerosis": 1_000_000,
            "depression": 21_000_000,
            "rare_disease": 30_000,  # Typical rare disease
            "default": 500_000,
        }

        indication_lower = indication.lower()
        for key, value in US_PREVALENCE.items():
            if key in indication_lower:
                return value

        return US_PREVALENCE["default"]

    def _estimate_price(self, indication: str) -> float:
        """Estimate annual drug price by indication.

        Args:
            indication: Therapeutic indication

        Returns:
            Estimated annual price in USD
        """
        # Annual price benchmarks by indication
        ANNUAL_PRICES = {
            "oncology": 150_000,
            "cancer": 150_000,
            "rare_disease": 300_000,
            "neurology": 80_000,
            "alzheimer": 28_000,  # Based on Leqembi
            "obesity": 15_000,  # GLP-1 class
            "diabetes": 12_000,
            "immunology": 50_000,
            "default": 50_000,
        }

        indication_lower = indication.lower()
        for key, value in ANNUAL_PRICES.items():
            if key in indication_lower:
                return value

        return ANNUAL_PRICES["default"]

    def _calculate_npv(
        self,
        peak_sales: float,
        probability: float,
        discount_rate: float,
    ) -> float:
        """Calculate risk-adjusted NPV.

        Assumes simplified cash flow profile:
        - Peak sales reached in YEARS_TO_PEAK
        - 10-year revenue window
        - 70% gross margin

        Args:
            peak_sales: Peak annual sales
            probability: Probability of success
            discount_rate: Discount rate

        Returns:
            Risk-adjusted NPV
        """
        gross_margin = 0.70
        revenue_years = 10

        # Simplified: assume ramp to peak then flat
        total_revenues = peak_sales * revenue_years * 0.8  # Simplified average

        # Apply margin and probability
        risk_adjusted = total_revenues * gross_margin * probability

        # Discount to present
        npv = risk_adjusted / ((1 + discount_rate) ** YEARS_TO_PEAK)

        return npv

    def recalculate_with_assumptions(
        self,
        ticker: str,
        indication: str,
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recalculate DCF with user-provided assumption overrides.

        Args:
            ticker: Company ticker
            indication: Therapeutic indication
            overrides: Dict of assumption overrides

        Returns:
            Updated valuation
        """
        # Start with first-principles calculation
        result = self._first_principles(ticker, indication)

        # Apply overrides
        funnel = result["patient_funnel"]

        if "diagnosed_rate" in overrides:
            funnel["diagnosed_rate"] = overrides["diagnosed_rate"]
        if "treated_rate" in overrides:
            funnel["treated_rate"] = overrides["treated_rate"]
        if "eligible_rate" in overrides:
            funnel["eligible_rate"] = overrides["eligible_rate"]
        if "market_share" in overrides:
            funnel["market_share"] = overrides["market_share"]

        if "annual_price_usd" in overrides:
            result["annual_price_usd"] = overrides["annual_price_usd"]
        if "probability_of_success" in overrides:
            result["probability_of_success"] = overrides["probability_of_success"]
        if "discount_rate" in overrides:
            result["discount_rate"] = overrides["discount_rate"]

        # Recalculate
        addressable = (
            result["patient_population"]
            * funnel["diagnosed_rate"]
            * funnel["treated_rate"]
            * funnel["eligible_rate"]
            * funnel["market_share"]
        )

        peak_sales = addressable * result["annual_price_usd"]

        npv = self._calculate_npv(
            peak_sales,
            result["probability_of_success"],
            result["discount_rate"],
        )

        result["addressable_patients"] = addressable
        result["peak_sales_usd"] = peak_sales
        result["npv_usd"] = npv
        result["patient_funnel"] = funnel
        result["user_overrides"] = overrides

        result["summary"] = (
            f"From {result['patient_population']:,.0f} patients, {addressable:,.0f} addressable. "
            f"At ${result['annual_price_usd']:,.0f}/yr, peak sales ${peak_sales/1e9:.1f}B. "
            f"Risk-adjusted NPV: ${npv/1e9:.2f}B"
        )

        return result


# Singleton instance
_calculator_instance: Optional[DCFCalculator] = None


def get_dcf_calculator() -> DCFCalculator:
    """Get singleton calculator instance."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = DCFCalculator()
    return _calculator_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test DCF calculation
    calc = get_dcf_calculator()

    # Free tier
    free_result = calc.calculate_dcf("ACAD", "Rett Syndrome", tier="free")
    print("Free Tier DCF:")
    print(f"  Summary: {free_result['summary']}")
    print(f"  NPV: ${free_result['npv_usd']/1e9:.2f}B")
    print()

    # Paid tier
    paid_result = calc.calculate_dcf("ACAD", "Rett Syndrome", tier="paid")
    print("Paid Tier DCF:")
    print(f"  Summary: {paid_result['summary']}")
    print(f"  NPV: ${paid_result['npv_usd']/1e9:.2f}B")
    print(f"  Patient Population: {paid_result['patient_population']:,.0f}")
    print(f"  Addressable: {paid_result['addressable_patients']:,.0f}")
