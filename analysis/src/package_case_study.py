"""Generate narrative, executed notebook and fully self-contained dashboard."""
from pathlib import Path
import json,sqlite3,math,io,contextlib,html,sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
stats=json.loads((ROOT/'data/processed/headline_metrics.json').read_text())
risk=json.loads((ROOT/'data/processed/risk_validation.json').read_text())
audit=json.loads((ROOT/'data/processed/quality_report.json').read_text())
db=sqlite3.connect(ROOT/'data/marketplace.sqlite')
f=pd.read_sql_query("SELECT * FROM fact_order WHERE purchase_month BETWEEN '2017-01' AND '2018-08'",db)
def wilson(k,n):
 z=1.96; p=k/n; denom=1+z*z/n; center=(p+z*z/(2*n))/denom; radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
 return center-radius,center+radius
def ci(k,n):return '–'.join(f'{x:.1%}' for x in wilson(k,n))
r=f[(f.delivery_eligible==1)&f.review_score.notna()]
late=r[r.is_late==1];on=r[r.is_late==0]
lo=int((late.review_score<=2).sum());oo=int((on.review_score<=2).sum())
rg=f[(f.delivery_eligible==1)&(f.customer_state=='RJ')]
top=pd.read_sql_query("""SELECT i.seller_id,COUNT(*) n,SUM(o.is_late) late
 FROM fact_order o JOIN (SELECT DISTINCT order_id,seller_id FROM fact_item) i USING(order_id)
 WHERE o.purchase_month BETWEEN '2017-01' AND '2018-08' AND o.delivery_eligible=1 AND o.seller_count=1
 GROUP BY 1 HAVING COUNT(*)>=100 ORDER BY late DESC""",db)
