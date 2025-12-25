# Feature Spec: Chat Agent for Catalyst Discovery

## Overview

Implement a conversational chat interface that allows users to discover catalysts using natural language queries instead of manual filtering. The agent parses intent, executes structured queries, and presents results in an interactive, conversational format.

**Strategic Value**:
- Reduces time-to-insight from minutes to seconds
- Lowers learning curve for new users
- Differentiates from spreadsheet-style competitors
- Enables mobile-friendly interaction

**Target Metrics**:
- 80%+ successful query resolution rate
- <500ms average response time
- 30%+ increase in user engagement (queries per session)

---

## User Stories

### As a retail trader
- **I want to** ask "Show me Phase 3 oncology trials under $2B"
- **So that** I can find opportunities without learning complex filters
- **Acceptance**: Agent returns matching catalysts in <1 second with clear formatting

### As a day trader
- **I want to** ask "What catalysts are completing this month?"
- **So that** I can plan my trades around upcoming data releases
- **Acceptance**: Agent shows trials grouped by completion date with countdown

### As a new user
- **I want to** see example queries when I open the chat
- **So that** I understand what questions I can ask
- **Acceptance**: Chat shows 4-5 pre-written query suggestions on load

### As a mobile user
- **I want to** interact via chat instead of filtering tables
- **So that** I can research on my phone during commute
- **Acceptance**: Chat UI is fully responsive and works on mobile screens

---

## Requirements

### Functional Requirements

1. **Natural Language Understanding**
   - Parse user queries for intent and parameters
   - Extract filters: therapeutic_area, market_cap, phase, completion_days, sponsor
   - Handle variations: "oncology" = "cancer" = "tumor"
   - Support compound queries: "Phase 3 oncology under $2B in next 60 days"

2. **Query Execution**
   - Convert parsed intent to SQL query parameters
   - Execute against catalysts table
   - Apply user's subscription tier limits (10 rows for preview, unlimited for paid)
   - Return structured results with metadata

3. **Response Generation**
   - Format results as catalyst cards in chat
   - Include summary statistics (e.g., "Found 7 catalysts matching your criteria")
   - Provide action buttons: "View Details", "Add to Watchlist", "Refine Search"
   - Handle edge cases: no results, ambiguous query, too broad query

4. **Conversation History**
   - Maintain session-level chat history
   - Allow follow-up queries: "Show me only those under $1B"
   - Clear history button for privacy

5. **Example Queries**
   - Show 5 pre-written queries on chat load:
     - "Phase 3 trials completing in next 30 days"
     - "Oncology catalysts under $2B market cap"
     - "All trials from Amgen or Pfizer"
     - "Phase 2 with completion dates in Q1 2026"
     - "Small caps under $500M with upcoming data"

---

### Non-Functional Requirements

- **Performance**: Response time <500ms for 90th percentile
- **Accuracy**: 80%+ successful query parsing rate
- **Scalability**: Handle 1000 queries/day without degradation
- **UX**: Conversational, friendly tone; no error codes exposed to user
- **Mobile**: Fully responsive chat UI (works on 360px screens)

---

## Technical Design

### Architecture

```
┌──────────────────┐
│  Streamlit UI    │
│  (Chat Input)    │
└────────┬─────────┘
         │
         │ User query: "Phase 3 oncology under $2B"
         ▼
┌──────────────────┐
│  ChatAgent       │
│  parse_query()   │◄─── Keyword matching rules
└────────┬─────────┘
         │
         │ Parsed: {phase: "3", therapeutic_area: "oncology",
         │          market_cap_max: 2000000000}
         ▼
┌──────────────────┐
│  CatalystQuery   │
│  execute()       │◄─── SQL generator
└────────┬─────────┘
         │
         │ DataFrame with results
         ▼
┌──────────────────┐
│  ResponseFormatter│
│  format_results()│◄─── Template-based responses
└────────┬─────────┘
         │
         │ Structured response JSON
         ▼
┌──────────────────┐
│  Streamlit UI    │
│  (Chat Output)   │◄─── Render cards, buttons
└──────────────────┘
```

