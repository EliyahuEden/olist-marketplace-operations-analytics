"""Reproduce native PBIP semantic model and PBIR visuals from the analyzed Olist snapshot.
Uses portable native DAX snapshot tables; no absolute source paths or credentials.
"""
from pathlib import Path
import json,sqlite3,uuid,hashlib,datetime
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'analysis'
REPORT=ROOT/'Olist.Report'; DEF=REPORT/'definition'; MODEL=ROOT/'Olist.SemanticModel'
MODEL.mkdir(exist_ok=True)
def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def ident(s):return hashlib.sha256(s.encode()).hexdigest()[:20]
def guid():return str(uuid.uuid4())
tables=[]
def table(name,df,types,sorts=None,hidden=None):
 df=df.copy().astype(object).where(pd.notna(df),None)
 rows=df.values.tolist()
 # Native DATATABLE snapshots avoid an environment-specific Power Query COM failure.
 # These are actual source-derived values, not synthetic records. Python/SQL owns refresh.
 def dax(v):
  if v is None:return 'BLANK()'
  if isinstance(v,str):return '"'+v.replace('"','""')+'"'
  if isinstance(v,(bool,np.bool_)):return 'TRUE()' if v else 'FALSE()'
  return repr(float(v)) if isinstance(v,(float,np.floating)) else str(int(v))
 header=', '.join('"'+c+'", '+{'string':'STRING','double':'DOUBLE','int64':'INTEGER','boolean':'BOOLEAN'}[types[c]] for c in df.columns)
 expression='DATATABLE(\n'+header+',\n{\n'+',\n'.join('{'+','.join(dax(v) for v in row)+'}' for row in rows)+'\n})'
 columns=[]
 for c in df.columns:
  col={'name':c,'dataType':types[c],'type':'calculatedTableColumn','sourceColumn':'['+c+']','summarizeBy':'none','lineageTag':guid()}
  if sorts and c in sorts:col['sortByColumn']=sorts[c]
  if hidden and c in hidden:col['isHidden']=True
  columns.append(col)
 t={'name':name,'lineageTag':guid(),'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'calculated','expression':expression}}]}
 tables.append(t);return t

db=sqlite3.connect(SOURCE/'data/marketplace.sqlite')
f=pd.read_sql_query("SELECT * FROM fact_order WHERE purchase_month BETWEEN '2017-01' AND '2018-08'",db)
it=pd.read_sql_query('SELECT DISTINCT order_id,seller_id FROM fact_item',db)
seller=it.groupby('order_id').seller_id.first()
f['SingleSellerId']=f.order_id.map(seller).where(f.seller_count.eq(1))
bands=pd.cut(f.delivery_days,[-np.inf,7,14,21,30,60,np.inf],right=False,labels=['Under 7 days','7–13 days','14–20 days','21–29 days','30–59 days','60+ days'])
orders=pd.DataFrame({'OrderKey':np.arange(1,len(f)+1),'MonthKey':f.purchase_month.str.replace('-','').astype(int),'State':f.customer_state,
 'Category':f.primary_category.str.replace('_',' ').str.title(),'GMV':f.gmv,'Freight':f.freight,'Status':f.order_status,
 'Eligible':f.delivery_eligible,'Late':f.is_late,'DeliveryDays':f.delivery_days,'ReviewScore':f.review_score,
 'SingleSellerId':f.SingleSellerId,'DeliveryBand':bands.astype(object),
 'DeliveryBandOrder':bands.cat.codes.replace(-1,np.nan),'DeliveryOutcome':np.where(f.delivery_eligible.ne(1),None,np.where(f.is_late.eq(1),'Late','On-time'))})
types={c:'string' for c in orders.columns}
for c in ['OrderKey','MonthKey','Eligible','Late','ReviewScore','DeliveryBandOrder']:types[c]='int64'
for c in ['GMV','Freight','DeliveryDays']:types[c]='double'
ot=table('Orders',orders,types,{'DeliveryBand':'DeliveryBandOrder'},['OrderKey','MonthKey','DeliveryBandOrder','SingleSellerId'])
monthkeys=sorted(orders.MonthKey.unique().tolist())
mt=table('Months',pd.DataFrame({'MonthKey':monthkeys,'Month':[datetime.datetime.strptime(str(k),'%Y%m').strftime('%b %y') for k in monthkeys]}),{'MonthKey':'int64','Month':'string'},{'Month':'MonthKey'},['MonthKey'])
mt['columns'].append({'name':'MonthStart','dataType':'dateTime','type':'calculated','expression':'DATE(INT(Months[MonthKey]/100), MOD(Months[MonthKey],100), 1)','formatString':'MMM yyyy','summarizeBy':'none','lineageTag':guid()})
table('States',pd.DataFrame({'State':sorted(orders.State.unique())}),{'State':'string'})
table('Categories',pd.DataFrame({'Category':sorted(orders.Category.unique())}),{'Category':'string'})
s=pd.read_sql_query('SELECT seller_id SellerId,seller_state State,seller_city City FROM sellers',db)
table('Sellers',s,{c:'string' for c in s.columns})
co=pd.read_csv(SOURCE/'data/processed/cohort_90_day.csv');co.columns=['Cohort','Customers','Repeat90'];table('Cohorts',co,{'Cohort':'string','Customers':'int64','Repeat90':'double'})
stats=json.loads((SOURCE/'data/processed/headline_metrics.json').read_text());risk=json.loads((SOURCE/'data/processed/risk_validation.json').read_text())
benchmark=pd.DataFrame([{'YTDGrowth':stats['comparable_ytd_growth'],'Repeat90':stats['repeat90'],'RepeatEligible':stats['repeat90_eligible'],
 'RiskBaseRate':risk['test_base_late_rate'],'RiskFlaggedRate':risk['flagged_late_rate'],'RiskLift':risk['flagged_late_rate']/risk['test_base_late_rate'],'RiskCapture':risk['late_capture']}])
table('Benchmarks',benchmark,{c:('int64' if c=='RepeatEligible' else 'double') for c in benchmark.columns})
table('Reduction',pd.DataFrame({'Value':list(range(0,51,5))}),{'Value':'int64'})
measures=[]
def measure(name,expr,fmt=None,folder='Business KPIs'):
 m={'name':name,'expression':expr,'lineageTag':guid(),'displayFolder':folder}
 if fmt:m['formatString']=fmt
 measures.append(m)
measure('Orders','COUNTROWS(Orders)','#,0')
measure('Delivered Orders','CALCULATE([Orders], Orders[Status] = "delivered")','#,0')
measure('Delivered GMV','CALCULATE(SUM(Orders[GMV]), Orders[Status] = "delivered")','"R$ "#,0.00')
measure('AOV','DIVIDE([Delivered GMV], [Delivered Orders])','"R$ "#,0')
measure('Eligible Deliveries','CALCULATE([Orders], Orders[Eligible] = 1)','#,0')
measure('Late Orders','CALCULATE([Orders], Orders[Eligible] = 1, Orders[Late] = 1)','#,0')
measure('Late Rate','DIVIDE([Late Orders], [Eligible Deliveries])','0.0%')
measure('On Time Rate','IF([Eligible Deliveries]>0, 1-[Late Rate])','0.0%')
measure('Reviewed Deliveries','CALCULATE([Eligible Deliveries], KEEPFILTERS(NOT ISBLANK(Orders[ReviewScore])))','#,0')
measure('Average Review','CALCULATE(AVERAGE(Orders[ReviewScore]), Orders[Eligible]=1)','0.00')
measure('Low Rating Rate','DIVIDE(CALCULATE([Reviewed Deliveries], Orders[ReviewScore] IN {1,2}), [Reviewed Deliveries])','0.0%')
measure('Low Rating Late','CALCULATE([Low Rating Rate], Orders[Late]=1)','0.0%')
measure('Low Rating On Time','CALCULATE([Low Rating Rate], Orders[Late]=0)','0.0%')
measure('Rating Risk Ratio','DIVIDE([Low Rating Late],[Low Rating On Time])','0.0"×"')
measure('Median Delivery Days','CALCULATE(MEDIAN(Orders[DeliveryDays]), Orders[Eligible]=1)','0.0" days"')
measure('Freight Ratio','DIVIDE(CALCULATE(SUM(Orders[Freight]),Orders[Status]="delivered"),[Delivered GMV])','0.0%')
measure('GMV Headline','"R$ " & FORMAT(DIVIDE([Delivered GMV],1000000),"0.00") & "M"',folder='Display')
measure('Delivered Caption','FORMAT([Delivered Orders],"#,0") & " delivered orders · excludes freight"',folder='Display')
measure('Late Caption','FORMAT([Late Orders],"#,0") & " late / " & FORMAT([Eligible Deliveries],"#,0") & " eligible"',folder='Display')
measure('Review Caption','FORMAT([Reviewed Deliveries],"#,0") & " reviewed eligible deliveries"',folder='Display')
measure('Scope Caption','FORMAT([Orders],"#,0") & " orders in view"',folder='Display')
measure('Growth Benchmark','MAX(Benchmarks[YTDGrowth])','+0.0%;-0.0%',folder='Fixed benchmarks')
measure('Repeat Benchmark','MAX(Benchmarks[Repeat90])','0.0%',folder='Fixed benchmarks')
for n,col,fmt in [('Risk Base Rate','RiskBaseRate','0.0%'),('Risk Flagged Rate','RiskFlaggedRate','0.0%'),('Risk Lift','RiskLift','0.00"×"'),('Risk Capture','RiskCapture','0.0%')]:measure(n,f'MAX(Benchmarks[{col}])',fmt,'Fixed benchmarks')
measure('Cohort Repeat Rate','MAX(Cohorts[Repeat90])','0.0%',folder='Fixed benchmarks')
measure('Cohort Buyers','SUM(Cohorts[Customers])','#,0',folder='Fixed benchmarks')
measure('Reduction Rate','DIVIDE(SELECTEDVALUE(Reduction[Value],20),100)','0%',folder='Scenario')
measure('Avoided Late Orders','ROUND([Late Orders]*[Reduction Rate],0)','#,0','Scenario')
measure('Scenario Late Rate','[Late Rate]*(1-[Reduction Rate])','0.0%','Scenario')
measure('Scenario Caption','FORMAT([Late Rate],"0.0%") & " → " & FORMAT([Scenario Late Rate],"0.0%") & " late rate"',folder='Scenario')
measure('Top Category GMV','IF(RANKX(ALLSELECTED(Categories[Category]),[Delivered GMV],,DESC,Dense)<=6,[Delivered GMV])','"R$ "#,0','Ranking')
measure('Top State Late Orders','IF(RANKX(ALLSELECTED(States[State]),[Late Orders],,DESC,Dense)<=6,[Late Orders])','#,0','Ranking')
measure('Eligible Share','DIVIDE([Eligible Deliveries],CALCULATE([Eligible Deliveries],REMOVEFILTERS(States)))','0.0%')
measure('Delivery Band Share','DIVIDE([Eligible Deliveries],CALCULATE([Eligible Deliveries],REMOVEFILTERS(Orders[DeliveryBand],Orders[DeliveryBandOrder])))','0.0%')
measure('Seller Eligible','CALCULATE([Eligible Deliveries],NOT ISBLANK(Orders[SingleSellerId]))','#,0','Seller investigation')
measure('Seller Late','CALCULATE([Late Orders],NOT ISBLANK(Orders[SingleSellerId]))','#,0','Seller investigation')
measure('Seller Rate','DIVIDE([Seller Late],[Seller Eligible])','0.0%','Seller investigation')
for n,e,fmt in [('Queue Eligible','[Seller Eligible]','#,0'),('Queue Late','[Seller Late]','#,0'),('Queue Rate','[Seller Rate]','0.0%'),('Queue GMV','[Delivered GMV]','"R$ "#,0')]:
 measure(n,'IF([Seller Eligible]>=100 && NOT ISBLANK(SELECTEDVALUE(Sellers[SellerId])), '+e+')',fmt,'Seller investigation')
ot['measures']=measures
relationships=[]
for dim,dcol,fcol in [('Months','MonthKey','MonthKey'),('States','State','State'),('Categories','Category','Category'),('Sellers','SellerId','SingleSellerId')]:
 relationships.append({'name':guid(),'fromTable':'Orders','fromColumn':fcol,'toTable':dim,'toColumn':dcol,'crossFilteringBehavior':'oneDirection'})
model={'name':'Olist','compatibilityLevel':1601,'model':{'culture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','tables':tables,'relationships':relationships,'annotations':[{'name':'PBI_QueryOrder','value':json.dumps([t['name'] for t in tables])},{'name':'PBI_TimeIntelligenceEnabled','value':'0'}]}}
dump(MODEL/'model.bim',model)
dump(MODEL/'definition.pbism',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'4.2','settings':{'qnaEnabled':False}})
dump(MODEL/'.platform',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json','metadata':{'type':'SemanticModel','displayName':'Olist'},'config':{'version':'2.0','logicalId':guid()}})
db.close()
print(f'Native semantic model: {len(orders):,} orders; {len(tables)} tables; {len(measures)} DAX measures.',flush=True)

# Restore the reviewed business report template after rebuilding the semantic snapshot.
import shutil
template=Path(__file__).resolve().parent/'report_template'
for name in ['definition','StaticResources']:
 target=REPORT/name
 if target.exists():
  assert target.resolve().is_relative_to(ROOT.resolve())
  shutil.rmtree(target)
 shutil.copytree(template/name,target)
print('Restored reviewed business dashboard layout.')
