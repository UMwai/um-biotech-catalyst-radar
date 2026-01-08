"""Main dashboard view for Streamlit.

Per spec Section 4.3:
- First: AI-curated view ("Here are today's top opportunities")
- Then: Personalized watchlist ("Here's what changed on YOUR stocks")
- Always visible: 3 AI-recommended opportunities

Per spec Section 4.4:
- Free tier: <14, <30 days catalyst window
- Paid tier: <90 days + full timeline

Phase 3 Enhancements:
- NL filter input for natural language filtering
- Alert badge for unread watchlist alerts
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from .charts import render_price_chart
from .paywall import render_paywall
from .components.timeline import render_timeline
from .components.alert_badge import render_alert_summary


def render_proactive_feed(
    insights: List[Dict[str, Any]],
    max_free: int = 3,
    has_access: bool = False,
) -> None:
    """Render AI-curated proactive feed.

    Per spec: "Here are today's top opportunities" - always visible.

    Args:
        insights: List of insight dicts from FeedGenerator
        max_free: Number of insights to show for free users
        has_access: Whether user has paid access
    """
    st.markdown("### 🎯 AI Picks Today")
    st.caption("AI-curated opportunities based on catalyst timing, cash runway, and trial quality")

    if not insights:
        st.info("Generating fresh insights... Check back in a few minutes.")
        return

    # Show top 3 always (free preview)
    for i, insight in enumerate(insights[:max_free]):
        _render_ai_insight_card(insight, index=i)

    # Show remaining with blur/paywall for free users
    remaining = insights[max_free:]
    if remaining:
        if has_access:
            for i, insight in enumerate(remaining, start=max_free):
                _render_ai_insight_card(insight, index=i)
        else:
            # Blurred preview
            st.markdown("---")
            st.markdown(f"**🔒 {len(remaining)} more high-conviction opportunities available**")
            with st.container():
                for insight in remaining[:3]:
                    st.markdown(
                        f"""
                        <div style="filter: blur(4px); user-select: none; pointer-events: none;
                                    background: #f8f9fa; padding: 15px; border-radius: 8px;
                                    margin: 10px 0; border-left: 4px solid #6366f1;">
                            <strong>{insight.get('ticker', 'XXXX')}</strong>: {insight.get('headline', 'Premium insight')}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            st.info("Upgrade to unlock all insights and <90 day catalyst window")


