"""Durable scan queue. One sequential worker; no automatic retries of paid failures."""
from pathlib import Path
import os,json,base64,subprocess,time,traceback
from copy import deepcopy
from sqlalchemy import select,update
import db,service,pipeline
from extract_local import extract
from reporting import NAMES,validate

def scan(document,request,company_name,cache_dir):
 from PIL import Image,ImageDraw,ImageFont
 src=Path(document['path']);cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True)
 local=extract(src);local['file']=document['filename'];parts=[]
 if src.suffix=='.txt':
  lines=src.read_text().splitlines()
  if len(lines)>45 or any(len(line)>110 for line in lines):raise RuntimeError('TXT exceeds one-page demo layout; upload a PDF instead')
  im=Image.new('RGB',(1800,2400),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype('DejaVuSans.ttf',24)
  for i,line in enumerate(lines):draw.text((80,80+i*45),line,font=font,fill='black')
  pages=[cache/'page.png'];im.save(pages[0])
 else:
  subprocess.run(['pdftoppm','-r','160','-png',str(src),str(cache/'page')],check=True,capture_output=True,timeout=120)
  pages=sorted(cache.glob('page-*.png'),key=lambda p:int(p.stem.rsplit('-',1)[1]))
 for n,page in enumerate(pages,1):parts.extend([{'type':'input_text','text':f"Document: {document['filename']}; page {n}"},{'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(page.read_bytes()).decode(),'detail':'high'}])
 key=pipeline.load_key(os.environ.get('OPENAI_ENV_FILE','../.env'));drafts={};records=[]
 for reader in ['local_text','vision']:
  content=[{'type':'input_text','text':json.dumps(local)}] if reader=='local_text' else parts
  record=pipeline.call(key,content,cache/(reader+'_response.json'));reading=pipeline.parsed(record)
  draft,prov=pipeline.make_draft(reading,reader,[local],request,company_name)
  for evidence in draft['fields'].values():
   for cand in evidence['candidates']:cand['id']=document['id']+':'+cand['id']
  drafts[reader]=draft;records.append({'reader':reader,'record':record,'provenance':prov})
 comparison=pipeline.compare(drafts['local_text'],drafts['vision'])
 combined=pipeline.assemble(drafts['local_text'],drafts['vision'],comparison);combined['request']=request
 return {'draft':combined,'records':records,'comparison':comparison}

def process_one(e,storage,scanner=scan):
 with e.begin() as c:
  q=select(db.jobs).where(db.jobs.c.status=='queued').order_by(db.jobs.c.created_at).with_for_update(skip_locked=True)
  job=c.execute(q).mappings().first()
  if not job:return False
  job=dict(job);changed=c.execute(update(db.jobs).where(db.jobs.c.id==job['id'],db.jobs.c.status=='queued').values(status='running'))
  if changed.rowcount!=1:return False
  doc=dict(c.execute(select(db.documents).where(db.documents.c.id==job['document_id'])).mappings().one())
  r=dict(c.execute(select(db.reports).where(db.reports.c.id==doc['report_id'])).mappings().one());company=c.execute(select(db.companies).where(db.companies.c.id==r['company_id'])).mappings().one()
 try:
  result=scanner(doc,r['draft']['request'],company['name'],Path(storage)/'scan-cache'/job['id'])
  with e.begin() as c:
   r=dict(c.execute(select(db.reports).where(db.reports.c.id==doc['report_id']).with_for_update()).mappings().one());draft=deepcopy(r['draft']);runmap={}
   for record in result['records']:
    runid=db.uid();c.execute(db.runs.insert().values(id=runid,report_id=r['id'],document_id=doc['id'],reader=record['reader'],model=record['record'].get('model'),payload=record,created_at=db.now()))
    for f in result['draft']['fields'].values():
     for cand in f['candidates']:
      if ':'+record['reader']+'-' in cand['id']:runmap[cand['id']]=runid
   for name,field in result['draft']['fields'].items():
    if not field['candidates']:continue
    target=draft['fields'].setdefault(name,{'candidates':[]});target['candidates'].extend(field['candidates']);target['selected_id']=None;target['resolution']=None
   # New evidence may challenge a previously selected answer; require review again.
   service.save_draft(c,r,draft);service.sync(c,r['id'],draft,runmap)
   for key,runid in runmap.items():c.execute(update(db.candidates).where(db.candidates.c.report_id==r['id'],db.candidates.c.candidate_key==key).values(run_id=runid))
   c.execute(update(db.jobs).where(db.jobs.c.id==job['id']).values(status='succeeded',finished_at=db.now()))
   service.append_update(c,r['id'],doc['uploaded_by'],'scan_completed',f"Scan completed for {doc['filename']}. New evidence is available in the draft; submitted figures are unchanged.",doc['id'])
 except Exception as error:
  with e.begin() as c:
   # Avoid logging credentials/provider request bodies; detailed saved responses remain local.
   c.execute(update(db.jobs).where(db.jobs.c.id==job['id']).values(status='failed',error=type(error).__name__+': scan failed; operator review required before retrying',finished_at=db.now()))
 return True

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--once',action='store_true');args=ap.parse_args();e=db.engine();db.init(e)
 while True:
  worked=process_one(e,os.environ.get('NEMO_STORAGE','storage'))
  if args.once:break
  if not worked:time.sleep(2)
