"""Paired cell probes on top of nofull (85.02): REMOVE copies of group A (CDM delta = A's contribution),
CONVERT group B (source text block replaced by its formula copies; Text/RO delta = B's conversion cost)."""
import json,re,sys,zipfile,os
G={'YANF_num':  lambda d,s: d=='8e154f2f',
   'TRAVEL_guide': lambda d,s: d=='3135ee8c' and not re.search(r'\d',s),
   'TRAVEL_furn':  lambda d,s: d=='3135ee8c' and bool(re.search(r'\d',s)),
   'TECH':      lambda d,s: d=='7da538b6',
   'YA':        lambda d,s: d=='9cdbf6bc',
   'HOUSE':     lambda d,s: d=='ad04f287',
   'LAW':       lambda d,s: d=='2ca460ec',
   'NATURE':    lambda d,s: d=='bc7b5e32'}
def build(remove,convert,name):
    c={(r['document_id'],r['page']):r for r in map(json.loads,open('clean_1007.jsonl'))}
    out=[];st={'removed':0,'converted_blocks':0,'copies_left':0}
    for r in map(json.loads,open('furn2_5books_roman_nofull_1007.jsonl')):
        k=(r['document_id'],r['page']); d=k[0][:8]; cb=set(c[k]['markdown'].split('\n\n'))
        bl=r['markdown'].split('\n\n'); nb=[]; i=0
        while i<len(bl):
            b=bl[i]; j=i+1
            while j<len(bl) and bl[j].startswith('$') and bl[j] not in cb: j+=1
            g=bl[i+1:j]
            if g and any(G[x](d,b) for x in remove): nb.append(b); st['removed']+=len(g)
            elif g and any(G[x](d,b) for x in convert): nb+=g; st['converted_blocks']+=1
            else: nb.append(b); nb+=g; st['copies_left']+=len(g)
            i=j
        out.append(dict(r,markdown='\n\n'.join(nb)))
    with open(f'{name}.jsonl','w') as fo:
        for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
    z=f'../../submissions/tabswap/{name}.zip'
    if os.path.exists(z): os.remove(z)
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zf: zf.write(f'{name}.jsonl','predictions.jsonl')
    print(name,'remove',remove,'convert',convert,st)
build(['TECH'],['YANF_num'],'probe1_rmTECH_cvYANF')
build(['TRAVEL_furn'],['TRAVEL_guide'],'probe2_rmTRAVfurn_cvTRAVguide')
