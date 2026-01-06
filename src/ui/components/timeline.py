"""Timeline component for upcoming catalysts."""

import pandas as pd
import plotly.express as px
import streamlit as st

def render_timeline(df: pd.DataFrame) -> None:
    """Render a timeline Gantt chart of upcoming catalysts.
    
    Args:
        df: DataFrame with 'ticker', 'catalyst_date', 'phase', 'description'
    """
    if df.empty or "catalyst_date" not in df.columns:
        return

    # Filter for future dates mostly
    today = pd.Timestamp.now()
    future_df = df[df["catalyst_date"] >= today].copy()
    
    if future_df.empty:
        st.info("No upcoming catalysts to visualize.")
        return

    future_df = future_df.sort_values("catalyst_date").head(20) # Top 20 next items
    
    # Create start date (today) for the bar
    future_df["start_date"] = today
    future_df["days_until"] = (future_df["catalyst_date"] - today).dt.days
    
    # Label
    future_df["label"] = future_df["ticker"] + ": " + future_df["phase"]

    fig = px.timeline(
        future_df, 
        x_start="start_date", 
        x_end="catalyst_date", 
        y="label",
        color="days_until",
        title="Catalyst Timeline (Next 20 Events)",
        labels={"label": "Ticker", "catalyst_date": "Expected Date"},
        hover_data=["description", "condition"],
        color_continuous_scale="RdYlGn_r" # Red for close, Green for far
    )
    
    fig.update_yaxes(categoryorder="total ascending") # Closest at top (if sorted correctly)
    fig.update_layout(height=400, template="plotly_dark")
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    # Test
    data = {
        "ticker": ["ABC", "XYZ"],
        "catalyst_date": [pd.Timestamp.now() + pd.Timedelta(days=30), pd.Timestamp.now() + pd.Timedelta(days=60)],
        "phase": ["Phase 2", "Phase 3"],
        "description": ["Data readout", "FDA Approval"]
    }
    render_timeline(pd.DataFrame(data))