---

### Query Parsing Rules

**File**: `src/agent/query_parser.py`

```python
"""Natural language query parser for chat agent."""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ParsedQuery:
    """Structured query parameters."""
    phase: Optional[List[str]] = None  # ["2", "3"]
    therapeutic_area: Optional[List[str]] = None
    market_cap_max: Optional[float] = None
    market_cap_min: Optional[float] = None
    completion_days_min: Optional[int] = None
    completion_days_max: Optional[int] = None
    sponsor: Optional[List[str]] = None
    raw_query: str = ""

class QueryParser:
    """Parse natural language queries into structured filters."""

    # Keyword mappings
    PHASE_PATTERNS = {
        r'\bphase\s*3\b': '3',
        r'\bphase\s*III\b': '3',
        r'\bphase\s*2\b': '2',
        r'\bphase\s*II\b': '2',
        r'\bp3\b': '3',
        r'\bp2\b': '2',
    }

    THERAPEUTIC_AREA_ALIASES = {
        'oncology': ['oncology', 'cancer', 'tumor', 'carcinoma', 'leukemia', 'lymphoma'],
        'neurology': ['neurology', 'alzheimer', 'parkinson', 'dementia', 'brain'],
        'immunology': ['immunology', 'autoimmune', 'immune', 'inflammation'],
        'cardiology': ['cardiology', 'cardiovascular', 'heart', 'cardiac'],
        'diabetes': ['diabetes', 'diabetic', 'glucose', 'insulin'],
        'rare': ['rare disease', 'orphan', 'rare'],
    }

    MARKET_CAP_PATTERNS = {
        r'\bunder\s+\$?(\d+\.?\d*)\s*b(illion)?\b': lambda m: ('max', float(m.group(1)) * 1e9),
        r'\babove\s+\$?(\d+\.?\d*)\s*b(illion)?\b': lambda m: ('min', float(m.group(1)) * 1e9),
        r'\bunder\s+\$?(\d+)\s*m(illion)?\b': lambda m: ('max', float(m.group(1)) * 1e6),
        r'\babove\s+\$?(\d+)\s*m(illion)?\b': lambda m: ('min', float(m.group(1)) * 1e6),
        r'\bsmall\s+caps?\b': lambda m: ('max', 2e9),
        r'\bmicro\s+caps?\b': lambda m: ('max', 300e6),
    }

    COMPLETION_PATTERNS = {
        r'\bnext\s+(\d+)\s+days?\b': lambda m: ('max', int(m.group(1))),
        r'\bwithin\s+(\d+)\s+days?\b': lambda m: ('max', int(m.group(1))),
        r'\bthis\s+month\b': lambda m: ('max', 30),
        r'\bthis\s+quarter\b': lambda m: ('max', 90),
        r'\bnext\s+(\d+)\s+months?\b': lambda m: ('max', int(m.group(1)) * 30),
        r'\bQ1\s+2026\b': lambda m: ('range', (30, 120)),  # Custom handler
    }

    def parse(self, query: str) -> ParsedQuery:
        """Parse natural language query.

        Args:
            query: User's natural language query

        Returns:
            ParsedQuery with extracted filters
        """
        query_lower = query.lower()
        parsed = ParsedQuery(raw_query=query)

        # Parse phase
        parsed.phase = self._parse_phase(query_lower)

        # Parse therapeutic area
        parsed.therapeutic_area = self._parse_therapeutic_area(query_lower)

        # Parse market cap
        market_cap = self._parse_market_cap(query_lower)
        if market_cap:
            if market_cap[0] == 'max':
                parsed.market_cap_max = market_cap[1]
            elif market_cap[0] == 'min':
                parsed.market_cap_min = market_cap[1]

        # Parse completion timeframe
        completion = self._parse_completion(query_lower)
        if completion:
            if completion[0] == 'max':
                parsed.completion_days_max = completion[1]
            elif completion[0] == 'min':
                parsed.completion_days_min = completion[1]

        # Parse sponsor
        parsed.sponsor = self._parse_sponsor(query)

        return parsed

    def _parse_phase(self, query: str) -> Optional[List[str]]:
        """Extract phase from query."""
        phases = []
        for pattern, phase in self.PHASE_PATTERNS.items():
            if re.search(pattern, query, re.IGNORECASE):
                if phase not in phases:
                    phases.append(phase)
        return phases if phases else None

    def _parse_therapeutic_area(self, query: str) -> Optional[List[str]]:
        """Extract therapeutic area from query."""
        for canonical, aliases in self.THERAPEUTIC_AREA_ALIASES.items():
            for alias in aliases:
                if alias in query:
                    return [canonical]
        return None

    def _parse_market_cap(self, query: str) -> Optional[tuple]:
        """Extract market cap filter."""
        for pattern, handler in self.MARKET_CAP_PATTERNS.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return handler(match)
        return None

    def _parse_completion(self, query: str) -> Optional[tuple]:
        """Extract completion timeframe."""
        for pattern, handler in self.COMPLETION_PATTERNS.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return handler(match)
        return None

    def _parse_sponsor(self, query: str) -> Optional[List[str]]:
        """Extract sponsor names."""
        # Look for common pharma names
        pharma_names = [
            'Pfizer', 'Moderna', 'Amgen', 'Gilead', 'Biogen',
            'Regeneron', 'Vertex', 'BioNTech', 'Novavax'
        ]
        found = []
        for name in pharma_names:
            if name.lower() in query.lower():
                found.append(name)
        return found if found else None
```

