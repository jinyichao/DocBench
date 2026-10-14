"""Docling 'Heron' layout model (RT-DETRv2) via transformers -> {img: {'dets': [[label, score, box]]}}"""
import sys, json, os, time, torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection
MID = 'ds4sd/docling-layout-heron'
out, lst = sys.argv[1], sys.argv[2]; thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
dev = 'cpu'
proc = AutoImageProcessor.from_pretrained(MID); model = AutoModelForObjectDetection.from_pretrained(MID).to(dev).eval()
imgs = [l.strip() for l in open(lst) if l.strip()]
res = json.load(open(out)) if os.path.exists(out) else {}
t0 = time.time(); n = 0
for p in imgs:
    if p in res: continue
    im = Image.open(p).convert('RGB')
    inp = proc(images=im, return_tensors='pt').to(dev)
    with torch.no_grad(): o = model(**inp)
    r = proc.post_process_object_detection(o, target_sizes=torch.tensor([im.size[::-1]]), threshold=thr)[0]
    res[p] = {'w': im.size[0], 'h': im.size[1], 'dets': [[model.config.id2label[int(l)], round(float(s), 3), [round(float(v)) for v in b]]
                                                       for s, l, b in zip(r['scores'].cpu(), r['labels'].cpu(), r['boxes'].cpu())]}
    n += 1
    if n % 50 == 0: json.dump(res, open(out, 'w')); print(n, f'{(time.time()-t0)/n:.2f}s/page', flush=True)
json.dump(res, open(out, 'w')); print('done', n, f'{(time.time()-t0)/max(n,1):.2f}s/page')
