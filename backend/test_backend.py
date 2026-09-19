import unittest,tempfile,os,json,hashlib
from pathlib import Path
from copy import deepcopy
from sqlalchemy import select,text,func
from fastapi.testclient import TestClient
import db,service
from app import create_app
from reporting import NAMES
from worker import process_one
from import_scans import import_cases

def ready(rid='r1',company='c1'):
 req={'request_id':rid,'company_id':company,'frequency':'monthly','period_start':'2026-08-01','period_end':'2026-08-31','due_date':'2026-09-15','currency':'USD','required_fields':list(NAMES),'arr_applicable':True,'max_questions':3}
 fields={}
 for name in NAMES:
  numeric=name in ('revenue','cash_on_hand','arr')
  c={'id':'seed-'+name,'request_id':rid,'company_id':company,'value':100 if numeric else 'Company-provided context.','currency':'USD' if numeric else None,'unit':'base_units' if numeric else None,'period_start':'2026-08-01' if name not in ('cash_on_hand','arr') else None,'period_end':'2026-08-31' if name not in ('cash_on_hand','arr') else None,'as_of_date':'2026-08-31' if name in ('cash_on_hand','arr') else None,'definition':'Live recurring contracts only' if name=='arr' else None,'source':{'kind':'document','file':'seed.pdf','page':1,'quote':'Sample evidence','uncertain':False}}
  fields[name]={'candidates':[c]}
 return {'request':req,'fields':fields}

class BackendTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=None
  url=os.environ.get('NEMO_TEST_DATABASE_URL')
  if url:
   self.schema='test_'+db.uid().replace('-','');self.base=db.engine(url)
   with self.base.begin() as c:c.execute(text('CREATE SCHEMA '+self.schema))
   self.e=db.engine(url+('&' if '?' in url else '?')+'options=-csearch_path%3D'+self.schema)
  else:self.e=db.engine('sqlite://')
  db.init(self.e)
  with self.e.begin() as c:
   for cid in ['c1','c2']:c.execute(db.companies.insert().values(id=cid,vc_id=1,name=cid,settings={}))
   self.aid,self.company=db.provision_actor(c,'Finance','company','c1');_,self.other=db.provision_actor(c,'Other finance','company','c2');_,self.vc=db.provision_actor(c,'VC','vc')
   c.execute(db.reports.insert().values(id='r1',company_id='c1',period_start='2026-08-01',period_end='2026-08-31',scenario='live',revision=1,draft=ready(),created_at=db.now()));service.sync(c,'r1',ready())
  self.client=TestClient(create_app(self.e,Path(self.tmp.name)/'files'));self.client.__enter__()
 def tearDown(self):
  self.client.__exit__(None,None,None);self.e.dispose()
  if self.base:
   with self.base.begin() as c:c.execute(text('DROP SCHEMA '+self.schema+' CASCADE'))
   self.base.dispose()
  self.tmp.cleanup()
 def h(self,token=None):return {'Authorization':'Bearer '+(token or self.company)}
 def get(self):return self.client.get('/reports/r1',headers=self.h()).json()
 def submit(self):
  r=self.get();return self.client.post('/reports/r1/submit',headers=self.h(),json={'expected_revision':r['revision'],'reviewed_hash':r['reviewed_hash'],'company_confirmed':True})
 def upload(self,content=b'New company update',revision=None):
  return self.client.post('/reports/r1/documents',headers=self.h(),params={'expected_revision':revision or self.get()['revision']},files={'file':('later.txt',content,'text/plain')})
 def test_auth_and_company_isolation(self):
  self.assertEqual(self.client.get('/companies').status_code,401)
  self.assertEqual(self.client.get('/reports/r1',headers=self.h(self.other)).status_code,404)
  self.assertEqual(len(self.client.get('/companies',headers=self.h()).json()),1)
 def test_vc_cannot_submit_and_does_not_receive_unsubmitted_draft(self):
  self.assertNotIn('draft',self.client.get('/reports/r1',headers=self.h(self.vc)).json())
  self.assertEqual(self.client.post('/reports/r1/submit',headers=self.h(self.vc),json={'expected_revision':1,'reviewed_hash':'x','company_confirmed':True}).status_code,403)
 def test_confirmation_required(self):
  r=self.get();res=self.client.post('/reports/r1/submit',headers=self.h(),json={'expected_revision':1,'reviewed_hash':r['reviewed_hash'],'company_confirmed':False});self.assertEqual(res.status_code,422)
 def test_submitted_snapshot_comments_and_corrections(self):
  first=self.submit();self.assertEqual(first.status_code,201);original=first.json()['snapshot']
  self.assertEqual(self.client.post('/reports/r1/comments',headers=self.h(),json={'body':'Renewal now signed.'}).status_code,201)
  res=self.client.post('/reports/r1/fields/cash_on_hand/corrections',headers=self.h(),json={'expected_revision':1,'message':'Cash corrected to USD 150 on August 31','answer':{'value':150,'currency':'USD','unit':'base_units','as_of_date':'2026-08-31'}});self.assertEqual(res.status_code,200)
  vc=self.client.get('/reports/r1',headers=self.h(self.vc)).json();self.assertEqual(vc['latest_submission']['snapshot'],original);self.assertEqual([u['kind'] for u in vc['updates']],['comment','correction'])
  second=self.submit();self.assertEqual(second.status_code,201);self.assertEqual(second.json()['version'],2)
  history=self.client.get('/reports/r1/versions',headers=self.h()).json();self.assertEqual(len(history),2);self.assertEqual(history[0]['snapshot'],original)
 def test_stale_review_and_duplicate_submit(self):
  r=self.get();self.assertEqual(self.submit().status_code,201);self.assertEqual(self.submit().status_code,409)
  self.upload();res=self.client.post('/reports/r1/submit',headers=self.h(),json={'expected_revision':r['revision'],'reviewed_hash':r['reviewed_hash'],'company_confirmed':True});self.assertEqual(res.status_code,409)
 def test_pending_upload_blocks_submission_and_appears_below_report(self):
  original=self.submit().json()['snapshot'];u=self.upload();self.assertEqual(u.status_code,202);self.assertEqual(self.submit().status_code,409)
  vc=self.client.get('/reports/r1',headers=self.h(self.vc)).json();self.assertEqual(vc['latest_submission']['snapshot'],original);self.assertEqual(vc['updates'][0]['kind'],'upload')
 def test_duplicate_upload_does_not_queue_again(self):
  first=self.upload().json();second=self.upload().json();self.assertTrue(second['duplicate']);self.assertEqual(first['document_id'],second['document_id'])
  with self.e.connect() as c:self.assertEqual(c.scalar(select(func.count()).select_from(db.jobs)),1)
 def test_document_access_and_validation(self):
  u=self.upload().json();self.assertEqual(self.client.get('/documents/'+u['document_id']+'/download',headers=self.h(self.other)).status_code,404)
  bad=self.client.post('/reports/r1/documents',headers=self.h(),params={'expected_revision':2},files={'file':('bad.pdf',b'not pdf','application/pdf')});self.assertEqual(bad.status_code,422)
 def test_worker_merges_new_evidence_without_replacing_history(self):
  original=self.submit().json()['snapshot'];u=self.upload().json()
  def fake(doc,request,company,cache):
   d=ready();d['fields']={n:{'candidates':[]} for n in NAMES};candidate=deepcopy(ready()['fields']['cash_on_hand']['candidates'][0]);candidate['id']=doc['id']+':local_text-cash';candidate['value']=900;candidate['source']['file']=doc['filename'];d['fields']['cash_on_hand']['candidates']=[candidate]
   return {'draft':d,'records':[{'reader':'local_text','record':{'model':'TEST-DOUBLE'}}]}
  self.assertTrue(process_one(self.e,self.tmp.name,fake));self.assertFalse(process_one(self.e,self.tmp.name,fake))
  r=self.get();self.assertEqual(r['report']['fields']['cash_on_hand']['status'],'conflicting');self.assertEqual(r['latest_submission']['snapshot'],original);self.assertEqual(self.client.get('/jobs/'+u['job_id'],headers=self.h()).json()['status'],'succeeded')
 def test_failed_worker_is_durable_and_blocks_submission(self):
  u=self.upload().json()
  def fail(*args):raise RuntimeError('test provider failure')
  process_one(self.e,self.tmp.name,fail);self.assertEqual(self.client.get('/jobs/'+u['job_id'],headers=self.h()).json()['status'],'failed');self.assertEqual(self.submit().status_code,409)
 def test_snapshot_database_is_immutable(self):
  vid=self.submit().json()['id']
  with self.assertRaises(Exception):
   with self.e.begin() as c:c.execute(db.versions.update().where(db.versions.c.id==vid).values(snapshot={'changed':True}))
 def test_import_is_idempotent_and_keeps_cases_separate(self):
  source=Path(os.environ.get('SCAN_DATA_DIR',str(Path(__file__).parent.parent/'nemo-ai-pipeline')))
  if not (source/'results').exists():self.skipTest('Set SCAN_DATA_DIR to the extracted scan package')
  ids=import_cases(self.e,source,Path(self.tmp.name)/'imports');again=import_cases(self.e,source,Path(self.tmp.name)/'imports');self.assertEqual(ids,again);self.assertEqual(len(ids),5)
  with self.e.connect() as c:self.assertEqual(c.scalar(select(func.count()).select_from(db.imports)),5)
 def test_duplicate_live_period_prevented(self):
  b={'frequency':'monthly','period_start':'2026-08-01','period_end':'2026-08-31','due_date':'2026-09-15'}
  self.assertEqual(self.client.post('/companies/c1/reports',headers=self.h(self.vc),json=b).status_code,409)
if __name__=='__main__':unittest.main()
