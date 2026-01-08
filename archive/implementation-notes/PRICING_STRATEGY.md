# Biotech Run-Up Radar - Pricing Strategy Recommendation

## Executive Summary

**Recommendation: Increase base price to $29-39/month + launch annual option**

Current $19/month pricing is sustainable but leaves significant value on the table. With a focused 90-day growth strategy, reaching 53 subscribers (MRR $957) is achievable. Optimized pricing unlocks $1.5K+ MRR at same subscriber count.

---

## 1. Unit Economics Analysis

### Current Pricing ($19/month)

| Metric | Value |
|--------|-------|
| Monthly Subscription | $19.00 |
| Stripe Fees (2.9% + $0.30 + 0.5%) | $0.95 (5.0%) |
| **Net Revenue per Customer** | **$18.05** |
| MRR @ 53 subscribers | **$956.86** |
| Payback Period (@ $20 acquisition cost) | 1.1 months |

**Key Insight**: Fees are reasonable (~5%) but the absolute margin per customer is thin ($18). At $19, you need consistent >80% retention to build resilience.

### Revised Pricing ($29/month)

| Metric | Value |
|--------|-------|
| Monthly Subscription | $29.00 |
| Stripe Fees | $1.14 (3.9%) |
| **Net Revenue per Customer** | **$27.71** |
| MRR @ 53 subscribers | **$1,468.84** |
| Payback Period (@ $20 acquisition cost) | 0.7 months |

**Why $29?**
- 53% price increase = 53% more revenue per customer
- Still 5x cheaper than BioPharmCatalyst ($150)
- Closer to Seeking Alpha Premium ($29)
- Psychological: $29 feels like "legit SaaS" vs "$19 feels cheap"
- Higher perceived value = better retention

---

## 2. Price Sensitivity Analysis

| Price | Net/Sub | MRR @ 53 | Lift vs $19 |
|-------|---------|----------|-----------|
| $19/mo | $18.05 | $957 | baseline |
| $29/mo | $27.71 | $1,469 | +53% |
| $39/mo | $37.37 | $1,981 | +107% |
| $49/mo | $47.03 | $2,493 | +161% |
| $59/mo | $56.69 | $3,005 | +214% |

**Recommendation Matrix**:
- **$19**: Only if you're chasing volume/MAU over MRR (not recommended)
- **$29**: Sweet spot - proven SaaS pricing, defensible, high conversion
- **$39-49**: Only if you build enterprise features (API, alerts, compliance reports)
- **$59+**: Only for institutional tier (separate product)

---

## 3. Annual Pricing Strategy

### Recommended Tier Structure

**Monthly Plan**: $29/month

**Annual Plan**: $232/year (33% discount)
- Equivalent to $19.33/month
- Annual discount incentivizes commitment
- Stripe net: $223.66/year per customer

**Why 33% vs other discounts?**

| Annual Option | Price | Annual Net | Need to Match $957 MRR |
|---|---|---|---|
| 20% discount ($278/yr) | $278 | $269 | 44 annual subs |
| 25% discount ($261/yr) | $261 | $253 | 46 annual subs |
| **30% discount ($244/yr)** | $244 | $237 | 49 annual subs |
| **33% discount ($232/yr)** | $232 | $223 | 52 annual subs |

**Recommendation: 33% discount** to:
1. Match pricing psychology (round number: $19-20/mo equivalent)
2. Incentivize annual commitments early (better cash flow, retention signal)
3. Require only 52 annual subs to hit $1K MRR (nearly identical to 53 monthly)

**Implementation**:
- Launch with Monthly-only first (prove demand at $29)
- Add Annual option after 20-30 subscribers (reduces refund risk)

---

## 4. Free Trial vs Freemium Decision

### Recommended: Free Trial (7 days) + Demo Mode

