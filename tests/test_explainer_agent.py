"""Tests for ExplainerAgent rule-based explanations."""

from datetime import date, datetime, timedelta
import pytest

from src.agents.explainer_agent import ExplainerAgent
from src.utils.historical_data import (
    classify_therapeutic_area,
    get_success_rate,
    get_run_up_estimate,
)


class TestExplainerAgent:
    """Test ExplainerAgent class."""

    @pytest.fixture
    def agent(self):
        """Create an ExplainerAgent instance."""
        return ExplainerAgent()

    @pytest.fixture
    def sample_catalyst(self):
        """Create sample catalyst data for testing."""
        return {
            "ticker": "TEST",
            "sponsor": "Test Pharma Inc",
            "phase": "Phase 3",
            "condition": "Advanced Non-Small Cell Lung Cancer",
            "completion_date": date.today() + timedelta(days=60),
            "market_cap": 1_500_000_000,  # $1.5B
            "enrollment": 450,
            "nct_id": "NCT12345678",
            "status": "RECRUITING",
            "sponsor_class": "INDUSTRY",
            "title": "A Phase 3 Study of Drug X in Advanced NSCLC",
            "current_price": 12.50,
        }

    def test_explain_trial_what_does_trial_test(self, agent, sample_catalyst):
        """Test explanation for 'what does trial test' question."""
        explanation = agent.explain_trial(sample_catalyst, "what_does_trial_test")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "Phase 3" in explanation
        assert "cancer" in explanation.lower()
        assert "Disclaimer" in explanation

    def test_explain_trial_why_completion_important(self, agent, sample_catalyst):
        """Test explanation for 'why completion important' question."""
        explanation = agent.explain_trial(sample_catalyst, "why_completion_important")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "60 days" in explanation
        assert "run-up" in explanation.lower()
        assert "Disclaimer" in explanation

    def test_explain_trial_historical_success_rate(self, agent, sample_catalyst):
        """Test explanation for 'historical success rate' question."""
        explanation = agent.explain_trial(sample_catalyst, "historical_success_rate")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "%" in explanation  # Should contain percentage
        assert "oncology" in explanation.lower()  # Should classify as oncology
        assert "Data source" in explanation

    def test_explain_trial_market_cap_impact(self, agent, sample_catalyst):
        """Test explanation for 'market cap impact' question."""
        explanation = agent.explain_trial(sample_catalyst, "market_cap_impact")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "$1.5" in explanation or "$1.50" in explanation  # Market cap
        assert "small-cap" in explanation.lower()
        assert "volatility" in explanation.lower()

    def test_explain_trial_enrollment_significance(self, agent, sample_catalyst):
        """Test explanation for 'enrollment significance' question."""
        explanation = agent.explain_trial(sample_catalyst, "enrollment_significance")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "450" in explanation  # Enrollment number
        assert "patient" in explanation.lower()

    def test_explain_trial_catalyst_timeline(self, agent, sample_catalyst):
        """Test explanation for 'catalyst timeline' question."""
        explanation = agent.explain_trial(sample_catalyst, "catalyst_timeline")

        assert isinstance(explanation, str)
        assert len(explanation) > 50
        assert "days" in explanation.lower()
        assert "entry" in explanation.lower()

    def test_explain_trial_unknown_question_type(self, agent, sample_catalyst):
        """Test handling of unknown question type."""
        explanation = agent.explain_trial(sample_catalyst, "invalid_question")

        assert "Unknown question type" in explanation
        assert "Disclaimer" in explanation

    def test_explain_trial_missing_data(self, agent):
        """Test explanation generation with missing catalyst data."""
        minimal_catalyst = {
            "ticker": "TEST",
            "phase": "Phase 2",
            "condition": "Unknown",
        }

        explanation = agent.explain_trial(minimal_catalyst, "what_does_trial_test")

        # Should still generate explanation without crashing
        assert isinstance(explanation, str)
        assert len(explanation) > 0

    def test_explain_trial_phase_2(self, agent, sample_catalyst):
        """Test explanation for Phase 2 trial."""
        sample_catalyst["phase"] = "Phase 2"

        explanation = agent.explain_trial(sample_catalyst, "what_does_trial_test")

        assert "Phase 2" in explanation
        assert "100-300 patients" in explanation

    def test_get_historical_context(self, agent):
        """Test getting historical context for therapeutic area."""
        context = agent.get_historical_context("oncology", "Phase 3")

        assert context["therapeutic_area"] == "oncology"
        assert context["phase"] == "Phase 3"
        assert isinstance(context["success_rate"], float)
        assert 0 <= context["success_rate"] <= 1
        assert "%" in context["success_rate_formatted"]

    def test_calculate_run_up_window(self, agent):
        """Test run-up window calculation."""
        completion_date = date.today() + timedelta(days=90)
        market_cap = 1_000_000_000

        window = agent.calculate_run_up_window(completion_date, market_cap)

        assert "optimal_entry_date" in window
        assert "optimal_days_before" in window
        assert "expected_run_up" in window
        assert "risk_level" in window
        assert "rationale" in window

        assert isinstance(window["optimal_entry_date"], date)
        assert isinstance(window["optimal_days_before"], int)
        assert isinstance(window["expected_run_up"], float)

    def test_find_similar_catalysts(self, agent, sample_catalyst):
        """Test finding similar catalysts (Phase 1 returns empty)."""
        similar = agent.find_similar_catalysts(sample_catalyst)

        # Phase 1: Should return empty list
        assert isinstance(similar, list)
        assert len(similar) == 0

    def test_get_available_questions(self, agent):
        """Test getting available questions."""
        questions = agent.get_available_questions()

        assert isinstance(questions, list)
        assert len(questions) == 6  # Should have 6 question types

        for question in questions:
            assert "type" in question
            assert "label" in question
            assert "icon" in question
            assert "category" in question

    def test_disclaimer_in_all_explanations(self, agent, sample_catalyst):
        """Test that disclaimer appears in all explanations."""
        question_types = [
            "what_does_trial_test",
            "why_completion_important",
            "historical_success_rate",
            "market_cap_impact",
            "enrollment_significance",
            "catalyst_timeline",
        ]

        for q_type in question_types:
            explanation = agent.explain_trial(sample_catalyst, q_type)
            assert "Disclaimer" in explanation
            assert "not financial advice" in explanation