---

### Response Format

**Structured JSON Response**:
```json
{
  "type": "catalyst_results",
  "message": "Found 7 Phase 3 oncology catalysts under $2B market cap",
  "summary": {
    "total_results": 7,
    "filters_applied": ["phase=3", "therapeutic_area=oncology", "market_cap<$2B"]
  },
  "data": [
    {
      "nct_id": "NCT12345678",
      "title": "Phase 3 Study of Drug X in Lung Cancer",
      "sponsor": "SmallBio Inc.",
      "ticker": "SBIO",
      "phase": "3",
      "therapeutic_area": "Oncology",
      "completion_date": "2026-03-15",
      "days_until": 82,
      "market_cap": 1200000000,
      "current_price": 15.32
    }
    // ... more results
  ],
  "actions": [
    {
      "label": "Refine to under $1B",
      "type": "refine_query",
      "query": "Phase 3 oncology under $1B"
    },
    {
      "label": "Show only next 30 days",
      "type": "refine_query",
      "query": "Phase 3 oncology under $2B in next 30 days"
    },
    {
      "label": "Export to CSV",
      "type": "export",
      "format": "csv"
    }
  ],
  "suggestions": [
    "Try: 'Show me Phase 2 trials from these sponsors'",
    "Or: 'Filter to only trials completing this quarter'"
  ]
}
```

---

### UI Components

**File**: `src/ui/chat_interface.py`

