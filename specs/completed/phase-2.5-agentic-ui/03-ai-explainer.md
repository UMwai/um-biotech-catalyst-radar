# Feature Spec: AI Explainer Component

## Overview

Implement an AI-powered explainer that translates complex clinical trial data into plain English insights. When users click on a catalyst, they can ask pre-written questions and receive instant, contextual explanations. This feature reduces the learning curve for non-technical traders and increases confidence in trading decisions.

**Strategic Value**:
- **Education**: Helps retail traders understand trial implications without PhD
- **Trust**: Transparent explanations build confidence in platform data
- **Engagement**: Users spend more time exploring catalysts
- **Premium feature**: Advanced AI explanations reserved for Pro tier

**Target Metrics**:
- 90%+ user satisfaction with explanations
- <1 second response time for Phase 1 (rule-based)
- 50%+ users interact with explainer in first session
- 3x increase in avg. time on catalyst detail page

---

## User Stories

### As a retail trader
- **I want to** understand what "Phase 3 oncology trial" means
- **So that** I can assess if it's a good trading opportunity
- **Acceptance**: Click catalyst → See "What does this trial test?" → Get plain English explanation

### As a beginner investor
- **I want to** know the historical success rate for Phase 3 trials
- **So that** I can estimate the probability of catalyst success
- **Acceptance**: Click "Historical success rate?" → See "Phase 3 trials succeed ~60% of the time"

### As a day trader
- **I want to** understand why completion dates matter for stock prices
- **So that** I can time my entries/exits
- **Acceptance**: Click "Why is completion important?" → Get explanation with historical price chart examples

### As a skeptical user
- **I want to** see data sources for AI explanations
- **So that** I can verify the information
- **Acceptance**: Every explanation includes citation (e.g., "Source: ClinicalTrials.gov NCT12345678")

---

## Requirements

### Functional Requirements

1. **Pre-Written Question Templates**

   For each catalyst, show 4-6 clickable questions:
   - **"What does this trial test?"** - Explain indication, drug mechanism, patient population
   - **"Why is completion important?"** - Explain catalyst event, data release timing, stock impact
   - **"Historical success rate?"** - Show phase-specific approval rates, therapeutic area benchmarks
   - **"Market cap impact?"** - Historical examples of similar trials → stock moves
   - **"What are the risks?"** - Explain trial failure scenarios, side effects, competitive drugs
   - **"Related catalysts?"** - Show other trials from same sponsor or therapeutic area

2. **Response Format**

   Each explanation includes:
   - **Plain English summary** (100-150 words, 8th grade reading level)
   - **Key data points** (bulleted facts with numbers)
   - **Visual element** (chart, timeline, or diagram where applicable)
   - **Source citation** (ClinicalTrials.gov NCT ID, FDA data, industry reports)
   - **Action suggestions** ("Consider: Add to watchlist", "Research: Check sponsor's other trials")

3. **Data Sources**

   **Phase 1: Rule-Based (Starter tier)**
   - ClinicalTrials.gov trial metadata (indication, phase, dates)
   - Historical stock price data (yfinance)
   - Hardcoded industry statistics (phase success rates, approval timelines)

   **Phase 2: AI-Enhanced (Pro tier)**
   - Claude API for natural language generation
   - Real-time FDA data scraping
   - Custom biotech knowledge base (curated articles, analyst reports)

4. **Contextual Intelligence**

   Tailor explanations based on:
   - **User's experience level** (beginner vs. advanced, inferred from behavior)
   - **Trial specifics** (Phase 2 vs. 3, oncology vs. rare disease)
   - **Market context** (recent similar trial results, sector trends)

5. **Interactive Elements**

   - **Follow-up questions**: "Want to know more about Phase 3 trials?"
   - **Related catalysts**: Show 3-5 similar trials
   - **Action buttons**: "Add to Watchlist", "Set Alert", "View Price Chart"

---

### Non-Functional Requirements

- **Performance**: <1s response for rule-based (Phase 1), <3s for AI (Phase 2)
- **Accuracy**: 95%+ factual correctness (validated by domain expert)
- **Readability**: Flesch-Kincaid grade level ≤10
- **Cost**: <$0.01/explanation for AI-powered responses
- **Mobile-friendly**: Explanations render well on 360px screens

---