top10=int(top.head(10).late.sum())
brief=f'''# Olist Marketplace Intelligence

## Decision brief

Prioritize delivery reliability alongside growth. In this historical marketplace snapshot, delivered merchandise value reached **R$ {stats['delivered_gmv']:,.2f}** across **{stats['delivered_orders']:,} delivered orders** purchased Jan 2017–Aug 2018. **{stats['late_orders']:,} of {stats['eligible']:,} eligible deliveries were late ({stats['late_rate']:.1%})**. Comparable Jan–Aug delivered GMV grew **{stats['comparable_ytd_growth']:.1%}** in 2018 versus 2017; this is descriptive growth, not the effect of a known initiative.

### 1. Investigate Rio de Janeiro routes

**Finding:** RJ had {len(rg):,} eligible deliveries and {int(rg.is_late.sum()):,} late orders, a {rg.is_late.mean():.1%} late rate. It contributed {rg.is_late.sum()/stats['late_orders']:.1%} of late orders from {len(rg)/stats['eligible']:.1%} of eligible deliveries. Late-rate 95% Wilson interval: {ci(int(rg.is_late.sum()),len(rg))}.

**So what:** RJ combines meaningful exception volume with a high rate. SP has more absolute late orders (1,817) but a much lower 4.5% rate; both volume and reliability matter.

**Why:** Destination, seller mix, dispatch timing and logistics may differ; the available data does not identify a carrier-level cause.

**Next move:** Logistics lead audits RJ lanes and handoffs, stratified by seller/category and dispatch lag. Pilot an intervention on matched routes before broader rollout. Track late rate, actual lead time, freight burden and delivery coverage. **Confidence:** high in the descriptive location signal, low in any causal explanation.

### 2. Test customer communication around delivery exceptions

**Finding:** {lo:,}/{len(late):,} reviewed late orders received 1–2 stars ({lo/len(late):.1%}; 95% Wilson {ci(lo,len(late))}), versus {oo:,}/{len(on):,} on-time reviewed orders ({oo/len(on):.1%}; {ci(oo,len(on))}). The observed difference is {(lo/len(late)-oo/len(on))*100:.1f} percentage points.

**So what:** Late deliveries are a strong customer-experience warning. This is an association, not proof that eliminating a delay or adding a message would create the same rating improvement. Overall review coverage among eligible deliveries is {stats['review_coverage']:.1%}; missing responses can still be nonrandom.

**Next move:** CX lead randomizes eligible orders into proactive updates vs usual communication. Predefine the observation window, useful effect and sample size; track low-rating rate, review response, complaint contacts, cancellation and cost. **Confidence:** high in the descriptive difference; intervention effect unknown.

### 3. Work the seller queue by exception volume

**Finding:** The 10 sellers with the most late eligible single-seller orders account for {top10:,} late orders ({top10/stats['late_orders']:.1%} of all eligible late orders). Seller outcomes are attributable to an order, not necessarily to the seller's actions. Single-seller orders cover {stats['single_seller_coverage']:.1%} of eligible deliveries.

**Next move:** Seller operations reviews the highest-volume queue, examines route/category mix and dispatch evidence, and agrees a measurable recovery plan. Queue inclusion requires at least 100 eligible deliveries. Compare treatment with matched untreated sellers to reduce regression-to-the-mean mistakes. **Confidence:** high in counts, medium in prioritization, low in causal blame.

### 4. Do not deploy the simple risk rule

**Finding:** A state × primary-category historical-rate flag captured {risk['late_capture']:.1%} of holdout late orders while flagging {risk['flagged_orders']/risk['test_orders']:.1%} of deliveries. Flagged late rate was {risk['flagged_late_rate']:.2%} versus {risk['test_base_late_rate']:.2%} baseline; lift {risk['flagged_late_rate']/risk['test_base_late_rate']:.2f}×. It failed out-of-time validation.

**Next move:** Reject the rule for operations. Add carrier, dispatch and richer route features if obtained; use an outcome-maturation embargo and rolling temporal tests. Training only includes outcomes observed by June 30, which can bias the boundary sample toward faster deliveries. **Confidence:** high that this particular tested rule did not provide useful ranking in this holdout; not evidence that all risk prediction is impossible.

### 5. Treat repeat purchase as another question

**Finding:** Fixed 90-day observed repeat purchase was {stats['repeat90']:.2%} among {stats['repeat90_eligible']:,} eligible first-observed buyers. Only complete follow-up windows are used. Identities use customer_unique_id, not per-order customer_id.

**Next move:** Validate whether Olist's marketplace coverage and categories make repeat purchase a useful goal before designing lifecycle campaigns. Purchase history outside the public extract is unobserved. This is neither lifetime churn nor a subscription-retention measure.

## Planning scenario, not forecast

A 20% relative reduction in the selected full-window late-order pool would correspond to **{round(stats['late_orders']*.2):,} avoided late orders**, lowering the rate from {stats['late_rate']:.1%} to {stats['late_rate']*.8:.1%}, assuming unchanged volume. No realized reduction, revenue uplift, savings or profit impact has been measured. The dashboard slider recomputes this assumption for the current filters.

## Reliability and interpretation

The source has 1,550,922 records across nine tables. All 99,441 source orders are preserved in the mart; the dashboard reporting window includes 99,092. Order, item-value, freight and payment totals reconcile. There are no orphan keys in the tested relationships. The 551 additional review rows are version-selected; eight delivered orders without actual dates are excluded from the delivery denominator. Full null counts are retained. 95% Wilson intervals describe binomial sampling uncertainty; these historical records are not a random sample of the company's present-day business and intervals do not capture confounding.

This portfolio project uses actual anonymized historical records, not generated sample data. It is an independent case study, not an Olist client engagement. It cannot support current company claims, margin analysis or causal uplift estimates.

Source: [Olist public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), CC BY-NC-SA 4.0. Accessed October 23, 2026. Metric details: METRIC_CONTRACT.md. SQL and Python code accompany every calculation.
'''
(ROOT/'docs/FINDINGS.md').write_text(brief,encoding='utf-8')
quality_rows=''.join(f"<tr><td>{html.escape(c['check'])}</td><td>{c['exceptions']:,}</td><td>{c['severity']}</td><td>{html.escape(c['note'])}</td></tr>" for c in audit['checks'])
profiles=''.join(f"<h2>{name} · {info['rows']:,} rows</h2><p>Exact duplicate rows: {info['exact_duplicate_rows']:,}</p><table><tr><th>Column</th><th>Missing</th><th>Missing %</th></tr>"+''.join(f'<tr><td>{col}</td><td>{v:,}</td><td>{v/info["rows"]:.1%}</td></tr>' for col,v in info['nulls'].items())+'</table>' for name,info in audit['tables'].items())
quality=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Olist | Data quality report</title><style>body{{font:14px/1.6 'Segoe UI',sans-serif;color:#292842;background:#f5f6fa;max-width:1050px;margin:45px auto;padding:25px}}h1{{font-size:33px}}h2{{margin-top:35px}}table{{border-collapse:collapse;width:100%;background:white;font-size:12px}}td,th{{padding:10px;border-bottom:1px solid #ececf3;text-align:left}}th{{color:#7460df}}.badge{{padding:15px;background:#eae5fa;border-radius:8px}}p{{color:#7d7b8b}}@media print{{body{{margin:0;background:white}}table{{break-inside:auto}}tr{{break-inside:avoid}}}}</style><h1>Data quality, made visible.</h1><p>Olist Marketplace Intelligence · October 23, 2026</p><div class="badge">Critical integrity checks passed. Marts reconcile to source order, merchandise, freight and payment totals.</div><p>{audit['freshness']}</p><h2>Business-rule exceptions</h2><table><tr><th>Check</th><th>Exceptions</th><th>Severity</th><th>Treatment</th></tr>{quality_rows}</table><h2>Column completeness</h2>{profiles}</html>'''
(ROOT/'docs/DATA_QUALITY.html').write_text(quality,encoding='utf-8')
# Standard notebook JSON, with code genuinely executed below and captured outputs.
cells=[];env={}
def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(keepends=True)})
def code(s):
 stream=io.StringIO()
 with contextlib.redirect_stdout(stream):exec(s,env)
 count=sum(c['cell_type']=='code' for c in cells)+1
 cells.append({'cell_type':'code','metadata':{},'source':s.splitlines(keepends=True),'execution_count':count,'outputs':[{'output_type':'stream','name':'stdout','text':stream.getvalue().splitlines(keepends=True)}]})
