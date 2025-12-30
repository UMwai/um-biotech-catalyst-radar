"""Biotech Run-Up Radar - Streamlit Application."""

import streamlit as st

from data import ClinicalTrialsScraper, TickerMapper, StockEnricher
from ui import render_dashboard
from ui.trial_banner import render_trial_banner, render_trial_info_sidebar
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

    # Show trial banner if user is logged in
    # For MVP, we'll use a simple email in session state
    # In production, replace with proper authentication
    if "user_email" in st.session_state:
        render_trial_banner(st.session_state["user_email"])

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")

        # Demo mode toggle (only in development)
        if config.debug:
            demo_mode = st.checkbox("Demo Mode (bypass paywall)", value=False)
            if demo_mode:
                st.session_state["is_subscribed"] = True

            # Trial testing controls
            st.subheader("Trial Testing")
            test_email = st.text_input("Test User Email", value="test@example.com")
            if st.button("Set Test User"):
                st.session_state["user_email"] = test_email
                st.success(f"Test user set: {test_email}")
                st.rerun()

        # Show trial status in sidebar
        if "user_email" in st.session_state:
            render_trial_info_sidebar(st.session_state["user_email"])

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
        df = df[(df["days_until"] >= days_filter[0]) & (df["days_until"] <= days_filter[1])]

    # Check subscription
    is_subscribed = check_subscription()

    # Get user email for trial management
    user_email = st.session_state.get("user_email")

    # Render dashboard
    render_dashboard(
        df,
        is_subscribed=is_subscribed,
        payment_link=config.stripe_payment_link or None,
        user_email=user_email,
    )

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
