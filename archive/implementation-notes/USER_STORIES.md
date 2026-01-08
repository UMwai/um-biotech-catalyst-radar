# Biotech Run-Up Radar - User Stories

## Overview

User stories for retail biotech traders who want to capitalize on pre-catalyst stock run-ups.

---

## Personas

### Primary: Active Retail Trader
- **Name**: Mike
- **Age**: 35
- **Profile**: Part-time day trader, works full-time job, trades biotech stocks
- **Portfolio**: $50K-150K
- **Goals**: Find catalysts early, time entries before run-up
- **Pain Points**: BioPharmCatalyst too expensive ($150/mo), manual tracking is tedious

### Secondary: Biotech Enthusiast
- **Name**: Sarah
- **Age**: 42
- **Profile**: Pharmacist with domain expertise, invests in biotech
- **Portfolio**: $100K+
- **Goals**: Understand trial timelines, make informed long-term investments
- **Pain Points**: Scattered data sources, no consolidated view

### Secondary: Swing Trader
- **Name**: Alex
- **Age**: 28
- **Profile**: Full-time swing trader, holds positions 2-8 weeks
- **Portfolio**: $200K+
- **Goals**: Catch 20-50% run-ups before data releases
- **Pain Points**: Missing catalysts, entering too late

---

## Epic 1: Catalyst Discovery

### Story 1.1: Browse Upcoming Catalysts
**As a** retail biotech trader,
**I want to** see all upcoming Phase 2/3 trial results,
**So that** I can identify potential trading opportunities.

**Acceptance Criteria**:
- [ ] I can see a table of upcoming catalysts
- [ ] Each row shows ticker, company, phase, indication, date
- [ ] I can see market cap and current price
- [ ] Data is refreshed daily

**Priority**: High | **Phase**: 1 | **Status**: Complete

---

### Story 1.2: Filter Catalysts by Phase
**As a** retail biotech trader,
**I want to** filter catalysts by trial phase,
**So that** I can focus on Phase 3 (higher conviction) or Phase 2 (higher risk/reward).

**Acceptance Criteria**:
- [ ] I can filter by Phase 2 only
- [ ] I can filter by Phase 3 only
- [ ] I can view both phases together
- [ ] Filter persists during session

**Priority**: High | **Phase**: 1 | **Status**: Complete

---

### Story 1.3: Filter by Time Horizon
**As a** retail biotech trader,
**I want to** filter catalysts by date range,
**So that** I can focus on near-term opportunities.

**Acceptance Criteria**:
- [ ] I can filter to next 30 days
- [ ] I can filter to next 60 days
- [ ] I can filter to next 90 days
- [ ] Custom date range option

**Priority**: High | **Phase**: 1 | **Status**: Complete

---

### Story 1.4: View Price Chart with Catalyst Overlay
**As a** retail biotech trader,
**I want to** see the stock price chart with the catalyst date marked,
**So that** I can assess the run-up pattern.

**Acceptance Criteria**:
- [ ] I can click a row to see the chart
- [ ] Chart shows 6-month price history
- [ ] Vertical line marks catalyst date
- [ ] I can zoom and pan the chart

**Priority**: High | **Phase**: 1 | **Status**: Complete

---

### Story 1.5: Filter by Market Cap
**As a** retail biotech trader,
**I want to** filter by market cap,
**So that** I can focus on small caps with higher volatility.

**Acceptance Criteria**:
- [ ] Default filter: < $5B market cap
- [ ] I can adjust the market cap threshold
- [ ] Micro-cap option: < $500M
- [ ] Small-cap option: < $2B

**Priority**: Medium | **Phase**: 1 | **Status**: Complete

---

## Epic 2: Free Trial Experience

### Story 2.1: Start Free Trial
**As a** potential subscriber,
**I want to** try the full product for free,
**So that** I can evaluate if it's worth paying for.

**Acceptance Criteria**:
- [ ] I can sign up with just email
- [ ] No credit card required
- [ ] Trial lasts 7 days
- [ ] Full access during trial

**Priority**: High | **Phase**: 2 | **Status**: Complete

---

### Story 2.2: See Trial Status
**As a** trial user,
**I want to** see how many days remain in my trial,
**So that** I can decide whether to subscribe.

**Acceptance Criteria**:
- [ ] Trial banner shows days remaining
- [ ] Countdown is accurate
- [ ] CTA to subscribe is visible
- [ ] No nagging popups

**Priority**: High | **Phase**: 2 | **Status**: Complete

---

### Story 2.3: Trial Expiration
**As a** trial user whose trial has expired,
**I want to** understand what happens next,
**So that** I can decide to subscribe or leave.