```python
"""Chat interface for catalyst discovery."""

import streamlit as st
from typing import List, Dict
from agent.query_parser import QueryParser, ParsedQuery
from agent.catalyst_query import CatalystQueryEngine
from agent.response_formatter import ResponseFormatter

class ChatInterface:
    """Conversational chat interface."""

    EXAMPLE_QUERIES = [
        "Phase 3 trials completing in next 30 days",
        "Oncology catalysts under $2B market cap",
        "All trials from Amgen or Pfizer",
        "Phase 2 with completion dates in Q1 2026",
        "Small caps under $500M with upcoming data",
    ]

    def __init__(self):
        self.parser = QueryParser()
        self.query_engine = CatalystQueryEngine()
        self.formatter = ResponseFormatter()

        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

    def render(self):
        """Render chat interface."""
        st.markdown("### 💬 Ask About Catalysts")

        # Show example queries
        if not st.session_state.chat_history:
            st.markdown("**Try asking:**")
            cols = st.columns(len(self.EXAMPLE_QUERIES))
            for i, query in enumerate(self.EXAMPLE_QUERIES):
                with cols[i % len(cols)]:
                    if st.button(f"💡 {query[:30]}...", key=f"example_{i}"):
                        self._handle_query(query)

        # Chat history
        for msg in st.session_state.chat_history:
            self._render_message(msg)

        # Chat input
        user_query = st.chat_input("Ask about catalysts...")
        if user_query:
            self._handle_query(user_query)

    def _handle_query(self, query: str):
        """Process user query and show response."""
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': query
        })

        # Parse query
        parsed = self.parser.parse(query)

        # Execute query
        results = self.query_engine.execute(parsed)

        # Format response
        response = self.formatter.format(query, parsed, results)

        # Add assistant response to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response
        })

        # Trigger rerun to show new messages
        st.rerun()

    def _render_message(self, message: Dict):
        """Render a single chat message."""
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.markdown(message['content'])
        else:
            with st.chat_message("assistant"):
                response = message['content']

                # Show summary
                st.markdown(f"**{response['message']}**")

                # Show catalyst cards
                if response['data']:
                    for catalyst in response['data'][:5]:  # Show top 5
                        self._render_catalyst_card(catalyst)

                    if len(response['data']) > 5:
                        st.info(f"+ {len(response['data']) - 5} more results")

                # Show action buttons
                if response.get('actions'):
                    cols = st.columns(len(response['actions']))
                    for i, action in enumerate(response['actions']):
                        with cols[i]:
                            if st.button(action['label'], key=f"action_{i}"):
                                if action['type'] == 'refine_query':
                                    self._handle_query(action['query'])

    def _render_catalyst_card(self, catalyst: Dict):
        """Render a catalyst result card."""
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{catalyst['ticker']}** - {catalyst['sponsor']}")
                st.caption(catalyst['title'][:100] + "...")
                st.markdown(f"📅 {catalyst['completion_date']} ({catalyst['days_until']} days)")

            with col2:
                st.metric(
                    "Market Cap",
                    f"${catalyst['market_cap'] / 1e9:.2f}B"
                )
                st.metric(
                    "Price",
                    f"${catalyst['current_price']:.2f}"
                )

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📊 View Chart", key=f"chart_{catalyst['nct_id']}"):
                    st.session_state.selected_catalyst = catalyst['nct_id']
            with col2:
                if st.button("⭐ Watchlist", key=f"watch_{catalyst['nct_id']}"):
                    st.success("Added to watchlist!")
```

---

### Database Schema

No new tables required. Agent queries existing `catalysts` table:

```sql
-- Existing table (from architecture spec)
CREATE TABLE catalysts (
    nct_id VARCHAR(20) PRIMARY KEY,
    title TEXT NOT NULL,
    sponsor VARCHAR(255),
    ticker VARCHAR(10),
    phase VARCHAR(10),
    therapeutic_area VARCHAR(100),
    completion_date DATE,
    days_until_completion INTEGER,
    market_cap BIGINT,
    current_price DECIMAL(10, 2),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Index for fast filtering
CREATE INDEX idx_catalysts_filters
ON catalysts(phase, therapeutic_area, market_cap, days_until_completion);
```

---

## Testing Plan

### Unit Tests

```python
# tests/test_query_parser.py

from agent.query_parser import QueryParser

def test_parse_phase_3_oncology():
    parser = QueryParser()
    query = "Show me Phase 3 oncology trials under $2B"
    parsed = parser.parse(query)

    assert parsed.phase == ['3']
    assert parsed.therapeutic_area == ['oncology']
    assert parsed.market_cap_max == 2e9

def test_parse_completion_timeframe():
    parser = QueryParser()
    query = "Catalysts completing in next 30 days"
    parsed = parser.parse(query)

    assert parsed.completion_days_max == 30

def test_parse_compound_query():
    parser = QueryParser()
    query = "Phase 3 oncology under $2B in next 60 days from Pfizer"
    parsed = parser.parse(query)

    assert parsed.phase == ['3']
    assert parsed.therapeutic_area == ['oncology']
    assert parsed.market_cap_max == 2e9
    assert parsed.completion_days_max == 60
    assert 'Pfizer' in parsed.sponsor

def test_parse_ambiguous_query():
    parser = QueryParser()
    query = "Show me some trials"
    parsed = parser.parse(query)

    # Should return empty filters
    assert parsed.phase is None
    assert parsed.therapeutic_area is None
```

