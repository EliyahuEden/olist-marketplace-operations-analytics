# Olist Marketplace Intelligence

## Decision brief

Prioritize delivery reliability alongside growth. In this historical marketplace snapshot, delivered merchandise value reached **R$ 13,181,027.13** across **96,211 delivered orders** purchased Jan 2017–Aug 2018. **6,531 of 96,203 eligible deliveries were late (6.8%)**. Comparable Jan–Aug delivered GMV grew **141.1%** in 2018 versus 2017; this is descriptive growth, not the effect of a known initiative.

### 1. Investigate Rio de Janeiro routes

**Finding:** RJ had 12,310 eligible deliveries and 1,495 late orders, a 12.1% late rate. It contributed 22.9% of late orders from 12.8% of eligible deliveries. Late-rate 95% Wilson interval: 11.6%–12.7%.

**So what:** RJ combines meaningful exception volume with a high rate. SP has more absolute late orders (1,817) but a much lower 4.5% rate; both volume and reliability matter.

**Why:** Destination, seller mix, dispatch timing and logistics may differ; the available data does not identify a carrier-level cause.

**Next move:** Logistics lead audits RJ lanes and handoffs, stratified by seller/category and dispatch lag. Pilot an intervention on matched routes before broader rollout. Track late rate, actual lead time, freight burden and delivery coverage. **Confidence:** high in the descriptive location signal, low in any causal explanation.

### 2. Test customer communication around delivery exceptions

**Finding:** 3,981/6,378 reviewed late orders received 1–2 stars (62.4%; 95% Wilson 61.2%–63.6%), versus 8,247/89,182 on-time reviewed orders (9.2%; 9.1%–9.4%). The observed difference is 53.2 percentage points.

**So what:** Late deliveries are a strong customer-experience warning. This is an association, not proof that eliminating a delay or adding a message would create the same rating improvement. Overall review coverage among eligible deliveries is 99.3%; missing responses can still be nonrandom.

**Next move:** CX lead randomizes eligible orders into proactive updates vs usual communication. Predefine the observation window, useful effect and sample size; track low-rating rate, review response, complaint contacts, cancellation and cost. **Confidence:** high in the descriptive difference; intervention effect unknown.

### 3. Work the seller queue by exception volume

**Finding:** The 10 sellers with the most late eligible single-seller orders account for 1,019 late orders (15.6% of all eligible late orders). Seller outcomes are attributable to an order, not necessarily to the seller's actions. Single-seller orders cover 98.7% of eligible deliveries.

**Next move:** Seller operations reviews the highest-volume queue, examines route/category mix and dispatch evidence, and agrees a measurable recovery plan. Queue inclusion requires at least 100 eligible deliveries. Compare treatment with matched untreated sellers to reduce regression-to-the-mean mistakes. **Confidence:** high in counts, medium in prioritization, low in causal blame.

### 4. Do not deploy the simple risk rule

**Finding:** A state × primary-category historical-rate flag captured 18.1% of holdout late orders while flagging 20.2% of deliveries. Flagged late rate was 4.31% versus 4.81% baseline; lift 0.90×. It failed out-of-time validation.

**Next move:** Reject the rule for operations. Add carrier, dispatch and richer route features if obtained; use an outcome-maturation embargo and rolling temporal tests. Training only includes outcomes observed by June 30, which can bias the boundary sample toward faster deliveries. **Confidence:** high that this particular tested rule did not provide useful ranking in this holdout; not evidence that all risk prediction is impossible.

### 5. Treat repeat purchase as another question

**Finding:** Fixed 90-day observed repeat purchase was 2.01% among 75,439 eligible first-observed buyers. Only complete follow-up windows are used. Identities use customer_unique_id, not per-order customer_id.

**Next move:** Validate whether Olist's marketplace coverage and categories make repeat purchase a useful goal before designing lifecycle campaigns. Purchase history outside the public extract is unobserved. This is neither lifetime churn nor a subscription-retention measure.

## Planning scenario, not forecast

A 20% relative reduction in the selected full-window late-order pool would correspond to **1,306 avoided late orders**, lowering the rate from 6.8% to 5.4%, assuming unchanged volume. No realized reduction, revenue uplift, savings or profit impact has been measured. The dashboard slider recomputes this assumption for the current filters.

## Reliability and interpretation

The source has 1,550,922 records across nine tables. All 99,441 source orders are preserved in the mart; the dashboard reporting window includes 99,092. Order, item-value, freight and payment totals reconcile. There are no orphan keys in the tested relationships. The 551 additional review rows are version-selected; eight delivered orders without actual dates are excluded from the delivery denominator. Full null counts are retained. 95% Wilson intervals describe binomial sampling uncertainty; these historical records are not a random sample of the company's present-day business and intervals do not capture confounding.

This portfolio project uses actual anonymized historical records, not generated sample data. It is an independent case study, not an Olist client engagement. It cannot support current company claims, margin analysis or causal uplift estimates.

Source: [Olist public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), CC BY-NC-SA 4.0. Accessed October 23, 2026. Metric details: METRIC_CONTRACT.md. SQL and Python code accompany every calculation.
