"""UI components for Streamlit app."""

from .dashboard import render_dashboard
from .charts import render_price_chart
from .chat_agent import render_chat_agent, clear_chat_history
from .explainer import render_explainer, render_explainer_compact
from .catalyst_detail import (
    render_catalyst_detail_page,
    render_catalyst_detail_sidebar,
    show_catalyst_detail,
)

__all__ = [
    "render_dashboard",
    "render_price_chart",
    "render_chat_agent",
    "clear_chat_history",
    "render_explainer",
    "render_explainer_compact",
    "render_catalyst_detail_page",
    "render_catalyst_detail_sidebar",
    "show_catalyst_detail",
]
