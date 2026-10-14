"""zerocopy_J = I + italic-inline on the running heads/page numbers of books printing them in italics
(HUMOR 53a172d1, LAW ba58d30d, BUSINESS 558c4212, JUVNF adf56403, DRAMA 5ffbad37, LAW 2ca460ec head).
Source blocks = those clean_ittails converted for these docs."""
import json,re,zipfile,collections
DOCS={'53a172d1','ba58d30d','558c4212','adf56403','5ffbad37','2ca460ec'}
c={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,open('clean_1007.jsonl'))}
t={(r['document_id'],r['page']):r['markdown'] for r in map(json.loads,open('clean_ittails_1007.jsonl'))}
def esc(s):
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]: s=s.replace(a,b)
    return s
NUM=r'(?<![\w.,/])(\d{1,4}|[ivxlc]{1,7})(?![\w.,/])'
def line_pieces(l):
    l=re.sub(r'\*','',l).strip()
    m=re.fullmatch(r'(\d{1,3})\s+(\D*[A-Za-z]{3}.*)',l) or re.fullmatch(r'(.*[A-Za-z]{3}\D*)\s+(\d{1,3})',l)
    return [x.strip() for x in m.groups()] if m else ([l] if l else [])
out=[];cnt=collections.Counter();ex=[]
for r in map(json.loads,open('zerocopy_I_1008.jsonl')):
    k=(r['document_id'],r['page']); d=k[0][:8]; md=r['markdown']
    if d in DOCS and t[k]!=c[k]:
        src=[b for b in c[k].split('\n\n') if b not in t[k].split('\n\n')]
        bl=md.split('\n\n')
        for i,b in enumerate(bl):
            if b in src and '$' not in b and len(b)<=120 and not re.search(r'[\\<{}^~_]',b):
                if d=='2ca460ec':   # number already inline in I; nothing else
                    continue
                lines=[' '.join('$\\textit{'+esc(p)+'}$' for p in line_pieces(l)) for l in b.split('\n')]
                lines=[x for x in lines if x]
                if not lines: continue
                bl[i]='*'+'\n'.join(lines)+'*'; cnt[r['subject'][:10]+' '+d]+=1
                if len(ex)<8: ex.append((b[:50],bl[i][:90]))
        md='\n\n'.join(bl)
    if d=='2ca460ec':
        bl=md.split('\n\n')
        # LAW 2ca460ec: italic head next to the inline numeral -> `$\textit{lvi}$ *$\textit{Table of cases}$*`
        for i,b in enumerate(bl):
                m=re.fullmatch(r'(\$\\textit\{[ivxlc]+\}\$ )?\*(Table of (?:cases|legislation))\*( \$\\textit\{[ivxlc]+\}\$)?',b.strip())
                if m and (m.group(1) or m.group(3)):
                    bl[i]=(m.group(1) or '')+'*$\\textit{'+m.group(2)+'}$*'+(m.group(3) or ''); cnt['LAW 2ca460ec head']+=1
        md='\n\n'.join(bl)
    out.append(dict(r,markdown=md))
with open('zerocopy_J_1008.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
with zipfile.ZipFile('../../submissions/tabswap/zerocopy_J_1008.zip','w',zipfile.ZIP_DEFLATED) as zf: zf.write('zerocopy_J_1008.jsonl','predictions.jsonl')
print(dict(cnt),sum(cnt.values()))
for e in ex: print('  ',e)
