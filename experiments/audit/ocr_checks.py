import json,re,glob,collections
from PIL import Image
B='outputs/work_backup_20261006'
O=json.load(open('outputs/ocr_test/ocr_test.json'))
R=[json.loads(l) for l in open(f'{B}/next_base.jsonl')]
subj={p.split('/')[-1]:p.split('/')[-2] for p in glob.glob('data/DrDocBench/test/*/*')}
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
out=collections.defaultdict(list)
for r in R:
    d=r['document_id']; key=[k for k in O if f'/{d}/' in k and k.endswith(f'/page_{r["page"]}.jpg')]
    if not key or not O[key[0]]: continue
    ocr=O[key[0]]; W,H=Image.open(key[0]).size; tag=(subj[d][:12],d[:8],r['page'])
    md=r['markdown']; txt=re.sub(r'<table.*?</table>','',md,flags=re.S)
    bl=[b for b in md.split('\n\n') if b.strip()]
    # line -> box lookup by prefix
    idx=collections.defaultdict(list)
    for t,bx in ocr:
        n=norm(t)
        if len(n)>=6: idx[n[:8]].append(bx)
    def pos(line):
        n=norm(line)
        if len(n)<6: return None
        c=idx.get(n[:8]); return c[0] if c else None
    # (2) fused columns: inside one block, consecutive located lines jump right by >0.2W and continue there
    for bi,b in enumerate(bl):
        if '<t' in b: continue
        P=[pos(l) for l in b.split('\n')]; xs=[(i,p[0],p[1]) for i,p in enumerate(P) if p]
        for (i1,x1,y1),(i2,x2,y2) in zip(xs,xs[1:]):
            if x2-x1>0.2*W and y2<y1-0.1*H:
                out['fused columns'].append((tag,bi,b.split('\n')[i2][:30])); break
    # (3) omission / extra by word multiset
    wo=collections.Counter(re.findall(r'[a-z]{3,}',' '.join(t for t,_ in ocr).lower()))
    wp=collections.Counter(re.findall(r'[a-z]{3,}',re.sub(r'\\[a-zA-Z]+','',txt).lower()))
    if sum(wo.values())>=40:
        inter=sum((wo&wp).values()); rec=inter/sum(wo.values()); prec=inter/max(1,sum(wp.values()))
        if rec<0.8: out['possible omission'].append((tag,round(rec,2),sum(wo.values())))
        if prec<0.8: out['possible extra text'].append((tag,round(prec,2),sum(wp.values())))
    # (4) column order: block starting in the left column and higher up, placed after a right-column block
    starts=[]
    for bi,b in enumerate(bl):
        p=pos(b.split('\n')[0]) if '<t' not in b else None
        if p: starts.append((bi,p[0]/W,p[1]/H))
    for (b1,x1,y1),(b2,x2,y2) in zip(starts,starts[1:]):
        if x1>0.5 and x2<0.35 and y2<y1-0.15 and y2>0.08:
            out['order: left-col block after right-col block'].append((tag,b1,b2,bl[b2][:30].replace('\n',' ')))
for k,v in out.items():
    print(f'\n### {k}: {len(v)}')
    for x in v[:40]: print('  ',x)