## Technical Design

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     User clicks question                       │
│          "What does this trial test?" on NCT12345678           │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│                    ExplainerAgent                              │
│                                                                 │
│  1. Determine user tier (Starter vs Pro)                       │
│  2. Fetch catalyst data (NCT ID, phase, indication, etc.)      │
│  3. Route to appropriate explainer:                            │
│     - Starter: RuleBasedExplainer                              │
│     - Pro: AIEnhancedExplainer                                 │
└────────────────┬───────────────────────────────────────────────┘
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
┌─────────────────┐   ┌─────────────────┐
│ Rule-Based      │   │ AI-Enhanced     │
│ Explainer       │   │ Explainer       │
│                 │   │                 │
│ - Templates     │   │ - Claude API    │
│ - Static data   │   │ - Dynamic gen   │
└────────┬────────┘   └────────┬────────┘
         │                     │
         └──────────┬──────────┘
                    ▼
      ┌─────────────────────────┐
      │  Format response JSON   │
      │  {                      │
      │    summary: "...",      │
      │    data_points: [...],  │
      │    source: "...",       │
      │    actions: [...]       │
      │  }                      │
      └────────────┬────────────┘
                   ▼
      ┌─────────────────────────┐
      │  Render in Streamlit    │
      │  - Summary card         │
      │  - Data bullets         │
      │  - Action buttons       │
      └─────────────────────────┘
```

---

### Rule-Based Explainer (Phase 1)

**File**: `src/agent/rule_based_explainer.py`

```python
"""Rule-based explainer for catalyst questions (Starter tier)."""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class Explanation:
    """Structured explanation response."""
    summary: str
    data_points: List[str]
    source: str
    actions: List[Dict[str, str]]
    related_catalysts: List[str] = None

