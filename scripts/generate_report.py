#!/usr/bin/env python3
"""
Generate a comprehensive biotech catalyst report.
Fetches Phase 2/3 trials, enriches with market data, and produces an HTML report.
"""

import sys
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add src to path so we can import modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
src_dir = project_root / "src"
sys.path.append(str(src_dir))

from data.scraper import ClinicalTrialsScraper
from data.enricher import StockEnricher

DATA_DIR = project_root / "data"
DOCS_DIR = project_root / "docs"
DATA_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

def fetch_and_enrich_data():
    """Fetch trials and enrich with stock data."""
    print("Fetching Phase 2/3 trials from ClinicalTrials.gov...")
    scraper = ClinicalTrialsScraper(months_ahead=6)
    trials_df = scraper.fetch_trials()
    
    if trials_df.empty:
        print("No trials found.")
        return pd.DataFrame()

    print(f"Found {len(trials_df)} trials. Enriching with stock data...")
    # Assume ticker is available or try to map it. 
    # NOTE: The existing codebase has a ticker_mapper, but we need to check if it's integrated.
    # For now, we'll try to use the sponsor name as a proxy for ticker filtering if available,
    # or rely on what's in the dataframe.
    # Looking at scraper.py, it returns: nct_id, title, sponsor, phase, completion_date, condition
    # It does NOT return a ticker. We need the TickerMapper.
    
    try:
        from data.ticker_mapper import TickerMapper
        mapper = TickerMapper()
        trials_df["ticker"] = trials_df["sponsor"].apply(mapper.map_sponsor_to_ticker)
    except ImportError:
        print("Warning: TickerMapper not found or failed. Skipping mapping.")
        trials_df["ticker"] = None

    enricher = StockEnricher()
    # Filter for rows that have a ticker
    
    trials_with_ticker = trials_df.dropna(subset=["ticker"]).copy()
    print(f"Mapped {len(trials_with_ticker)} trials to tickers.")
    
    enriched_df = enricher.enrich(trials_with_ticker)
    
    # Filter small caps
    small_caps_df = enricher.filter_small_caps(enriched_df)
    
    # Calculate days to catalyst
    today = pd.Timestamp.now()
    small_caps_df["days_to_catalyst"] = (pd.to_datetime(small_caps_df["completion_date"]) - today).dt.days
    
    # Ensure numeric columns for plotting
    small_caps_df["pct_change_30d"] = pd.to_numeric(small_caps_df["pct_change_30d"], errors='coerce').fillna(0)
    small_caps_df["market_cap"] = pd.to_numeric(small_caps_df["market_cap"], errors='coerce')
    
    return small_caps_df

def create_visualizations(df):
    """Create Plotly figures."""
    figs = {}
    
    if df.empty:
        return figs

    # 1. Timeline Gantt-like Chart
    df_sorted = df.sort_values("completion_date")
    fig_timeline = px.scatter(
        df_sorted,
        x="completion_date",
        y="ticker",
        color="phase",
        hover_data=["title", "condition", "market_cap"],
        title="Upcoming Biotech Catalysts (Timeline)",
        labels={"completion_date": "Estimated Completion", "ticker": "Ticker"}
    )
    fig_timeline.update_layout(height=max(400, len(df)*20))
    figs["timeline"] = fig_timeline

    # 2. Market Cap vs Days to Catalyst
    # Using absolute value for size to avoid negative sizes
    df["size_metric"] = df["pct_change_30d"].abs() + 1 # offset to be visible
    fig_scatter = px.scatter(
        df,
        x="days_to_catalyst",
        y="market_cap",
        size="size_metric", # use absolute size
        color="phase",
        hover_name="ticker",
        hover_data=["title", "condition", "pct_change_30d"],
        title="Market Cap vs. Time to Catalyst",
        labels={"days_to_catalyst": "Days to Catalyst", "market_cap": "Market Cap ($)"}
    )
    figs["scatter"] = fig_scatter
    
    return figs

def generate_html_report(df, figs):
    """Generate HTML report string."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Biotech Catalyst Radar Report</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max_width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            .metadata {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
            .chart-container {{ margin-bottom: 40px; border: 1px solid #eee; padding: 10px; border-radius: 4px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Biotech Catalyst Radar Report</h1>
            <div class="metadata">Generated on: {timestamp}</div>
            
            <div class="chart-container">
                {figs.get('timeline', go.Figure()).to_html(full_html=False, include_plotlyjs='cdn')}
            </div>
            
            <div class="chart-container">
                {figs.get('scatter', go.Figure()).to_html(full_html=False, include_plotlyjs=False)}
            </div>
            
            <h2>Upcoming Catalysts Table</h2>
            {df[['completion_date', 'ticker', 'phase', 'market_cap', 'pct_change_30d', 'condition']].fillna('').to_html(classes='table', index=False)}
        </div>
    </body>
    </html>
    """
    return html_content

def main():
    print("Starting report generation...")
    
    # 1. Generate Data
    df = fetch_and_enrich_data()
    
    # Save raw data
    csv_path = DATA_DIR / "latest_catalysts.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved dataset to {csv_path}")
    
    if df.empty:
        print("No data to report.")
        return

    # 2. Create Visualizations
    figs = create_visualizations(df)
    
    # 3. Generate Report
    html_content = generate_html_report(df, figs)
    
    report_path = DOCS_DIR / "catalyst_report.html"
    with open(report_path, "w") as f:
        f.write(html_content)
    
    print(f"Report generated at: {report_path}")
    
if __name__ == "__main__":
    main()
