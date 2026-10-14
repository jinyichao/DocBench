import sys,json,re,zipfile
B='outputs/work_backup_20261006'
sys.path.insert(0,B); sys.path.insert(0,'.')
import copies_tails as C
from utils.extract import md_tex_filter
f=C.VARIANTS['v7_tails3']
rows=[dict(r,markdown=f(r['markdown'])) for r in map(json.loads,open(f'{B}/clean_1007.jsonl'))]
with open(f'{B}/tails3_1007.jsonl','w') as fo:
    for r in rows: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
cl={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,open(f'{B}/clean_1007.jsonl'))}
txt=lambda m:[x['content'] for x in md_tex_filter(m).get('text_all',[])]
ncopy=sum(r['markdown'].count('$\\textit{') for r in rows)
same=sum(1 for r in rows if txt(r['markdown'])==txt(cl[(r['document_id'],r['page'])]))
print('tail copies:',ncopy,'| pages with copies:',sum(1 for r in rows if '$\\textit{' in r['markdown']),'| scored text identical to clean on',same,'/ 509 pages')
