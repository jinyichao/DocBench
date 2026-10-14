import json,re,collections,difflib
from PIL import Image
try:
    from rapidfuzz import fuzz; pr=lambda a,b: fuzz.partial_ratio(a,b)
except ImportError:
    pr=lambda a,b: 100*max((difflib.SequenceMatcher(None,a,b[i:i+len(a)+10]).ratio() for i in range(0,max(1,len(b)-len(a)),max(1,len(a)//3))),default=0)
B='outputs/work_backup_20261006'
O=json.load(open('outputs/ocr_test/ocr_test.json'))
R=[json.loads(l) for l in open(f'{B}/clean_1007.jsonl')]
norm=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
SKIP={'4dddeac8'}  # word-search grids (excluded from scoring)
drops=[];inv=[]
for r in R:
    d=r['document_id']
    if d[:8] in SKIP: continue
    key=[k for k in O if f'/{d}/' in k and k.endswith(f'/page_{r["page"]}.jpg')]
    if not key or not O[key[0]]: continue
    ocr=O[key[0]]; W,H=Image.open(key[0]).size; tag=(r['subject'][:12],d[:8],r['page'])
    md=r['markdown']; P=norm(re.sub(r'<[^>]+>',' ',md))
    dl=[]
    for t,bx in ocr:
        n=norm(t)
        if len(n)>=15 and n[2:12] not in P and pr(n,P)<75: dl.append((round(bx[1]/H,2),t[:60]))
    if dl: drops.append((tag,len(dl),dl[:4]))
    # unique-line positions
    cnt=collections.Counter(norm(t) for t,_ in ocr); pos={norm(t):bx for t,bx in ocr if len(norm(t))>=15 and cnt[norm(t)]==1}
    st=[]
    for bi,b in enumerate([x for x in md.split('\n\n') if x.strip()]):
        if '<t' in b: continue
        f=norm(b.split('\n')[0])
        hit=[v for k,v in pos.items() if k==f or (len(f)>=15 and k.startswith(f[:20]))]
        if len(hit)==1: st.append((bi,hit[0][0]/W,hit[0][1]/H,b[:35].replace('\n',' ')))
    for (b1,x1,y1,s1),(b2,x2,y2,s2) in zip(st,st[1:]):
        if abs(x1-x2)<0.08 and y1>y2+0.12 and 0.07<y2 and y1<0.93: inv.append((tag,b1,round(x1,2),round(y1,2),s1,'->',round(y2,2),s2))
print('### dropped lines (fuzzy <75):',len(drops),'pages')
for x in sorted(drops,key=lambda z:-z[1])[:30]: print('  ',x)
print('\n### same-column upward jumps (unique lines):',len(inv))
for x in inv[:40]: print('  ',x)
