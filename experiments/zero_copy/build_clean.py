"""Clean builds (no formula copies): next_base + STUDYAIDS header order [+ italic<=N whole-block -> $\textit{}$]."""
import sys,json,re
B='outputs/work_backup_20261006'
N=int(sys.argv[1]) if len(sys.argv)>1 else 0; name=sys.argv[2]
HDR=re.compile(r'\**(KEY TECHNIQUES : QUESTIONS|UNITS 1,2 AND 3 : WORKBOOK)\**')
IT=re.compile(r'\*(?!\*)[^*\n]{1,%d}(?<!\*)\*'%max(N,1))
def esc(s):
    s=re.sub(r'[*`#>]|\\','',s); s=re.sub(r'\s+',' ',s).strip()
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('{',r'\{'),('}',r'\}')]: s=s.replace(a,b)
    return s
rows=[]; conv=[]
for r in map(json.loads,open(f'{B}/next_base.jsonl')):
    md=r['markdown']
    if r['document_id'].startswith('9352143f'):
        bl=md.split('\n\n'); n=len(bl); ts=max(0,n-4)
        hi=[i for i in range(ts,n) if HDR.fullmatch(bl[i].strip())]
        fi=[i for i in range(ts,n) if 'KAPLAN PUBLISHING' in bl[i] or re.fullmatch(r'\d{1,3}',bl[i].strip())]
        if hi and fi and hi[0]>min(fi): h=bl.pop(hi[0]); bl.insert(min(fi),h); md='\n\n'.join(bl)
    if N:
        out=[]
        for b in md.split('\n\n'):
            s=b.strip()
            if s and '<' not in s and '$' not in s and '\\(' not in s and not s.startswith('#') and IT.fullmatch(s):
                out.append('$\\textit{'+esc(s)+'}$'); conv.append((r['document_id'][:8],r['page'],s[:40]))
            else: out.append(b)
        md='\n\n'.join(out)
    rows.append(dict(r,markdown=md))
with open(f'{B}/{name}.jsonl','w') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(name,'converted italic blocks:',len(conv),'| formula copies present:',sum(r['markdown'].count('$\\textit{') for r in rows)-len(conv))
for c in conv: print('  ',c)
