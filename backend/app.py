from pathlib import Path
from contextlib import asynccontextmanager
import os,hashlib,json,io
from typing import Annotated
from fastapi import FastAPI,Depends,HTTPException,UploadFile,Query
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,update
from sqlalchemy.exc import IntegrityError
from pypdf import PdfReader
import db,service
from reporting import Request,NAMES

class Body(BaseModel):model_config=ConfigDict(extra='forbid')
class CompanyCreate(Body):name:str=Field(min_length=1,max_length=200)
class RequestCreate(Body):
 frequency:str='monthly'
 period_start:str
 period_end:str
 due_date:str
 currency:str='USD'
 required_fields:list[str]=Field(default_factory=lambda:list(NAMES))
 arr_applicable:bool|None=None
class Answer(Body):
 expected_revision:int=Field(ge=1)
 answer:dict
 message:str=Field(min_length=1,max_length=12000)
class Comment(Body):body:str=Field(min_length=1,max_length=12000)
class Submission(Body):
 expected_revision:int=Field(ge=1)
 reviewed_hash:str
 company_confirmed:bool

def create_app(engine=None,storage=None):
 e=engine or db.engine();store=Path(storage or os.environ.get('NEMO_STORAGE','storage')).resolve();store.mkdir(parents=True,exist_ok=True)
 @asynccontextmanager
 async def lifespan(app):
  db.init(e);yield
 app=FastAPI(title='Nemo single-VC API',version='0.1.0',lifespan=lifespan)
 app.state.engine=e
 app.add_middleware(CORSMiddleware,allow_origins=os.environ.get('CORS_ORIGINS','http://localhost:3000,http://localhost:5173').split(','),allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
 bearer=HTTPBearer()
 def actor(credentials:Annotated[HTTPAuthorizationCredentials,Depends(bearer)]):
  digest=hashlib.sha256(credentials.credentials.encode()).hexdigest()
  with e.connect() as c:a=c.execute(select(db.actors).where(db.actors.c.token_hash==digest)).mappings().first()
  if not a:raise HTTPException(401,'Invalid credential')
  return dict(a)
 Auth=Annotated[dict,Depends(actor)]
 @app.exception_handler(IntegrityError)
 async def integrity_error(request,exc):
  from fastapi.responses import JSONResponse
  return JSONResponse(status_code=409,content={'detail':'Record conflicts with existing data; refresh before retrying.'})
 @app.get('/health')
 def health():return {'status':'ok'}
 @app.get('/companies')
 def companies(a:Auth):
  with e.connect() as c:
   q=select(db.companies)
   if a['role']=='company':q=q.where(db.companies.c.id==a['company_id'])
   return [dict(r) for r in c.execute(q).mappings()]
 @app.post('/companies',status_code=201)
 def company(body:CompanyCreate,a:Auth):
  if a['role']!='vc':raise HTTPException(403,'VC role required')
  cid=db.uid()
  with e.begin() as c:c.execute(db.companies.insert().values(id=cid,vc_id=1,name=body.name,settings={'frequency':'monthly','currency':'USD'}))
  return {'id':cid,'name':body.name}
 @app.post('/companies/{cid}/reports',status_code=201)
 def new_report(cid:str,body:RequestCreate,a:Auth):
  if a['role']!='vc':raise HTTPException(403,'VC role required')
  rid=db.uid()
  try:req=Request.model_validate(dict(body.model_dump(),company_id=cid,request_id=rid)).model_dump(mode='json')
  except ValueError:raise HTTPException(422,'Invalid period, currency or requested fields') from None
  draft={'request':req,'fields':{n:{'candidates':[]} for n in NAMES}}
  with e.begin() as c:
   if not c.execute(select(db.companies.c.id).where(db.companies.c.id==cid)).first():raise HTTPException(404,'Company not found')
   c.execute(db.reports.insert().values(id=rid,company_id=cid,period_start=req['period_start'],period_end=req['period_end'],scenario='live',revision=1,draft=draft,created_at=db.now()));service.sync(c,rid,draft)
  return {'id':rid,'revision':1}
 @app.get('/companies/{cid}/reports')
 def reports(cid:str,a:Auth):
  if a['role']=='company' and a['company_id']!=cid:raise HTTPException(404,'Company not found')
  with e.connect() as c:return [{k:v for k,v in r.items() if k!='draft'} for r in c.execute(select(db.reports).where(db.reports.c.company_id==cid)).mappings()]
 @app.get('/reports/{rid}')
 def report(rid:str,a:Auth):
  with e.connect() as c:return service.view(c,service.find_report(c,rid,a),a)
 @app.post('/reports/{rid}/questions/{qid}/answers')
 def answer(rid:str,qid:str,body:Answer,a:Auth):
  with e.begin() as c:return service.answer(c,service.find_report(c,rid,a,True),a,qid,body.answer,body.message,body.expected_revision)
 @app.post('/reports/{rid}/fields/{name}/corrections')
 def correct(rid:str,name:str,body:Answer,a:Auth):
  with e.begin() as c:return service.correction(c,service.find_report(c,rid,a,True),a,name,body.answer,body.message,body.expected_revision)
 @app.post('/reports/{rid}/submit',status_code=201)
 def submit(rid:str,body:Submission,a:Auth):
  with e.begin() as c:return service.submission(c,service.find_report(c,rid,a,True),a,body.expected_revision,body.reviewed_hash,body.company_confirmed)
 @app.get('/reports/{rid}/versions')
 def versions(rid:str,a:Auth):
  with e.connect() as c:
   service.find_report(c,rid,a)
   return [dict(v) for v in c.execute(select(db.versions).where(db.versions.c.report_id==rid).order_by(db.versions.c.version)).mappings()]
 @app.post('/reports/{rid}/comments',status_code=201)
 def comment(rid:str,body:Comment,a:Auth):
  if not body.body.strip():raise HTTPException(422,'Comment cannot be blank')
  with e.begin() as c:
   service.find_report(c,rid,a,True)
   if not service.latest(c,rid):raise HTTPException(409,'Comments below a report require a submitted version')
   service.append_update(c,rid,a['id'],'comment',body.body)
  return {'saved':True}
 @app.post('/reports/{rid}/documents',status_code=202)
 async def upload(rid:str,file:UploadFile,a:Auth,expected_revision:int=Query(ge=1)):
  service.require_company(a)
  name=Path(file.filename or '').name;suffix=Path(name).suffix.lower()
  if suffix not in ('.pdf','.txt'):raise HTTPException(415,'Only PDF and UTF-8 TXT are supported')
  data=await file.read(10*1024*1024+1)
  if len(data)>10*1024*1024:raise HTTPException(413,'Maximum upload size is 10 MB')
  if not data:raise HTTPException(422,'Empty document')
  try:
   if suffix=='.pdf':
    if not data.startswith(b'%PDF-') or len(PdfReader(io.BytesIO(data)).pages)>10:raise ValueError()
   else:data.decode('utf-8')
  except Exception:raise HTTPException(422,'Unreadable document or more than 10 PDF pages') from None
  sha=hashlib.sha256(data).hexdigest();did=db.uid();jid=db.uid();dest=store/(did+suffix);written=False
  try:
   with e.begin() as c:
    r=service.find_report(c,rid,a,True);service.check_revision(r,expected_revision)
    old=c.execute(select(db.documents).where(db.documents.c.report_id==rid,db.documents.c.sha256==sha)).mappings().first()
    if old:return {'document_id':old['id'],'duplicate':True,'revision':r['revision']}
    dest.write_bytes(data);written=True
    c.execute(db.documents.insert().values(id=did,report_id=rid,filename=name,sha256=sha,path=str(dest),uploaded_by=a['id'],created_at=db.now()))
    c.execute(db.jobs.insert().values(id=jid,document_id=did,status='queued',created_at=db.now()))
    service.save_draft(c,r,r['draft']) # invalidate previous review even before scanning finishes
    service.append_update(c,rid,a['id'],'upload',f'New document uploaded: {name}. Scan pending.',did)
   return {'document_id':did,'job_id':jid,'status':'queued','revision':r['revision']+1}
  except BaseException:
   if written:dest.unlink(missing_ok=True)
   raise
 @app.get('/documents/{did}/download')
 def download(did:str,a:Auth):
  with e.connect() as c:
   doc=c.execute(select(db.documents).where(db.documents.c.id==did)).mappings().first()
   if not doc:raise HTTPException(404,'Document not found')
   service.find_report(c,doc['report_id'],a)
   return FileResponse(doc['path'],filename=doc['filename'],media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff'})
 @app.get('/jobs/{jid}')
 def job(jid:str,a:Auth):
  with e.connect() as c:
   j=c.execute(select(db.jobs,db.documents.c.report_id).join(db.documents,db.documents.c.id==db.jobs.c.document_id).where(db.jobs.c.id==jid)).mappings().first()
   if not j:raise HTTPException(404,'Job not found')
   service.find_report(c,j['report_id'],a);return dict(j)
 return app
app=create_app()
