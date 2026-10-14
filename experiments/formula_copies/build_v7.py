import sys,json,re,zipfile
B='outputs/work_backup_20261006'
sys.path.insert(0,B); sys.path.insert(0,'.')
import copies
from utils.extract import md_tex_filter
v7=copies.VARIANTS['v7']; name=sys.argv[1]
HDR=re.compile(r'\**(KEY TECHNIQUES : QUESTIONS|UNITS 1,2 AND 3 : WORKBOOK)\**')
rows=[]
for r in map(json.loads,open(f'{B}/next_base.jsonl')):
    md=r['markdown']
    if r['document_id'].startswith('9352143f'):
        bl=md.split('\n\n'); n=len(bl); ts=max(0,n-4)
        hi=[i for i in range(ts,n) if HDR.fullmatch(bl[i].strip())]
        fi=[i for i in range(ts,n) if 'KAPLAN PUBLISHING' in bl[i] or re.fullmatch(r'\d{1,3}',bl[i].strip())]
        if hi and fi and hi[0]>min(fi): h=bl.pop(hi[0]); bl.insert(min(fi),h); md='\n\n'.join(bl)
    rows.append(dict(r,markdown=v7(md)))
with open(f'{B}/{name}.jsonl','w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
best={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,zipfile.ZipFile('submission_85.91.zip').open('predictions.jsonl'))}
txt=lambda m:[x['content'] for x in md_tex_filter(m).get('text_all',[])]
print('pages changed vs 85.91 (scored text):',[(r['document_id'][:8],r['page']) for r in rows if txt(r['markdown'])!=txt(best[(r['document_id'],r['page'])])])
print('pages differing at all:',sum(1 for r in rows if r['markdown']!=best[(r['document_id'],r['page'])]))
