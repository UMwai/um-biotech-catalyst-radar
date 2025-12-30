"""
Chat agent UI component for Streamlit.

Provides an interactive chat interface for querying biotech catalysts
using natural language. Uses a rule-based agent (no LLM).
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List

from agents import CatalystAgent


def render_chat_agent():
    """Render the chat agent interface.

    Features:
    - Chat input with st.chat_input()
    - Message history with st.chat_message()
    - Structured catalyst cards (not just text)
    - Action buttons for each result
    - Example queries as quick-start buttons
    - Custom CSS styling
    """
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "catalyst_agent" not in st.session_state:
        st.session_state.catalyst_agent = CatalystAgent()

    # Apply custom CSS
    _apply_custom_css()

    # Show example queries if no chat history
    if not st.session_state.chat_history:
        _render_example_queries()

    # Render chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar="🤖"):
                # Render agent response (structured)
                _render_agent_response(message)

    # Chat input
    user_input = st.chat_input(
        "Ask me about biotech catalysts... (e.g., 'Phase 3 oncology under $2B')",
        key="chat_input",
    )

    if user_input:
        _handle_user_message(user_input)


def _render_example_queries():
    """Render example query buttons for quick start."""
    st.markdown("### 💬 Ask me about biotech catalysts")
    st.markdown(
        "Try these example queries or type your own below:",
        help="Click any example to get started",
    )

    # Example queries in a grid
    col1, col2, col3 = st.columns(3)

    examples = [
        "Phase 3 oncology under $2B",
        "trials next 60 days",
        "neurology catalysts",
        "Phase 2 rare disease under $1B",
        "infectious disease next 30 days",
        "cardiology under $5B",
    ]

    for i, example in enumerate(examples):
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
                _handle_user_message(example)
                st.rerun()


def _handle_user_message(user_message: str):
    """Process user message and generate agent response.

    Args:
        user_message: User's query text
    """
    # Add user message to history
    st.session_state.chat_history.append(
        {"role": "user", "content": user_message, "timestamp": datetime.now()}
    )

    # Get agent response
    agent = st.session_state.catalyst_agent
    response = agent.process_query(user_message)

    # Add agent response to history
    st.session_state.chat_history.append(
        {"role": "assistant", "content": response, "timestamp": datetime.now()}
    )

    # Force rerun to display new messages
    st.rerun()


def _render_agent_response(message: Dict[str, Any]):
    """Render agent response with structured content.

    Args:
        message: Message dictionary with agent response
    """
    response = message["content"]
    response_type = response.get("type")

    # Show message
    st.markdown(response.get("message", ""))

    # Render based on type
    if response_type == "catalyst_list":
        _render_catalyst_list(response)
    elif response_type == "no_results":
        # Message already shown above
        pass
    elif response_type == "error":
        st.error("An error occurred. Please try again.")


def _render_catalyst_list(response: Dict[str, Any]):
    """Render list of catalysts as structured cards.

    Args:
        response: Agent response with catalyst data
    """
    catalysts = response.get("data", [])
    actions = response.get("actions", [])

    if not catalysts:
        return

    st.divider()

    # Render each catalyst as a card
    for i, catalyst in enumerate(catalysts):
        _render_catalyst_card(catalyst, actions, index=i)


def _render_catalyst_card(catalyst: Dict[str, Any], actions: List[Dict[str, str]], index: int):
    """Render a single catalyst as a card with action buttons.

    Args:
        catalyst: Catalyst data dictionary
        actions: List of available actions
        index: Card index (for unique keys)
    """
    # Extract catalyst data
    ticker = catalyst.get("ticker", "N/A")
    phase = catalyst.get("phase", "N/A")
    indication = catalyst.get("indication", "N/A")
    sponsor = catalyst.get("sponsor", "N/A")
    completion_date = catalyst.get("completion_date")
    market_cap = catalyst.get("market_cap")
    current_price = catalyst.get("current_price")

    # Format completion date
    if completion_date:
        if isinstance(completion_date, str):
            date_str = completion_date
        else:
            date_str = completion_date.strftime("%Y-%m-%d")
        days_until = (
            (completion_date - datetime.now()).days if hasattr(completion_date, "year") else None
        )
    else:
        date_str = "TBD"
        days_until = None

    # Format market cap
    if market_cap:
        market_cap_str = f"${market_cap / 1e9:.2f}B"
    else:
        market_cap_str = "N/A"

    # Format price
    price_str = f"${current_price:.2f}" if current_price else "N/A"

    # Render card with custom styling
    st.markdown(
        f"""
        <div class="catalyst-card">
            <div class="catalyst-header">
                <span class="catalyst-ticker">{ticker}</span>
                <span class="catalyst-phase">{phase}</span>
            </div>
            <div class="catalyst-indication">{indication[:100]}{"..." if len(indication) > 100 else ""}</div>
            <div class="catalyst-sponsor">Sponsor: {sponsor}</div>
            <div class="catalyst-metrics">
                <span>📅 {date_str}</span>
                {f'<span class="days-until">({days_until} days)</span>' if days_until is not None else ""}
                <span>💰 {price_str}</span>
                <span>📊 {market_cap_str}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action buttons
    if actions:
        cols = st.columns(len(actions))
        for i, action in enumerate(actions):
            with cols[i]:
                button_key = f"action_{action['action']}_{index}_{ticker}"
                if st.button(
                    f"{action['icon']} {action['label']}",
                    key=button_key,
                    use_container_width=True,
                ):
                    _handle_action(action["action"], catalyst)


def _handle_action(action: str, catalyst: Dict[str, Any]):
    """Handle action button clicks.

    Args:
        action: Action identifier (view_details, add_to_watchlist, set_alert)
        catalyst: Catalyst data
    """
    ticker = catalyst.get("ticker", "Unknown")

    if action == "view_details":
        st.info(f"Viewing details for {ticker}... (Feature coming soon)")
    elif action == "add_to_watchlist":
        st.success(f"Added {ticker} to watchlist! (Feature coming soon)")
    elif action == "set_alert":
        st.success(f"Alert set for {ticker}! (Feature coming soon)")


def _apply_custom_css():
    """Apply custom CSS for chat interface and catalyst cards."""
    st.markdown(
        """
        <style>
        /* Chat container styling */
        .stChatMessage {
            background-color: #f8f9fa;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        /* Catalyst card styling */
        .catalyst-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .catalyst-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }

        .catalyst-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .catalyst-ticker {
            font-size: 1.5rem;
            font-weight: bold;
            color: #fff;
        }

        .catalyst-phase {
            background-color: rgba(255, 255, 255, 0.2);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .catalyst-indication {
            font-size: 1rem;
            margin-bottom: 0.5rem;
            line-height: 1.4;
            color: rgba(255, 255, 255, 0.95);
        }

        .catalyst-sponsor {
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 0.75rem;
        }

        .catalyst-metrics {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.9);
        }

        .catalyst-metrics span {
            background-color: rgba(255, 255, 255, 0.15);
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
        }

        .days-until {
            color: #ffd700 !important;
            font-weight: 600;
        }

        /* Chat input styling */
        .stChatInput {
            border-radius: 24px;
        }

        /* Button styling */
        .stButton button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        }

        /* Example query buttons */
        .stButton button[kind="secondary"] {
            background-color: #f0f2f6;
            color: #262730;
            border: 1px solid #e0e2e6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def clear_chat_history():
    """Clear chat history and reset the conversation."""
    st.session_state.chat_history = []
    st.success("Chat history cleared!")
    st.rerun()
