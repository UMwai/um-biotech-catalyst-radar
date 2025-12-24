# AI Explainer Component

A rule-based AI assistant that explains clinical trial catalysts in plain English without requiring LLM API calls.

## Quick Start

```python
from agents.explainer_agent import ExplainerAgent
from datetime import date, timedelta

# Create agent
agent = ExplainerAgent()

# Prepare catalyst data
catalyst = {
    "ticker": "BGNE",
    "phase": "Phase 3",
    "condition": "Advanced Non-Small Cell Lung Cancer",
    "completion_date": date.today() + timedelta(days=60),
    "market_cap": 1_500_000_000,  # $1.5B
    "enrollment": 450,
}

# Get explanation
explanation = agent.explain_trial(catalyst, "historical_success_rate")
print(explanation)
```

## Available Question Types

| Question Type | Description | Example Use Case |
|--------------|-------------|------------------|
| `what_does_trial_test` | Explains trial purpose and phase | New users learning about a trial |
| `why_completion_important` | Explains catalyst timing patterns | Understanding why dates matter |
| `historical_success_rate` | Shows phase success statistics | Risk assessment |
| `market_cap_impact` | Explains volatility by company size | Position sizing decisions |
| `enrollment_significance` | Explains patient count implications | Trial quality evaluation |
| `catalyst_timeline` | Shows optimal entry timing | Entry/exit strategy planning |

## UI Integration

### Streamlit Full View

```python
from ui.explainer import render_explainer

# In your Streamlit app
catalyst_data = {...}  # Your catalyst dictionary
user_tier = "starter"  # or "pro"

render_explainer(catalyst_data, user_tier)
```

### Streamlit Compact View (Sidebar)

```python
from ui.explainer import render_explainer_compact

# Show limited questions (e.g., in sidebar)
render_explainer_compact(catalyst_data, max_questions=3)
```

### Detail Page

```python
from ui import show_catalyst_detail

# Full detail page with tabs
show_catalyst_detail(catalyst_data, user_tier="starter")
```

## Catalyst Data Format

The explainer expects a dictionary with the following keys:

```python
{
    # Required fields
    "ticker": str,          # Stock ticker symbol
    "phase": str,           # "Phase 2" or "Phase 3"
    "condition": str,       # Medical condition/indication

    # Recommended fields
    "completion_date": date,  # Expected completion date
    "market_cap": float,      # Market cap in dollars
    "sponsor": str,           # Company name

    # Optional fields
    "enrollment": int,        # Number of patients
    "nct_id": str,           # ClinicalTrials.gov ID
    "current_price": float,   # Stock price
    "status": str,           # Trial status
    "title": str,            # Full trial title
}
```

## Example Responses

### Success Rate Question

**Input:**
```python
catalyst = {
    "ticker": "BGNE",
    "phase": "Phase 3",
    "condition": "Metastatic Melanoma",
    "market_cap": 15_000_000_000,
}

explanation = agent.explain_trial(catalyst, "historical_success_rate")
```

**Output:**
> Based on historical industry data, **50%** of oncology Phase 3 trials achieve their primary endpoints and lead to FDA approval. This is significantly higher than Phase 2 success rates, making Phase 3 readouts more predictable but still risky.
>
> **Why this matters:** The 50% historical success rate provides a baseline probability for your risk assessment. However, individual trials can vary significantly based on mechanism of action, endpoint selection, patient population, and competitive landscape...
>
> *Data source: BIO Clinical Development Success Rates 2006-2015*
>
> **Disclaimer:** This is educational information only, not financial advice...

### Entry Timing Question

**Input:**
```python
catalyst = {
    "ticker": "TEST",
    "completion_date": date(2025, 3, 15),
    "market_cap": 1_200_000_000,  # $1.2B
}

explanation = agent.explain_trial(catalyst, "catalyst_timeline")
```

**Output:**
> Based on historical run-up patterns, the **optimal entry window** for TEST is approximately **60 days before** the catalyst date, which would be around **January 14, 2025**.
>
> **Historical pattern analysis:**
> - Expected run-up from optimal entry: **+28%**
> - Risk level: **High**
> - Current days until catalyst: **60 days**
> - Estimated remaining run-up potential: **+28%**
>
> *Rationale:* Small caps have higher volatility but larger run-up potential
>
> **Trading strategy considerations:**
> 1. **If entering now (60 days out):** You're in the sweet spot
> 2. **Stop-loss:** Consider 15-25% below entry for risk management
> 3. **Position sizing:** Use 2-5% of portfolio max for binary catalyst plays...

## Historical Data

The explainer uses hardcoded industry statistics (Phase 1). These will be replaced with real historical data in Phase 2.

### Phase Success Rates

```python
from utils.historical_data import get_success_rate

# Get Phase 3 success rate for oncology
rate = get_success_rate("oncology", "Phase 3")
print(f"Success rate: {rate}")  # 0.50 (50%)
```

**Available therapeutic areas:**
- `oncology` - Cancer trials
- `rare_disease` - Orphan/rare diseases
- `neurology` - Neurological conditions
- `cardiovascular` - Heart/cardiovascular
- `immunology` - Autoimmune diseases
- `infectious_disease` - Viral/bacterial infections
- `default` - All other areas

