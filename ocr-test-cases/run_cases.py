"""Rerun the sample-suite experiment using installed Poppler and Tesseract. No model calls or semantic inference.
"""
from pathlib import Path
import os,sys,json,time,subprocess,re
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ocr-test-cases';TMP=ROOT/'work/ocr-test-cases';SRC=ROOT/'sample-data/uploads';RT=ROOT/'work/ocr-runtime'
TMP.mkdir(parents=True,exist_ok=True)
os.environ['OMP_THREAD_LIMIT']='2'
sys.path.insert(0,str(ROOT/'sample-data/developer'))
from extract_local import extract

def ocr(path):
    if path.suffix=='.txt':
        # Render the exact source text, without adding metadata absent from the file.
        im=Image.new('RGB',(2550,3300),'white');d=ImageDraw.Draw(im)
        font=ImageFont.truetype(os.environ.get('NEMO_OCR_FONT','DejaVuSans.ttf'),36)
        for i,line in enumerate(path.read_text().splitlines()): d.text((160,180+i*60),line,fill='black',font=font)
        png=TMP/(path.stem+'.png');im.save(png,dpi=(300,300));images=[png]
    else:
        prefix=TMP/path.stem
        subprocess.run(['pdftoppm','-r','300','-png',str(path),str(prefix)],check=True,capture_output=True)
        images=sorted(TMP.glob(path.stem+'-*.png'),key=lambda p:int(p.stem.rsplit('-',1)[1]))
    pages=[]
    for n,png in enumerate(images,1):
        res=subprocess.run(['tesseract',str(png),'stdout','-l','eng','--psm','3'],check=True,capture_output=True,text=True)
        pages.append({'page':n,'method':'tesseract_ocr','text':res.stdout})
    return {'file':path.name,'pages':pages}

cases={'missing':['02_income_only_missing_context.pdf'],'conflict':['01_complete_monthly.pdf','04_ambiguous_conflicting_note.pdf'],'wrong_period':['05_wrong_period.txt']}
all_results={}
for case,files in cases.items():
    case_results={}
    for method,fn in [('direct',extract),('ocr',ocr)]:
        start=time.perf_counter();docs=[fn(SRC/f) for f in files];seconds=round(time.perf_counter()-start,2)
        (OUT/f'{case}_{method}.json').write_text(json.dumps({'case':case,'method':method,'seconds':seconds,'documents':docs},indent=2))
        (OUT/f'{case}_{method}.txt').write_text('\n\n'.join(f'=== {doc["file"]} / PAGE {p["page"]} / {p["method"]} ===\n'+p['text'] for doc in docs for p in doc['pages']))
        case_results[method]={'seconds':seconds,'documents':docs}
        print(case,method,seconds,'seconds',flush=True)
    all_results[case]=case_results
# Fixed expected snippets verify this fixture's extraction, not a general financial parser.
checks={
 'missing':[(0,1,r'Total\s+revenue\s+120,000\s+100,000','Revenue and comparison preserved'),(0,1,r'Net\s+loss\s+\(56,000\)\s+\(60,000\)','Loss values and signs preserved')],
 'conflict':[(0,2,r'Cash\s+and\s+cash\s+equivalents\s+420,000\s+500,000','Statement cash preserved'),(1,1,r'Cash\s+at\s+August\s+31,\s*2026:\s*450,000','Different cash in note preserved'),(1,1,r'Revenue:\s*120\b','Ambiguous revenue preserved without scaling')],
 'wrong_period':[(0,1,r'Year\s+ended\s+December\s+31,\s*2025','2025 measurement period preserved'),(0,1,r'Revenue:\s*900,000','Annual revenue preserved'),(0,1,r'Cash\s+at\s+December\s+31,\s*2025:\s*800,000','Dated annual cash preserved')]
}
summary=[]
for case,methods in all_results.items():
    entry={'case':case,'methods':{}}
    for method,result in methods.items():
        tests=[]
        for di,pg,pattern,label in checks[case]:
            txt=result['documents'][di]['pages'][pg-1]['text'];tests.append({'check':label,'matched':bool(re.search(pattern,txt))})
        entry['methods'][method]={'seconds':result['seconds'],'page_count':sum(len(d['pages']) for d in result['documents']),'spot_checks':tests}
    summary.append(entry)
(OUT/'comparison.json').write_text(json.dumps({'scope':'Fixture-specific text-preservation checks only. No LLM extraction or follow-up generation tested.','cases':summary},indent=2))
print(json.dumps(summary,indent=2))
