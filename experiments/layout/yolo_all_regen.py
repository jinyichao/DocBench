"""Regenerate yolo_all.json: DocLayout-YOLO (docstructbench, imgsz 1024, MPS) over all dev+test page images."""
import os
import json, glob, sys
from PIL import Image
from doclayout_yolo import YOLOv10
S = os.environ.get('DRDOC_WORK', 'outputs/work')
m = YOLOv10('vendor/doclayout/doclayout_yolo_docstructbench_imgsz1024.pt')
imgs = sorted(glob.glob('data/DrDocBench/dev/*/*/images/*.jpg') + glob.glob('data/DrDocBench/test/*/*/images/*.jpg'))
out = {}
for i, p in enumerate(imgs):
    r = m.predict(p, imgsz=1024, conf=0.2, device='mps', verbose=False)[0]
    w, h = Image.open(p).size
    out[p] = {'w': w, 'h': h, 'dets': [[r.names[int(c)], round(float(s), 3), [round(float(v)) for v in b]]
                                       for c, s, b in zip(r.boxes.cls, r.boxes.conf, r.boxes.xyxy)]}
    if i % 200 == 0: print(i, len(imgs), flush=True)
json.dump(out, open(f'{S}/yolo_all.json', 'w')); print('done', len(out))