class RuleBasedExplainer:
    """Generate explanations using templates and static data."""

    # Industry statistics (hardcoded, updated quarterly)
    PHASE_SUCCESS_RATES = {
        '1': 0.63,
        '2': 0.31,
        '3': 0.58,
    }

    THERAPEUTIC_AREA_RATES = {
        'Oncology': 0.05,  # Very low approval rate
        'Neurology': 0.08,
        'Rare Disease': 0.24,  # Orphan drug advantage
        'Immunology': 0.15,
    }

    APPROVAL_TIMELINES = {
        '3': '12-18 months',  # Phase 3 → Approval
        '2': '18-24 months',  # Phase 2 → Approval (via Phase 3)
    }

    def explain_what_trial_tests(self, catalyst: Dict) -> Explanation:
        """Explain what the trial is testing.

        Args:
            catalyst: Catalyst data from database

        Returns:
            Explanation object
        """
        title = catalyst['title']
        phase = catalyst['phase']
        indication = self._extract_indication(title)
        sponsor = catalyst['sponsor']

        # Template-based summary
        summary = f"""
        This is a Phase {phase} clinical trial testing a new treatment for {indication}.
        {sponsor} is the sponsor, meaning they're funding and running the study.

        In Phase {phase}, researchers are {'testing if the drug works better than current treatments and is safe enough for FDA approval' if phase == '3' else 'testing if the drug works in patients and finding the right dose'}.
        """

        data_points = [
            f"Trial Phase: {phase}",
            f"Indication: {indication}",
            f"Sponsor: {sponsor}",
            f"Expected completion: {catalyst['completion_date']}",
        ]

        source = f"Source: ClinicalTrials.gov {catalyst['nct_id']}"

        actions = [
            {'label': 'View full trial details', 'type': 'link', 'url': f"https://clinicaltrials.gov/study/{catalyst['nct_id']}"},
            {'label': 'Add to watchlist', 'type': 'action', 'action': 'add_watchlist'},
        ]

        return Explanation(
            summary=summary.strip(),
            data_points=data_points,
            source=source,
            actions=actions
        )

    def explain_completion_importance(self, catalyst: Dict) -> Explanation:
        """Explain why completion date matters."""
        days_until = catalyst['days_until_completion']
        phase = catalyst['phase']

        summary = f"""
        The completion date is when the trial finishes collecting data and announces results.
        This is a major catalyst event for the stock because it reveals if the drug works.

        For biotech stocks, completion dates often trigger 20-50% price moves (up or down)
        within 1-3 days. Traders position {'weeks' if days_until > 30 else 'days'} in advance
        to capitalize on the volatility.
        """

        data_points = [
            f"Completion in {days_until} days ({catalyst['completion_date']})",
            f"Phase {phase} results typically move stocks 20-50%",
            "Data release usually happens 1-3 days after completion",
            "FDA decision timeline: " + self.APPROVAL_TIMELINES.get(phase, "N/A"),
        ]

        source = "Source: Historical biotech catalyst analysis"

        actions = [
            {'label': 'Set completion alert', 'type': 'action', 'action': 'set_alert'},
            {'label': 'View price chart', 'type': 'action', 'action': 'view_chart'},
        ]

        return Explanation(
            summary=summary.strip(),
            data_points=data_points,
            source=source,
            actions=actions
        )

    def explain_historical_success_rate(self, catalyst: Dict) -> Explanation:
        """Explain historical success rates for this type of trial."""
        phase = catalyst['phase']
        therapeutic_area = catalyst.get('therapeutic_area', 'Unknown')

        phase_rate = self.PHASE_SUCCESS_RATES.get(phase, 0.5)
        area_rate = self.THERAPEUTIC_AREA_RATES.get(therapeutic_area, 0.1)

        summary = f"""
        Based on FDA data, Phase {phase} trials succeed about {phase_rate*100:.0f}% of the time.
        However, {therapeutic_area} trials have a lower approval rate of ~{area_rate*100:.0f}%
        due to the complexity of the disease.

        This means there's roughly a {area_rate*100:.0f}% chance this drug gets approved,
        though individual trial results vary widely based on drug quality and trial design.
        """

        data_points = [
            f"Phase {phase} success rate: {phase_rate*100:.0f}%",
            f"{therapeutic_area} approval rate: {area_rate*100:.0f}%",
            "Success = meets primary endpoint",
            "Approval still requires FDA review (6-12 months)",
        ]

        source = "Source: FDA approval statistics (2015-2023)"

        return Explanation(
            summary=summary.strip(),
            data_points=data_points,
            source=source,
            actions=[]
        )

    def explain_market_cap_impact(self, catalyst: Dict) -> Explanation:
        """Explain how market cap affects stock volatility."""
        market_cap = catalyst['market_cap']
        market_cap_b = market_cap / 1e9

        if market_cap_b < 0.5:
            size = "micro-cap"
            volatility = "50-100%"
        elif market_cap_b < 2:
            size = "small-cap"
            volatility = "20-50%"
        else:
            size = "mid-cap"
            volatility = "10-30%"

        summary = f"""
        At ${market_cap_b:.2f}B market cap, this is a {size} biotech. Smaller companies
        tend to see bigger stock price swings on catalyst events.

        Historical data shows {size} biotechs move {volatility} on Phase {catalyst['phase']}
        results, compared to 5-15% for large-cap pharma. This creates both higher risk
        and higher reward potential.
        """

        data_points = [
            f"Market cap: ${market_cap_b:.2f}B ({size})",
            f"Expected volatility: {volatility}",
            f"Current price: ${catalyst['current_price']:.2f}",
            "Smaller market cap = higher volatility",
        ]

        source = "Source: Historical biotech stock analysis"

        return Explanation(
            summary=summary.strip(),
            data_points=data_points,
            source=source,
            actions=[]
        )

    def _extract_indication(self, title: str) -> str:
        """Extract disease/indication from trial title."""
        # Simple keyword matching
        keywords = {
            'cancer': 'Cancer',
            'oncology': 'Cancer',
            'tumor': 'Cancer',
            'leukemia': 'Leukemia',
            'alzheimer': "Alzheimer's Disease",
            'parkinson': "Parkinson's Disease",
            'diabetes': 'Diabetes',
            'heart': 'Cardiovascular Disease',
        }

        title_lower = title.lower()
        for keyword, indication in keywords.items():
            if keyword in title_lower:
                return indication

        return "the indicated condition"
```

---

### AI-Enhanced Explainer (Phase 2 - Pro Tier)

**File**: `src/agent/ai_enhanced_explainer.py`

```python
"""AI-enhanced explainer using Claude API (Pro tier)."""

import anthropic
from typing import Dict
from .rule_based_explainer import Explanation
from utils.config import Config

