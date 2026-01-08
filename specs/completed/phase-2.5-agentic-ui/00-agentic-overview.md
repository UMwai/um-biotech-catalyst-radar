# Agentic UI Overview - Strategic Implementation

> **Mission**: Build the first biotech catalyst tracker with conversational AI to eliminate learning curves and enable proactive discovery

## Executive Summary

**What**: Conversational AI interface for biotech catalyst discovery
**Why**: Lower barrier to entry, better discovery, proactive assistance
**How**: Rule-based agents (Phase 1), LLM-powered agents (Phase 2), Multi-agent orchestration (Phase 3)
**When**: Phase 2.5 (Week 5-6)
**Cost**: $0/month (rule-based), $0.01-0.05/query (LLM, future)

---

## Why Agentic UI Matters

### Problem: Traditional Tools Have High Learning Curves

**BioPharmCatalyst** (and most data tools):
- 15+ dropdown filters
- Complex multi-step queries
- No guidance on what to search for
- Static interface (you drive everything)
- 30+ minute learning curve

**Impact**:
- High bounce rate (users get overwhelmed)
- Low engagement (too much friction)
- Missed opportunities (users don't know what to look for)

### Solution: Conversational AI + Proactive Agents

**Our Approach**:
- Natural language queries: "Show me oncology trials under $2B"
- AI suggests catalysts you might have missed
- Agent monitors saved searches 24/7
- Every trial explained in plain English
- 30-second learning curve (read 3 example queries)

**Impact**:
- Lower barrier to entry → more signups
- Better discovery → more value
- Proactive monitoring → stickier product
- Educational → builds trust

---

## The 3 Agent Types

### 1. Chat Agent (Discovery)

**Purpose**: Conversational search interface

**User experience**:
```
User: "Show me oncology trials under $2B completing next 60 days"

Agent: Found 12 oncology trials matching your criteria:

[Card 1]
$EXBT - Phase 3 Non-Small Cell Lung Cancer
Market cap: $1.8B
Completion: March 15, 2025 (42 days)
Explanation: Testing new EGFR inhibitor with 450 patients.
Similar trials showed 30-50% stock run-up 2-4 weeks before data.
[Save] [Alert] [Details]

[Card 2]
...
```

**How it works** (Phase 1 - Rule-based):
1. Parse query for keywords: "oncology", "under $2B", "60 days"
2. Map to database filters:
   - `indication LIKE '%oncology%'`
   - `market_cap < 2000000000`
   - `completion_date BETWEEN NOW() AND NOW() + INTERVAL 60 DAY`
3. Execute query
4. Format results with AI explanations (template-based)
5. Return cards with action buttons

**Keyword mapping**:
- "oncology" / "cancer" → `indication LIKE '%oncology%' OR indication LIKE '%cancer%'`
- "under $XB" → `market_cap < X * 1000000000`
- "next X days" → `completion_date BETWEEN NOW() AND NOW() + INTERVAL X DAY`
- "Phase 2" / "Phase 3" → `phase IN ('Phase 2', 'Phase 3')`
- "small cap" → `market_cap < 2000000000`

**Example queries** (pre-written for users):
- "Show me Phase 3 trials in next 30 days"
- "Find oncology trials under $2B"
- "What's completing this quarter?"
- "Trials like the one I saved last week"
- "Show me everything in rare disease"

**Success metrics**:
- 80%+ queries successfully answered
- <500ms response time
- 90%+ user satisfaction

---

### 2. Alert Agent (Monitoring)

**Purpose**: Proactive monitoring of saved searches (Pro tier feature)

**User experience**:
```
User saves search: "Oncology trials under $2B"

Agent monitors database every 6 hours.

When new match appears:
→ Email: "New match for your saved search: $BIOTECH Phase 3 oncology trial"
→ SMS (Pro): "🧬 New catalyst: $BIOTECH oncology P3 - $1.5B cap - 45 days out"
→ Slack (Pro): [Card with full details]
```

**How it works** (Phase 1 - Rule-based):
1. User creates saved search (stores query parameters)
2. Cron job runs every 6 hours
3. Re-execute saved search queries
4. Compare results to last run (find new matches)
5. Send notifications via configured channels
6. Update "last checked" timestamp

**Pro tier differentiation**:
- **Free/Starter**: Email alerts only, 3 saved searches max
- **Pro**: SMS + Slack + Email, unlimited saved searches

**Success metrics**:
- 50%+ of Pro users create saved searches
- <5 minute alert latency (from database update to notification)
- <1% false positive rate (duplicate alerts)

---

### 3. Explainer Agent (Education)

**Purpose**: AI-generated explanations for every trial (plain English)

**User experience**:
```
Raw data:
NCT05123456 - Phase 3 - NSCLC - EGFR+ - 450 pts - 2025-03-15

AI explanation:
"This company is testing a new lung cancer drug for patients with
a specific gene mutation (EGFR+). They've enrolled 450 patients
in a Phase 3 trial, which is the final stage before FDA approval.

Results are expected March 15, 2025 (42 days from now).

Why it matters:
- Market cap: $1.8B (small enough for big moves)
- Historical pattern: Similar trials showed 30-50% run-up 2-4 weeks before data
- High risk/reward: If successful, could see FDA approval by Q4 2025

Risks: Phase 3 trials have ~50-60% success rate for oncology"
```

**How it works** (Phase 1 - Template-based):
1. Fetch trial metadata (phase, indication, enrollment, date)
2. Fetch company data (ticker, market cap, price)
3. Look up historical patterns for similar trials
4. Fill template with personalized data
5. Return formatted explanation

**Template structure**:
```python
template = """
{company_name} is testing a new {indication} drug {target_info}.
They've enrolled {enrollment} patients in a {phase} trial.

Results expected: {completion_date} ({days_until} days from now)

Why it matters:
- Market cap: {market_cap_formatted} ({size_category})
- Historical pattern: {historical_runup}
- Risk/reward: {risk_assessment}

Risks: {phase} trials have ~{success_rate}% success rate for {indication_category}
"""
```

**Phase 2 upgrade** (LLM-powered, optional):
- Use Claude API to generate dynamic explanations
- Cost: $0.01-0.05 per explanation
- Only for Pro tier (to justify cost)
- Fallback to templates if API fails

**Success metrics**:
- 90%+ user satisfaction with explanations
- <100ms generation time (templates)
- <2s generation time (LLM, Phase 2)

---

## Implementation Phases

### Phase 1: Rule-Based Agents (Current - Week 5-6)

**Scope**: Keyword matching + templates

**Components**:
1. Chat Agent: Keyword parser → SQL query → Template formatter
2. Alert Agent: Cron job + saved search executor + Email sender
3. Explainer Agent: Template engine + historical data lookup

**Files to create**:
- `src/agents/chat_agent.py` (250 lines)
- `src/agents/alert_agent.py` (200 lines)
- `src/agents/explainer_agent.py` (150 lines)
- `src/ui/chat_interface.py` (300 lines)
- `specs/features/07-chat-agent.md` (documentation)
- `specs/features/08-alert-agent.md` (documentation)
- `specs/features/09-trial-explainer.md` (documentation)

**Infrastructure**:
- No new services needed
- Supabase for storage (saved searches table)
- SendGrid for emails (existing)
- Cron via Supabase Edge Functions

**Cost**: $0/month

**Timeline**: 1 week (40 hours)
- Day 1-2: Chat agent backend + keyword parser
- Day 3: Chat UI + example queries
- Day 4: Alert agent + cron job
- Day 5: Explainer templates + historical data
- Day 6-7: Testing + documentation

---

### Phase 2: LLM-Powered Agents (Future - Month 4-6)

**Scope**: Claude API for Pro tier

**Upgrades**:
1. Chat Agent: Natural language understanding (not just keywords)
2. Alert Agent: Smart summaries (weekly digest with insights)
3. Explainer Agent: Dynamic explanations (personalized to user's portfolio)

**Example**:
```
User: "Show me trials similar to the EXBT one I saved, but in different indications"

Phase 1 (rule-based): [Error - too complex]
Phase 2 (LLM): [Understands context, fetches EXBT trial, finds similar patterns]
```

**Cost**: $0.01-0.05 per query
- 1,000 queries/month = $10-50/month
- Pro tier only ($39/month) to cover costs
- Free tier stays rule-based (no LLM costs)

**API**: Anthropic Claude API (claude-3-haiku-20240307)
- Fast: <1s response time
- Cheap: $0.25 / 1M input tokens
- Reliable: 99.9% uptime

**Timeline**: 2 weeks (80 hours)

---

### Phase 3: Multi-Agent Orchestration (Future - Month 6+)

**Scope**: Agents collaborate on complex tasks

**Example**:
```
User: "Find me the best catalyst opportunity this month"

Agent 1 (Research): Analyze all trials → Rank by potential
Agent 2 (Risk): Calculate risk scores → Filter by risk tolerance
Agent 3 (Portfolio): Compare to user's holdings → Avoid duplicates
Agent 4 (Presenter): Synthesize results → Present top 3 with rationale

Result: "Here are your top 3 catalyst opportunities this month:
1. $TICKER - Highest upside potential (60% projected run-up)
2. $TICKER - Lowest risk (90% historical success rate)
3. $TICKER - Best timing (optimal entry window: next 7 days)"
```

**Cost**: $0.10-0.50 per complex query
- Pro tier only
- Limited to 50 queries/month per user

**Timeline**: 4+ weeks

---

## Architecture Diagram

### Phase 1 (Rule-Based)

```
User Query
    ↓
[Chat UI Component]
    ↓
[Keyword Parser]
    ↓
    ├─ Extract keywords: "oncology", "$2B", "60 days"
    ├─ Map to SQL filters
    └─ Build structured query
    ↓
[Database Query Executor]
    ↓
[Results Fetcher]
    ↓
[Template Formatter]
    ↓
    ├─ Generate AI explanations (templates)
    ├─ Add historical context
    └─ Create action buttons (Save, Alert)
    ↓
[Response Renderer]
    ↓
[UI Cards + Actions]
```

### Phase 2 (LLM-Enhanced)

```
User Query
    ↓
[Chat UI Component]
    ↓
[Intent Classifier]
    ↓
    ├─ Simple query → Keyword Parser (Phase 1)
    └─ Complex query → Claude API
           ↓
      [Claude API]
           ↓
      [Query Planner]
           ↓
      [Database Query Executor]
           ↓
      [Claude API] (explanation generation)
           ↓
      [Response Renderer]
```

---

## Success Metrics & KPIs

### User Engagement

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Agent queries per user** | 10/month | Track query events |
| **Saved searches created** | 50% of Pro users | Database count |
| **Alert engagement** | 40% click-through | Email/SMS analytics |
| **Query success rate** | 80%+ | Manual review + feedback |
| **Response time** | <500ms | Server-side timing |

### Product Metrics

| Metric | Phase 1 (Rule-based) | Phase 2 (LLM) |
|--------|---------------------|---------------|
| **Query accuracy** | 80%+ | 95%+ |
| **Response time** | <500ms | <2s |
| **Infrastructure cost** | $0/month | $10-50/month |
| **User satisfaction** | 85%+ | 95%+ |

### Business Impact

| Metric | Month 1 | Month 2 | Month 3 |
|--------|---------|---------|---------|
| **Agent queries** | 100 | 500 | 2,000 |
| **Saved searches** | 5 | 25 | 100 |
| **Pro tier conversions** | 1 | 5 | 15 |
| **"Agent features" in reviews** | 2 | 5 | 10+ |

---

## Cost Analysis

### Phase 1: Rule-Based (Current)

**Infrastructure**: $0/month
- Keyword parsing: CPU-only (negligible)
- Template generation: CPU-only (negligible)
- Database queries: Supabase free tier
- Cron jobs: Supabase Edge Functions (free tier)

**Scalability**:
- 10,000 queries/day: $0/month
- 100,000 queries/day: $0/month
- 1M queries/day: ~$50/month (Supabase upgrade)

**Margin**: 100% (no variable costs)

---

### Phase 2: LLM-Powered (Future)

**Infrastructure**: $10-50/month (Pro tier only)

**Cost per query**:
- Claude API (Haiku): $0.01-0.05
- Average query: 500 input tokens + 200 output tokens
- Cost: ~$0.02 per query

**Revenue**:
- Pro tier: $39/month
- Expected queries: 50/month per user
- Total cost: $1/month per user
- **Margin**: 97% ($38 profit per user)

**Scalability**:
- 100 Pro users × 50 queries = $100/month API cost
- Revenue: $3,900/month
- **Net margin**: $3,800/month (97%)

**Fallback strategy**:
- If API costs spike → rate limit to 50 queries/month
- If API fails → fallback to Phase 1 templates
- If user exceeds quota → offer add-on ($10 for 100 queries)

---

## Competitive Advantage

### Why BioPharmCatalyst Can't Copy This

1. **Technical debt**: Legacy filter UI, can't easily add chat
2. **Cost structure**: Enterprise pricing can't justify $0 LLM costs
3. **User expectations**: Enterprise users expect complex filters
4. **Organization**: Manual curation team (not agent-friendly)

### Our Moat

1. **First-mover**: Only biotech tracker with conversational AI
2. **Cost advantage**: $0/month for rule-based agents
3. **UX simplicity**: Built for agents from day 1
4. **Community feedback**: Rapid iteration based on Reddit users

**Defensibility**: 2-3 years until competitors catch up

---

## Implementation Roadmap

### Week 5: Chat Agent

**Day 1-2**: Backend
- [ ] Keyword parser (20 patterns)
- [ ] SQL query builder
- [ ] Example queries library

**Day 3**: Frontend
- [ ] Chat UI component
- [ ] Example query buttons
- [ ] Result cards with actions

**Day 4**: Integration
- [ ] Connect UI to backend
- [ ] Add analytics tracking
- [ ] Error handling

---

### Week 6: Alert Agent + Explainer

**Day 1-2**: Alert Agent
- [ ] Saved search database schema
- [ ] Cron job (every 6 hours)
- [ ] Email notification templates
- [ ] De-duplication logic

**Day 3**: Explainer Agent
- [ ] Template library (10 templates)
- [ ] Historical data lookup
- [ ] Risk assessment logic
- [ ] Formatter + renderer

**Day 4-5**: Testing
- [ ] Unit tests (80% coverage)
- [ ] Integration tests
- [ ] User acceptance testing (5 beta users)

**Day 6-7**: Documentation
- [ ] Feature specs (3 docs)
- [ ] User guide (example queries)
- [ ] Developer docs (API reference)

---

## User Experience Examples

### Example 1: New User (30 seconds to value)

```
[Landing on dashboard]

Chat Agent: 👋 Hi! Try asking me something like:
- "Show me oncology trials under $2B"
- "Phase 3 trials in next 30 days"
- "What's completing this quarter?"

User: "Show me oncology trials under $2B"

[2 seconds later]

Agent: Found 12 oncology trials under $2B market cap:

[Cards with Save/Alert buttons]

User: [Clicks "Save" on 3 trials]

Agent: Saved! Want me to alert you when new oncology trials appear?

User: [Clicks "Yes"]

Agent: Done! You'll get email alerts for new matches.
```

**Time to value**: 30 seconds
**Actions taken**: 1 query, 3 saves, 1 alert
**Learning curve**: 0 (guided by agent)

---

### Example 2: Power User (saved searches)

```
User: "Show me trials like the EXBT one I saved"

Agent: Based on your saved EXBT trial (Phase 3 oncology, $1.8B cap),
I found 5 similar trials:

[Cards]

User: "Alert me when trials like this appear"

Agent: Created saved search: "Phase 3 oncology trials, $1-3B market cap"
You'll get alerts when new matches appear (checked every 6 hours).

[3 days later]

Email: "🧬 New match for your saved search!"
$BIOTECH - Phase 3 oncology - $2.1B cap - 55 days to completion
[View details]
```

---

## Risk Mitigation

### Risk 1: Query Understanding Fails

**Probability**: Medium (20% of queries in Phase 1)

**Mitigation**:
- Fallback to filters: "I didn't understand that. Try using filters below."
- Learn from failures: Track failed queries, add patterns
- User education: Show example queries prominently

---

### Risk 2: Alert Fatigue

**Probability**: Medium (if too many alerts)

**Mitigation**:
- Rate limiting: Max 5 alerts/week per saved search
- Digest mode: Daily summary instead of instant alerts
- User control: Easy unsubscribe per search
- Smart filtering: Only alert if >X% different from last alert

---

### Risk 3: LLM Costs Spike (Phase 2)

**Probability**: Low (controlled rollout)

**Mitigation**:
- Pro tier only (revenue covers costs)
- Rate limiting: 50 queries/month per user
- Fallback to templates if quota exceeded
- Monitor costs daily, adjust limits if needed

---

## Success Criteria

### Week 6 (Launch)

- [ ] 80%+ of pre-written queries work correctly
- [ ] <500ms average response time
- [ ] Chat UI deployed to production
- [ ] 5 beta users test successfully
- [ ] 3 feature specs documented

### Month 1

- [ ] 100+ agent queries from real users
- [ ] 5+ saved searches created
- [ ] 1+ Pro tier conversion attributed to agents
- [ ] 90%+ user satisfaction (survey)
- [ ] "Agent features" mentioned in 2+ user reviews

### Month 3

- [ ] 2,000+ agent queries
- [ ] 100+ saved searches
- [ ] 15+ Pro tier users using alerts
- [ ] 95%+ user satisfaction
- [ ] "Agent features" mentioned in 10+ user reviews
- [ ] Featured in Reddit post with 1K+ upvotes

---

## Conclusion

**Agentic UI is our killer differentiator**:
- ✅ Lower barrier to entry (30s learning curve vs 30min)
- ✅ Better discovery (agent suggests, not just filters)
- ✅ Proactive monitoring (set it and forget it)
- ✅ Educational (plain English explanations)
- ✅ Cost advantage ($0/month vs $1,000s for competitors)

**Strategic positioning**:
> "The only biotech catalyst tracker with an AI research assistant"

**Reddit hook**:
> "I built an AI agent that reads ClinicalTrials.gov so you don't have to"

**Competitive moat**:
- BioPharmCatalyst can't add this without LLM costs
- We built it from day 1 (architectural advantage)
- 2-3 year defensibility window

**Next actions**:
1. Build Phase 1 agents (Week 5-6)
2. Launch with Reddit demo (Week 7)
3. Iterate based on user feedback
4. Upgrade to Phase 2 LLM agents (Month 4-6)

---

**Last Updated**: 2025-12-24
**Status**: Ready for implementation (Phase 2.5 of roadmap)
**Owner**: Dev team
