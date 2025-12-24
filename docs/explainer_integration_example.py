"""
Example integration of the AI Explainer component into the main app.

This file shows how to integrate the explainer into different parts
of the Biotech Run-Up Radar application.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Example 1: Add explainer to existing dashboard stock detail view
def integrate_explainer_into_dashboard():
    """Example: Integrate explainer into dashboard.py _render_stock_detail()"""

    from ui.explainer import render_explainer_compact

    # This code would go into src/ui/dashboard.py, _render_stock_detail() function
    def _render_stock_detail(row: pd.Series) -> None:
        """Render detailed view for a single stock with AI explainer."""
        col1, col2 = st.columns([2, 1])

        with col1:
            # Existing chart code
            from ui.charts import render_price_chart
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

            # NEW: Add AI Explainer (compact version)
            st.divider()
            st.markdown("### 🤖 Quick AI Insights")
            render_explainer_compact(row.to_dict(), max_questions=3)


# Example 2: Create a dedicated catalyst detail page
def create_catalyst_detail_page():
    """Example: Create a new Streamlit page for catalyst details"""

    # This would go into src/pages/catalyst_detail.py
    import streamlit as st
    from ui import show_catalyst_detail

    st.set_page_config(
        page_title="Catalyst Detail - Biotech Run-Up Radar",
        page_icon="🧬",
        layout="wide",
    )

    # Get catalyst ticker from URL query params
    query_params = st.query_params
    ticker = query_params.get("ticker")

    if not ticker:
        st.error("No catalyst specified")
        if st.button("← Back to Dashboard"):
            st.switch_page("pages/main.py")
        st.stop()

    # Load catalyst data from session state or database
    catalyst_data = st.session_state.get(f"catalyst_{ticker}")

    if not catalyst_data:
        st.error(f"Catalyst data not found for {ticker}")
        if st.button("← Back to Dashboard"):
            st.switch_page("pages/main.py")
        st.stop()

    # Get user tier for feature gating
    user_tier = st.session_state.get("user_tier", "starter")

    # Render the full catalyst detail view
    show_catalyst_detail(catalyst_data, user_tier)


# Example 3: Add "Ask AI" button to each row in the table
def add_ai_button_to_table():
    """Example: Add AI explainer button to dashboard table rows"""

    import streamlit as st
    import pandas as pd
    from ui.explainer import render_explainer

    def _render_table_with_ai(df: pd.DataFrame) -> None:
        """Render a styled DataFrame table with AI buttons."""
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

        # Render table with AI button column
        for idx, row in df_display.iterrows():
            cols = st.columns([2, 1, 2, 2, 1, 1, 1, 0.5])

            with cols[0]:
                st.markdown(f"**{row.get('ticker', 'N/A')}**")
            with cols[1]:
                st.write(row.get("phase", "N/A"))
            with cols[2]:
                st.write(row.get("condition", "N/A")[:30] + "...")
            with cols[3]:
                st.write(row.get("completion_date", "N/A"))
            with cols[4]:
                st.write(row.get("days_until", "N/A"))
            with cols[5]:
                st.write(row.get("current_price", "N/A"))
            with cols[6]:
                st.write(row.get("market_cap", "N/A"))
            with cols[7]:
                if st.button("🤖", key=f"ai_{idx}", help="Ask AI about this catalyst"):
                    st.session_state.show_explainer_for = df.iloc[idx].to_dict()
                    st.rerun()

        # Show explainer modal if triggered
        if st.session_state.get("show_explainer_for"):
            st.divider()
            with st.container(border=True):
                ticker = st.session_state.show_explainer_for.get("ticker", "Unknown")
                st.markdown(f"### 🤖 AI Explainer - {ticker}")

                if st.button("✕ Close", key="close_explainer"):
                    st.session_state.show_explainer_for = None
                    st.rerun()

                user_tier = st.session_state.get("user_tier", "starter")
                render_explainer(st.session_state.show_explainer_for, user_tier)


# Example 4: Simple usage in any Streamlit component
def simple_explainer_usage():
    """Simplest way to use the explainer"""

    import streamlit as st
    from agents.explainer_agent import ExplainerAgent
    from datetime import date, timedelta

    # Create sample catalyst data
    catalyst = {
        "ticker": "BGNE",
        "sponsor": "BeiGene Ltd",
        "phase": "Phase 3",
        "condition": "Advanced Non-Small Cell Lung Cancer",
        "completion_date": date.today() + timedelta(days=60),
        "market_cap": 15_000_000_000,  # $15B
        "enrollment": 650,
        "nct_id": "NCT12345678",
        "current_price": 185.50,
    }

    # Create explainer agent
    agent = ExplainerAgent()

    # Get available questions
    questions = agent.get_available_questions()

    # Display question buttons
    st.subheader("Ask AI About This Catalyst")
    for question in questions[:3]:  # Show first 3 questions
        if st.button(f"{question['icon']} {question['label']}", key=question['type']):
            # Generate explanation
            with st.spinner("Analyzing..."):
                explanation = agent.explain_trial(catalyst, question['type'])

            # Display explanation
            with st.expander(question['label'], expanded=True):
                st.markdown(explanation)


# Example 5: Integration with existing chat agent
def integrate_with_chat_agent():
    """Example: Use explainer alongside existing chat agent"""

    import streamlit as st
    from agents.explainer_agent import ExplainerAgent

    # Initialize both agents
    if "explainer_agent" not in st.session_state:
        st.session_state.explainer_agent = ExplainerAgent()

    explainer = st.session_state.explainer_agent

    # Create tabs for different AI features
    tab1, tab2 = st.tabs(["💬 Chat Agent", "🤖 Quick Explainer"])

    with tab1:
        # Existing chat agent code
        from ui.chat_agent import render_chat_agent
        render_chat_agent()

    with tab2:
        # Quick explainer for current catalyst
        catalyst = st.session_state.get("current_catalyst")
        if catalyst:
            from ui.explainer import render_explainer
            render_explainer(catalyst, user_tier="starter")
        else:
            st.info("Select a catalyst from the dashboard to ask AI questions")


# Example 6: Standalone explainer demo page
def create_explainer_demo_page():
    """Example: Standalone demo page for the explainer"""

    import streamlit as st
    from datetime import date, timedelta
    from agents.explainer_agent import ExplainerAgent
    from ui.explainer import render_explainer

    st.title("🤖 AI Explainer Demo")
    st.markdown("See how the AI explains biotech catalysts in plain English")

    # Create demo catalyst
    demo_catalyst = {
        "ticker": "DEMO",
        "sponsor": "Demo Pharma Inc",
        "phase": st.selectbox("Phase", ["Phase 2", "Phase 3"]),
        "condition": st.text_input("Condition", "Advanced Non-Small Cell Lung Cancer"),
        "completion_date": date.today() + timedelta(days=60),
        "market_cap": st.slider(
            "Market Cap ($B)",
            min_value=0.5,
            max_value=5.0,
            value=1.5,
            step=0.1
        ) * 1_000_000_000,
        "enrollment": st.number_input("Enrollment", min_value=50, max_value=2000, value=450),
        "current_price": 12.50,
    }

    st.divider()

    # Render explainer
    render_explainer(demo_catalyst, user_tier="starter")


# Example 7: Watchlist integration
def integrate_with_watchlist():
    """Example: Show AI insights for watchlist items"""

    import streamlit as st
    from agents.explainer_agent import ExplainerAgent

    st.subheader("📌 Your Watchlist")

    # Get watchlist from session state
    watchlist = st.session_state.get("watchlist", [])

    if not watchlist:
        st.info("Your watchlist is empty. Add catalysts from the dashboard.")
        return

    # Show each watchlist item with quick AI insight
    agent = ExplainerAgent()

    for ticker in watchlist:
        # Get catalyst data for this ticker
        catalyst = st.session_state.get(f"catalyst_{ticker}")

        if catalyst:
            with st.expander(f"{ticker} - {catalyst.get('condition', 'Unknown')}", expanded=False):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.metric("Days Until Catalyst", catalyst.get("days_until", "?"))
                    st.metric("Market Cap", f"${catalyst.get('market_cap', 0)/1e9:.2f}B")

                with col2:
                    # Show quick timing insight
                    explanation = agent.explain_trial(catalyst, "catalyst_timeline")
                    # Show first 200 characters
                    st.markdown(explanation[:200] + "...")

                    if st.button("Read Full Analysis", key=f"read_{ticker}"):
                        st.session_state.current_catalyst = catalyst
                        st.switch_page("pages/catalyst_detail.py")


if __name__ == "__main__":
    st.title("Explainer Integration Examples")
    st.markdown("Choose an example to see implementation details")

    example = st.selectbox(
        "Select Example",
        [
            "Dashboard Integration",
            "Detail Page",
            "Table AI Buttons",
            "Simple Usage",
            "Chat Integration",
            "Demo Page",
            "Watchlist Integration",
        ]
    )

    if example == "Dashboard Integration":
        integrate_explainer_into_dashboard()
    elif example == "Detail Page":
        create_catalyst_detail_page()
    elif example == "Table AI Buttons":
        add_ai_button_to_table()
    elif example == "Simple Usage":
        simple_explainer_usage()
    elif example == "Chat Integration":
        integrate_with_chat_agent()
    elif example == "Demo Page":
        create_explainer_demo_page()
    elif example == "Watchlist Integration":
        integrate_with_watchlist()