class TestHistoricalData:
    """Test historical data helper functions."""

    def test_classify_therapeutic_area_oncology(self):
        """Test oncology classification."""
        condition = "Advanced Non-Small Cell Lung Cancer"
        area = classify_therapeutic_area(condition)
        assert area == "oncology"

    def test_classify_therapeutic_area_rare_disease(self):
        """Test rare disease classification."""
        condition = "Rare Genetic Disorder"
        area = classify_therapeutic_area(condition)
        assert area == "rare_disease"

    def test_classify_therapeutic_area_neurology(self):
        """Test neurology classification."""
        condition = "Alzheimer's Disease"
        area = classify_therapeutic_area(condition)
        assert area == "neurology"

    def test_classify_therapeutic_area_default(self):
        """Test default classification for unknown condition."""
        condition = "Some Unknown Disease"
        area = classify_therapeutic_area(condition)
        assert area == "default"

    def test_classify_therapeutic_area_empty(self):
        """Test classification with empty string."""
        area = classify_therapeutic_area("")
        assert area == "default"

    def test_get_success_rate_phase_2(self):
        """Test getting Phase 2 success rate."""
        rate = get_success_rate("oncology", "Phase 2")
        assert isinstance(rate, float)
        assert 0 <= rate <= 1
        assert rate == 0.30  # Oncology Phase 2→3 rate

    def test_get_success_rate_phase_3(self):
        """Test getting Phase 3 success rate."""
        rate = get_success_rate("oncology", "Phase 3")
        assert isinstance(rate, float)
        assert 0 <= rate <= 1
        assert rate == 0.50  # Oncology Phase 3→approval rate

    def test_get_success_rate_default_area(self):
        """Test getting success rate for unknown therapeutic area."""
        rate = get_success_rate("unknown_area", "Phase 2")
        assert isinstance(rate, float)
        assert 0 <= rate <= 1
        assert rate == 0.35  # Default Phase 2→3 rate

    def test_get_run_up_estimate_small_cap_90_days(self):
        """Test run-up estimate for small cap at 90 days."""
        market_cap = 1_000_000_000  # $1B
        days = 90
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        assert run_up == 0.35  # 90-day small cap run-up

    def test_get_run_up_estimate_small_cap_60_days(self):
        """Test run-up estimate for small cap at 60 days."""
        market_cap = 1_500_000_000  # $1.5B
        days = 60
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        assert run_up == 0.28  # 60-day small cap run-up

    def test_get_run_up_estimate_mid_cap(self):
        """Test run-up estimate for mid cap."""
        market_cap = 3_000_000_000  # $3B
        days = 60
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        assert run_up == 0.15  # 60-day mid cap run-up

    def test_get_run_up_estimate_short_timeframe(self):
        """Test run-up estimate for very short timeframe."""
        market_cap = 1_000_000_000  # $1B
        days = 15  # Less than 30 days
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        assert 0 <= run_up <= 0.15  # Should be less than 30-day rate
        # Should be half of 30-day rate (linear interpolation)
        assert abs(run_up - 0.075) < 0.01

    def test_edge_case_zero_days(self):
        """Test edge case with zero days until completion."""
        market_cap = 1_000_000_000
        days = 0
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        assert run_up == 0.0  # No run-up at zero days

    def test_edge_case_negative_days(self):
        """Test edge case with negative days (past date)."""
        market_cap = 1_000_000_000
        days = -10
        run_up = get_run_up_estimate(market_cap, days)

        assert isinstance(run_up, float)
        # Should handle gracefully (likely negative or zero)
        assert run_up <= 0.0