def _render_ai_insight_card(insight: Dict[str, Any], index: int = 0) -> None:
    """Render a single AI insight card with conviction scoring."""
    score = insight.get("conviction_score", 50)

    # Color based on score
    if score >= 75:
        border_color = "#10B981"  # Green
        badge = "🟢 High"
    elif score >= 50:
        border_color = "#F59E0B"  # Amber
        badge = "🟡 Medium"
    else:
        border_color = "#6B7280"  # Gray
        badge = "⚪ Low"

    with st.container():
        st.markdown(
            f"""
            <div style="border-left: 4px solid {border_color}; padding: 15px;
                        background: #f8f9fa; border-radius: 0 8px 8px 0; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 18px; font-weight: bold; color: #1F2937;">
                        {insight.get('ticker', 'N/A')}
                    </span>
                    <span style="font-size: 12px; background: {'#D1FAE5' if score >= 75 else '#FEF3C7' if score >= 50 else '#F3F4F6'};
                                 padding: 2px 8px; border-radius: 12px; color: #374151;">
                        {badge} ({score})
                    </span>
                </div>
                <p style="margin: 8px 0 4px 0; color: #4B5563; font-size: 14px;">
                    {insight.get('headline', 'No headline')}
                </p>
                <p style="margin: 4px 0; color: #6B7280; font-size: 13px;">
                    {insight.get('body', '')[:200]}{'...' if len(insight.get('body', '')) > 200 else ''}
                </p>
                <div style="margin-top: 8px; font-size: 11px; color: #9CA3AF;">
                    📅 {insight.get('catalyst_type', 'Catalyst')} in {insight.get('days_until', '?')} days |
                    💊 {insight.get('indication', 'N/A')[:30]} |
                    📎 {insight.get('source', 'Internal')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def load_ai_insights() -> List[Dict[str, Any]]:
    """Load AI insights from database or generate fresh ones."""
    try:
        from utils.sqlite_db import get_db
        db = get_db()
        insights = db.get_active_insights(limit=10)
        if insights:
            return insights
    except Exception:
        pass

    # Fallback: generate on-the-fly
    try:
        from data.feed_generator import FeedGenerator
        generator = FeedGenerator()
        return generator.generate_feed(days_ahead=90, limit=10, use_llm=False)
    except Exception:
        return []


def render_nl_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Render natural language filter input and apply filters.

    Args:
        df: Original catalyst dataframe

    Returns:
        Filtered dataframe
    """
    from utils.nl_filter import get_nl_filter_parser

    # NL Filter input
    filter_query = st.text_input(
        "Filter with natural language",
        placeholder="e.g., 'obesity plays under $3B with catalyst in 30 days'",
        key="nl_filter_input",
        help="Try: 'Phase 3 oncology next 60 days' or 'small cap neuro with PDUFA'",
    )

    if filter_query:
        parser = get_nl_filter_parser()

        with st.spinner("Parsing filter..."):
            filters = parser.parse_query(filter_query)

        # Show applied filters
        if filters:
            formatted = parser.format_applied_filters(filters)
            st.info(f"Applied: {formatted}")

            # Apply filters
            df = parser.apply_filters(df, filters)

            if df.empty:
                st.warning("No catalysts match your filter. Try broadening your search.")

    return df


def render_dashboard(
    df: pd.DataFrame,
    is_subscribed: bool = False,
    payment_link: Optional[str] = None,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
) -> None:
    """Render the main catalyst dashboard.

    Args:
        df: DataFrame with trial and stock data
        is_subscribed: Whether user has active subscription
        payment_link: Stripe payment link (deprecated, using trial system now)
        user_email: User's email for trial management
        user_id: User ID for alerts and watchlist (Phase 3)
    """
    # Phase 3: Show alert summary if user has alerts
    if user_id:
        render_alert_summary(user_id)

    # AI-Curated Feed First (per spec 4.3)
    insights = load_ai_insights()
    has_access = is_subscribed

    # Check trial status
    if user_email and not has_access:
        try:
            from utils.trial_manager import is_trial_active
            has_access = is_trial_active(user_email)
        except Exception:
            pass

    render_proactive_feed(insights, max_free=3, has_access=has_access)

    st.divider()

    # Phase 3: NL Filter for quick filtering
    df = render_nl_filter(df)

    # Summary metrics
    st.header("📊 Catalyst Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Catalysts", len(df))
    with col2:
        next_30 = len(df[df["days_until"] <= 30]) if "days_until" in df.columns else 0
        st.metric("Next 30 Days", next_30)
    with col3:
        phase3_count = len(df[df["phase"] == "Phase 3"]) if "phase" in df.columns else 0
        st.metric("Phase 3 Trials", phase3_count)
    with col4:
        avg_score = sum(i.get("conviction_score", 50) for i in insights[:5]) / max(len(insights[:5]), 1)
        st.metric("Avg Conviction", f"{avg_score:.0f}")

    st.divider()

    # Calculate days until catalyst
    if "completion_date" in df.columns and not df.empty:
        today = pd.Timestamp.now().normalize()
        df = df.copy()
        df["completion_date"] = pd.to_datetime(df["completion_date"], errors="coerce")
        df["days_until"] = (df["completion_date"] - today).dt.days

    # Prepare display columns
    display_cols = [
        "ticker",
        "phase",
        "condition",
        "completion_date",
        "days_until",
        "current_price",
        "market_cap",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    # Split into free preview and gated content
    free_preview_count = 10
    free_df = df.head(free_preview_count)
    gated_df = df.iloc[free_preview_count:]

    # Render free preview
    st.subheader("Free Preview (Past Catalysts)")
    _render_insight_cards(free_df[display_cols])

    # Gated content
    if not gated_df.empty:
        st.divider()
        st.subheader("Upcoming Catalysts")

        # Check if user has access (trial or subscription)
        # If user_email is provided, use trial system; otherwise fall back to is_subscribed
        has_access = is_subscribed

        # Render Timeline (only if user has access)
        if has_access:
            render_timeline(gated_df)
            st.divider()

        if user_email:
            # Use trial-based paywall
            paywall_shown = render_paywall(user_email)
            if paywall_shown:
                return  # Stop rendering, paywall is blocking

            # If no paywall shown, user has access (trial active or subscribed)
            has_access = True

        if has_access:
            _render_insight_cards(gated_df[display_cols])

            # Individual stock drill-down
            st.divider()
            st.subheader("Stock Details")
            tickers = gated_df["ticker"].dropna().unique().tolist()
            if tickers:
                selected = st.selectbox("Select ticker for details", tickers)
                if selected:
                    row = gated_df[gated_df["ticker"] == selected].iloc[0]
                    _render_stock_detail(row)
        else:
            # Fallback to old paywall for non-trial users
            _render_paywall(len(gated_df), payment_link=payment_link)


def _render_insight_cards(df: pd.DataFrame) -> None:
    """Render data as Insight Cards."""
    if df.empty:
        st.info("No catalysts to display.")
        return

    for idx, row in df.iterrows():
        with st.container(border=True):
            cols = st.columns([1, 4, 1])
            
            # Left: Ticker & Price
            with cols[0]:
                st.subheader(row.get("ticker", "N/A"))
                current_price = row.get("current_price")
                price_str = f"${current_price:.2f}" if pd.notna(current_price) else "N/A"
                st.markdown(f"**{price_str}**")
                
                market_cap = row.get("market_cap")
                mc_str = f"${market_cap/1e9:.1f}B" if pd.notna(market_cap) else "N/A"
                st.caption(f"MC: {mc_str}")

            # Center: Insight & Timeline
            with cols[1]:
                days = row.get("days_until", 0)
                phase = row.get("phase", "Unknown")
                
                # Mock AI Insight (In future, fetch from LLM)
                condition = row.get("condition", "Unspecified indication")
                insight = f"**{phase} Analysis**: Upcoming data for {condition}. "
                if days < 30:
                    insight += "High volatility expected as catalyst approaches."
                elif days < 60:
                    insight += "Accumulation zone potential."
                else:
                    insight += "Monitor for updates."
                
                st.markdown(insight)
                
                # Progress Bar
                progress = max(0.0, min(1.0, 1.0 - (days / 180.0))) # Assume 180 day lookback
                st.progress(progress, text=f"{days} days until catalyst")
                st.caption(f"Catalyst: {row.get('completion_date', 'Unknown')}")

            # Right: Action
            with cols[2]:
                st.button("Analyze", key=f"btn_{idx}", use_container_width=True)
                st.button("Chart", key=f"btn_chart_{idx}", use_container_width=True)


def _render_stock_detail(row: pd.Series) -> None:
    """Render detailed view for a single stock."""
    col1, col2 = st.columns([2, 1])

    with col1:
        render_price_chart(
            ticker=row["ticker"],
            catalyst_date=row.get("completion_date"),
        )

    with col2:
        st.markdown("### Trial Details")
        st.markdown(f"**Ticker:** {row.get('ticker', 'N/A')}")
        st.markdown(f"**Phase:** {row.get('phase', 'N/A')}")
        st.markdown(f"**Condition:** {row.get('condition', 'N/A')}")
        st.markdown(f"**Sponsor:** {row.get('sponsor', 'N/A')}")

        if pd.notna(row.get("completion_date")):
            date_str = row["completion_date"].strftime("%Y-%m-%d")
            st.markdown(f"**Catalyst Date:** {date_str}")

        if pd.notna(row.get("current_price")):
            st.markdown(f"**Current Price:** ${row['current_price']:.2f}")

        if pd.notna(row.get("market_cap")):
            st.markdown(f"**Market Cap:** ${row['market_cap'] / 1e9:.2f}B")


def _render_paywall(gated_count: int, payment_link: Optional[str] = None) -> None:
    """Render subscription paywall."""
    st.warning(
        f"**{gated_count} more upcoming catalysts available**\n\n"
        "Subscribe for $29/month to unlock:\n"
        "- All upcoming Phase 2/3 catalysts\n"
        "- Real-time price charts with catalyst overlay\n"
        "- 7-day free trial included"
    )

    if payment_link:
        st.link_button(
            "Start Free Trial - $29/month",
            payment_link,
            type="primary",
            use_container_width=True,
        )
    else:
        st.info("Payment coming soon! Set STRIPE_PAYMENT_LINK in environment variables.")
