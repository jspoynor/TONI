from copy import deepcopy
from decimal import Decimal
import hashlib,json
from fastapi import HTTPException
from sqlalchemy import select,update,delete,func
import db
from reporting import Draft,validate,review_hash,submit,NAMES
from questions import question_queue,apply_answer

def find_report(c,rid,actor,lock=False):
 q=select(db.reports).where(db.reports.c.id==rid)
 if lock:q=q.with_for_update()
 r=c.execute(q).mappings().first()
 if not r or (actor['role']=='company' and actor['company_id']!=r['company_id']):raise HTTPException(404,'Report not found')
 return dict(r)

def require_company(actor):
 if actor['role']!='company':raise HTTPException(403,'Company user required for answering or submitting')

def latest(c,rid):return c.execute(select(db.versions).where(db.versions.c.report_id==rid).order_by(db.versions.c.version.desc())).mappings().first()

def append_update(c,rid,actor_id,kind,body,document_id=None):
 v=latest(c,rid)
 if v:c.execute(db.updates.insert().values(id=db.uid(),report_id=rid,version_id=v['id'],actor_id=actor_id,kind=kind,body=body,document_id=document_id,created_at=db.now()))

def sync(c,rid,draft,run_map=None):
 report=validate(draft);queue=question_queue(report)
 for name,f in report['fields'].items():
  c.execute(delete(db.fields).where(db.fields.c.report_id==rid,db.fields.c.field==name))
  c.execute(db.fields.insert().values(report_id=rid,field=name,status=f['status'],payload=f))
  for candidate in f['candidates']:
   exists=c.execute(select(db.candidates.c.id).where(db.candidates.c.report_id==rid,db.candidates.c.field==name,db.candidates.c.candidate_key==candidate['id'])).first()
   if not exists:
    amount=Decimal(str(candidate['value'])) if isinstance(candidate['value'],(int,float)) else None
    c.execute(db.candidates.insert().values(id=db.uid(),report_id=rid,run_id=(run_map or {}).get(candidate['id']),field=name,candidate_key=candidate['id'],amount=amount,payload=candidate))
 c.execute(update(db.questions).where(db.questions.c.report_id==rid,db.questions.c.status=='open').values(status='superseded'))
 for q in queue['questions']+queue['remaining']:
  old=c.execute(select(db.questions).where(db.questions.c.report_id==rid,db.questions.c.question_id==q['question_id'])).first()
  if old:c.execute(update(db.questions).where(db.questions.c.report_id==rid,db.questions.c.question_id==q['question_id']).values(status='open'))
  else:c.execute(db.questions.insert().values(report_id=rid,question_id=q['question_id'],field=q['field'],status='open',payload=q))
 return report,queue

def save_draft(c,r,new_draft):
 Draft.model_validate(new_draft)
 changed=c.execute(update(db.reports).where(db.reports.c.id==r['id'],db.reports.c.revision==r['revision']).values(draft=new_draft,revision=r['revision']+1))
 if changed.rowcount!=1:raise HTTPException(409,'Draft changed; refresh and review again')
 sync(c,r['id'],new_draft)

def check_revision(r,expected):
 if r['revision']!=expected:raise HTTPException(409,'Draft changed; refresh and review again')

def view(c,r,actor):
 v=latest(c,r['id']);docs=c.execute(select(db.documents).where(db.documents.c.report_id==r['id']).order_by(db.documents.c.created_at)).mappings().all()
 history=c.execute(select(db.updates,db.actors.c.name.label('author')).outerjoin(db.actors,db.updates.c.actor_id==db.actors.c.id).where(db.updates.c.report_id==r['id']).order_by(db.updates.c.created_at)).mappings().all()
 base={'id':r['id'],'company_id':r['company_id'],'period_start':r['period_start'],'period_end':r['period_end'],'scenario':r['scenario'],'revision':r['revision'],'latest_submission':dict(v) if v else None,'updates':[dict(x) for x in history],'documents':[{k:v for k,v in d.items() if k!='path'} for d in docs]}
 if actor['role']=='company':
  report=validate(r['draft']);base.update(draft=r['draft'],report=report,question_queue=question_queue(report),reviewed_hash=review_hash(r['draft']))
 return base

def answer(c,r,actor,question_id,answer,body,expected):
 require_company(actor);check_revision(r,expected)
 report=validate(r['draft']);q=next((q for q in question_queue(report)['questions'] if q['question_id']==question_id),None)
 if not q:raise HTTPException(409,'Question changed or is not in current batch; refresh')
 mid=db.uid()
 try:result=apply_answer(r['draft'],q,answer,message_id=mid,quote=body)
 except ValueError as e:raise HTTPException(422,str(e)) from None
 c.execute(db.messages.insert().values(id=mid,report_id=r['id'],actor_id=actor['id'],question_id=question_id,body=body,created_at=db.now()))
 save_draft(c,r,result['draft']);c.execute(update(db.questions).where(db.questions.c.report_id==r['id'],db.questions.c.question_id==question_id).values(status='answered'))
 append_update(c,r['id'],actor['id'],'correction',f"Correction to {q['field']}: {body}")
 return {'revision':r['revision']+1,'report':result['report'],'question_queue':result['question_queue']}

def submission(c,r,actor,expected,reviewed_hash_value,confirmed):
 require_company(actor);check_revision(r,expected)
 pending=c.execute(select(db.jobs.c.id).join(db.documents,db.jobs.c.document_id==db.documents.c.id).where(db.documents.c.report_id==r['id'],db.jobs.c.status!='succeeded')).first()
 if pending:raise HTTPException(409,'Uploaded documents must finish scanning successfully before submission')
 prev=latest(c,r['id'])
 if prev and prev['revision']==r['revision']:raise HTTPException(409,'This draft revision is already submitted')
 number=(prev['version'] if prev else 0)+1
 try:snapshot=json.loads(submit(r['draft'],reviewed_hash=reviewed_hash_value,confirmed_by=actor['id'],company_confirmed=confirmed,version=number))
 except ValueError as e:raise HTTPException(422,str(e)) from None
 vid=db.uid();c.execute(db.versions.insert().values(id=vid,report_id=r['id'],version=number,revision=r['revision'],snapshot=snapshot,submitted_by=actor['id'],created_at=db.now()))
 return {'id':vid,'version':number,'snapshot':snapshot}

def correction(c,r,actor,name,answer_value,body,expected):
 require_company(actor);check_revision(r,expected)
 if name not in NAMES:raise HTTPException(404,'Unknown field')
 allowed={'value','currency','unit','period_start','period_end','as_of_date','definition'}
 if not answer_value or set(answer_value)-allowed:raise HTTPException(422,'Invalid field correction')
 draft=deepcopy(r['draft']);mid=db.uid();source={'kind':'company_answer','message_id':mid,'quote':body,'uncertain':False}
 candidate={k:answer_value.get(k) for k in allowed};candidate.update(id='answer-'+mid,company_id=r['company_id'],request_id=r['id'],source=source)
 evidence=draft['fields'].setdefault(name,{'candidates':[]});evidence['candidates'].append(candidate);evidence.update(selected_id=candidate['id'],resolution=source)
 try:Draft.model_validate(draft)
 except ValueError:raise HTTPException(422,'Invalid typed correction') from None
 c.execute(db.messages.insert().values(id=mid,report_id=r['id'],actor_id=actor['id'],body=body,created_at=db.now()))
 save_draft(c,r,draft);append_update(c,r['id'],actor['id'],'correction',f'Correction to {name}: {body}')
 return {'revision':r['revision']+1,'report':validate(draft)}