class TestExplanationQuality:
    """Test explanation quality and content."""

    @pytest.fixture
    def agent(self):
        """Create an ExplainerAgent instance."""
        return ExplainerAgent()

    @pytest.fixture
    def oncology_catalyst(self):
        """Create oncology catalyst for testing."""
        return {
            "ticker": "ONCO",
            "phase": "Phase 3",
            "condition": "Metastatic Melanoma",
            "completion_date": date.today() + timedelta(days=45),
            "market_cap": 2_500_000_000,  # $2.5B
            "enrollment": 800,
        }

    def test_explanation_length(self, agent, oncology_catalyst):
        """Test that explanations are appropriate length (2-3 paragraphs)."""
        explanation = agent.explain_trial(oncology_catalyst, "what_does_trial_test")

        # Should be at least 50 words and less than 500 words
        word_count = len(explanation.split())
        assert 50 <= word_count <= 500

    def test_explanation_contains_specific_data(self, agent, oncology_catalyst):
        """Test that explanations reference specific catalyst data."""
        explanation = agent.explain_trial(
            oncology_catalyst, "enrollment_significance"
        )

        # Should mention the actual enrollment number
        assert "800" in explanation

    def test_explanation_no_markdown_errors(self, agent, oncology_catalyst):
        """Test that explanations have valid markdown formatting."""
        explanation = agent.explain_trial(oncology_catalyst, "what_does_trial_test")

        # Check for balanced markdown formatting
        assert explanation.count("**") % 2 == 0  # Bold markers should be paired
        assert explanation.count("*") % 2 == 0  # Italic markers should be paired

    def test_phase_2_vs_phase_3_differences(self, agent):
        """Test that Phase 2 and Phase 3 explanations are different."""
        catalyst_p2 = {
            "ticker": "TEST",
            "phase": "Phase 2",
            "condition": "Cancer",
            "completion_date": date.today() + timedelta(days=60),
            "market_cap": 1_000_000_000,
        }

        catalyst_p3 = catalyst_p2.copy()
        catalyst_p3["phase"] = "Phase 3"

        explanation_p2 = agent.explain_trial(catalyst_p2, "what_does_trial_test")
        explanation_p3 = agent.explain_trial(catalyst_p3, "what_does_trial_test")

        # Explanations should be different for different phases
        assert explanation_p2 != explanation_p3
        assert "Phase 2" in explanation_p2
        assert "Phase 3" in explanation_p3
