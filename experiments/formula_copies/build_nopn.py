import sys,json,re,zipfile,collections
B='outputs/work_backup_20261006'
sys.path.insert(0,B); sys.path.insert(0,'.')
import copies
from utils.extract import md_tex_filter
v7=copies.VARIANTS['v7']
base=[json.loads(l) for l in open(f'{B}/next_base.jsonl')]
HDR=re.compile(r'\**(KEY TECHNIQUES : QUESTIONS|UNITS 1,2 AND 3 : WORKBOOK)\**')
PN=re.compile(r'\$\\textit\{\s*(\d{1,4}|[ivxlcdm]{1,7}|[A-Z]\d{1,3})\s*\}\$',re.I)
rows=[]; removed=collections.Counter(); kept=0
for r in base:
    md=r['markdown']
    if r['document_id'].startswith('9352143f'):
        bl=md.split('\n\n'); n=len(bl); ts=max(0,n-4)
        hi=[i for i in range(ts,n) if HDR.fullmatch(bl[i].strip())]
        fi=[i for i in range(ts,n) if 'KAPLAN PUBLISHING' in bl[i] or re.fullmatch(r'\d{1,3}',bl[i].strip())]
        if hi and fi and hi[0]>min(fi): h=bl.pop(hi[0]); bl.insert(min(fi),h); md='\n\n'.join(bl)
    out=[]
    for b in v7(md).split('\n\n'):
        s=b.strip()
        if PN.fullmatch(s): removed[s]+=1; continue
        if s.startswith('$\\textit{'): kept+=1
        out.append(b)
    rows.append(dict(r,markdown='\n\n'.join(out)))
with open(f'{B}/nopn_copies.jsonl','w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print('page-number copies removed:',sum(removed.values()),'| other copies kept:',kept)
print('examples removed:',list(removed)[:15])
best={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,zipfile.ZipFile('submission_85.91.zip').open('predictions.jsonl'))}
txt=lambda m:[x['content'] for x in md_tex_filter(m).get('text_all',[])]
print('pages with changed scored text vs 85.91:',[(r['document_id'][:8],r['page']) for r in rows if txt(r['markdown'])!=txt(best[(r['document_id'],r['page'])])])