**Why NOT Freemium?**
- Freemium works for high-growth consumer products (network effects, viral loops)
- Biotech Radar has NO network effects (users don't benefit from other users)
- Free tier cannibalizes paid tier without driving retention

**Why Free Trial?**
- Lowers activation friction for cautious retail traders
- Proves value before payment information required
- Typical SaaS conversion: 10-15% free trial → paid
- Aligns with Stripe's payment integration

### Trial Implementation

```
Day 1-7:   Full access (all features)
Day 8:     Paywall - "Trial expired, subscribe to continue"
Action:    Link to $29/mo checkout or $232/annual
CTA:       "Subscribe now" (not aggressive)
```

**Expected Metrics**:
- Free trial signups: 300-500 in 90 days (with marketing)
- Conversion rate: 10-12% → 30-60 paid customers
- Demo mode: Keep toggle on app for investors/press

---

## 5. 90-Day Path to 53 Subscribers

### Growth Assumptions

**Channels**:
1. **Reddit/Discord** (R/investing, R/stocks, trading Discord)
   - Cost: Free (time)
   - Target: 5-10 signups/week
   - Strategy: Share catalyst picks, link to app

2. **Twitter/X** (biotech trading community)
   - Cost: Free (content creation)
   - Target: 5-8 signups/week
   - Strategy: Live catalyst alerts, memes ("FDA approval incoming 📈")

3. **Organic search** (SEO)
   - Cost: Free (content already live)
   - Target: 2-3 signups/week
   - Strategy: "clinical trial catalyst tracker", "biotech run-up finder"

4. **Paid ads** (if budget available)
   - Cost: $5-10/signup
   - Target: 10-20 signups/week
   - Strategy: Reddit/Twitter ads targeting "biotech traders"

### Projected Runway

| Week | Reddit/Discord | Twitter | Organic | Paid | Cumulative | Notes |
|------|---|---|---|---|---|---|
| 1-2 | 10 | 5 | 2 | 0 | 17 | MVP soft launch |
| 3-4 | 15 | 12 | 4 | 0 | 48 | Natural traction |
| 5-6 | 20 | 15 | 6 | 15 | 104 | Consider paid if needed |
| 7-8 | 18 | 14 | 7 | 20 | 163 | Momentum compounds |
| 9-10 | 15 | 12 | 8 | 25 | 223 | Word-of-mouth kicks in |
| 11-12 | 10 | 10 | 10 | 20 | 283 | Mature phase |

**Result**: 280+ total signups, ~30-35 paid subscribers by week 12 (conservative)

**To hit 53 subscribers**:
- Need 40% trial → paid conversion (achievable with strong product)
- OR reach 130+ trial signups
- OR hybrid: 25 monthly + 28 annual customers

---

## 6. Competitive Positioning

### Your Position in Market

```
PRICE vs COMPLEXITY

$0      ThinkorSwim (free general trading)
        ↓ (no specialization)

$29     Seeking Alpha Premium (general research)
        Biotech Radar ($29 → RECOMMENDED)
        ↓ (specialized but easy to use)

$150+   BioPharmCatalyst (institutional, compliance, reporting)
        ↓ (complex, regulatory-grade)

$500+   Bloomberg Terminal (industry standard)
```

### Defensibility

| Factor | Your Edge |
|--------|-----------|
| **Price** | 80%+ cheaper than institutional alternatives |
| **Niche** | Laser-focused on biotech small-cap run-ups (not general trading) |
| **Speed** | Real-time ClinicalTrials.gov data (not manual analyst reports) |
| **UX** | Streamlit → simple, fast, no learning curve |
| **Moat** | Ticker mapping accuracy (manual verification defensible) |

**Weakness to address**:
- Competitors could copy the scraper
- Mitigation: Build community (Slack, Discord), add expert commentary, expand to other catalysts (FDA approvals, earnings dates)

---

## 7. Decision Framework

### Question 1: Is $19/month right?

**Answer: NO - Increase to $29-39**

| Reasoning |
|-----------|
| $19 leaves 53% revenue upside while maintaining same subscriber growth |
| Psychological pricing: $29 feels like "legit SaaS" |
| Payback period remains excellent (0.7 months @ $20 CAC) |
| Only 2x Seeking Alpha, 1/5 of BioPharmCatalyst - defensible positioning |
| Typical SaaS conversion rates are *insensitive* to ±50% price moves (7-10% difference) |

**Recommendation**: Launch $29/month. If conversion drops >20%, drop to $25. Don't go back to $19.

---

### Question 2: Unit Economics with Stripe Fees?

**Answer: Healthy at $29+**

| Price | Net Revenue | @ 53 subs | Runway | Verdict |
|-------|---|---|---|---|
| $19 | $18.05 | $957 | 1.1 months | Tight |
| $29 | $27.71 | $1,469 | 1.6+ months | Comfortable |
| $39 | $37.37 | $1,981 | 2.1+ months | Strong |

- Stripe fees are 3.9-5% (industry standard)
- At $29, you retain $27.71/customer = excellent unit economics
- Monthly recurring revenue model = predictable growth path
- Break-even on $20 acquisition cost in <1 month

---

### Question 3: Annual Pricing?

**Answer: YES - Launch after 20 subscribers**

| Tier | Price | Strategy |
|------|-------|----------|
| **Monthly** | $29/mo | Launch immediately (prove demand) |
| **Annual** | $232/yr | Launch after 20-30 paid subs (de-risk) |
| **Discount** | 33% off | Incentivizes commitment, matches psychology |

**Why wait to launch annual?**
- Reduces refund risk (unknown retention)
- Signals "we've validated demand"
- Easier to get customers to commit when there's social proof

**Expected mix**: 65% monthly, 35% annual (mature SaaS)

---

### Question 4: Free Trial vs Freemium?

**Answer: Free Trial (7 days)**

| Model | Best For | Your Case |
|-------|----------|-----------|
| **Freemium** | Network effects, viral, high-volume | ❌ No network effects |
| **Free Trial** | Specialized SaaS, proving ROI | ✅ Perfect fit |
| **Hybrid** | Two-tier (limited free, full paid) | Maybe later |

**Implementation**:
- 7-day free trial (full access)
- Day 8: Soft paywall ("Trial expired")
- Demo mode: Permanent for marketing
- Expected conversion: 10-15% → 30-60 paid customers

---

### Question 5: Realistic Path to 53 Subscribers in 90 Days?

**Answer: YES - 30-35 realistic, 50+ possible with focused effort**

**Conservative estimate** (1-2 hours/week marketing):
- Week 12: 30-35 paid subscribers
- Monthly burn rate: ~$400 (cloud, data)
- MRR: $833-$1,000

**Aggressive estimate** (10+ hours/week marketing + paid ads):
- Week 12: 50-60 paid subscribers
- With annual tier: 40 monthly + 15 annual
- MRR: $1,300-$1,600

**Critical success factors**:
1. **Product quality** (accurate ticker mapping, real trial data)
2. **Community presence** (Reddit, Twitter, Discord)
3. **Content strategy** ("FDA approval incoming" threads)
4. **Paid ads** (Reddit, Twitter) only if organic hits ceiling
5. **Analytics** (track which channels convert best)

---

## Final Recommendation

### Pricing Tier Structure

| Tier | Price | Launch | Target |
|------|-------|--------|--------|
| **Starter (Monthly)** | $29/month | Now | Volume |
| **Annual** | $232/year | After 20 subs | Commitment |
| **Future: Pro** | $79/month | Month 6+ | Alerts, API, reports |

### Go-to-Market

1. **Week 1**: Launch at $29/month with free 7-day trial
2. **Week 4**: Add annual option ($232/year = 33% discount)
3. **Week 8**: Evaluate pricing elasticity, adjust if needed
4. **Month 6**: If hitting >50% monthly retention, launch Pro tier

### Expected Outcome

| Metric | Conservative | Realistic | Upside |
|--------|---|---|---|
| 90-day subscribers | 25 | 35-45 | 60+ |
| MRR | $700 | $1,000-$1,300 | $1,700+ |
| Retention (month 3) | 70% | 75% | 85%+ |
| CAC payback | 1.2 mo | 0.8 mo | 0.5 mo |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Price too high → low conversion | High | A/B test $19 vs $29 with 5% traffic |
| Competitor copies model | Medium | Build community moat, expand feature set |
| Trial → paid conversion low | Medium | Optimize onboarding, add success metrics |
| Churn >10% monthly | High | Weekly product updates, early user feedback |
| Stripe dependency | Low | Plan Paddle alternative by month 6 |

---

## Implementation Checklist

- [ ] Update `.env` to reflect $29 pricing
- [ ] Update `config.py` with annual price ($232/year)
- [ ] Modify `stripe_gate.py` to support both monthly + annual plans
- [ ] Add analytics tracking (signup source, trial conversion, churn)
- [ ] Create landing page explaining why $29 is fair (vs competitors)
- [ ] Draft free trial email sequence (3 emails over 7 days)
- [ ] Set up Reddit bot for weekly catalyst posts
- [ ] Create Twitter template for daily catalyst alerts
- [ ] Document ticker mapping accuracy (build trust)
- [ ] Launch pricing as A/B test (10% $19, 90% $29) for 2 weeks

---

## Conclusion

**Increase to $29/month immediately.** This pricing:
- ✅ Doubles revenue per customer
- ✅ Maintains acquisition cost payback <1 month
- ✅ Positions you above consumer tools, below institutional platforms
- ✅ Leaves room to grow into $39-79 premium tiers
- ✅ Creates psychological credibility ("real SaaS")

The path to $1,000 MRR is achievable in 90 days with disciplined execution. Start with $29/month + 7-day free trial, add annual option after you validate demand, and reinvest in retention and community building.

**Next step**: Update Stripe products and run 2-week A/B test.
