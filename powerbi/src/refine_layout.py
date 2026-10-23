"""Apply desktop-rendered layout refinements without rebuilding the semantic model."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def literal(value):return {'expr':{'Literal':{'Value':str(value)+'D' if isinstance(value,(int,float)) else "'"+value+"'"}}}
def refine():
 for p in (ROOT/'Olist.Report/definition/pages').rglob('visual.json'):
  d=json.loads(p.read_text(encoding='utf-8'));v=d['visual'];objs=v.get('objects',{})
  if v['visualType'] in ['areaChart','barChart']:
   objs.setdefault('categoryAxis',[{'properties':{}}])[0]['properties']['preferredCategoryWidth']=literal(14)
  if v['visualType']=='tableEx' and 'query' in v:
   projections=v['query']['queryState']['Values']['projections']
   if any(x['queryRef']=='Orders.Queue Late' for x in projections):
    widths=[430,180,150,150,190]
    objs['columnWidth']=[{'properties':{'value':literal(w)},'selector':{'metadata':pr['queryRef']}} for pr,w in zip(projections,widths)]
    objs.setdefault('grid',[{'properties':{}}])[0]['properties']['rowPadding']=literal(3)
  if v['visualType']=='textbox':
   paras=objs.get('general',[{'properties':{}}])[0]['properties'].get('paragraphs',[])
   text=' '.join(run.get('value','') for para in paras for run in para.get('textRuns',[]))
   if text.startswith('OLIST ANALYTICS'):
    d['position']['y']-=12;d['position']['height']=66
    for para in paras:
     for run in para.get('textRuns',[]):run['textStyle']['fontSize']='8pt'
  p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
 print('Refined categorical chart widths, seller table spacing, and sidebar footer.')
if __name__=='__main__':refine()
