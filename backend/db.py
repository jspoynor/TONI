"""Single-VC schema, compatible with PostgreSQL and SQLite for isolated tests."""
import os,uuid,hashlib,secrets
from datetime import datetime,timezone
from sqlalchemy import MetaData,Table,Column,String,Integer,Text,JSON,Numeric,ForeignKey,UniqueConstraint,CheckConstraint,create_engine,event,text
from sqlalchemy.pool import StaticPool
M=MetaData()
def uid():return str(uuid.uuid4())
def now():return datetime.now(timezone.utc).isoformat()
def ID():return Column('id',String,primary_key=True)
vc=Table('vc',M,Column('id',Integer,primary_key=True),Column('name',String,nullable=False),CheckConstraint('id=1'))
companies=Table('companies',M,ID(),Column('vc_id',Integer,ForeignKey('vc.id'),nullable=False,default=1),Column('name',String,nullable=False),Column('settings',JSON,nullable=False))
actors=Table('actors',M,ID(),Column('name',String,nullable=False),Column('role',String,nullable=False),Column('company_id',String,ForeignKey('companies.id')),Column('token_hash',String,unique=True,nullable=False),CheckConstraint("role IN ('vc','company')"),CheckConstraint("(role='vc' AND company_id IS NULL) OR (role='company' AND company_id IS NOT NULL)"))
reports=Table('report_requests',M,ID(),Column('company_id',String,ForeignKey('companies.id'),nullable=False),Column('period_start',String,nullable=False),Column('period_end',String,nullable=False),Column('scenario',String,nullable=False,default='live'),Column('revision',Integer,nullable=False,default=1),Column('draft',JSON,nullable=False),Column('created_at',String,nullable=False),UniqueConstraint('company_id','period_start','period_end','scenario'))
documents=Table('documents',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('filename',String,nullable=False),Column('sha256',String,nullable=False),Column('path',String,nullable=False),Column('uploaded_by',String,ForeignKey('actors.id')),Column('created_at',String,nullable=False),UniqueConstraint('report_id','sha256'))
jobs=Table('scan_jobs',M,ID(),Column('document_id',String,ForeignKey('documents.id'),nullable=False),Column('status',String,nullable=False),Column('error',Text),Column('created_at',String,nullable=False),Column('finished_at',String),CheckConstraint("status IN ('queued','running','succeeded','failed')"))
runs=Table('extraction_runs',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('document_id',String,ForeignKey('documents.id')),Column('reader',String,nullable=False),Column('model',String),Column('payload',JSON,nullable=False),Column('created_at',String,nullable=False))
candidates=Table('field_candidates',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('run_id',String,ForeignKey('extraction_runs.id')),Column('field',String,nullable=False),Column('candidate_key',String,nullable=False),Column('amount',Numeric(24,6)),Column('payload',JSON,nullable=False),UniqueConstraint('report_id','field','candidate_key'))
fields=Table('report_fields',M,Column('report_id',String,ForeignKey('report_requests.id'),primary_key=True),Column('field',String,primary_key=True),Column('status',String,nullable=False),Column('payload',JSON,nullable=False))
questions=Table('questions',M,Column('report_id',String,ForeignKey('report_requests.id'),primary_key=True),Column('question_id',String,primary_key=True),Column('field',String,nullable=False),Column('status',String,nullable=False),Column('payload',JSON,nullable=False))
messages=Table('messages',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('actor_id',String,ForeignKey('actors.id')),Column('question_id',String),Column('body',Text,nullable=False),Column('created_at',String,nullable=False))
versions=Table('report_versions',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('version',Integer,nullable=False),Column('revision',Integer,nullable=False),Column('snapshot',JSON,nullable=False),Column('submitted_by',String,ForeignKey('actors.id'),nullable=False),Column('created_at',String,nullable=False),UniqueConstraint('report_id','version'),UniqueConstraint('report_id','revision'))
updates=Table('report_updates',M,ID(),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False),Column('version_id',String,ForeignKey('report_versions.id'),nullable=False),Column('actor_id',String,ForeignKey('actors.id')),Column('kind',String,nullable=False),Column('body',Text,nullable=False),Column('document_id',String,ForeignKey('documents.id')),Column('created_at',String,nullable=False))
imports=Table('import_batches',M,Column('source_key',String,primary_key=True),Column('sha256',String,nullable=False),Column('report_id',String,ForeignKey('report_requests.id'),nullable=False))

def engine(url=None):
 url=url or os.environ.get('DATABASE_URL','sqlite:///nemo.db')
 kw={'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {}
 if url=='sqlite://':kw['poolclass']=StaticPool
 e=create_engine(url,**kw)
 if url.startswith('sqlite'):
  @event.listens_for(e,'connect')
  def fk(dbapi,_):dbapi.execute('PRAGMA foreign_keys=ON')
 return e

def init(e):
 M.create_all(e)
 with e.begin() as c:
  if not c.execute(vc.select()).first():c.execute(vc.insert().values(id=1,name='TGH Ventures — demo'))
  if e.dialect.name=='postgresql':
   c.execute(text("CREATE OR REPLACE FUNCTION nemo_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Submitted versions and updates are immutable'; END $$"))
   for table in ['report_versions','report_updates']:
    c.execute(text(f'DROP TRIGGER IF EXISTS prevent_mutation ON {table}'))
    c.execute(text(f'CREATE TRIGGER prevent_mutation BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION nemo_immutable()'))
  elif e.dialect.name=='sqlite':
   for table in ['report_versions','report_updates']:
    for action in ['UPDATE','DELETE']:c.execute(text(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable submitted history'); END"))

def provision_actor(c,name,role,company_id=None):
 token=secrets.token_urlsafe(32);actor_id=uid();c.execute(actors.insert().values(id=actor_id,name=name,role=role,company_id=company_id,token_hash=hashlib.sha256(token.encode()).hexdigest()));return actor_id,token
