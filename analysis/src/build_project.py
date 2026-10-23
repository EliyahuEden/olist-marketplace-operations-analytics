"""Rebuild SQLite marts, quality evidence, dashboard payload and BI exports.
Run from any directory: python src/build_project.py. Dependencies: pandas, numpy.
"""
from pathlib import Path
import sqlite3, json, hashlib, urllib.request, zipfile, io
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; OUT.mkdir(parents=True,exist_ok=True)
TABLES={'orders':'olist_orders_dataset.csv','customers':'olist_customers_dataset.csv',
 'order_items':'olist_order_items_dataset.csv','payments':'olist_order_payments_dataset.csv',
 'reviews':'olist_order_reviews_dataset.csv','products':'olist_products_dataset.csv',
 'sellers':'olist_sellers_dataset.csv','category_translation':'product_category_name_translation.csv',
 'geolocation':'olist_geolocation_dataset.csv'}
if not all((RAW/f).exists() for f in TABLES.values()):
 RAW.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen('https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce',timeout=180) as r:
  with zipfile.ZipFile(io.BytesIO(r.read())) as z:
   for f in TABLES.values():
    (RAW/f).write_bytes(z.read(f))
db=sqlite3.connect(ROOT/'data/marketplace.sqlite')
frames={k:pd.read_csv(RAW/f) for k,f in TABLES.items()}
manifest={f:{'sha256':hashlib.sha256((RAW/f).read_bytes()).hexdigest(),'rows':len(frames[k])} for k,f in TABLES.items()}
(ROOT/'data/source_manifest.json').write_text(json.dumps(manifest,indent=2))
audit={'tables':{},'checks':[]}
for name,d in frames.items():
 d.to_sql(name,db,if_exists='replace',index=False,chunksize=10000)
 audit['tables'][name]={'rows':len(d),'exact_duplicate_rows':int(d.duplicated().sum()),
 'nulls':{k:int(v) for k,v in d.isna().sum().items()}}
def check(name, count, severity='HIGH',note=''):
 audit['checks'].append({'check':name,'exceptions':int(count),'severity':severity,'note':note})
for name,keys in [('orders',['order_id']),('customers',['customer_id']),('products',['product_id']),('sellers',['seller_id']),('order_items',['order_id','order_item_id'])]:
 check(name+' duplicate primary key',frames[name].duplicated(keys).sum())
for child,key,parent in [('orders','customer_id','customers'),('order_items','order_id','orders'),('payments','order_id','orders'),('reviews','order_id','orders'),('order_items','product_id','products'),('order_items','seller_id','sellers')]:
 check(f'{child}.{key} orphan to {parent}',(~frames[child][key].isin(frames[parent][key])).sum())
check('reviews multiple rows per order',frames['reviews'].duplicated('order_id').sum(),'MEDIUM','Latest answer timestamp retained; tie-break by creation timestamp then review_id.')
check('nonpositive item prices',(frames['order_items'].price<=0).sum())
check('negative freight',(frames['order_items'].freight_value<0).sum())
check('reviews outside 1-5',(~frames['reviews'].review_score.between(1,5)).sum())
db.executescript((ROOT/'sql/01_order_mart.sql').read_text())
f=pd.read_sql_query('SELECT * FROM fact_order',db)
assert len(f)==len(frames['orders']) and f.order_id.is_unique
assert abs(f.gmv.sum()-frames['order_items'].price.sum())<.01
assert abs(f.freight.sum()-frames['order_items'].freight_value.sum())<.01
assert abs(f.payment_value.sum()-frames['payments'].payment_value.sum())<.01
check('orders without items',(f.units==0).sum(),'MEDIUM','Preserved; not all orders complete checkout or fulfillment.')
check('delivered orders missing actual date',((f.order_status=='delivered') & f.order_delivered_customer_date.isna()).sum(),'MEDIUM','Excluded from delivery KPI denominator.')
check('negative delivery durations',(f.delivery_days<0).sum())
audit['reconciliation']={'source_item_value':float(frames['order_items'].price.sum()),'mart_item_value':float(f.gmv.sum()),'source_orders':len(frames['orders']),'mart_orders':len(f),'assertions_passed':True}
audit['freshness']='Historical snapshot: 2016-2018; not a current operating feed. Purchase window Jan 2017-Aug 2018 avoids sparse boundary months. Outcomes use available eventual delivery records.'
(OUT/'quality_report.json').write_text(json.dumps(audit,indent=2))
f.to_csv(OUT/'fact_order.csv',index=False)
items=pd.read_sql_query('SELECT * FROM fact_item',db);items.to_csv(OUT/'fact_item.csv',index=False)
for n in ['customers','sellers','products']:
 frames[n].to_csv(OUT/('dim_'+n+'.csv'),index=False)
calendar=pd.DataFrame({'date':pd.date_range('2016-01-01','2018-12-31')})
calendar['year']=calendar.date.dt.year;calendar['month']=calendar.date.dt.strftime('%Y-%m');calendar.to_csv(OUT/'dim_date.csv',index=False)
w=f[f.purchase_month.between('2017-01','2018-08')].copy()
deliv=w[w.order_status=='delivered']; e=w[w.delivery_eligible==1];rated=e[e.review_score.notna()]
stats={'orders':len(w),'delivered_orders':len(deliv),'delivered_gmv':round(deliv.gmv.sum(),2),
 'aov':round(deliv.gmv.mean(),2),'eligible':len(e),'late_orders':int(e.is_late.sum()),'late_rate':float(e.is_late.mean()),
 'review_coverage':float(e.review_score.notna().mean()),'low_rating_late':float((rated[rated.is_late==1].review_score<=2).mean()),
 'low_rating_ontime':float((rated[rated.is_late==0].review_score<=2).mean()),'median_days':float(e.delivery_days.median()),
 'single_seller_coverage':float((e.seller_count==1).mean())}