**Acceptance Criteria**:
- [ ] Access limited to 10 rows after expiration
- [ ] Clear message explaining limitation
- [ ] Easy path to subscribe
- [ ] Can still browse limited data

**Priority**: High | **Phase**: 2 | **Status**: Complete

---

## Epic 3: Subscription & Payments

### Story 3.1: Subscribe to Paid Plan
**As a** trial user ready to subscribe,
**I want to** easily upgrade to a paid plan,
**So that** I can continue using the full product.

**Acceptance Criteria**:
- [ ] I can see pricing options
- [ ] I can choose monthly or annual
- [ ] Checkout is secure (Stripe)
- [ ] Access unlocked immediately after payment

**Priority**: High | **Phase**: 2 | **Status**: Complete

---

### Story 3.2: Manage My Subscription
**As a** paying subscriber,
**I want to** manage my subscription,
**So that** I can update payment info or cancel.

**Acceptance Criteria**:
- [ ] I can access billing portal
- [ ] I can view past invoices
- [ ] I can update payment method
- [ ] I can cancel subscription

**Priority**: High | **Phase**: 2 | **Status**: Complete

---

### Story 3.3: Cancel and Reactivate
**As a** subscriber who wants to cancel,
**I want to** easily cancel and optionally reactivate,
**So that** I have control over my subscription.

**Acceptance Criteria**:
- [ ] I can cancel anytime
- [ ] Access continues until period end
- [ ] I can reactivate before period end
- [ ] Clear confirmation of cancellation

**Priority**: Medium | **Phase**: 2 | **Status**: Complete

---

## Epic 4: Agentic Features

### Story 4.1: Natural Language Search
**As a** retail trader,
**I want to** ask questions in plain English,
**So that** I can find catalysts without learning filters.

**Acceptance Criteria**:
- [ ] I can type "show me oncology trials"
- [ ] I can ask "what's coming up this month?"
- [ ] Results displayed as catalyst cards
- [ ] Suggestions for follow-up queries

**Priority**: Medium | **Phase**: 2.5 | **Status**: Planned

---

### Story 4.2: Understand Trial Details
**As a** biotech enthusiast,
**I want to** get plain-English explanations of trials,
**So that** I can understand what I'm investing in.

**Acceptance Criteria**:
- [ ] I can click "Explain" on any trial
- [ ] Get explanation of indication
- [ ] Get mechanism of action summary
- [ ] See competitive landscape context

**Priority**: Medium | **Phase**: 2.5 | **Status**: Planned

---

### Story 4.3: Save Search Criteria
**As a** regular user,
**I want to** save my favorite search filters,
**So that** I don't have to reconfigure them each visit.

**Acceptance Criteria**:
- [ ] I can save current filter combination
- [ ] I can name my saved searches
- [ ] I can load saved searches with one click
- [ ] I can delete saved searches

**Priority**: Medium | **Phase**: 2.5 | **Status**: Planned

---

### Story 4.4: Get Proactive Alerts (Pro)
**As a** Pro subscriber,
**I want to** receive alerts when new catalysts match my criteria,
**So that** I don't miss opportunities.

**Acceptance Criteria**:
- [ ] I can create alert rules from saved searches
- [ ] I receive email when new matches appear
- [ ] I can enable SMS alerts (Twilio)
- [ ] I can set alert frequency

**Priority**: Medium | **Phase**: 2.5 | **Status**: Planned

---

## Epic 5: Conversion Optimization

### Story 5.1: Receive Trial Welcome Email
**As a** new trial user,
**I want to** receive a welcome email,
**So that** I understand how to use the product.

**Acceptance Criteria**:
- [ ] Email arrives within minutes of signup
- [ ] Contains quick start guide
- [ ] Links to key features
- [ ] Sets expectation for trial duration

**Priority**: High | **Phase**: 3 | **Status**: Complete

---

### Story 5.2: Receive Value Reminder
**As a** trial user on day 3,
**I want to** see the value I've gotten,
**So that** I'm reminded why to subscribe.

**Acceptance Criteria**:
- [ ] Email shows "catalysts you explored"
- [ ] Highlights any price movements
- [ ] Social proof from other traders
- [ ] Soft CTA to subscribe

**Priority**: High | **Phase**: 3 | **Status**: Complete

---

### Story 5.3: Receive Expiration Warning
**As a** trial user on day 6,
**I want to** be reminded my trial is ending,
**So that** I can decide to subscribe in time.

