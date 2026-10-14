import json,re,glob,collections
from PIL import Image
B='outputs/work_backup_20261006'
O=json.load(open('outputs/ocr_test/ocr_test.json'))
R=[json.loads(l) for l in open(f'{B}/clean_1007.jsonl')]
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
res=collections.defaultdict(list)
for r in R:
    d=r['document_id']; key=[k for k in O if f'/{d}/' in k and k.endswith(f'/page_{r["page"]}.jpg')]
    if not key or not O[key[0]]: continue
    ocr=O[key[0]]; W,H=Image.open(key[0]).size; tag=(r['subject'][:12],d[:8],r['page'])
    md=r['markdown']; P=norm(re.sub(r'<[^>]+>',' ',md))
    # 1 dropped lines: OCR line (>=12 norm chars, not in a table region heuristic) whose middle 10 chars are absent from pred
    drop=[]
    for t,bx in ocr:
        n=norm(t)
        if len(n)>=12 and n[1:11] not in P and n[-10:] not in P and n[:10] not in P: drop.append((round(bx[1]/H,2),t[:50]))
    if drop: res['dropped OCR lines'].append((tag,len(drop),drop[:3]))
    # 2 repeated lines in pred (>=25 chars, appears twice)
    lines=[norm(l) for l in re.sub(r'<table.*?</table>','',md,flags=re.S).split('\n') if len(norm(l))>=25]
    dup=[l for l,c in collections.Counter(lines).items() if c>1]
    if dup: res['repeated pred lines'].append((tag,len(dup),dup[0][:40]))
    # 3 vertical inversions within a column: block i starts below block i+1 in the same column (x within 0.1W), y gap > 0.1H
    idx={}
    for t,bx in ocr:
        n=norm(t)
        if len(n)>=8: idx.setdefault(n[:8],bx)
    st=[]
    for bi,b in enumerate([x for x in md.split('\n\n') if x.strip()]):
        if '<t' in b: continue
        p=idx.get(norm(b.split('\n')[0])[:8])
        if p: st.append((bi,p[0]/W,p[1]/H,b[:30].replace('\n',' ')))
    for (b1,x1,y1,s1),(b2,x2,y2,s2) in zip(st,st[1:]):
        if abs(x1-x2)<0.1 and y1>y2+0.1 and y2>0.07 and y1<0.93:
            res['vertical inversion (same column)'].append((tag,b1,round(y1,2),s1,'->',round(y2,2),s2))
for k,v in res.items():
    print(f'\n### {k}: {len(v)} pages')
    for x in sorted(v,key=lambda z:-z[1] if isinstance(z[1],int) else 0)[:25]: print('  ',x)
