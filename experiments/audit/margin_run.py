import json, os, sys, collections
S = os.environ.get('DRDOC_WORK', 'outputs/work')
sys.path.insert(0, S); import margin_heads as mh
src, dst, minp = sys.argv[1], sys.argv[2], int(sys.argv[3])
R = [json.loads(l) for l in open(f'outputs/{src}/index.jsonl')]; R = [r for r in R if os.path.exists(r['md_path'])]
docs = collections.defaultdict(list)
for r in R: docs[r['document_id']].append(r)
os.makedirs(f'outputs/{dst}', exist_ok=True); tot = 0
with open(f'outputs/{dst}/index.jsonl', 'w') as f:
    for d, rs in docs.items():
        new, n = mh.recover_recurring([(open(r['md_path']).read(), r['image_path']) for r in rs], minp); tot += n
        for r, md in zip(rs, new):
            p = r['md_path'].replace(f'/{src}/', f'/{dst}/'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(md); f.write(json.dumps(dict(r, md_path=p)) + '\n')
print(dst, 'added', tot)