class AIEnhancedExplainer:
    """Generate explanations using Claude API."""

    def __init__(self):
        config = Config.from_env()
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def explain(self, question: str, catalyst: Dict) -> Explanation:
        """Generate AI explanation for any question.

        Args:
            question: User's question about the catalyst
            catalyst: Catalyst data from database

        Returns:
            Explanation object
        """
        # Build context from catalyst data
        context = f"""
        Trial: {catalyst['title']}
        NCT ID: {catalyst['nct_id']}
        Sponsor: {catalyst['sponsor']}
        Ticker: {catalyst['ticker']}
        Phase: {catalyst['phase']}
        Therapeutic Area: {catalyst.get('therapeutic_area', 'N/A')}
        Completion Date: {catalyst['completion_date']} ({catalyst['days_until_completion']} days)
        Market Cap: ${catalyst['market_cap'] / 1e9:.2f}B
        Current Price: ${catalyst['current_price']:.2f}
        """

        # Prompt Claude
        prompt = f"""You are an expert biotech analyst explaining clinical trials to retail traders.

User's question: {question}

Clinical trial context:
{context}

Provide a clear, concise explanation (100-150 words) at an 8th grade reading level.
Include:
1. Plain English summary
2. 3-4 key data points (bulleted)
3. Why this matters for traders
4. 1-2 action suggestions

Be factual and cite sources. Avoid medical advice."""

        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        response_text = message.content[0].text

        # Extract sections (simple parsing, improve with regex)
        summary = self._extract_summary(response_text)
        data_points = self._extract_bullets(response_text)

        return Explanation(
            summary=summary,
            data_points=data_points,
            source=f"Source: AI analysis of ClinicalTrials.gov {catalyst['nct_id']}",
            actions=[
                {'label': 'Add to watchlist', 'type': 'action', 'action': 'add_watchlist'},
            ]
        )

    def _extract_summary(self, text: str) -> str:
        """Extract summary paragraph from response."""
        # Simple: take first paragraph
        return text.split('\n\n')[0]

    def _extract_bullets(self, text: str) -> list:
        """Extract bullet points from response."""
        bullets = []
        for line in text.split('\n'):
            if line.strip().startswith('-') or line.strip().startswith('•'):
                bullets.append(line.strip().lstrip('-•').strip())
        return bullets
```

---

### UI Component

**File**: `src/ui/explainer_card.py`

```python
"""Explainer UI component."""

import streamlit as st
from typing import Dict
from agent.rule_based_explainer import RuleBasedExplainer
from agent.ai_enhanced_explainer import AIEnhancedExplainer
from utils.auth import get_user_tier

def render_explainer(catalyst: Dict):
    """Render explainer component for a catalyst.

    Args:
        catalyst: Catalyst data from database
    """
    st.markdown("### 🤔 Ask About This Catalyst")

    # Pre-written questions
    questions = [
        ("What does this trial test?", "what_trial_tests"),
        ("Why is completion important?", "completion_importance"),
        ("Historical success rate?", "success_rate"),
        ("Market cap impact?", "market_cap_impact"),
    ]

    # Show question buttons
    cols = st.columns(len(questions))
    selected_question = None

    for i, (label, key) in enumerate(questions):
        with cols[i]:
            if st.button(f"💡 {label}", key=f"q_{key}"):
                selected_question = key

    # If question selected, show explanation
    if selected_question:
        with st.spinner("Generating explanation..."):
            explanation = get_explanation(selected_question, catalyst)
            render_explanation(explanation)

def get_explanation(question_key: str, catalyst: Dict):
    """Get explanation based on user tier."""
    user_tier = get_user_tier()

    if user_tier == 'pro':
        # Use AI-enhanced explainer
        explainer = AIEnhancedExplainer()
        question_map = {
            'what_trial_tests': "What does this trial test and why does it matter?",
            'completion_importance': "Why is the completion date important for stock price?",
            'success_rate': "What's the historical success rate for this type of trial?",
            'market_cap_impact': "How does market cap affect stock volatility on catalyst events?",
        }
        return explainer.explain(question_map[question_key], catalyst)
    else:
        # Use rule-based explainer
        explainer = RuleBasedExplainer()
        method_map = {
            'what_trial_tests': explainer.explain_what_trial_tests,
            'completion_importance': explainer.explain_completion_importance,
            'success_rate': explainer.explain_historical_success_rate,
            'market_cap_impact': explainer.explain_market_cap_impact,
        }
        return method_map[question_key](catalyst)

def render_explanation(explanation):
    """Render explanation card."""
    with st.container(border=True):
        # Summary
        st.markdown(explanation.summary)

        # Data points
        if explanation.data_points:
            st.markdown("**Key Facts:**")
            for point in explanation.data_points:
                st.markdown(f"- {point}")

        # Source
        st.caption(explanation.source)

        # Actions
        if explanation.actions:
            st.markdown("---")
            cols = st.columns(len(explanation.actions))
            for i, action in enumerate(explanation.actions):
                with cols[i]:
                    if action['type'] == 'link':
                        st.link_button(action['label'], action['url'])
                    elif action['type'] == 'action':
                        if st.button(action['label'], key=f"action_{i}"):
                            handle_action(action['action'])

def handle_action(action: str):
    """Handle action button clicks."""
    if action == 'add_watchlist':
        st.success("Added to watchlist!")
    elif action == 'set_alert':
        st.info("Alert set for 7 days before completion")
    elif action == 'view_chart':
        st.session_state.show_chart = True
