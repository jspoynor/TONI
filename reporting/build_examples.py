"""Adapt human-authored answer keys into structured rule-test fixtures. NOT OCR parsing."""
from pathlib import Path
from copy import deepcopy
import json
from reporting import Draft,validate,review_hash,submit
HERE=Path(__file__).parent;SRC=HERE.parent/'sample-data/developer';OUT=HERE/'examples'
def convert(filename):
 old=json.loads((SRC/filename).read_text());q=old['request']
 req={k:q[k] for k in ['company_id','frequency','period_start','period_end','due_date','currency','required_fields','arr_applicable']}
 req.update(request_id='demo-careflow-2026-08',max_questions=3)
 fields={}
 for name,f in old['fields'].items():
  if f['value'] is None: fields[name]={'candidates':[]};continue
  c={'id':name+'-document','company_id':req['company_id'],'request_id':req['request_id'],'value':f['value'],
     'currency':f['currency'],'unit':'base_units' if f['unit']=='dollars' else None,
     'period_start':f['period_start'],'period_end':f['period_end'],'as_of_date':f['as_of_date'],
     'definition':f.get('definition'),
     'source':{'kind':'document','file':f['source']['file'],'page':f['source']['page'],'quote':f['source']['label']}}
  # Narrative is manually assigned to the report period from the management update header.
  if isinstance(f['value'],str):c.update(period_start=req['period_start'],period_end=req['period_end'])
  fields[name]={'candidates':[c]}
 return {'request':req,'fields':fields}
complete=convert('expected_complete.json');missing=convert('expected_income_only.json')
conflict=deepcopy(complete)
c=deepcopy(complete['fields']['cash_on_hand']['candidates'][0]);c.update(id='cash-note',value=450000,currency=None,unit=None,source={'kind':'document','file':'04_ambiguous_conflicting_note.pdf','page':1,'quote':'Cash at August 31, 2026: 450,000'})
conflict['fields']['cash_on_hand']['candidates'].append(c)
c=deepcopy(complete['fields']['revenue']['candidates'][0]);c.update(id='revenue-note',value=120,currency=None,unit=None,period_start=None,period_end=None,source={'kind':'document','file':'04_ambiguous_conflicting_note.pdf','page':1,'quote':'Revenue: 120'})
conflict['fields']['revenue']['candidates'].append(c)
wrong=deepcopy(missing)
c=wrong['fields']['revenue']['candidates'][0];c.update(value=900000,period_start='2025-01-01',period_end='2025-12-31',source={'kind':'document','file':'05_wrong_period.txt','page':1,'quote':'Revenue: 900,000'})
c=deepcopy(complete['fields']['cash_on_hand']['candidates'][0]);c.update(value=800000,as_of_date='2025-12-31',source={'kind':'document','file':'05_wrong_period.txt','page':1,'quote':'Cash at December 31, 2025: 800,000'});wrong['fields']['cash_on_hand']={'candidates':[c]}
resolved=deepcopy(conflict)
for name in ['cash_on_hand','revenue']:
 resolved['fields'][name].update(selected_id=name+'-document',resolution={'kind':'company_answer','message_id':'demo-resolution-1','quote':'The statement values are correct: USD 420,000 cash at August 31 and USD 120,000 revenue for August. Disregard the draft note.'})
for name,draft in [('complete',complete),('missing',missing),('conflict',conflict),('wrong_period',wrong),('resolved',resolved)]:
 Draft.model_validate(draft)
 (OUT/f'{name}_input.json').write_text(json.dumps(draft,indent=2))
 (OUT/f'{name}_report.json').write_text(json.dumps(validate(draft),indent=2))
(OUT/'submitted_demo.json').write_text(submit(resolved,reviewed_hash=review_hash(resolved),confirmed_by='demo-finance-lead (simulated)',company_confirmed=True,version=1))
(HERE/'draft.schema.json').write_text(json.dumps(Draft.model_json_schema(),indent=2))
print('Generated five structured test inputs/reports, a simulated submitted snapshot, and JSON Schema.')
