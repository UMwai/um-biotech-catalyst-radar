# Biotech Run-Up Radar - Feature Specifications

## Feature Overview

| Feature | Phase | Status | Priority | User Tier |
|---------|-------|--------|----------|-----------|
| Catalyst Dashboard | 1 | Complete | High | All |
| Trial System (7-day) | 2 | Complete | High | Free |
| Stripe Payments | 2 | Complete | High | Paid |
| Email Automation | 3 | Complete | High | All |
| Chat Agent | 2.5 | Planned | Medium | All |
| Proactive Alerts | 2.5 | Planned | Medium | Pro |
| AI Trial Explainer | 2.5 | Planned | Medium | Paid |
| API Access | 5 | Planned | Low | Pro |
| Real-time Alerts | 5 | Planned | Low | Pro |

---

## Phase 1: Core Product

### F1.1: Catalyst Dashboard

**Description**: Interactive table displaying upcoming Phase 2/3 clinical trial catalysts for small-cap biotech stocks.

**User Interface**:
- Filterable data table
- Phase filter (Phase 2, Phase 3)
- Date range filter (30/60/90 days)
- Market cap filter
- Sortable columns
- Price chart on row click

**Data Displayed**:
| Column | Description |
|--------|-------------|
| Ticker | Stock symbol |
| Company | Sponsor name |
| Phase | Trial phase (2 or 3) |
| Indication | Disease/condition |
| Catalyst Date | Primary completion date |
| Market Cap | Current market cap |
| Price | Current stock price |
| 30D Change | Price change % |

**Business Rules**:
- Only show trials with completion dates in next 90 days
- Only show stocks with market cap < $5B
- Minimum fuzzy match score of 80 for ticker mapping
- Data refreshes daily at 6 AM UTC

**Paywall Rules**:
- Free users: see 10 rows (most recent catalysts)
- Trial users: see all rows for 7 days
- Subscribers: unlimited access

---

### F1.2: Price Charts with Catalyst Overlay

**Description**: 6-month price chart with vertical line marking catalyst date.

**User Interface**:
- Plotly interactive chart
- Volume bars (optional)
- Catalyst date vertical line
- Zoom and pan controls

**Data Source**: yfinance (6 months historical)

---

## Phase 2: Monetization

### F2.1: Free Trial System

**Description**: 7-day free trial with full access, followed by paywall.

**Trial Flow**:
```
Day 0: User signs up with email
       -> Full access unlocked
       -> Welcome email sent

Day 1-6: Full access continues
         -> Email sequence continues

Day 7: Trial expires
       -> Access limited to 10 rows
       -> "Upgrade Now" prompt
```

**Trial Banner Display**:
- Days remaining countdown
- "Trial" badge in UI
- Upgrade CTA button

**Business Rules**:
- One trial per email address
- Trial starts on email confirmation
- No credit card required
- Trial cannot be paused or extended

---

### F2.2: Stripe Subscription

**Description**: Monthly and annual subscription plans via Stripe Checkout.

**Pricing Tiers**:
| Plan | Price | Features |
|------|-------|----------|
| Early Bird | $19/month | All catalysts, grandfathered pricing |
| Starter | $29/month | All catalysts |
| Pro | $39/month | All catalysts + alerts + API |
| Annual | $149/year | Starter features, 2 months free |

**Checkout Flow**:
1. User clicks "Subscribe" button
2. App creates Stripe Checkout Session
3. Redirect to Stripe-hosted payment page
4. User enters payment details
5. Stripe processes payment
6. Webhook updates subscription status
7. User redirected to app with full access

**Subscription Management**:
- Access Stripe Customer Portal from settings
- View invoices
- Update payment method
- Cancel subscription
- Reactivate canceled subscription

---

### F2.3: Paywall Implementation

**Description**: Content gating based on subscription status.

**Paywall UI**:
- Blurred/hidden rows beyond limit
- "Unlock Full Access" overlay
- Pricing comparison
- Social proof testimonials

**Access Levels**:
| Status | Rows Visible | Features |
|--------|--------------|----------|
| Free | 10 | Basic dashboard |
| Trial | All | Full dashboard |
| Starter | All | Full dashboard |
| Pro | All | Dashboard + Alerts + API |

---

## Phase 2.5: Agentic Features

### F2.5.1: Chat Agent

**Description**: Conversational interface for discovering catalysts.

**Query Examples**:
- "Show me oncology trials under $2B market cap"
- "What Phase 3 trials complete this month?"
- "Find CRISPR-related catalysts"
- "Top 5 catalysts by price momentum"

**Implementation**:
- Rule-based query parsing (no LLM cost)
- Keyword extraction
- Filter construction
- Natural language response

**User Interface**:
- Chat input at bottom of dashboard
- Response cards with catalyst matches
- Quick action buttons (Add to watchlist, View chart)

---

### F2.5.2: Proactive Alert Agent (Pro Tier)

**Description**: Automated alerts when matching catalysts appear.

**Alert Types**:
| Type | Trigger | Channel |
|------|---------|---------|
| New Catalyst | Matches saved search | Email, SMS |
| Price Movement | >10% change | Email, Slack |
| Date Change | Completion date updated | Email |
| Phase Update | Trial phase changed | Email |

