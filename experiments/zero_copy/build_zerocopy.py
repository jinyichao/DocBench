"""Zero-copy builds: for chosen groups, REPLACE the source text block by its formula piece(s) (in source order); every other copy dropped."""
import json,re,sys
G={'YANF':lambda d,s: d=='8e154f2f',
   'TRAVguide':lambda d,s: d=='3135ee8c' and not re.search(r'\d',s),
   'TRAVfurn':lambda d,s: d=='3135ee8c' and bool(re.search(r'\d',s)),
   'TECHfurn':lambda d,s: d=='7da538b6' and bool(re.search(r'\d',s)),
   'TECHcont':lambda d,s: d=='7da538b6' and not re.search(r'\d',s),
   'YAnum':lambda d,s: d=='9cdbf6bc' and bool(re.search(r'\d',s)),
   'YAother':lambda d,s: d=='9cdbf6bc' and not re.search(r'\d',s),
   'HOUSE':lambda d,s: d=='ad04f287',
   'LAW':lambda d,s: d=='2ca460ec',
   'NATURE':lambda d,s: d=='bc7b5e32'}
def inner(b): return re.sub(r'^\$\\textit\{|\}\$$','',b)
def convert(src,g,d):
    pieces=[x for x in g if not (d=='9cdbf6bc' and not re.fullmatch(r'[\divxlcdm\s]+',inner(x)))] if d=='9cdbf6bc' and re.search(r'\d',src) else g
    if d in ('2ca460ec','bc7b5e32') or d=='9cdbf6bc':
        # number-only formula, rest of the block stays text (YA: head is printed upright)
        num=[x for x in g if re.fullmatch(r'[\divxlcdm\s]+',inner(x))]
        if not num: return g if d!='9cdbf6bc' else g
        n=inner(num[0]); lines=src.split('\n')
        rest=re.sub(r'(?<![\w])'+re.escape(n)+r'(?![\w])','',src,count=1)
        rest='\n'.join(l.strip() for l in rest.split('\n') if l.strip()).strip()
        first=src.strip().startswith(n) or src.split('\n')[0].strip()==n
        out=[num[0]]+([rest] if rest else [])
        return out if first else ([rest] if rest else [])+[num[0]]
    # TECH/TRAVEL/HOUSE: all pieces, in source order
    pos=lambda x: (src.find(inner(x).split()[0]) if inner(x).split() else 0)
    return sorted(g,key=pos)
def build(conv,name):
    c={(r['document_id'],r['page']):r for r in map(json.loads,open('clean_1007.jsonl'))}
    out=[];n=0
    for r in map(json.loads,open('furn2_5books_roman_nofull_1007.jsonl')):
        k=(r['document_id'],r['page']); d=k[0][:8]; cb=set(c[k]['markdown'].split('\n\n'))
        bl=r['markdown'].split('\n\n'); nb=[]; i=0
        while i<len(bl):
            b=bl[i]; j=i+1
            while j<len(bl) and bl[j].startswith('$') and bl[j] not in cb: j+=1
            g=bl[i+1:j]
            if g and any(G[x](d,b) for x in conv): nb+=convert(b,g,d); n+=1
            else: nb.append(b)
            i=j
        out.append(dict(r,markdown='\n\n'.join(nb)))
    with open(f'{name}.jsonl','w') as fo:
        for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
    return n
if __name__=='__main__':
    for g in G: print(g, build([g],f'outputs/work/sim/zc_{g}'))
