"""zerocopy_F = E, but TECH/TRAVEL running heads: number as its own formula block, head stays a text block (source order)."""
import json,re,zipfile
import build_inline as I
out=[];n=0
for r in map(json.loads,open('zerocopy_E_1007.jsonl')):
    d=r['document_id'][:8]; bl=r['markdown'].split('\n\n'); nb=[]
    for b in bl:
        if d in ('7da538b6','3135ee8c') and b.startswith('*$\\textit{'):
            parts=re.findall(r'\$\\textit\{(.*?)\}\$',b)
            nb+=[f'$\\textit{{{p}}}$' if re.fullmatch(r'\d{1,4}',p) else (f'*{p}*' if d=='7da538b6' else p) for p in parts]; n+=1
        else: nb.append(b)
    out.append(dict(r,markdown='\n\n'.join(nb)))
with open('zerocopy_F_1007.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_F_1007.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_F_1007.jsonl','predictions.jsonl')
print('split blocks',n)
L={(x['document_id'][:8],x['page']):x['markdown'] for x in out}
for k in [('7da538b6',801),('3135ee8c',217),('3135ee8c',218)]: print(k,L[k].split('\n\n')[-2:])