### Integration Tests

1. **Query → Results flow**:
   - [ ] User enters query → Parser extracts filters → Query executes → Results returned
   - [ ] Verify response time <500ms
   - [ ] Verify results match filters

2. **Edge cases**:
   - [ ] No results found → Show helpful message
   - [ ] Ambiguous query → Ask clarifying question
   - [ ] Too many results (>100) → Suggest refinement

3. **Mobile testing**:
   - [ ] Chat UI renders on 360px screen
   - [ ] Example query buttons are tappable
   - [ ] Catalyst cards are readable

---

## Success Criteria

- [ ] 80%+ query parsing success rate (measured on 100 test queries)
- [ ] <500ms response time for 90th percentile
- [ ] 30%+ increase in queries per session vs. manual filtering
- [ ] 90%+ user satisfaction (in-app survey after 10 queries)
- [ ] Zero crashes or error pages over 7 days
- [ ] Mobile-friendly (works on 360px screens)

---

## Implementation Phases

### Phase 1: MVP (Week 1-2)
- [ ] Build QueryParser with keyword matching
- [ ] Implement CatalystQueryEngine
- [ ] Create basic chat UI (text input + output)
- [ ] Add 5 example queries
- [ ] Unit tests

**Success Metric**: Can handle 5 common query patterns with 80% accuracy

### Phase 2: Enhanced UX (Week 3)
- [ ] Add catalyst result cards
- [ ] Implement action buttons (refine, export)
- [ ] Add conversation history
- [ ] Mobile responsive design

**Success Metric**: <500ms response time, mobile-friendly

### Phase 3: Intelligence (Week 4+)
- [ ] Add fuzzy matching for therapeutic areas
- [ ] Implement "no results" suggestions
- [ ] Add follow-up query context
- [ ] A/B test query suggestions

**Success Metric**: 90%+ query success rate

### Future Enhancements
- [ ] Multi-turn conversations with context
- [ ] Voice input (speech-to-text)
- [ ] Integration with Claude API for complex queries (Pro tier)
- [ ] Saved query templates

---

## Cost Analysis

### Development Cost
- **Engineering**: 2 weeks × 1 developer = $4,000
- **Design**: 20 hours × $75/hr = $1,500
- **Testing**: 40 hours × $50/hr = $2,000
- **Total**: $7,500

### Operational Cost
- **Compute**: Negligible (Python string parsing)
- **API Calls**: $0 (no LLM in Phase 1)
- **Storage**: $0 (chat history in session state)

### ROI Calculation
- **Benefit**: 30% increase in engagement = 15% conversion lift
- **Revenue Impact**: 53 subscribers × 15% × $29/mo = +$230/mo = $2,760/year
- **Payback Period**: 3.3 months

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Query parsing failures | High | Medium | Extensive testing + fallback to manual filter |
| <80% accuracy | High | Low | Iterate on keyword patterns, add fuzzy matching |
| Slow response time | Medium | Low | Cache common queries, optimize SQL indexes |
| User confusion | Medium | Medium | Clear example queries + "I don't understand" messages |
| Mobile UX issues | Low | Medium | Responsive design testing on real devices |

---

## References

- [Streamlit Chat Elements](https://docs.streamlit.io/library/api-reference/chat)
- [Natural Language Query Parsing Patterns](https://www.elastic.co/blog/text-search)
- Competitor analysis: BioPharmCatalyst has filtering but no chat interface

---

## Implementation Status

**Status**: 🔜 **PLANNED**
**Planned Start**: Week 5
**Estimated Completion**: Week 7
**Priority**: High (Differentiation feature)

---

**Last Updated**: 2025-12-24
**Owner**: Product Team
**Stakeholders**: Engineering, Design, Marketing