### Run-Up Patterns

```python
from utils.historical_data import get_run_up_estimate

# Estimate run-up for $1.5B company, 60 days before catalyst
market_cap = 1_500_000_000
days_until = 60
estimate = get_run_up_estimate(market_cap, days_until)
print(f"Expected run-up: {estimate * 100}%")  # 28%
```

**Market cap tiers:**
- **Small cap (<$2B):** Higher volatility, larger run-ups (30-100%)
- **Mid cap ($2-5B):** Moderate volatility, moderate run-ups (15-40%)

### Optimal Entry Timing

```python
from utils.historical_data import get_optimal_entry_window

completion_date = date(2025, 3, 15)
market_cap = 1_000_000_000  # $1B

window = get_optimal_entry_window(completion_date, market_cap)

print(f"Optimal entry: {window['optimal_entry_date']}")
print(f"Days before: {window['optimal_days_before']}")
print(f"Expected run-up: {window['expected_run_up'] * 100}%")
print(f"Risk level: {window['risk_level']}")
```

## Testing

Run the test suite:

```bash
pytest tests/test_explainer_agent.py -v
```

**Test coverage:**
- ✅ All 6 question types
- ✅ Edge cases (missing data, invalid dates)
- ✅ Historical data calculations
- ✅ Explanation quality (length, formatting)
- ✅ Disclaimer presence

## API Reference

### ExplainerAgent

```python
class ExplainerAgent:
    def explain_trial(
        self,
        catalyst: Dict[str, Any],
        question_type: str
    ) -> str:
        """Generate explanation for a question about the catalyst.

        Args:
            catalyst: Trial and stock data
            question_type: One of the 6 available question types

        Returns:
            Formatted explanation with disclaimer
        """

    def get_historical_context(
        self,
        therapeutic_area: str,
        phase: str
    ) -> Dict[str, Any]:
        """Get historical statistics for area and phase.

        Returns:
            {
                "therapeutic_area": str,
                "phase": str,
                "success_rate": float,
                "success_rate_formatted": str,
                "all_stats": {...}
            }
        """

    def calculate_run_up_window(
        self,
        completion_date: date,
        market_cap: float
    ) -> Dict[str, Any]:
        """Calculate optimal entry timing.

        Returns:
            {
                "optimal_entry_date": date,
                "optimal_days_before": int,
                "expected_run_up": float,
                "risk_level": str,
                "rationale": str
            }
        """

    def find_similar_catalysts(
        self,
        catalyst: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find similar historical catalysts.

        Note: Returns empty list in Phase 1.
        Will be implemented with database in Phase 2.
        """

    def get_available_questions(self) -> List[Dict[str, str]]:
        """Get list of available question types.

        Returns:
            [
                {
                    "type": "what_does_trial_test",
                    "label": "What does this trial test?",
                    "icon": "💡",
                    "category": "basics"
                },
                ...
            ]
        """
```

### UI Functions

```python
def render_explainer(
    catalyst: Dict[str, Any],
    user_tier: str = "starter"
) -> None:
    """Render full explainer UI with all questions."""

def render_explainer_compact(
    catalyst: Dict[str, Any],
    max_questions: int = 3
) -> None:
    """Render compact explainer with limited questions."""

def show_catalyst_detail(
    catalyst_data: Dict[str, Any],
    user_tier: str = "starter"
) -> None:
    """Show full catalyst detail page with tabs."""
```

## Features by Tier

### Starter Tier (Included)
✅ 6 pre-written question types
✅ Historical success rate data
✅ Run-up pattern analysis
✅ Optimal entry timing
✅ Therapeutic area classification
✅ Basic action buttons (Watchlist, Alerts)

### Pro Tier (Upgrade)
🔒 Claude-powered custom questions
🔒 Historical catalyst comparisons
🔒 View similar catalysts
🔒 Sentiment analysis integration
🔒 Early alert notifications
🔒 Price target predictions

## Data Sources

- **Phase Success Rates:** BIO Clinical Development Success Rates 2006-2015
- **Run-Up Patterns:** Proprietary analysis of small-cap biotech price movements
- **Therapeutic Classification:** Industry-standard keyword mapping

## Compliance

✅ **Educational only** - All responses include disclaimer
✅ **No financial advice** - Clear positioning as learning tool
✅ **Source citations** - Historical data sources are cited
✅ **Privacy friendly** - No user data sent to external services
✅ **Offline capable** - No API dependencies

## Roadmap

### Phase 1 (Current) ✅
- Rule-based explanations
- 6 question types
- Historical statistics
- Streamlit UI components

### Phase 2 (Q1 2025)
- Claude API integration for custom questions
- Historical catalyst database (Supabase)
- Real outcome tracking
- Sentiment analysis

### Phase 3 (Q2 2025)
- Backtesting framework
- Portfolio optimization
- Risk-adjusted position sizing
- Email/SMS alerts

## Support

For issues or questions:
1. Check this README
2. Review `/docs/explainer_integration_example.py` for examples
3. Run tests: `pytest tests/test_explainer_agent.py`
4. Check implementation summary: `EXPLAINER_IMPLEMENTATION_SUMMARY.md`

## License

Part of the Biotech Run-Up Radar project. See main project LICENSE.