**Configuration**:
- Create saved searches (e.g., "Oncology Phase 3")
- Set alert frequency (immediate, daily digest)
- Choose channels (email, SMS, Slack)

---

### F2.5.3: AI Trial Explainer

**Description**: Plain-English explanations of clinical trial details.

**Features**:
- Indication explanation (what disease?)
- Mechanism of action (how does it work?)
- Competitive landscape (other treatments?)
- Historical context (previous trial results?)

**Example Output**:
```
Trial: NCT12345678
Indication: Non-small cell lung cancer (NSCLC)

What it treats:
NSCLC is the most common type of lung cancer,
accounting for 85% of cases. It typically affects
smokers and has a 5-year survival rate of 25%.

How it works:
This drug is a checkpoint inhibitor targeting PD-L1.
It helps the immune system recognize and attack
cancer cells that were previously "hiding."

Competition:
Similar drugs: Keytruda (Merck), Opdivo (BMS)
This trial focuses on a novel combination therapy
that may improve response rates.
```

**Implementation**: Claude API for Pro tier (optional upgrade)

---

## Phase 3: Conversion & Retention

### F3.1: Trial Conversion Email Sequence

**Description**: Automated 7-email sequence to convert trial users.

**Email Schedule**:
| Day | Email | Goal |
|-----|-------|------|
| 0 | Welcome | Set expectations |
| 3 | Value | Show missed opportunities |
| 5 | Social Proof | Build credibility |
| 6 | Urgency | Create FOMO |
| 7 | Last Chance | Final conversion push |
| 9 | Follow-up | Re-engage dropoffs |
| 14 | Win-back | Special discount offer |

**Email Content**:
- Personalized with name
- Dynamic catalyst highlights
- Clear CTA buttons
- Mobile-optimized HTML

---

### F3.2: User Analytics Tracking

**Description**: Track user behavior for optimization.

**Events Tracked**:
| Event | Data |
|-------|------|
| page_view | page_name, timestamp |
| catalyst_view | nct_id, ticker |
| filter_applied | filter_type, value |
| chart_opened | ticker, timeframe |
| paywall_hit | user_id, context |
| checkout_started | plan_type |
| subscription_created | plan_type, price |

**Metrics Dashboard**:
- Daily/weekly/monthly active users
- Trial signup rate
- Trial-to-paid conversion rate
- Feature usage heatmap
- Churn analysis

---

## Phase 4: Distribution & Growth

### F4.1: Referral Program

**Description**: Incentivize users to refer others.

**Program Structure**:
- Referrer: 1 month free for each 3 referrals
- Referee: 20% off first month
- Tracking via unique referral codes

**Implementation**:
- Referral link generation
- Referral tracking in database
- Automatic reward application
- Referral dashboard

---

### F4.2: Landing Page Optimization

**Description**: Convert visitors to trial signups.

**Page Elements**:
- Hero section with value proposition
- Competitive comparison (vs BioPharmCatalyst)
- Feature highlights
- Social proof (testimonials, logos)
- Pricing table
- FAQ section
- Email capture form

---

## Phase 5: Pro Features

### F5.1: API Access

**Description**: Programmatic access to catalyst data.

**API Endpoints**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/catalysts | GET | List all catalysts |
| /api/catalysts/{nct_id} | GET | Single catalyst |
| /api/tickers/{ticker}/catalysts | GET | Catalysts by ticker |
| /api/search | POST | Search with filters |

**Authentication**: API key in header

**Rate Limits**: 100 requests/day (Pro tier)

---

### F5.2: Real-Time Alerts

**Description**: Instant notifications for price-sensitive events.

**Alert Channels**:
- SMS (Twilio)
- Slack webhook
- Discord webhook
- Email

**Alert Types**:
- Catalyst date within 48 hours
- Price drop >5% (buying opportunity)
- Price spike >10% (momentum)
- New Phase 3 trial announced

---

## Feature Comparison Matrix

| Feature | Free | Trial | Starter | Pro |
|---------|------|-------|---------|-----|
| Catalyst view | 10 rows | All | All | All |
| Price charts | Yes | Yes | Yes | Yes |
| Filters | Basic | All | All | All |
| Chat agent | 5 queries/day | Unlimited | Unlimited | Unlimited |
| Saved searches | 0 | 3 | 5 | Unlimited |
| Email alerts | No | No | No | Yes |
| SMS alerts | No | No | No | Yes |
| API access | No | No | No | Yes |
| Priority support | No | No | No | Yes |
| Price | $0 | $0 (7 days) | $29/mo | $39/mo |

---

## Non-Functional Requirements

### Performance
- Dashboard load time: < 2 seconds
- API response time: < 500ms
- Chart render time: < 1 second

### Reliability
- 99.5% uptime target
- Daily data refresh success rate: > 99%
- Webhook processing: < 30 seconds

### Scalability
- Support 1,000 concurrent users
- Handle 10,000 API requests/day

### Security
- HTTPS everywhere
- PCI compliance via Stripe
- No PII storage beyond email
- SOC 2 Type 1 (future)

---

**Last Updated**: 2024-12-30
**Document Version**: 1.0
