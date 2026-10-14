import json,re,zipfile,collections
f={(r['document_id'],r['page']):r for r in map(json.loads,open('furn2_t3_1007.jsonl'))}
KEEP_ALL={'7da538b6','3135ee8c','ad04f287','9cdbf6bc','8e154f2f','2ca460ec'}
ROMAN_ONLY={'bc7b5e32'}
ROM=re.compile(r'(?<![A-Za-z])[ivxlcdm]{1,7}(?![A-Za-z])')
out=[];cnt=collections.Counter()
for r in map(json.loads,open('clean_1007.jsonl')):
    k=(r['document_id'],r['page']); d=k[0][:8]
    cb=set(r['markdown'].split('\n\n')); fb=f[k]['markdown'].split('\n\n')
    if d in KEEP_ALL or d in ROMAN_ONLY:
        keep=[]
        for b in fb:
            new=b.startswith('$') and b not in cb
            if new and d in ROMAN_ONLY and not ROM.search(b.replace('\\textit','')): continue
            if new: cnt[r['subject']]+=1
            keep.append(b)
        r=dict(r,markdown='\n\n'.join(keep))
    out.append(r)
with open('furn2_5books_roman_1007.jsonl','w') as fo:
    for r in out: fo.write(json.dumps(r,ensure_ascii=False)+'\n')
print(dict(cnt),sum(cnt.values()),len(out))
