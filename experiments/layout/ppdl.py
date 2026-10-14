"""Run a PaddleX layout model over page images -> json {img: {'dets': [[label, score, [x0,y0,x1,y1]], ...]}}"""
import sys, json, time, os
from paddlex import create_model
model_name, out, lst = sys.argv[1], sys.argv[2], sys.argv[3]
imgs = [l.strip() for l in open(lst) if l.strip()]
res = json.load(open(out)) if os.path.exists(out) else {}
m = create_model(model_name=model_name)
t0 = time.time(); n = 0
for img in imgs:
    if img in res: continue
    r = list(m.predict(img, batch_size=1))[0]
    boxes = r['boxes'] if isinstance(r, dict) else r.json['res']['boxes']
    res[img] = {'dets': [[b['label'], round(float(b['score']), 3), [round(float(v)) for v in b['coordinate']]] for b in boxes]}
    n += 1
    if n % 20 == 0:
        json.dump(res, open(out, 'w')); print(n, f'{(time.time()-t0)/n:.2f}s/page', flush=True)
json.dump(res, open(out, 'w')); print('done', n, f'{(time.time()-t0)/max(n,1):.2f}s/page')
