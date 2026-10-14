"""zerocopy_K = J, but on pages with genuine math (frac/times/sub/sup/$$/\\[/smiles) the I/H additions
(bold headings, whole-italic blocks) are reverted to their G form, so they cannot steal the real formulas' matches."""
import json,re,zipfile,collections
G={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,open('zerocopy_G_1007.jsonl'))}
def realmath(md):
    md2=re.sub(r'\$\\text(it|bf)\{[^$]*\}\$','',md)
    return bool(re.search(r'\$\$|\\\[|```smiles|\\frac|\\times|_\{|\^\{(?!\\circ)|\\ce\{|\\Delta|\\alpha|\\beta',md2))
out=[];rev=collections.Counter()
for r in map(json.loads,open('zerocopy_J_1008.jsonl')):
    k=(r['document_id'],r['page']); md=r['markdown']
    if md!=G[k] and realmath(G[k]):
        gb=G[k].split('\n\n'); jb=md.split('\n\n')
        if len(gb)==len(jb):
            nb=[g if ('$\\textbf{' in j or (j.startswith('*$\\textit{') and not g.startswith('*$\\textit{') and r['document_id'][:8] not in ('53a172d1','ba58d30d','558c4212','adf56403','5ffbad37','2ca460ec'))) else j for g,j in zip(gb,jb)]
            n=sum(a!=b for a,b in zip(nb,jb))
            if n: rev[r['subject'][:12]+' p'+str(k[1])]+=n; md='\n\n'.join(nb)
        else: print('block count differs',k)
    out.append(dict(r,markdown=md))
with open('zerocopy_K_1009.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_K_1009.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_K_1009.jsonl','predictions.jsonl')
print('reverted',sum(rev.values()),'blocks on',len(rev),'pages'); print(dict(rev))
