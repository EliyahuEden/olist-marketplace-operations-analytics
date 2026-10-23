"""Independent business-metric checks against source CSVs and dashboard payload."""
from pathlib import Path
import json,sqlite3
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
db=sqlite3.connect(ROOT/'data/marketplace.sqlite')
f=pd.read_sql_query('SELECT * FROM fact_order',db)
raw=pd.read_csv(ROOT/'data/raw/olist_order_items_dataset.csv')
orders=pd.read_csv(ROOT/'data/raw/olist_orders_dataset.csv')
checks=[]
def test(name,condition):
 if not condition: raise AssertionError(name)
 checks.append({'check':name,'status':'PASS'})
test('Order grain and unique ID match all source orders',len(f)==len(orders)==f.order_id.nunique())
test('Merchandise totals reconcile to raw item rows',abs(raw.price.sum()-f.gmv.sum())<.01)
test('Freight totals reconcile to raw item rows',abs(raw.freight_value.sum()-f.freight.sum())<.01)
window=orders[orders.order_purchase_timestamp.between('2017-01-01','2018-09-01',inclusive='left')]
di=window.loc[window.order_status.eq('delivered'),'order_id']
source_gmv=raw[raw.order_id.isin(di)].price.sum()
stats=json.loads((ROOT/'data/processed/headline_metrics.json').read_text())
test('Dashboard delivered GMV independently matches source status and items',abs(source_gmv-stats['delivered_gmv'])<.01)
eligible=window[window.order_status.eq('delivered')&window.order_delivered_customer_date.notna()&window.order_estimated_delivery_date.notna()]
source_late=(pd.to_datetime(eligible.order_delivered_customer_date).dt.normalize()>pd.to_datetime(eligible.order_estimated_delivery_date).dt.normalize()).sum()
test('Late count independently matches calendar-day source calculation',int(source_late)==stats['late_orders'])
test('All eligible deliveries accounted for',len(eligible)==stats['eligible'])
test('Missing delivered dates are excluded from reliability denominator',stats['delivered_orders']-stats['eligible']==8)
payload=json.loads((ROOT/'dashboard/data.js').read_text(encoding='utf-8').removeprefix('window.DATA=').removesuffix(';'))
test('Dashboard contains every order in the reporting window',len(payload['rows'])==len(window)==stats['orders'])
test('Browser payload reconciles delivered GMV',abs(sum(r[3] for r in payload['rows'] if r[5])-source_gmv)<.01)
test('Browser payload reconciles late-order count',sum(r[7] for r in payload['rows'])==int(source_late))
test('No missing durations in eligible browser records',all(r[8] is not None for r in payload['rows'] if r[6]))
sql='\n'.join(line for line in (ROOT/'sql/02_business_analysis.sql').read_text().splitlines() if not line.lstrip().startswith('--'))
for query in sql.split(';'):
 if query.strip():db.execute(query).fetchall()
test('All business SQL queries execute successfully',True)
test('All critical quality checks pass',all(c['exceptions']==0 for c in payload['quality']['checks'] if c['severity']=='HIGH'))
report={'checks':checks,'count':len(checks),'status':'PASS'}
(ROOT/'docs/verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));db.close()
