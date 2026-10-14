"""zerocopy_I = H + bold-printed headings / whole-bold lines as inline $\\textbf{}$ (text unchanged)."""
import json,re,zipfile,collections
def esc(s):
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]: s=s.replace(a,b)
    return s
def bold_inline_block(b):
    s=b.strip()
    if not s or '\n' in s or len(s)>150 or re.search(r'[$\\<{}^~]',s): return b
    m=re.match(r'^(#{1,6})\s+(.+)$',s)
    if m:
        t=m.group(2).strip().strip('*').strip()
        if re.search(r'\w',t) and '*' not in t and '_' not in t: return f'{m.group(1)} $\\textbf{{{esc(t)}}}$'
        return b
    m=re.match(r'^\*\*([^*\n]+?)\*\*$',s)
    if m:
        t=m.group(1).strip()
        if len(t)>2 and t[0]==t[-1]=='_': t=t[1:-1].strip()
        if '_' in t or not re.search(r'\w',t): return b
        return '**$\\textbf{'+esc(t)+'}$**'
    return b
out=[];cnt=collections.Counter();ex=[]
for r in map(json.loads,open('zerocopy_H_1008.jsonl')):
    parts=re.split(r'(<table.*?</table>|```.*?```|\$\$.*?\$\$)',r['markdown'],flags=re.S); np=[]
    for i,p in enumerate(parts):
        if i%2: np.append(p); continue
        bl=p.split('\n\n'); nb=[bold_inline_block(b) for b in bl]
        for a,b in zip(bl,nb):
            if a!=b:
                cnt[r['subject'][:12]]+=1
                if len(ex)<10: ex.append(b[:70])
        np.append('\n\n'.join(nb))
    out.append(dict(r,markdown=''.join(np)))
with open('zerocopy_I_1008.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_I_1008.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_I_1008.jsonl','predictions.jsonl')
print('bold blocks',sum(cnt.values()),dict(cnt)); [print('  ',e) for e in ex]
