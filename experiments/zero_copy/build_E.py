"""zerocopy_E: block conversion where it is free (YA/LAW/NATURE numbers, HOUSE) + italic-inline form for
TECH/TRAVEL running heads and YANF page numbers (printed italic): `*$\\textit{216}$ $\\textit{A-Z Birmingham}$*`.
Every piece of content appears exactly once."""
import json,re,zipfile
import build_zerocopy as Z, build_inline as I
Z.build(['YAnum','HOUSE','LAW','NATURE'],'_E_base')
NUM=I.NUM
def italic_inline(s):
    t=re.sub(r'\*','',s).strip(); m=re.search(NUM,t); n=m.group(1)
    head=re.sub(r'\s+',' ',re.sub(NUM,'',t,count=1)).strip()
    parts=[f'$\\textit{{{n}}}$']+([f'$\\textit{{{head}}}$'] if head else [])
    if head and t.endswith(n): parts=parts[::-1]
    return '*'+' '.join(parts)+'*'
out=[];cnt={}
for r in map(json.loads,open('_E_base.jsonl')):
    d=r['document_id'][:8]; bl=r['markdown'].split('\n\n')
    for i,b in enumerate(bl):
        s=b.strip()
        hit=(d in ('7da538b6','3135ee8c') and I.furn(d,s,True)) or (d=='8e154f2f' and re.fullmatch(r'\**\d{1,4}\**',s) and i==len(bl)-1)
        if hit: bl[i]=italic_inline(s); cnt[d]=cnt.get(d,0)+1
    out.append(dict(r,markdown='\n\n'.join(bl)))
with open('zerocopy_E_1007.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_E_1007.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_E_1007.jsonl','predictions.jsonl')
print('inline blocks',cnt,sum(cnt.values()))
