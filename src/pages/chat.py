"""
Chat page for natural language catalyst queries.

This page provides an interactive chat interface where users can
query biotech catalysts using natural language instead of manual filters.

Example queries:
- "Phase 3 oncology under $2B"
- "trials next 60 days"
- "neurology catalysts"
"""

import streamlit as st
from ui.chat_agent import render_chat_agent, clear_chat_history


def main():
    """Render the chat page."""
    # Page config
    st.set_page_config(
        page_title="Chat with Catalyst Agent - Biotech Radar",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Header
    st.title("💬 Chat with Catalyst Agent")
    st.markdown(
        """
        Ask questions about biotech catalysts in plain English.
        The agent will help you find relevant Phase 2/3 trials based on your criteria.
        """
    )

    # Sidebar
    with st.sidebar:
        st.header("Chat Controls")

        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            clear_chat_history()

        st.divider()

        # Example queries section
        st.subheader("📝 Example Queries")
        st.markdown(
            """
            **By Therapeutic Area:**
            - `oncology catalysts`
            - `neurology trials`
            - `rare disease under $1B`

            **By Phase:**
            - `Phase 3 trials`
            - `Phase 2 under $2B`

            **By Timeframe:**
            - `trials next 30 days`
            - `catalysts next 60 days`
            - `Q1 2025 trials`

            **Combined:**
            - `Phase 3 oncology under $2B`
            - `neurology next 60 days`
            - `Phase 2 rare disease under $1B`
            """
        )

        st.divider()

        # Keyboard shortcuts
        st.subheader("⌨️ Keyboard Shortcuts")
        st.markdown(
            """
            - **Enter** - Send message
            - **Shift + Enter** - New line
            - **Ctrl + K** - Clear chat *(coming soon)*
            """
        )

        st.divider()

        # How it works
        with st.expander("ℹ️ How It Works"):
            st.markdown(
                """
                The Catalyst Agent uses **keyword matching**
                to understand your query. It looks for:

                1. **Therapeutic areas** (oncology, neurology, etc.)
                2. **Market cap thresholds** (under $1B, under $2B)
                3. **Phase filters** (Phase 2, Phase 3)
                4. **Timeframes** (next 30 days, Q1 2025)

                No AI or LLM is used - all responses are
                deterministic and rule-based.
                """
            )

        st.divider()

        # Upgrade CTA
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 1.5rem;
                        border-radius: 12px;
                        color: white;
                        text-align: center;">
                <h4 style="margin: 0 0 0.5rem 0;">💎 Want Smarter Responses?</h4>
                <p style="margin: 0 0 1rem 0; font-size: 0.9rem;">
                    Upgrade to Pro for Claude-powered AI that understands
                    complex queries and provides deeper insights.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("")  # Spacing

        if st.button("✨ Upgrade to Pro", type="primary", use_container_width=True):
            st.info("Pro plan coming soon! Stay tuned for AI-powered insights.")

    # Main content - render chat agent
    render_chat_agent()

    # Footer with tips
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.85rem;">
            <p><strong>💡 Pro Tip:</strong> Be specific with your queries for better results.
            Combine filters like "Phase 3 oncology under $2B next 60 days" for precise matching.</p>
            <p style="margin-top: 0.5rem;">
                Data sourced from ClinicalTrials.gov | Updates daily |
                <a href="https://github.com/UMwai/um-biotech-catalyst-radar">GitHub</a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