```

---

## Testing Plan

### Content Validation

1. **Accuracy testing**:
   - [ ] Review 50 generated explanations with domain expert
   - [ ] Verify all statistics are current (FDA approval rates, timelines)
   - [ ] Check citations are correct (NCT IDs, sources)

2. **Readability testing**:
   - [ ] Run explanations through Flesch-Kincaid analyzer
   - [ ] Target: Grade level ≤10
   - [ ] User testing with 10 non-biotech traders

3. **AI quality testing** (Phase 2):
   - [ ] Compare AI vs. rule-based explanations for accuracy
   - [ ] Measure user preference (A/B test)
   - [ ] Monitor Claude API costs per explanation

### Integration Tests

1. **Response time**:
   - [ ] Rule-based: <1s for 95% of queries
   - [ ] AI-enhanced: <3s for 95% of queries

2. **Error handling**:
   - [ ] Missing catalyst data → Show graceful fallback
   - [ ] API timeout → Fall back to rule-based

---

## Success Criteria

- [ ] 90%+ user satisfaction (in-app survey: "Was this helpful?")
- [ ] <1s response time for rule-based explanations
- [ ] 95%+ factual accuracy (validated by expert review)
- [ ] 50%+ users interact with explainer in first session
- [ ] 3x increase in avg. time on catalyst detail page
- [ ] Readability: Flesch-Kincaid grade level ≤10

---

## Implementation Phases

### Phase 1: Rule-Based (Week 1-2)
- [ ] Build RuleBasedExplainer class
- [ ] Implement 4 question templates
- [ ] Create UI component
- [ ] Accuracy validation (domain expert)

**Success Metric**: Can answer 4 common questions with <1s response time

### Phase 2: AI-Enhanced (Week 3-4)
- [ ] Integrate Claude API
- [ ] Build AIEnhancedExplainer
- [ ] Tier gating (Pro only)
- [ ] Cost monitoring

**Success Metric**: AI explanations score 4.5/5 in user satisfaction

### Phase 3: Expansion (Week 5+)
- [ ] Add 4 more question templates
- [ ] Related catalysts recommendation
- [ ] Visual enhancements (charts, timelines)
- [ ] Multi-language support (Spanish, Chinese)

**Success Metric**: 70%+ users interact with explainer

### Future Enhancements
- [ ] Custom question input (free-form)
- [ ] Voice output (text-to-speech)
- [ ] Video explanations (AI-generated)
- [ ] Explainer chatbot (multi-turn conversation)

---

## Cost Analysis

### Development Cost
- **Engineering**: 2 weeks × 1 developer = $4,000
- **Content validation**: Domain expert 20 hours × $150/hr = $3,000
- **Design**: 15 hours × $75/hr = $1,125
- **Total**: $8,125

### Operational Cost

**Phase 1 (Rule-Based)**:
- **Compute**: Negligible (Python templates)
- **Storage**: $0
- **Total**: **$0/mo**

**Phase 2 (AI-Enhanced, Pro tier)**:
- **Claude API**: 1,000 explanations/mo × $0.01 = $10/mo
- **Monitoring**: $5/mo
- **Total**: **$15/mo** = **$0.015/explanation**

### ROI Calculation
- **Engagement increase**: 3x time on page = 30% conversion lift
- **Revenue impact**: 53 subscribers × 30% × $29/mo = +$460/mo
- **Payback period**: 0.4 months

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Inaccurate explanations | High | Low | Expert review + fact-checking |
| High AI costs | Medium | Medium | Tier gating + caching common questions |
| User confusion | Medium | Low | Clear language + user testing |
| Liability (medical advice) | High | Low | Disclaimers + focus on trading, not medical |

---

## Compliance & Disclaimers

**Required Disclaimer** (shown with all explanations):
> "This information is for educational purposes only and does not constitute medical or investment advice. Always consult a healthcare professional for medical decisions and a financial advisor for investment decisions."

---

## References

- [Claude API Documentation](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [FDA Approval Statistics](https://www.fda.gov/drugs/development-approval-process-drugs/drug-approval-statistics)
- [Flesch-Kincaid Readability](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests)

---

## Implementation Status

**Status**: 🔜 **PLANNED**
**Planned Start**: Week 5
**Estimated Completion**: Week 7
**Priority**: Medium (Engagement feature)

---

**Last Updated**: 2025-12-24
**Owner**: Product Team
**Stakeholders**: Engineering, Content, Compliance
