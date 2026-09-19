"""Idempotent import of saved scan JSON. No OpenAI calls."""
from pathlib import Path
import argparse,json,hashlib,shutil,os
from copy import deepcopy
from sqlalchemy import select
import db,service

def import_cases(e,source,storage):
 source=Path(source);storage=Path(storage);storage.mkdir(parents=True,exist_ok=True)
 imported=[]
 with e.begin() as c:
  company='demo-careflow'
  if not c.execute(select(db.companies).where(db.companies.c.id==company)).first():c.execute(db.companies.insert().values(id=company,vc_id=1,name='Nemo Demo CareFlow Co.',settings={'frequency':'monthly','currency':'USD'}))
  for case in ['complete','scanned','missing','conflict','wrong_period']:
   file=source/'results'/f'{case}_comparison.json';raw=file.read_bytes();sha=hashlib.sha256(raw).hexdigest();key='scan-demo-v1:'+case
   existing=c.execute(select(db.imports).where(db.imports.c.source_key==key)).mappings().first()
   if existing:
    if existing['sha256']!=sha:raise ValueError('Import source changed; use a new explicit import version rather than overwriting drafts')
    imported.append(existing['report_id']);continue
   data=json.loads(raw);draft=deepcopy(data['draft']);rid='demo-'+case
   draft['request'].update(request_id=rid,company_id=company)
   for f in draft['fields'].values():
    for cand in f['candidates']:cand.update(request_id=rid,company_id=company)
   c.execute(db.reports.insert().values(id=rid,company_id=company,period_start=draft['request']['period_start'],period_end=draft['request']['period_end'],scenario='demo:'+case,revision=1,draft=draft,created_at=db.now()))
   docs=json.loads((source/'sample-inputs/local-text'/f'{case}.json').read_text());docmap={}
   for d in docs:
    content=(source/'sample-inputs/uploads'/d['file']).read_bytes();did=db.uid();dest=storage/(did+Path(d['file']).suffix);dest.write_bytes(content);docmap[d['file']]=did
    c.execute(db.documents.insert().values(id=did,report_id=rid,filename=d['file'],sha256=hashlib.sha256(content).hexdigest(),path=str(dest.resolve()),created_at=db.now()))
   runmap={}
   for reader in ['local_text','vision']:
    for di,d in enumerate(docs):
     saved=json.loads((source/'results'/f'{case}_{reader}_doc{di}_response.json').read_text());runid=db.uid()
     c.execute(db.runs.insert().values(id=runid,report_id=rid,document_id=docmap[d['file']],reader=reader,model=saved.get('model'),payload=saved,created_at=db.now()))
     for f in draft['fields'].values():
      for cand in f['candidates']:
       if cand['id'].startswith(reader+'-') and cand['source']['file']==d['file']:runmap[cand['id']]=runid
   service.sync(c,rid,draft,runmap);c.execute(db.imports.insert().values(source_key=key,sha256=sha,report_id=rid));imported.append(rid)
 return imported

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('--storage',type=Path,default=Path('storage'));ap.add_argument('--credentials',type=Path,default=Path('demo-credentials.json'));args=ap.parse_args();e=db.engine();db.init(e)
 ids=import_cases(e,args.source,args.storage)
 if not args.credentials.exists():
  with e.begin() as c:
   _,vc_token=db.provision_actor(c,'Demo VC analyst','vc');_,company_token=db.provision_actor(c,'Demo CareFlow finance lead','company','demo-careflow')
  fd=os.open(args.credentials,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump({'vc_token':vc_token,'company_token':company_token},f,indent=2)
 print(json.dumps({'imported_reports':ids,'credentials_file':str(args.credentials),'note':'Tokens are private; not printed.'}))
