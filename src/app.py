"""Biotech Run-Up Radar - Streamlit Application."""

import streamlit as st

from data import ClinicalTrialsScraper, TickerMapper, StockEnricher
from ui import render_dashboard
from utils import Config, check_subscription


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="Biotech Run-Up Radar",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Load config
    config = Config.from_env()

    # Title
    st.title("🧬 Biotech Run-Up Radar")
    st.markdown(
        "Track Phase 2/3 clinical trial catalysts for small-cap biotech stocks. "
        "Catch the run-up before data drops."
    )

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")

        # Demo mode toggle (only in development)
        if config.debug:
            demo_mode = st.checkbox("Demo Mode (bypass paywall)", value=False)
            if demo_mode:
                st.session_state["is_subscribed"] = True

        # Filters
        st.subheader("Filters")
        phase_filter = st.multiselect(
            "Phase",
            options=["Phase 2", "Phase 3"],
            default=["Phase 2", "Phase 3"],
        )

        days_filter = st.slider(
            "Days until catalyst",
            min_value=0,
            max_value=90,
            value=(0, 60),
        )

    # Load data (with caching)
    df = load_data(config)

    if df.empty:
        st.warning("No catalyst data available. Please try again later.")
        return

    # Apply filters
    if phase_filter:
        df = df[df["phase"].isin(phase_filter)]

    if "days_until" in df.columns:
        df = df[
            (df["days_until"] >= days_filter[0]) & (df["days_until"] <= days_filter[1])
        ]

    # Check subscription
    is_subscribed = check_subscription()

    # Render dashboard
    render_dashboard(df, is_subscribed=is_subscribed)

    # Footer
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.8em;">
        Data sourced from ClinicalTrials.gov | Not financial advice |
        <a href="https://github.com/UMwai/um-biotech-catalyst-radar">GitHub</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(config: Config):
    """Load and process catalyst data.

    Args:
        config: Application configuration

    Returns:
        Processed DataFrame with catalysts
    """
    with st.spinner("Fetching clinical trial data..."):
        try:
            # Step 1: Scrape ClinicalTrials.gov
            scraper = ClinicalTrialsScraper(months_ahead=config.months_ahead)
            df = scraper.fetch_trials()

            if df.empty:
                return df

            # Step 2: Map sponsors to tickers
            mapper = TickerMapper()
            df = mapper.map_all(df)

            # Filter to only matched tickers
            df = df[df["ticker"].notna()]

            if df.empty:
                return df

            # Step 3: Enrich with stock data
            enricher = StockEnricher(max_market_cap=config.max_market_cap)
            df = enricher.enrich(df)

            # Step 4: Filter to small caps
            df = enricher.filter_small_caps(df)

            return df

        except Exception as e:
            st.error(f"Error loading data: {e}")
            return __import__("pandas").DataFrame()


if __name__ == "__main__":
    main()
