# Run App

Start the Biotech Catalyst Radar Streamlit dashboard.

## Task: $ARGUMENTS

## Commands
```bash
cd /Users/waiyang/Desktop/repo/um-biotech-catalyst-radar
streamlit run src/app.py
```

## Features
- **Catalyst Table**: Filterable by phase, days until catalyst
- **Stock Charts**: 6-month candlestick with catalyst date overlay
- **Free Preview**: 10 rows of past/recent catalysts
- **Paywall**: Stripe subscription for full access ($19-29/month)

## Configuration
Create `.env` from `.env.example`:
```bash
STRIPE_API_KEY=sk_...
STRIPE_PRICE_ID=price_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PAYMENT_LINK=https://...
```

## Key Files
- `src/app.py` - Main Streamlit entry
- `src/ui/dashboard.py` - Dashboard table & paywall
- `src/ui/charts.py` - Plotly candlestick charts
- `src/utils/stripe_gate.py` - Subscription check

## Deployment
Hosted on Streamlit Community Cloud (free tier)

## Example Usage
- `/run-app` - Start local development
- `/run-app --demo` - Demo mode (bypass paywall)
