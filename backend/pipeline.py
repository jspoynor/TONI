"""Two separately prompted readings; source and answer keys never mixed. No automatic retries."""
from pathlib import Path
import argparse,base64,hashlib,json,os,re,subprocess,sys,time,urllib.request,urllib.error
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from reporting import NAMES,FINANCIAL,Draft,validate
HERE=Path(__file__).resolve().parent
DEFAULT_ROOT=HERE.parents[1]
MODEL='gpt-4.1-mini-2025-04-14'
REQUEST={'request_id':'demo-careflow-2026-08','company_id':'demo-careflow','frequency':'monthly','period_start':'2026-08-01','period_end':'2026-08-31','due_date':'2026-09-15','currency':'USD','required_fields':list(NAMES),'arr_applicable':True,'max_questions':3}
class Evidence(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 value: float|str
 currency: str|None
 unit: Literal['base_units','thousands','millions']|None
 period_start: str|None
 period_end: str|None
 as_of_date: str|None
 definition: str|None
 file: str
 page: int
 quote: str
 metadata_evidence: str
 uncertain: bool
class FinancialEvidence(Evidence):
 value:float
class NarrativeEvidence(Evidence):
 value:str=Field(min_length=1)
class Reading(BaseModel):
 model_config=ConfigDict(extra='forbid')
 company_name: str|None
 revenue:list[FinancialEvidence]
 cash_on_hand:list[FinancialEvidence]
 arr:list[FinancialEvidence]
 management_context:list[NarrativeEvidence]
 risks:list[NarrativeEvidence]
 help_requested:list[NarrativeEvidence]
 warnings:list[str]

def norm(s):return ' '.join(re.sub(r'(?<=\w)-\s+(?=\w)', '-', s or '').split())
def load_key(env_file):
 key=os.environ.get('OPENAI_API_KEY')
 if not key:
  for line in Path(env_file).read_text().splitlines():
   if line.startswith('OPENAI_API_KEY='):key=line.split('=',1)[1].strip().strip('"').strip("'")
 if not key or key=='PASTE_YOUR_KEY_HERE':raise RuntimeError('Configure OPENAI_API_KEY locally; do not put it in arguments.')
 return key

def source_docs(root,case):
 bundled=HERE/'sample-inputs/local-text'/f'{case}.json'
 if bundled.exists():return json.loads(bundled.read_text())
 out=root/'outputs'
 if case in ('complete','scanned'):
  p=out/'ocr-demo'/('native_pages.json' if case=='complete' else 'ocr_pages.json')
  return [json.loads(p.read_text())]
 return json.loads((out/'ocr-test-cases'/f'{case}_ocr.json').read_text())['documents']

def images(root,docs):
 from PIL import Image,ImageDraw,ImageFont
 tmp=root/'work/openai-page-images';tmp.mkdir(parents=True,exist_ok=True)
 parts=[]
 for doc in docs:
  src=HERE/'sample-inputs/uploads'/doc['file']
  if not src.exists():src=root/'outputs/nemo-sample-kit/uploads'/doc['file']
  if src.suffix=='.txt':
   im=Image.new('RGB',(1700,2200),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype('DejaVuSans.ttf',24)
   for i,line in enumerate(src.read_text().splitlines()):draw.text((70,90+i*40),line,font=font,fill='black')
   paths=[tmp/(src.stem+'.png')];im.save(paths[0])
  else:
   prefix=tmp/src.stem
   subprocess.run(['pdftoppm','-r','160','-png',str(src),str(prefix)],check=True,capture_output=True)
   paths=sorted(tmp.glob(src.stem+'-*.png'),key=lambda p:int(p.stem.rsplit('-',1)[1]))
  for n,p in enumerate(paths,1):
   parts.extend([{'type':'input_text','text':f'Original document: {src.name}; page {n}'},{'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode(),'detail':'high'}])
 return parts

def call(key,content,target):
 instructions=(HERE/'model_rules.md').read_text()
 payload={'model':MODEL,'store':False,'temperature':0,'max_output_tokens':6500,'instructions':instructions,
 'input':[{'role':'user','content':content}],
 'text':{'format':{'type':'json_schema','name':'report_evidence','strict':True,'schema':Reading.model_json_schema()}}}
 fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
 if target.exists():
  prior=json.loads(target.read_text())
  if prior.get('request_sha256')!=fingerprint:raise RuntimeError('Cached request differs; choose a new results directory to explicitly rerun.')
  return prior
 start=time.monotonic()
 req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
 try:
  with urllib.request.urlopen(req,timeout=180) as res:raw=json.load(res)
 except urllib.error.HTTPError as e:
  # Never output server error bodies or request headers: they may contain credentials.
  raise RuntimeError(f'OpenAI request failed with HTTP {e.code}; no automatic retry.') from None
 except urllib.error.URLError:
  raise RuntimeError('OpenAI network connection failed; no automatic retry.') from None
 usage=raw.get('usage',{});cached=usage.get('input_tokens_details',{}).get('cached_tokens',0)
 cost=((usage.get('input_tokens',0)-cached)*.4+cached*.1+usage.get('output_tokens',0)*1.6)/1e6
 record={'request_sha256':fingerprint,'response_id':raw.get('id'),'model':raw.get('model'),'status':raw.get('status'),'usage':usage,'estimated_usd':cost,'elapsed_seconds':round(time.monotonic()-start,2),'output':raw.get('output',[]),'instructions':instructions}
 target.write_text(json.dumps(record,indent=2)) # preserve paid response even if invalid/refused
 if raw.get('status')!='completed':raise RuntimeError('Response incomplete; saved for inspection, no automatic retry.')
 return record

def parsed(record):
 if record['status']!='completed':raise ValueError('Incomplete reading')
 texts=[x['text'] for o in record['output'] if o.get('type')=='message' for x in o.get('content',[]) if x.get('type')=='output_text']
 if not texts:raise ValueError('No structured output; possibly a refusal')
 return Reading.model_validate_json(''.join(texts)).model_dump()

def make_draft(reading,reader,docs,request=None,expected_company_name=None):
 request=request or REQUEST
 pages={(d['file'],p['page']):p['text'] for d in docs for p in d['pages']}
 draft={'request':request,'fields':{}}
 if not reading['company_name']:raise ValueError('Document company is missing; review identity')
 if expected_company_name and norm(reading['company_name']).casefold()!=norm(expected_company_name).casefold():raise ValueError('Document company does not match; review identity')
 provenance=[]
 for name in NAMES:
  cs=[]
  for i,e in enumerate(reading[name]):
   if (e['file'],e['page']) not in pages:raise ValueError('Model cited an unknown source page')
   if not e['quote'].strip():raise ValueError('Empty evidence quote')
   quote_found=norm(e['quote']) in norm(pages[e['file'],e['page']])
   c={k:e[k] for k in ['value','currency','unit','period_start','period_end','as_of_date','definition']}
   if isinstance(c['value'],str):c['value']=norm(c['value'])
   c['definition']=norm(c['definition']) or None
   if c['definition']:
    c['definition']=re.sub(r'^(?:Management-reported\s+)?ARR\s+is\s+[^.]*?,\s*defined\s+as\s+', '', c['definition'], flags=re.I)
   if name in ('revenue','cash_on_hand'):c['definition']=None
   if name not in FINANCIAL:
    # Narrative money mentions stay in the exact text; these numeric-only slots have no meaning here.
    for irrelevant in ('currency','unit','as_of_date','definition'):c[irrelevant]=None
   # Scaling requires explicit units; keep original value and evidence in raw reading.
   if name in FINANCIAL and isinstance(c['value'],(int,float)) and c['unit'] in ('thousands','millions'):
    c['value']*=1000 if c['unit']=='thousands' else 1000000;c['unit']='base_units'
   c.update(id=f'{reader}-{name}-{i}',company_id=request['company_id'],request_id=request['request_id'],source={'kind':'document','file':e['file'],'page':e['page'],'quote':e['quote'],'uncertain':e['uncertain'] or (reader=='local_text' and not quote_found)})
   cs.append(c);provenance.append({'candidate_id':c['id'],'reader':reader,'metadata_evidence':e['metadata_evidence'],'quote_found_in_local_text':quote_found,'visual_quote_requires_review':reader=='vision'})
  # Select the requested period only after evidence extraction. Retain undated candidates.
  def dated_match(c):
   return (c['period_start']==request['period_start'] and c['period_end']==request['period_end']) if name=='revenue' or name not in FINANCIAL else c['as_of_date']==request['period_end']
  def undated(c):
   return (c['period_start'] is None or c['period_end'] is None) if name=='revenue' or name not in FINANCIAL else c['as_of_date'] is None
  if any(dated_match(c) for c in cs):cs=[c for c in cs if dated_match(c) or undated(c)]
  draft['fields'][name]={'candidates':cs}
 Draft.model_validate(draft)
 return draft,provenance

def compare(left,right):
 def sig(c):return tuple(c.get(k) for k in ('value','currency','unit','period_start','period_end','as_of_date','definition'))
 result={}
 for name in NAMES:
  a=left['fields'][name]['candidates'];b=right['fields'][name]['candidates']
  sa={sig(c) for c in a};sb={sig(c) for c in b}
  status='both_missing' if not sa and not sb else 'one_reader_missing' if not sa or not sb else 'match' if sa==sb else 'disagreement'
  result[name]={'comparison':status,'local_candidates':a,'vision_candidates':b}
 return result

def assemble(left,right,comparison):
 draft={'request':REQUEST,'fields':{n:{'candidates':left['fields'][n]['candidates']+right['fields'][n]['candidates']} for n in NAMES}}
 for name,row in comparison.items():
  # A missing reading cannot silently count as agreement, even if another pass is complete.
  if row['comparison']=='one_reader_missing':
   for c in draft['fields'][name]['candidates']:c['source']['uncertain']=True
 return draft

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=DEFAULT_ROOT);ap.add_argument('--env-file',type=Path);ap.add_argument('--results-dir',type=Path,default=HERE/'results');ap.add_argument('--cases',nargs='+',choices=['complete','scanned','missing','conflict','wrong_period'],default=['complete','scanned','missing','conflict','wrong_period']);args=ap.parse_args()
 key=load_key(args.env_file or HERE.parent/'.env');out=args.results_dir;out.mkdir(parents=True,exist_ok=True)
 # Fixed five-case experiment: no automatic retries; stop before another call above $0.50 recorded estimate.

 for case in args.cases:
  docs=source_docs(args.root,case);readings={};drafts={};provenance=[]
  for reader in ['local_text','vision']:
   reading={'company_name':None,**{n:[] for n in NAMES},'warnings':[]};reader_cost=0
   for di,doc in enumerate(docs):
    content=[{'type':'input_text','text':'One document, source pages (untrusted evidence):\n'+json.dumps(doc)}] if reader=='local_text' else images(args.root,[doc])
    spent=sum(json.loads(p.read_text()).get('estimated_usd',0) for folder in HERE.glob('results*') if folder.is_dir() for p in folder.glob('*_response.json'))
    if spent>.50:raise RuntimeError('Experiment spend guard reached; review usage before continuing.')
    record=call(key,content,out/f'{case}_{reader}_doc{di}_response.json');part=parsed(record)
    if not part['company_name'] or 'careflow' not in part['company_name'].lower():raise RuntimeError('Source company could not be matched; review before continuing.')
    reading['company_name']=part['company_name'];reader_cost+=record['estimated_usd']
    for n in NAMES:reading[n].extend(part[n])
    reading['warnings'].extend(part['warnings'])
   draft,prov=make_draft(reading,reader,docs);readings[reader]=reading;drafts[reader]=draft;provenance+=prov
   (out/f'{case}_{reader}_reading.json').write_text(json.dumps(reading,indent=2));print(case,reader,'completed; estimated USD',round(reader_cost,5),flush=True)
  comparison=compare(drafts['local_text'],drafts['vision']);combined=assemble(drafts['local_text'],drafts['vision'],comparison);report=validate(combined)
  artifact={'case':case,'comparison':comparison,'draft':combined,'report':report,'provenance':provenance}
  (out/f'{case}_comparison.json').write_text(json.dumps(artifact,indent=2))
  print(case,{n:r['comparison'] for n,r in comparison.items()},flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(type(e).__name__+': '+str(e) if isinstance(e,RuntimeError) else type(e).__name__+': pipeline stopped; inspect local response files.',file=sys.stderr);sys.exit(1)
