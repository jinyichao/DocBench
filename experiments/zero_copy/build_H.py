"""zerocopy_H = G + italic-inline for whole blocks printed in italics (`*text*` single-line <=150 chars)."""
import json,re,zipfile
IT=re.compile(r'^\*(?!\*)([^*\n]+?)(?<!\*)\*$')
def esc(s):
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]: s=s.replace(a,b)
    return s
out=[];n=0;ex=[]
for r in map(json.loads,open('zerocopy_G_1007.jsonl')):
    bl=r['markdown'].split('\n\n')
    for i,b in enumerate(bl):
        s=b.strip(); m=IT.match(s)
        if m and len(s)<=150 and not re.search(r'[$\\<{}^~]',s) and re.search(r'\w',m.group(1)):
            bl[i]='*$\\textit{'+esc(m.group(1).strip())+'}$*'; n+=1
            if len(ex)<12: ex.append((r['subject'][:8],r['page'],s[:60]))
    out.append(dict(r,markdown='\n\n'.join(bl)))
with open('zerocopy_H_1008.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_H_1008.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_H_1008.jsonl','predictions.jsonl')
print('italic blocks inlined',n); [print('  ',e) for e in ex]
