import json,re,numpy as np,collections,sys
from PIL import Image
from rapidfuzz import fuzz
sys.path.insert(0,'outputs/ocr_test'); from slant import slant
O=json.load(open('outputs/ocr_test/ocr_test.json'))
R=[json.loads(l) for l in open('outputs/work_backup_20261006/zerocopy_Q_1009.jsonl')]
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
rows=[]
for r in R:
    d=r['document_id']
    k=[k for k in O if f'/{d}/' in k and k.endswith(f'/page_{r["page"]}.jpg')]
    if not k or not O[k[0]]: continue
    im=Image.open(k[0]); ocr=O[k[0]]
    sl=[(slant(im,bx),norm(t),t) for t,bx in ocr if len(norm(t))>=4]
    sl=[x for x in sl if x[0] is not None]
    if len(sl)<5: continue
    med=float(np.median([x[0] for x in sl]))
    for bi,b in enumerate(r['markdown'].split('\n\n')):
        s=b.strip()
        if not s or len(s)>150 or s.startswith(('<','$','#','|')) or '\n' in s: continue
        plain=re.sub(r'[*$\\]|textit|textbf|[{}]','',s); n=norm(plain)
        if len(n)<4: continue
        m=[x for x in sl if x[1]==n or (len(n)>=8 and fuzz.ratio(x[1],n)>=90)]
        if len(m)!=1: continue
        mk='italic' if re.fullmatch(r'\*(?!\*)[^*]+\*|\*\$\\textit.*\$\*',s) else ('bold' if s.startswith('**') else 'plain')
        rows.append(dict(diff=m[0][0]-med,mark=mk,s=s[:60],page=(r['subject'][:10],d[:8],r['page']),bi=bi))
json.dump(rows,open('outputs/ocr_test/slant_rows.json','w'))
for mk in ('italic','bold','plain'):
    v=np.array([x['diff'] for x in rows if x['mark']==mk])
    if len(v): print(f'{mk:6s} n={len(v):5d}  diff>=8: {np.mean(v>=8):.2f}  diff>=10: {np.mean(v>=10):.2f}  median {np.median(v):+.1f}')
