"""Price charts with catalyst date overlay."""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.enricher import StockEnricher


def render_price_chart(
    ticker: str,
    catalyst_date: datetime | pd.Timestamp | None = None,
    period: str = "6mo",
) -> None:
    """Render a price chart with catalyst date marked.

    Args:
        ticker: Stock ticker symbol
        catalyst_date: Date of the catalyst event
        period: yfinance period string
    """
    enricher = StockEnricher()
    history = enricher.get_price_history(ticker, period=period)

    if history is None or history.empty:
        st.warning(f"No price data available for {ticker}")
        return

    # Create candlestick chart
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=history["Date"],
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                name=ticker,
            )
        ]
    )

    # Add catalyst date vertical line
    if catalyst_date is not None:
        catalyst_ts = pd.Timestamp(catalyst_date)
        fig.add_vline(
            x=catalyst_ts,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text="Catalyst",
            annotation_position="top",
        )

    # Styling
    fig.update_layout(
        title=f"{ticker} - 6 Month Price History",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=400,
        template="plotly_dark",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_mini_chart(ticker: str, height: int = 100) -> None:
    """Render a minimal sparkline chart.

    Args:
        ticker: Stock ticker symbol
        height: Chart height in pixels
    """
    enricher = StockEnricher()
    history = enricher.get_price_history(ticker, period="1mo")

    if history is None or history.empty:
        return

    fig = go.Figure(
        data=[
            go.Scatter(
                x=history["Date"],
                y=history["Close"],
                mode="lines",
                line=dict(color="#00ff88", width=1),
                fill="tozeroy",
                fillcolor="rgba(0, 255, 136, 0.1)",
            )
        ]
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        template="plotly_dark",
    )

    st.plotly_chart(fig, use_container_width=True)
