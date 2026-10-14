# furn2_5books_roman minus the fused "full" copy in groups that already have both a number-only and a words-only copy
import json,re,collections
c={(r['document_id'],r['page']):r for r in map(json.loads,open('clean_1007.jsonl'))}
def kind(b):
    x=re.sub(r'^\$\\textit\{|\}\$$','',b)
    if re.fullmatch(r'[\divxlcdm\s]+',x): return 'num'
    return 'full' if re.search(r'\d',x) or re.search(r'(?<![A-Za-z])[ivxlcdm]{1,7}(?![A-Za-z])',x) else 'words'
out=[];dropped=collections.Counter();kept=0
for r in map(json.loads,open('furn2_5books_roman_1007.jsonl')):
    k=(r['document_id'],r['page']); cb=set(c[k]['markdown'].split('\n\n'))
    bl=r['markdown'].split('\n\n'); nb=[]; i=0
    while i<len(bl):
        if bl[i].startswith('$') and bl[i] not in cb:
            j=i
            while j<len(bl) and bl[j].startswith('$') and bl[j] not in cb: j+=1
            g=bl[i:j]; ks=[kind(x) for x in g]
            if len(g)==3 and ks==['num','words','full']: dropped[r['subject']]+=1; g=g[:2]
            kept+=len(g); nb+=g; i=j
        else: nb.append(bl[i]); i+=1
    out.append(dict(r,markdown='\n\n'.join(nb)))
with open('furn2_5books_roman_nofull_1007.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
print('dropped',dict(dropped),sum(dropped.values()),'copies kept',kept)
