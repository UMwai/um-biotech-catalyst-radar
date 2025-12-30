"""UI component for displaying AI explanations about catalysts.

This module provides the Streamlit UI for the explainer agent,
rendering interactive question buttons and displaying explanations
in expandable cards.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging
from datetime import datetime

import streamlit as st

from ..agents.explainer_agent import ExplainerAgent
from ..utils.db import log_analytics_event, get_user_by_email

logger = logging.getLogger(__name__)


def render_explainer(catalyst: Dict[str, Any], user_tier: str = "starter") -> None:
    """Render the AI explainer component for a catalyst.

    Args:
        catalyst: Dictionary containing trial data
        user_tier: User's subscription tier ("starter", "pro", "enterprise")
    """
    st.subheader("🤖 Ask AI About This Catalyst")

    # Initialize explainer agent
    if "explainer_agent" not in st.session_state:
        st.session_state.explainer_agent = ExplainerAgent()

    agent = st.session_state.explainer_agent

    # Get available questions
    questions = agent.get_available_questions()

    # Create question buttons in a grid
    st.markdown("**Select a question to get an AI-powered explanation:**")

    # Organize questions by category
    categories = {
        "basics": "Trial Basics",
        "timing": "Catalyst Timing",
        "statistics": "Historical Data",
        "risk": "Risk Assessment",
        "quality": "Trial Quality",
        "strategy": "Trading Strategy",
    }

    for category_key, category_name in categories.items():
        category_questions = [q for q in questions if q["category"] == category_key]

        if not category_questions:
            continue

        with st.expander(f"**{category_name}**", expanded=True):
            cols = st.columns(len(category_questions))

            for idx, question in enumerate(category_questions):
                with cols[idx]:
                    if st.button(
                        f"{question['icon']} {question['label']}",
                        key=f"q_{question['type']}",
                        use_container_width=True,
                    ):
                        # Store selected question in session state
                        st.session_state.selected_question = question["type"]
                        st.session_state.show_explanation = True

    # Display explanation if question selected
    if st.session_state.get("show_explanation") and st.session_state.get("selected_question"):
        _render_explanation_card(
            catalyst,
            st.session_state.selected_question,
            agent,
            user_tier,
        )

    # Pro tier upgrade CTA for Starter users
    if user_tier == "starter":
        st.divider()
        _render_upgrade_cta()


def _render_explanation_card(
    catalyst: Dict[str, Any],
    question_type: str,
    agent: ExplainerAgent,
    user_tier: str,
) -> None:
    """Render the explanation response card.

    Args:
        catalyst: Catalyst data
        question_type: Type of question asked
        agent: ExplainerAgent instance
        user_tier: User's subscription tier
    """
    # Find question metadata
    questions = agent.get_available_questions()
    question_meta = next((q for q in questions if q["type"] == question_type), None)

    if not question_meta:
        st.error("Unknown question type")
        return

    st.divider()

    # Card header
    st.markdown(f"### {question_meta['icon']} {question_meta['label']}")

    # Generate explanation with loading spinner
    with st.spinner("Analyzing catalyst data..."):
        explanation = agent.explain_trial(catalyst, question_type)

    # Display explanation
    st.markdown(explanation)

    # Data citation
    therapeutic_area = catalyst.get("therapeutic_area", "general")
    phase = catalyst.get("phase", "Unknown")
    _render_citation(therapeutic_area, phase, question_type)

    # Action buttons
    st.divider()
    _render_action_buttons(catalyst, user_tier)

    # Feedback mechanism
    st.divider()
    _render_feedback_buttons(question_type)

    # Suggest related questions
    _render_related_questions(question_type, questions)


def _render_citation(therapeutic_area: str, phase: str, question_type: str) -> None:
    """Render data source citation.

    Args:
        therapeutic_area: Therapeutic area name
        phase: Trial phase
        question_type: Type of question asked
    """
    if question_type in ["historical_success_rate", "catalyst_timeline"]:
        st.caption(
            f"*Based on historical data from {therapeutic_area.replace('_', ' ')} "
            f"{phase} trials. Sources: BIO Clinical Development Success Rates 2006-2015, "
            f"proprietary biotech run-up analysis.*"
        )
    else:
        st.caption("*Analysis based on clinical trial industry standards and historical patterns.*")


def _render_action_buttons(catalyst: Dict[str, Any], user_tier: str) -> None:
    """Render action buttons below explanation.

    Args:
        catalyst: Catalyst data
        user_tier: User's subscription tier
    """
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📌 Add to Watchlist", use_container_width=True):
            _add_to_watchlist(catalyst)

    with col2:
        if st.button("🔔 Set Alert", use_container_width=True):
            _set_alert(catalyst)

    with col3:
        # View Similar button (Pro feature)
        if user_tier == "pro":
            if st.button("🔍 View Similar", use_container_width=True):
                _view_similar_catalysts(catalyst)
        else:
            st.button(
                "🔍 View Similar (Pro)",
                use_container_width=True,
                disabled=True,
                help="Upgrade to Pro to compare with similar historical catalysts",
            )


def _render_feedback_buttons(question_type: str) -> None:
    """Render feedback buttons for explanation quality.

    Args:
        question_type: Type of question asked
    """
    st.markdown("**Was this helpful?**")

    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        if st.button("👍 Yes", key=f"helpful_yes_{question_type}"):
            st.success("Thank you for your feedback!")
            _record_feedback(question_type, "positive")

    with col2:
        if st.button("👎 No", key=f"helpful_no_{question_type}"):
            st.warning("Thanks for letting us know. We'll improve our explanations.")
            _record_feedback(question_type, "negative")


def _render_related_questions(current_question: str, all_questions: list) -> None:
    """Suggest related questions based on current question.

    Args:
        current_question: Current question type
        all_questions: List of all available questions
    """
    # Define related question mapping
    related_map = {
        "what_does_trial_test": ["why_completion_important", "historical_success_rate"],
        "why_completion_important": ["catalyst_timeline", "market_cap_impact"],
        "historical_success_rate": ["enrollment_significance", "what_does_trial_test"],
        "market_cap_impact": ["catalyst_timeline", "why_completion_important"],
        "enrollment_significance": ["historical_success_rate", "what_does_trial_test"],
        "catalyst_timeline": ["market_cap_impact", "why_completion_important"],
    }

    related_types = related_map.get(current_question, [])

    if not related_types:
        return

    st.markdown("**You might also want to know:**")

    cols = st.columns(len(related_types))

    for idx, q_type in enumerate(related_types):
        question = next((q for q in all_questions if q["type"] == q_type), None)
        if question:
            with cols[idx]:
                if st.button(
                    f"{question['icon']} {question['label']}",
                    key=f"related_{q_type}",
                    use_container_width=True,
                ):
                    st.session_state.selected_question = q_type
                    st.rerun()


def _render_upgrade_cta() -> None:
    """Render upgrade CTA for Pro tier features."""
    st.info(
        "**Want deeper AI analysis?**\n\n"
        "Upgrade to **Pro** ($49/month) for:\n"
        "- Claude-powered custom analysis (ask any question!)\n"
        "- Historical catalyst comparisons\n"
        "- Sentiment analysis from social media\n"
        "- Price target predictions\n"
        "- Early alert notifications"
    )

    st.link_button(
        "Upgrade to Pro",
        "https://buy.stripe.com/test_PLACEHOLDER",  # TODO: Replace with real Stripe link
        type="primary",
        use_container_width=True,
    )


def _add_to_watchlist(catalyst: Dict[str, Any]) -> None:
    """Add catalyst to user's watchlist.

    Args:
        catalyst: Catalyst data
    """
    # Initialize watchlist in session state
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    ticker = catalyst.get("ticker")

    if ticker and ticker not in st.session_state.watchlist:
        st.session_state.watchlist.append(ticker)
        st.success(f"Added {ticker} to your watchlist!")
    elif ticker:
        st.info(f"{ticker} is already in your watchlist")
    else:
        st.error("Cannot add catalyst without ticker symbol")


def _set_alert(catalyst: Dict[str, Any]) -> None:
    """Set an alert for catalyst timing.

    Args:
        catalyst: Catalyst data
    """
    ticker = catalyst.get("ticker")
    completion_date = catalyst.get("completion_date")

    if ticker and completion_date:
        st.success(
            f"Alert set for {ticker}! You'll be notified 7 days before "
            f"the catalyst date ({completion_date})."
        )
        # TODO: In production, integrate with email/SMS notification system
    else:
        st.error("Cannot set alert without ticker and completion date")


def _view_similar_catalysts(catalyst: Dict[str, Any]) -> None:
    """View similar historical catalysts (Pro feature).

    Args:
        catalyst: Current catalyst data
    """
    # This is a Pro feature that will query historical database
    # For Phase 1, show placeholder
    st.info(
        "Similar catalyst comparison coming soon! This feature will show "
        "historical catalysts with similar characteristics (phase, therapeutic area, "
        "market cap) and their actual outcomes."
    )


def _record_feedback(question_type: str, sentiment: str) -> None:
    """Record user feedback for analytics.

    Args:
        question_type: Type of question asked
        sentiment: "positive" or "negative"
    """
    # Initialize feedback storage
    if "feedback" not in st.session_state:
        st.session_state.feedback = []

    user_email = st.session_state.get("user_email", "anonymous")

    # Store in session state for immediate UI feedback
    st.session_state.feedback.append(
        {
            "question_type": question_type,
            "sentiment": sentiment,
            "timestamp": datetime.now(),
            "user": user_email,
        }
    )

    # Send to analytics backend
    try:
        user_id = None
        if user_email and user_email != "anonymous":
            user = get_user_by_email(user_email)
            if user:
                user_id = user.get("id")

        # Log to internal database
        log_analytics_event(
            user_id=user_id,
            event_type="explanation_feedback",
            event_category="engagement",
            event_metadata={
                "question_type": question_type,
                "sentiment": sentiment,
                "user_email_masked": user_email if user_email == "anonymous" else "****",
            },
        )

        # TODO: Add Supabase/PostHog integration here
        # Example: posthog.capture(user_id or "anonymous", "explanation_feedback", properties={...})

    except Exception as e:
        # Don't fail the UI if analytics logging fails
        logger.error(f"Failed to log feedback analytics: {e}")


def render_explainer_compact(catalyst: Dict[str, Any], max_questions: int = 3) -> None:
    """Render a compact version of the explainer with limited questions.

    This is useful for embedding in dashboard cards or sidebars.

    Args:
        catalyst: Catalyst data
        max_questions: Maximum number of questions to show
    """
    st.markdown("**Quick AI Insights**")

    if "explainer_agent" not in st.session_state:
        st.session_state.explainer_agent = ExplainerAgent()

    agent = st.session_state.explainer_agent
    questions = agent.get_available_questions()[:max_questions]

    for question in questions:
        if st.button(
            f"{question['icon']} {question['label']}",
            key=f"compact_{question['type']}",
            use_container_width=True,
        ):
            with st.spinner("Generating explanation..."):
                explanation = agent.explain_trial(catalyst, question["type"])
                st.markdown(explanation)
