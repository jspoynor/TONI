"""Local PDF/text extraction. No OpenAI calls and no paid service.
Install Python packages: python -m pip install pypdf
Scanned PDFs also require the pdftoppm and tesseract command-line tools.
Usage: python extract_local.py input.pdf --output extracted.json
"""
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
from pypdf import PdfReader

def extract(path):
    if path.suffix.lower()=='.txt':
        return {'file':path.name,'pages':[{'page':1,'method':'plain_text','text':path.read_text()}]}
    if path.suffix.lower()!='.pdf':
        raise ValueError('Only PDF and TXT inputs are supported in this starter.')
    result={'file':path.name,'pages':[],'warnings':[]}
    for number,page in enumerate(PdfReader(path).pages,1):
        txt=page.extract_text(extraction_mode='layout') or ''
        method='embedded_text'
        # A routing heuristic, not a guarantee of readable or complete financial tables.
        if len(''.join(txt.split()))<40:
            if not shutil.which('pdftoppm') or not shutil.which('tesseract'):
                raise RuntimeError(f'Page {number} needs OCR. Install Poppler and Tesseract, then retry.')
            with tempfile.TemporaryDirectory(prefix='nemo-ocr-') as tmp:
                base=Path(tmp)/'page'
                subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-singlefile','-r','300','-png',str(path),str(base)],check=True,capture_output=True)
                ocr=subprocess.run(['tesseract',str(base)+'.png','stdout','-l','eng','--psm','3'],check=True,capture_output=True,text=True)
                txt=ocr.stdout;method='tesseract_ocr'
        if not txt.strip(): result['warnings'].append(f'Page {number}: no text recovered; request clearer file.')
        result['pages'].append({'page':number,'method':method,'text':txt})
    result['warnings'].append('Review table alignment, negative signs, dates, currencies and units. Text length does not prove accuracy; mixed text/image pages can require manual OCR.')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    try: output=extract(args.input)
    except (RuntimeError,ValueError,OSError) as e:p.exit(1,str(e)+'\n')
    args.output.write_text(json.dumps(output,indent=2));print(f'Saved {len(output["pages"])} pages to {args.output}')