**Acceptance Criteria**:
- [ ] Email on day 6 with 24-hour warning
- [ ] Final email on day 7 with urgency
- [ ] Clear CTA to subscribe
- [ ] Special offer for immediate action

**Priority**: High | **Phase**: 3 | **Status**: Complete

---

## Epic 6: Pro Tier Features

### Story 6.1: Access API
**As a** Pro subscriber,
**I want to** access catalyst data via API,
**So that** I can integrate it into my trading tools.

**Acceptance Criteria**:
- [ ] I receive an API key
- [ ] I can fetch catalysts programmatically
- [ ] Rate limit of 100 requests/day
- [ ] API documentation available

**Priority**: Low | **Phase**: 5 | **Status**: Planned

---

### Story 6.2: Get Real-Time SMS Alerts
**As a** Pro subscriber,
**I want to** receive SMS alerts for time-sensitive events,
**So that** I can act immediately.

**Acceptance Criteria**:
- [ ] I can configure SMS alerts
- [ ] Alerts for catalysts within 48 hours
- [ ] Alerts for significant price moves
- [ ] I can disable SMS anytime

**Priority**: Low | **Phase**: 5 | **Status**: Planned

---

### Story 6.3: Export Data
**As a** Pro subscriber,
**I want to** export catalyst data,
**So that** I can analyze it in my own tools.

**Acceptance Criteria**:
- [ ] I can export to CSV
- [ ] I can export to Excel
- [ ] Export includes all visible columns
- [ ] Export respects current filters

**Priority**: Low | **Phase**: 5 | **Status**: Planned

---

## Epic 7: Community & Distribution

### Story 7.1: Share Catalyst on Social
**As a** user who found a good opportunity,
**I want to** share it on social media,
**So that** I can help others and build community.

**Acceptance Criteria**:
- [ ] I can click "Share" on any catalyst
- [ ] Pre-formatted tweet/post generated
- [ ] Includes key details and link
- [ ] Referral tracking (future)

**Priority**: Low | **Phase**: 4 | **Status**: Planned

---

### Story 7.2: Refer Friends
**As a** happy subscriber,
**I want to** refer friends and earn rewards,
**So that** I benefit from spreading the word.

**Acceptance Criteria**:
- [ ] I have a unique referral link
- [ ] Friend gets 20% off first month
- [ ] I get 1 month free per 3 referrals
- [ ] I can track my referrals

**Priority**: Low | **Phase**: 4 | **Status**: Planned

---

## Story Map Summary

```
                   Phase 1       Phase 2      Phase 2.5     Phase 3      Phase 4-5
                   (MVP)         (Money)      (Agentic)     (Growth)     (Pro)
                 +----------+  +----------+  +----------+  +----------+  +----------+
Discovery        | 1.1-1.5  |  |          |  | 4.1-4.3  |  |          |  |          |
                 | Complete |  |          |  | Planned  |  |          |  |          |
                 +----------+  +----------+  +----------+  +----------+  +----------+
Trial            |          |  | 2.1-2.3  |  |          |  | 5.1-5.3  |  |          |
                 |          |  | Complete |  |          |  | Complete |  |          |
                 +----------+  +----------+  +----------+  +----------+  +----------+
Subscription     |          |  | 3.1-3.3  |  |          |  |          |  |          |
                 |          |  | Complete |  |          |  |          |  |          |
                 +----------+  +----------+  +----------+  +----------+  +----------+
Alerts           |          |  |          |  | 4.4      |  |          |  | 6.2      |
                 |          |  |          |  | Planned  |  |          |  | Planned  |
                 +----------+  +----------+  +----------+  +----------+  +----------+
Pro Features     |          |  |          |  |          |  |          |  | 6.1, 6.3 |
                 |          |  |          |  |          |  |          |  | Planned  |
                 +----------+  +----------+  +----------+  +----------+  +----------+
Community        |          |  |          |  |          |  | 7.1-7.2  |  |          |
                 |          |  |          |  |          |  | Planned  |  |          |
                 +----------+  +----------+  +----------+  +----------+  +----------+
```

---

## Success Metrics by Epic

| Epic | Key Metric | Target |
|------|------------|--------|
| Catalyst Discovery | Daily Active Users | 100+ |
| Free Trial | Trial Signup Rate | 10%+ of visitors |
| Subscription | Trial-to-Paid Conversion | 10%+ |
| Agentic Features | Chat Queries/User/Day | 5+ |
| Conversion | Email Open Rate | 25%+ |
| Pro Tier | Pro Tier Adoption | 20% of subscribers |
| Community | Referral Rate | 10%+ of users |

---

**Last Updated**: 2024-12-30
**Document Version**: 1.0
