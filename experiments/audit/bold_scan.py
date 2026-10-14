import json,re,numpy as np,collections
from PIL import Image
from rapidfuzz import fuzz
from skimage.morphology import skeletonize
O=json.load(open('outputs/ocr_test/ocr_test.json'))
R=[json.loads(l) for l in open('outputs/work_backup_20261006/zerocopy_R_1009.jsonl')]
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
def thick(g,bx):
    x0,y0,x1,y1=[int(v) for v in bx]
    a=np.asarray(g.crop((max(0,x0-1),max(0,y0-1),x1+1,y1+1)),dtype=np.float32)
    if a.shape[0]<8 or a.shape[1]<15: return None
    ink=a<(a.mean()-0.5*a.std())
    sk=skeletonize(ink).sum()
    if sk<20: return None
    return (ink.sum()/sk, a.shape[0])               # raw stroke width, line height
rows=[]
for r in R:
    d=r['document_id']
    k=[k for k in O if f'/{d}/' in k and k.endswith(f'/page_{r["page"]}.jpg')]
    if not k or not O[k[0]]: continue
    g=Image.open(k[0]).convert('L'); ocr=O[k[0]]
    th=[(thick(g,bx),norm(t)) for t,bx in ocr if len(norm(t))>=4]; th=[x for x in th if x[0]]
    hmed=float(np.median([x[0][1] for x in th]))
    if len(th)<5: continue
    body=[x[0][0] for x in th if abs(x[0][1]/hmed-1)<0.25]
    if len(body)<5: continue
    med=float(np.median(body))
    for bi,b in enumerate(r['markdown'].split('\n\n')):
        s=b.strip()
        if not s or len(s)>150 or s.startswith(('<','|')) or '\n' in s: continue
        n=norm(re.sub(r'[*$\\#]|textit|textbf|[{}]','',s))
        if len(n)<4: continue
        m=[x for x in th if x[1]==n or (len(n)>=8 and fuzz.ratio(x[1],n)>=90)]
        if len(m)!=1: continue
        mk='bold' if re.fullmatch(r'\*\*[^*]+\*\*|\*\*\$\\textbf.*\$\*\*',s) or s.startswith('#') else ('italic' if s.startswith('*') else 'plain')
        rows.append(dict(ratio=m[0][0][0]/med,hrel=m[0][0][1]/hmed,mark=mk,s=s[:60],page=(r['subject'][:10],d[:8],r['page']),bi=bi,heading=s.startswith('#')))
json.dump(rows,open('outputs/ocr_test/bold_rows.json','w'))
for mk in ('bold','italic','plain'):
    v=np.array([x['ratio'] for x in rows if x['mark']==mk and abs(x['hrel']-1)<0.25])
    if len(v): print(f'{mk:6s} n={len(v):5d}  median ratio {np.median(v):.2f}  >=1.3: {np.mean(v>=1.3):.2f}  >=1.5: {np.mean(v>=1.5):.2f}')