states=e.groupby('customer_state').agg(orders=('order_id','size'),late_orders=('is_late','sum'),late_rate=('is_late','mean'),gmv=('gmv','sum')).sort_values('late_orders',ascending=False)
states.to_csv(OUT/'state_performance.csv')
trend=deliv.groupby('purchase_month').agg(gmv=('gmv','sum'),orders=('order_id','size'));trend.to_csv(OUT/'monthly_performance.csv')
y=deliv[deliv.purchase_month.str[5:7]<='08'].groupby(deliv.purchase_month.str[:4]).gmv.sum()
stats['comparable_ytd_growth']=float(y['2018']/y['2017']-1)
# Retention: fixed 90-day opportunity; exclude first purchases after June 2, 2018.
# Completed-order identities only; history begins with dataset, not true lifetime acquisition.
history=f[f.order_status=='delivered'].copy();history['p']=pd.to_datetime(history.order_purchase_timestamp)
first=history.groupby('customer_unique_id').p.min().rename('first')
hx=history.join(first,on='customer_unique_id');hx['gap']=(hx.p-hx['first']).dt.total_seconds()/86400
repeat=hx[(hx.gap>0)&(hx.gap<=90)].customer_unique_id.unique()
co=first.to_frame();co['cohort']=co['first'].dt.strftime('%Y-%m');co['repeat90']=co.index.isin(repeat)
co=co[(co['first']>=pd.Timestamp('2017-01-01'))&(co['first']<pd.Timestamp('2018-09-01')-pd.Timedelta(days=90))]
cohorts=co.groupby('cohort').agg(customers=('repeat90','size'),repeat90=('repeat90','mean')).reset_index()
cohorts.to_csv(OUT/'cohort_90_day.csv',index=False)
stats['repeat90']=float(co.repeat90.mean());stats['repeat90_eligible']=len(co)
# Honest temporal risk validation. Training outcomes must already be observed by cutoff.
# No delivery dates, reviews or post-order signals used as model features.
train=e[(e.purchase_month<='2018-06')&(e.order_delivered_customer_date<'2018-07-01')]
test=e[e.purchase_month.between('2018-07','2018-08')].copy()
base=train.is_late.mean(); g=train.groupby(['customer_state','primary_category']).is_late.agg(['sum','count'])
g['risk']=(g['sum']+50*base)/(g['count']+50)
test=test.join(g.risk,on=['customer_state','primary_category']);test['risk']=test.risk.fillna(base)
cut=float(test.risk.quantile(.8));flag=test.risk>=cut
risk={'training_orders':len(train),'test_orders':len(test),'test_base_late_rate':float(test.is_late.mean()),
 'flagged_orders':int(flag.sum()),'flagged_late_rate':float(test[flag].is_late.mean()),
 'late_capture':float(test[flag].is_late.sum()/test.is_late.sum()),'threshold':cut,
 'method':'State × primary-category late rate; additive smoothing equivalent to 50 orders at training base rate. Train observed outcomes through June 30 2018; test July-August purchases. Top quintile threshold uses test feature scores only; ties may exceed 20%. Not a production calibrated probability model.'}
(OUT/'risk_validation.json').write_text(json.dumps(risk,indent=2))
test[['order_id','customer_state','primary_category','risk','is_late']].to_csv(OUT/'risk_holdout.csv',index=False)
(OUT/'headline_metrics.json').write_text(json.dumps(stats,indent=2))
# Compact browser payload: every order, no sampling; one category per order by max merchandise value.
cats=sorted(w.primary_category.unique().tolist());sts=sorted(w.customer_state.unique().tolist());months=sorted(w.purchase_month.unique().tolist())
seller_by_order=items.groupby('order_id').seller_id.first()
seller_ids=sorted(items.seller_id.unique()); smap={s:i for i,s in enumerate(seller_ids)}
w['seller']=w.order_id.map(seller_by_order).map(smap).fillna(-1).astype(int)
rows=[]
for r in w.itertuples():
 rows.append([months.index(r.purchase_month),sts.index(r.customer_state),cats.index(r.primary_category),round(r.gmv,2),round(r.freight,2),int(r.order_status=='delivered'),int(r.delivery_eligible),int(r.is_late) if pd.notna(r.is_late) else 0,round(r.delivery_days,2) if pd.notna(r.delivery_days) else None,int(r.review_score) if pd.notna(r.review_score) else None,int(r.seller) if r.seller_count==1 else -1])
payload={'months':months,'states':sts,'categories':cats,'seller_ids':seller_ids,'rows':rows,'stats':stats,'cohorts':cohorts.to_dict('records'),'risk':risk,'quality':audit,'source_rows':sum(len(x) for x in frames.values())}
(ROOT/'dashboard/data.js').write_text('window.DATA='+json.dumps(payload,separators=(',',':'))+';',encoding='utf-8')
db.close()
print(json.dumps({'metrics':stats,'risk':risk,'top_states':states.head(6).reset_index().to_dict('records')},indent=2))