md('# Olist Marketplace Intelligence\nA reproducible SQL + Python investigation of growth, fulfillment and customer experience.\n\nQuestion: where should a marketplace operations team intervene first? Data is historical (2016–2018), not current company performance. Original data and license: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce')
code(f'''from pathlib import Path
import sqlite3, json
import pandas as pd
ROOT = Path.cwd()
if not (ROOT / 'data/marketplace.sqlite').exists():
    ROOT = ROOT.parent
# Run from the project root or notebooks folder after src/build_project.py.
db = sqlite3.connect(ROOT / 'data/marketplace.sqlite')
print(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", db).to_string(index=False))
'''.replace('ROOT = Path.cwd()',f"ROOT = Path({str(ROOT)!r})"))
# Replace only notebook source with a portable locator after execution.
cells[-1]['source']='''from pathlib import Path
import sqlite3, json
import pandas as pd
ROOT = Path.cwd()
if not (ROOT / 'data/marketplace.sqlite').exists():
    ROOT = ROOT.parent
db = sqlite3.connect(ROOT / 'data/marketplace.sqlite')
print(pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", db).to_string(index=False))
'''.splitlines(keepends=True)
md('## 1. Validate the grain before calculating KPIs\nEvery source order must appear exactly once. Child-table aggregation is implemented in sql/01_order_mart.sql. Full missingness and integrity checks are in docs/DATA_QUALITY.html.')
code('''print(pd.read_sql_query("""SELECT COUNT(*) rows,COUNT(DISTINCT order_id) unique_orders,
 SUM(gmv) item_value,SUM(freight) freight,SUM(payment_value) payment_value FROM fact_order""",db).to_string(index=False))
audit=json.loads((ROOT/'data/processed/quality_report.json').read_text())
print(pd.DataFrame(audit['checks'])[['check','exceptions','severity']].to_string(index=False))
''')
md('## 2. Define the executive scorecard\nDelivered GMV is item merchandise value, not company revenue. Late rate compares calendar dates among delivered orders with both dates recorded.')
code('''f=pd.read_sql_query("SELECT * FROM fact_order WHERE purchase_month BETWEEN '2017-01' AND '2018-08'",db)
print(json.dumps(json.loads((ROOT/'data/processed/headline_metrics.json').read_text()),indent=2))
''')
md('## 3. Compare like-for-like growth\nBoth years use Jan–Aug delivered purchases. Comparing all of 2017 with only part of 2018 would mislead.')
code('''print(pd.read_sql_query("""SELECT substr(purchase_month,1,4) year,COUNT(*) delivered_orders,SUM(gmv) gmv
 FROM fact_order WHERE order_status='delivered' AND purchase_month BETWEEN '2017-01' AND '2018-08'
 AND substr(purchase_month,6,2)<='08' GROUP BY 1""",db).to_string(index=False))
''')
md('## 4. Diagnose route concentration\nRank by late count as well as rate; tiny high-rate segments should not dominate the improvement queue.')
code('''e=f[f.delivery_eligible.eq(1)]
state=e.groupby('customer_state').agg(eligible=('order_id','size'),late=('is_late','sum'),late_rate=('is_late','mean'))
state['late_share']=state.late/state.late.sum()
print(state.sort_values('late',ascending=False).head(10).to_string())
''')
md('## 5. Quantify customer experience association\nLatest review per order; low rating is 1–2 stars. This is descriptive and potentially confounded. It does not measure the impact of a communication intervention.')
code('''rated=e[e.review_score.notna()].copy()
rated['low']=rated.review_score.le(2)
print(rated.groupby('is_late').agg(rated_orders=('order_id','size'),low_ratings=('low','sum'),low_rating_rate=('low','mean'),avg_score=('review_score','mean')).to_string())
''')
md('## 6. Avoid incomplete retention windows\nIdentity uses customer_unique_id. Only first-observed delivered purchasers with 90 days of follow-up opportunity are included. The source does not reveal purchases outside Olist marketplaces.')
code('''print(pd.read_csv(ROOT/'data/processed/cohort_90_day.csv').to_string(index=False))
''')
md('## 7. Reject a weak advance risk flag\nState × category late history, smoothed with 50 pseudo-orders. Training labels must already be observed before July 2018. Holdout is July–August purchases. Ranking below the baseline is a failed test, not a successful model. Outcome-maturation selection and time drift need further work.')
code('''print(json.dumps(json.loads((ROOT/'data/processed/risk_validation.json').read_text()),indent=2))
db.close()
''')
md('## 8. Recommendation and measurement\nAudit RJ lanes; investigate high-volume seller exceptions; run a randomized proactive-communication pilot. Track late rate, low ratings, response coverage and contact cost. Use the dashboard scenario only as a planning assumption. No realized savings or uplift is claimed.\n\nSee docs/FINDINGS.md for the full decision brief and docs/METRIC_CONTRACT.md for definitions.')
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}},'cells':cells}
for i,c in enumerate(nb['cells']):c['id']=f'olist-{i:03}'
(ROOT/'notebooks').mkdir(exist_ok=True)
(ROOT/'notebooks/marketplace_analysis.ipynb').write_text(json.dumps(nb,indent=1),encoding='utf-8')
# Completely offline: data, style and behavior are embedded; no CDN or server required.
index=(ROOT/'dashboard/index.html').read_text(encoding='utf-8')
index=index.replace('<link rel="stylesheet" href="style.css">','<style>'+(ROOT/'dashboard/style.css').read_text(encoding='utf-8')+'</style>')
index=index.replace('<script src="data.js"></script>','<script>'+(ROOT/'dashboard/data.js').read_text(encoding='utf-8')+'</script>')
index=index.replace('<script src="app.js"></script>','<script>'+(ROOT/'dashboard/app.js').read_text(encoding='utf-8')+'</script>')
(ROOT/'dashboard/OPEN_DASHBOARD.html').write_text(index,encoding='utf-8')
db.close()
print('Created findings, quality HTML, executed notebook, and standalone offline dashboard.')
