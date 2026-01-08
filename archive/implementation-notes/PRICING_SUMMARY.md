# Biotech Run-Up Radar - Pricing Recommendation (Quick Summary)

## TL;DR: Raise to $29/month, add $232/year annual option

---

## Quick Answers

### 1. Is $19/month right?
**NO.** Increase to **$29/month** immediately.
- Current: $18.05 net per customer = $956 MRR @ 53 subs
- Proposed: $27.71 net per customer = $1,469 MRR @ 53 subs (53% uplift)
- Conversion impact: Minimal (SaaS pricing is inelastic for ±50% moves)
- Positioning: Still 5x cheaper than BioPharmCatalyst ($150), matches Seeking Alpha ($29)

### 2. Unit Economics with Stripe Fees?
**Healthy at $29+**

| Price | Stripe Fees | Net/Customer | MRR @ 53 | Payback (@ $20 CAC) |
|-------|---|---|---|---|
| $19 | $0.95 (5%) | $18.05 | $957 | 1.1 months |
| $29 | $1.14 (4%) | $27.71 | $1,469 | 0.7 months |
| $39 | $1.63 (4%) | $37.37 | $1,981 | 0.5 months |

**Verdict**: At $29, you have excellent unit economics. Every customer pays back acquisition costs in <1 month.

### 3. Annual Pricing?
**YES.** After validating monthly demand with 20-30 subscribers:

| Plan | Price | Why |
|------|-------|-----|
| Monthly | $29/mo | Launch now, prove demand |
| Annual | $232/year (33% off) | Launch later, incentivize commitment |

- 33% discount matches psychology ($19.33/month equivalent)
- Only need 52 annual subs vs 53 monthly to hit $1K MRR
- Expected mix: 65% monthly, 35% annual (mature SaaS)

### 4. Free Trial vs Freemium?
**Free Trial (7 days).** Freemium is for network-effect products (you have none).

- Launch with 7-day full access trial
- Day 8: Paywall appears ("Trial expired, subscribe to continue")
- Expected conversion: 10-15% of trial users
- Expected paid customers: 30-60 from 300-500 trial signups

### 5. Path to 53 Subscribers in 90 Days?
**YES - 30-35 realistic, 50+ possible.**

| Channel | Source | 90-day Target |
|---------|--------|---|
| Reddit/Discord | Organic | 80-100 signups |
| Twitter/X | Organic | 60-80 signups |
| Organic Search | SEO | 20-30 signups |
| Paid Ads | Paid | 0 (free first 8 weeks) |
| **Total Trials** | **Mixed** | **150-200** |
| **Paid Customers** | 10-15% conversion | **30-35 (conservative)** |

**With focused effort**: 50-60 customers possible with paid ads + higher conversion.

---

## Pricing Tier Structure (Recommended)

```
Launch Now (Week 1):
├── Monthly Plan: $29/month (+ 7-day free trial)
└── Demo Mode: Free (for marketing + press)

Launch Later (Week 4+):
├── Annual Plan: $232/year (= $19.33/month, 33% discount)
└── Future Pro Tier: $79/month (alerts, API, reports) [Month 6+]
```

---

## Why $29 Specifically?

1. **Price psychology**: Looks like "legit SaaS" (not a hobby)
2. **Competitive gap**: $29 × 5 = $150 (room for premium tier later)
3. **Retention signal**: Higher price = more committed users
4. **Revenue**: 53% more per customer while maintaining conversion rates
5. **Precedent**: Seeking Alpha Premium is $29 (similar product type)

**A/B Testing**: If worried, run 50/50 test for 2 weeks:
- Group A: $19/month (control)
- Group B: $29/month (variant)
- Hypothesis: <10% conversion rate difference

---

## Expected Outcome (90 days)

### Conservative (1-2 hrs/week marketing)
- **Subscribers**: 25-35
- **MRR**: $700-$1,000
- **Monthly Churn**: ~5-10%

### Realistic (5-10 hrs/week marketing)
- **Subscribers**: 35-50
- **MRR**: $1,000-$1,400
- **Monthly Churn**: ~5-10%

### Upside (10+ hrs/week + paid ads)
- **Subscribers**: 50-70
- **MRR**: $1,400-$1,900
- **Monthly Churn**: ~5-10%

---

## Implementation Checklist

**Week 1:**
- [ ] Update Stripe pricing to $29/month
- [ ] Set up 7-day free trial in Stripe
- [ ] Update app to show trial countdown

**Week 4:**
- [ ] Create annual pricing plan ($232/year)
- [ ] Add annual option to checkout flow
- [ ] Update landing page with pricing comparison

**Ongoing:**
- [ ] Track conversion rate by traffic source
- [ ] Monitor monthly churn (target: <10%)
- [ ] Collect user feedback on pricing
- [ ] Plan Pro tier features ($79/month)

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|---|---|
| Price too high | Low | A/B test; can lower to $25 if needed |
| Conversion rate drops | Low | SaaS pricing is inelastic for ±50% |
| Churn too high | Medium | Weekly product updates; community building |
| Competitor copies | Medium | Build community moat; expand feature set |

---

## Next Steps

1. **Today**: Approve $29/month pricing
2. **This week**: Update Stripe products and webhook handlers
3. **Next week**: Update landing page and marketing collateral
4. **Week 4**: Add annual pricing option + analytics dashboard
5. **Week 8**: Analyze pricing elasticity, adjust if needed

---

## References

Full analysis: See `/PRICING_STRATEGY.md` for detailed unit economics, competitive positioning, and go-to-market strategy.

Key assumptions:
- Stripe fees: 2.9% + $0.30 + 0.5% = 5% total
- Customer Acquisition Cost (CAC): $15-30 (from organic + paid channels)
- Monthly churn: 5-10% (aggressive but healthy for micro-SaaS)
- Trial conversion: 10-15% (industry standard)
- Organic growth potential: 150-200 trial signups in 90 days
