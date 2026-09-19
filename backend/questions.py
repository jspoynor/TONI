"""Deterministic, field-bound follow-ups and structured company-answer updates."""
from copy import deepcopy
from pathlib import Path
import hashlib,json
from reporting import Draft,NAMES,FINANCIAL,validate
HERE=Path(__file__).parent

def question_queue(report,comparison=None):
 bank=json.loads((HERE/'question_bank.json').read_text());pending=[];req=report['request']
 for name in NAMES:
  field=report['fields'][name];issues=field['issues']
  if not issues:continue
  reading_status=(comparison or {}).get(name,{}).get('comparison')
  if 'conflicting_candidates' in issues:
   reason='conflict';priority=0
   cs=field['candidates']
   # Distinguish matching amounts with unclear metadata from contradictory amounts.
   if name in FINANCIAL and len({c['value'] for c in cs})==1:
    for attr,mapped in [('currency','currency'),('unit','units'),('period_start','period'),('period_end','period'),('as_of_date','period'),('definition','definition')]:
     if len({c.get(attr) for c in cs})>1:
      reason=mapped;priority=1;break
  elif reading_status=='one_reader_missing':reason='reader_missing';priority=1
  elif 'source_uncertain' in issues:reason='uncertain';priority=1
  elif 'currency_missing_or_different' in issues:reason='currency';priority=1
  elif 'units_missing_or_not_normalized' in issues:reason='units';priority=1
  elif 'reporting_period_missing_or_wrong' in issues or 'as_of_date_missing_or_wrong' in issues:reason='period';priority=1
  elif 'arr_definition_missing' in issues:reason='definition';priority=1
  elif issues==['missing']:reason='missing';priority=2 if name in FINANCIAL else 3
  else:reason='clarify';priority=1
  template=bank[name].get(reason,bank[name]['clarify'])
  text=template.format(start=req['period_start'],end=req['period_end'],currency=req['currency'])
  options=[]
  for c in field['candidates']:
   options.append({'candidate_id':c['id'],'value':c['value'],'currency':c['currency'],'unit':c['unit'],'period_start':c['period_start'],'period_end':c['period_end'],'as_of_date':c['as_of_date'],'source':c['source']})
  # Hash binds this question to its evidence and request. An updated draft produces a new ID.
  evidence_hash=hashlib.sha256(json.dumps([req,field],sort_keys=True).encode()).hexdigest()[:12]
  pending.append({'question_id':f'{name}:{reason}:{evidence_hash}','field':name,'write_path':f'fields.{name}','reason':reason,'all_issues':issues,'question':text,'priority':priority,'candidate_options':options,'answer_contract':bank[name]['answer_contract']})
 pending.sort(key=lambda q:q['priority'])
 return {'questions':pending[:req['max_questions']],'remaining':pending[req['max_questions']:],'total_unresolved_fields':len(pending)}

def apply_answer(draft,question,answer,*,message_id,quote,comparison=None):
 """Apply a UI/adapter-supplied structured answer, NOT arbitrary natural language.
 Caller authenticates the company user. This function never submits the report.
 """
 if not message_id.strip() or not quote.strip():raise ValueError('Company message reference and exact answer required')
 draft=Draft.model_validate(draft).model_dump(mode='json');before=validate(draft)
 live=question_queue(before,comparison)['questions']
 if question not in live:raise ValueError('Stale or unknown question; refresh before answering')
 name=question['field'];out=deepcopy(draft);req=out['request']
 if answer=={'not_applicable':True}:
  if name!='arr':raise ValueError('Not-applicable updates only supported for ARR')
  if out['fields'][name]['candidates']:raise ValueError('Existing ARR evidence must be explicitly reviewed; do not silently discard it')
  out['request']['arr_applicable']=False
 else:
  allowed={'value','currency','unit','period_start','period_end','as_of_date','definition'}
  if not answer or set(answer)-allowed:raise ValueError('Answer contains unknown properties')
  candidate={k:answer.get(k) for k in allowed};candidate.update(id=f'answer-{name}-{message_id}',request_id=req['request_id'],company_id=req['company_id'],source={'kind':'company_answer','message_id':message_id,'quote':quote,'uncertain':False})
  evidence=out['fields'].setdefault(name,{'candidates':[]})
  if any(c['id']==candidate['id'] for c in evidence['candidates']):raise ValueError('Duplicate answer message')
  evidence['candidates'].append(candidate);evidence.update(selected_id=candidate['id'],resolution=candidate['source'])
 Draft.model_validate(out);report=validate(out)
 return {'draft':out,'report':report,'question_queue':question_queue(report,comparison),'answer_audit':{'field':name,'question_id':question['question_id'],'message_id':message_id,'quote':quote}}
