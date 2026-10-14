import json,re,numpy as np,collections,sys
from PIL import Image
from rapidfuzz import fuzz, process
from skimage.morphology import skeletonize
sys.path.insert(0,'outputs/ocr_test'); from slant import slant
O=json.load(open('outputs/ocr_test/ocr_test.json'))
U=[json.loads(l) for l in open('outputs/work_backup_20261006/zerocopy_U_1009.jsonl')]
Lr={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,open('outputs/work_backup_20261006/zerocopy_L_1009.jsonl'))}
def has_formula(md): return bool(re.search(r'\$|\\\(|\\\[|```smiles',re.sub(r'<table.*?</table>','',md,flags=re.S)))
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
def thick(g,bx):
    x0,y0,x1,y1=[int(v) for v in bx]; a=np.asarray(g.crop((max(0,x0-1),max(0,y0-1),x1+1,y1+1)),dtype=np.float32)
    if a.shape[0]<8 or a.shape[1]<15: return None
    ink=a<(a.mean()-0.5*a.std()); sk=skeletonize(ink).sum()
    return (ink.sum()/sk, a.shape[0]) if sk>=20 else None
out=[]
for r in U:
    key=(r['document_id'],r['page'])
    if has_formula(Lr[key]) or r['document_id'][:8] in ('42c763cf','4dddeac8'): continue
    k=[k for k in O if f"/{r['document_id']}/" in k and k.endswith(f"/page_{r['page']}.jpg")]
    if not k or not O[k[0]]: continue
    im=Image.open(k[0]); g=im.convert('L'); ocr=O[k[0]]
    feats=[]
    for t,bx in ocr:
        n=norm(t)
        if len(n)<4: continue
        s=slant(im,bx); th=thick(g,bx)
        if s is not None and th: feats.append((n,s,th[0],th[1]))
    if len(feats)<5: continue
    smed=float(np.median([f[1] for f in feats])); hmed=float(np.median([f[3] for f in feats]))
    tmed=float(np.median([f[2] for f in feats if abs(f[3]/hmed-1)<0.25] or [f[2] for f in feats]))
    names=[f[0] for f in feats]
    for bi,b in enumerate(r['markdown'].split('\n\n')):
        s=b.strip()
        if not s or '$' in s or '\\' in s or s.startswith(('<','|')) or len(s)>300: continue
        lines=[l for l in s.split('\n') if len(norm(l))>=4]
        if not lines or len(lines)>5: continue
        if len(lines)==1 and s.startswith('*'): continue          # single-line already-marked blocks handled before
        res=[]
        for l in lines:
            m=process.extractOne(norm(l),names,scorer=fuzz.ratio)
            if not m or m[1]<85: res=None; break
            f=feats[m[2]]; res.append((f[1]-smed, f[2]/tmed if abs(f[3]/hmed-1)<0.3 else None))
        if not res: continue
        ital=all(x[0]>=9 for x in res); bold=all(x[1] and x[1]>=1.3 for x in res)
        if ital or bold: out.append(dict(page=(r['subject'][:12],r['document_id'][:8],r['page']),bi=bi,kind='italic' if ital else 'bold',n=len(lines),s=s[:120],marked=s.startswith('*')))
json.dump(out,open('outputs/ocr_test/multiline_rows.json','w'))
print(len(out),'flagged'); 
for x in out: print(f"  {x['kind']:6s} {x['n']}L {x['page'][0]} {x['page'][1]} p{x['page'][2]} b{x['bi']}  {x['s']!r}")
