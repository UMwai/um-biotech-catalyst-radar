"""Enhanced catalyst detail view with AI explainer integration.

This module provides a comprehensive detail view for individual catalysts,
including trial information, price charts, and AI-powered explanations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import pandas as pd
import streamlit as st

from .charts import render_price_chart
from .explainer import render_explainer
from utils.historical_data import classify_therapeutic_area


def render_catalyst_detail_page(
    catalyst: Dict[str, Any],
    user_tier: str = "starter",
    show_breadcrumbs: bool = True,
) -> None:
    """Render full-page catalyst detail view.

    Args:
        catalyst: Dictionary containing trial and stock data
        user_tier: User's subscription tier ("starter", "pro", "enterprise")
        show_breadcrumbs: Whether to show breadcrumb navigation
    """
    # Breadcrumb navigation
    if show_breadcrumbs:
        _render_breadcrumbs(catalyst)

    # Page title
    ticker = catalyst.get("ticker", "Unknown")
    sponsor = catalyst.get("sponsor", "Unknown Company")
    st.title(f"🧬 {ticker} - {sponsor}")

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 Overview",
            "🤖 Ask AI",
            "📈 Price Chart",
            "🔍 Similar Catalysts",
        ]
    )

    with tab1:
        _render_overview_tab(catalyst)

    with tab2:
        _render_ai_tab(catalyst, user_tier)

    with tab3:
        _render_chart_tab(catalyst)

    with tab4:
        _render_similar_tab(catalyst, user_tier)


def render_catalyst_detail_sidebar(
    catalyst: Dict[str, Any],
    user_tier: str = "starter",
) -> None:
    """Render catalyst detail in sidebar (compact view).

    Args:
        catalyst: Catalyst data
        user_tier: User's subscription tier
    """
    with st.sidebar:
        st.header("Catalyst Details")

        ticker = catalyst.get("ticker", "N/A")
        st.markdown(f"### {ticker}")

        # Key metrics
        _render_key_metrics(catalyst)

        st.divider()

        # Quick AI insights (compact)
        from .explainer import render_explainer_compact

        render_explainer_compact(catalyst, max_questions=3)


def _render_breadcrumbs(catalyst: Dict[str, Any]) -> None:
    """Render breadcrumb navigation.

    Args:
        catalyst: Catalyst data
    """
    ticker = catalyst.get("ticker", "Unknown")

    # Use markdown for breadcrumb styling
    st.markdown(
        f'<div style="color: #666; font-size: 0.9em; margin-bottom: 1em;">'
        f'<a href="/">Dashboard</a> → '
        f'<a href="/catalyst/{ticker}">Catalyst Detail</a> → '
        f"<strong>{ticker}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_overview_tab(catalyst: Dict[str, Any]) -> None:
    """Render the Overview tab with catalyst summary.

    Args:
        catalyst: Catalyst data
    """
    # Top section: Catalyst summary
    st.subheader("Catalyst Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Ticker",
            catalyst.get("ticker", "N/A"),
        )
        st.metric(
            "Phase",
            catalyst.get("phase", "Unknown"),
        )

    with col2:
        completion_date = catalyst.get("completion_date")
        if completion_date:
            if isinstance(completion_date, str):
                completion_date = datetime.fromisoformat(completion_date)
            date_str = completion_date.strftime("%Y-%m-%d")
            days_until = (
                completion_date.date()
                if hasattr(completion_date, "date")
                else completion_date - datetime.now().date()
            ).days
            st.metric(
                "Catalyst Date",
                date_str,
                delta=f"{days_until} days",
            )
        else:
            st.metric("Catalyst Date", "Unknown")

        market_cap = catalyst.get("market_cap", 0)
        if market_cap and market_cap > 0:
            st.metric(
                "Market Cap",
                f"${market_cap / 1e9:.2f}B",
            )
        else:
            st.metric("Market Cap", "N/A")

    with col3:
        price = catalyst.get("current_price", 0)
        if price and price > 0:
            st.metric(
                "Current Price",
                f"${price:.2f}",
            )
        else:
            st.metric("Current Price", "N/A")

        enrollment = catalyst.get("enrollment", 0)
        if enrollment and enrollment > 0:
            st.metric(
                "Enrollment",
                f"{enrollment:,} patients",
            )
        else:
            st.metric("Enrollment", "N/A")

    st.divider()

    # Middle section: Trial details
    st.subheader("Trial Details")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sponsor**")
        st.markdown(catalyst.get("sponsor", "Unknown"))

        st.markdown("**Condition**")
        condition = catalyst.get("condition", "Not specified")
        st.markdown(condition)

        # Classify therapeutic area
        therapeutic_area = classify_therapeutic_area(condition)
        st.markdown("**Therapeutic Area**")
        st.markdown(therapeutic_area.replace("_", " ").title())

    with col2:
        st.markdown("**NCT ID**")
        nct_id = catalyst.get("nct_id", "N/A")
        if nct_id != "N/A":
            st.markdown(f"[{nct_id}](https://clinicaltrials.gov/study/{nct_id})")
        else:
            st.markdown("N/A")

        st.markdown("**Status**")
        st.markdown(catalyst.get("status", "Unknown"))

        st.markdown("**Sponsor Class**")
        st.markdown(catalyst.get("sponsor_class", "Unknown"))

    st.divider()

    # Bottom section: Trial title
    if catalyst.get("title"):
        st.subheader("Full Trial Title")
        st.markdown(f"*{catalyst.get('title')}*")


def _render_ai_tab(catalyst: Dict[str, Any], user_tier: str) -> None:
    """Render the Ask AI tab with explainer component.

    Args:
        catalyst: Catalyst data
        user_tier: User's subscription tier
    """
    # Add therapeutic area to catalyst if not present
    if "therapeutic_area" not in catalyst:
        condition = catalyst.get("condition", "")
        catalyst["therapeutic_area"] = classify_therapeutic_area(condition)

    render_explainer(catalyst, user_tier)


def _render_chart_tab(catalyst: Dict[str, Any]) -> None:
    """Render the Price Chart tab.

    Args:
        catalyst: Catalyst data
    """
    ticker = catalyst.get("ticker")
    completion_date = catalyst.get("completion_date")

    if not ticker:
        st.warning("No ticker available for this catalyst")
        return

    st.subheader(f"Price Chart - {ticker}")

    # Chart period selector
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        period = st.selectbox(
            "Time Period",
            options=["1mo", "3mo", "6mo", "1y", "2y", "max"],
            index=2,  # Default to 6mo
        )

    with col2:
        show_catalyst = st.checkbox(
            "Show Catalyst Line",
            value=True,
            help="Display vertical line at catalyst date",
        )

    with col3:
        st.selectbox(
            "Chart Type",
            options=["Line", "Candlestick"],
            index=0,
        )

    # Render chart
    try:
        render_price_chart(
            ticker=ticker,
            catalyst_date=completion_date if show_catalyst else None,
            period=period,
        )
    except Exception as e:
        st.error(f"Error loading chart: {e}")

    # Additional chart info
    st.caption(f"*Price data from Yahoo Finance. Chart shows {period} of historical data.*")


def _render_similar_tab(catalyst: Dict[str, Any], user_tier: str) -> None:
    """Render the Similar Catalysts tab.

    Args:
        catalyst: Catalyst data
        user_tier: User's subscription tier
    """
    if user_tier == "starter":
        st.info(
            "**Similar Catalyst Analysis** is a Pro feature.\n\n"
            "Upgrade to Pro to:\n"
            "- Compare with historical catalysts in the same therapeutic area\n"
            "- See actual outcomes (positive/negative) and price movements\n"
            "- Analyze success patterns and failure modes\n"
            "- Get AI-powered similarity scoring"
        )

        if st.button("Upgrade to Pro - $49/month", type="primary", use_container_width=True):
            st.switch_page("pages/subscribe.py")
    else:
        # Pro feature: Show similar catalysts
        st.subheader("Similar Historical Catalysts")

        # This will be implemented in Phase 2 with real database
        st.info(
            "Similar catalyst database coming soon! This feature will show "
            "historical catalysts with comparable characteristics and their outcomes."
        )

        # Placeholder for future implementation
        _render_similar_placeholder(catalyst)


def _render_similar_placeholder(catalyst: Dict[str, Any]) -> None:
    """Render placeholder for similar catalysts (Phase 1).

    Args:
        catalyst: Current catalyst data
    """
    # Show what the feature will look like with mock data
    st.markdown("**Preview of Similar Catalyst Analysis:**")

    # Mock data for demonstration
    mock_similar = pd.DataFrame(
        {
            "Ticker": ["MOCK1", "MOCK2", "MOCK3"],
            "Phase": [catalyst.get("phase", "Phase 2")] * 3,
            "Therapeutic Area": ["Oncology", "Oncology", "Rare Disease"],
            "Outcome": ["Positive (+85%)", "Negative (-42%)", "Positive (+120%)"],
            "Market Cap": ["$1.2B", "$850M", "$2.1B"],
            "Similarity Score": ["92%", "88%", "85%"],
        }
    )

    st.dataframe(mock_similar, use_container_width=True, hide_index=True)

    st.caption("*Mock data for demonstration. Real historical data coming in Phase 2.*")


def _render_key_metrics(catalyst: Dict[str, Any]) -> None:
    """Render key metrics in compact format.

    Args:
        catalyst: Catalyst data
    """
    phase = catalyst.get("phase", "Unknown")
    st.markdown(f"**Phase:** {phase}")

    completion_date = catalyst.get("completion_date")
    if completion_date:
        if isinstance(completion_date, str):
            completion_date = datetime.fromisoformat(completion_date)
        date_str = completion_date.strftime("%Y-%m-%d")
        st.markdown(f"**Catalyst:** {date_str}")

    market_cap = catalyst.get("market_cap", 0)
    if market_cap and market_cap > 0:
        st.markdown(f"**Market Cap:** ${market_cap / 1e9:.2f}B")

    condition = catalyst.get("condition", "")
    if condition:
        # Truncate long conditions
        display_condition = condition[:50] + "..." if len(condition) > 50 else condition
        st.markdown(f"**Condition:** {display_condition}")


# Integration helper for main app
def show_catalyst_detail(
    catalyst_data: Dict[str, Any],
    user_tier: str = "starter",
) -> None:
    """Helper function to show catalyst detail from main app.

    This is the main entry point for displaying catalyst details.

    Args:
        catalyst_data: Full catalyst data dictionary
        user_tier: User's subscription tier
    """
    render_catalyst_detail_page(
        catalyst=catalyst_data,
        user_tier=user_tier,
        show_breadcrumbs=True,
    )
