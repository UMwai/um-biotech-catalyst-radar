"""Main dashboard view for Streamlit."""

from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from .charts import render_price_chart
from .paywall import render_paywall


def render_dashboard(
    df: pd.DataFrame,
    is_subscribed: bool = False,
    payment_link: Optional[str] = None,
    user_email: Optional[str] = None,
) -> None:
    """Render the main catalyst dashboard.

    Args:
        df: DataFrame with trial and stock data
        is_subscribed: Whether user has active subscription
        payment_link: Stripe payment link (deprecated, using trial system now)
        user_email: User's email for trial management
    """
    st.header("Upcoming Biotech Catalysts")

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Catalysts", len(df))
    with col2:
        next_30 = len(df[df["days_until"] <= 30]) if "days_until" in df.columns else 0
        st.metric("Next 30 Days", next_30)
    with col3:
        phase3_count = len(df[df["phase"] == "Phase 3"]) if "phase" in df.columns else 0
        st.metric("Phase 3 Trials", phase3_count)

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
    _render_table(free_df[display_cols])

    # Gated content
    if not gated_df.empty:
        st.divider()
        st.subheader("Upcoming Catalysts")

        # Check if user has access (trial or subscription)
        # If user_email is provided, use trial system; otherwise fall back to is_subscribed
        has_access = is_subscribed

        if user_email:
            # Use trial-based paywall
            paywall_shown = render_paywall(user_email)
            if paywall_shown:
                return  # Stop rendering, paywall is blocking

            # If no paywall shown, user has access (trial active or subscribed)
            has_access = True

        if has_access:
            _render_table(gated_df[display_cols])

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


def _render_table(df: pd.DataFrame) -> None:
    """Render a styled DataFrame table."""
    if df.empty:
        st.info("No catalysts to display.")
        return

    # Format columns
    df_display = df.copy()

    if "completion_date" in df_display.columns:
        df_display["completion_date"] = pd.to_datetime(
            df_display["completion_date"]
        ).dt.strftime("%Y-%m-%d")

    if "market_cap" in df_display.columns:
        df_display["market_cap"] = df_display["market_cap"].apply(
            lambda x: f"${x/1e9:.2f}B" if pd.notna(x) and x > 0 else "N/A"
        )

    if "current_price" in df_display.columns:
        df_display["current_price"] = df_display["current_price"].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
        )

    # Rename columns for display
    rename_map = {
        "ticker": "Ticker",
        "phase": "Phase",
        "condition": "Condition",
        "completion_date": "Catalyst Date",
        "days_until": "Days Until",
        "current_price": "Price",
        "market_cap": "Market Cap",
    }
    df_display = df_display.rename(columns=rename_map)

    st.dataframe(df_display, use_container_width=True, hide_index=True)


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
            st.markdown(f"**Market Cap:** ${row['market_cap']/1e9:.2f}B")


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
        st.info(
            "Payment coming soon! Set STRIPE_PAYMENT_LINK in environment variables."
        )
