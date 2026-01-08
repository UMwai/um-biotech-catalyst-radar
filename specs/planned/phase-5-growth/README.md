# Phase 5: Growth Features

**Trigger:** After 25 paid subscribers OR 30 days post-launch
**Timeline:** Month 2-3 after launch
**Goal:** Differentiate Pro tier, improve retention, reduce churn

## Features Overview

### 1. API Access (Pro Tier)
REST API for programmatic access to catalyst data.

**Use cases:**
- Automated trading scripts
- Custom dashboards
- Integration with other tools

**Scope:**
- `/api/v1/catalysts` - List catalysts with filters
- `/api/v1/catalysts/{id}` - Get catalyst detail
- Rate limit: 1000 requests/day

### 2. Advanced Alerts
Enhanced notification options beyond basic email.

**Features:**
- SMS alerts via Twilio (Pro only)
- Slack webhook integration (Pro only)
- Daily digest mode (batch alerts instead of real-time)
- Quiet hours configuration

**Tiers:**
- Starter: Email only, 3 saved searches
- Pro: Email + SMS + Slack, unlimited searches

### 3. LLM-Powered Agents
Upgrade chat agent from rule-based to Claude API.

**Benefits:**
- Handle complex, natural language queries
- "Why did MRNA run up last month?"
- "Compare NVAX vs BNTX catalyst timelines"

**Implementation:**
- Pro tier only (manages API costs)
- Fallback to rule-based for simple queries
- Cache common queries to reduce API calls

### 4. Unlimited Saved Searches
Remove saved search limits for Pro tier.

**Tiers:**
- Free: 0 saved searches
- Starter: 3 saved searches
- Pro: Unlimited saved searches

## Success Criteria

| Metric | Target |
|--------|--------|
| Pro tier adoption | 20% of paid users |
| Monthly churn | <5% |
| API requests | 1,000+/day |
| Advanced alert usage | 50% of Pro users |
| LLM agent satisfaction | 90%+ positive feedback |

## Dependencies

- Twilio account for SMS
- Slack app for webhooks
- Claude API key for LLM agent
- API gateway (Supabase Edge Functions)

## Cost Analysis

| Feature | Monthly Cost (100 users) |
|---------|--------------------------|
| SMS (Twilio) | ~$10 (100 alerts × $0.01) |
| Slack | $0 (webhooks are free) |
| Claude API | ~$20 (1000 queries × $0.02) |
| **Total** | ~$30/month |

Revenue at 100 users: $2,900+ MRR (assuming 20% on Pro @ $39)

## Next Steps

1. Prioritize features based on user feedback (Week 2 post-launch)
2. Create detailed specs for top 2 features
3. Implement in order of user demand
