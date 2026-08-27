"""Reusable multi-column detection + region ordering (run in .venv-layout).

For each page: detect layout boxes, decide column count, and emit an ORDERED list
of crop regions [x0,y0,x1,y1] following reading order:
  [optional top full-width band] -> left column -> right column -> [bottom band]
Single-column pages emit one whole-page region. Output: JSON {img_path: {ncols, regions}}.

Usage: .venv-layout/bin/python src/detect_columns.py --pages <file> --out <json>
"""
import argparse, glob, json
from doclayout_yolo import YOLOv10

MODEL="vendor/doclayout/doclayout_yolo_docstructbench_imgsz1024.pt"
CONTENT={"plain text","title","table","figure","figure_caption","isolate_formula"}

def regions_for(boxes, W, H):
    if not boxes: return 1, [[0,0,W,H]]
    def w(b): return b[2]-b[0]
    def cx(b): return (b[0]+b[2])/2
    full=[b for b in boxes if w(b)>0.6*W]
    cols=[b for b in boxes if w(b)<=0.6*W]
    if len(cols)<2:
        return 1, [[0,0,W,H]]
    centers=sorted(cx(b) for b in cols)
    # find ALL significant column gaps -> N-column split points (handles 2 and 3+ columns)
    splits=[(centers[i+1]+centers[i])/2 for i in range(len(centers)-1)
            if centers[i+1]-centers[i] > 0.15*W]
    if not splits:
        return 1, [[0,0,W,H]]
    ncols=len(splits)+1
    # top band = full-width blocks near top (title); bottom band = full-width near bottom
    col_top=min(b[1] for b in cols); col_bot=max(b[3] for b in cols)
    top_fw=[b for b in full if b[1] < col_top+0.05*H]
    bot_fw=[b for b in full if b[3] > col_bot-0.05*H]
    regions=[]
    top_y=max([b[3] for b in top_fw], default=0)
    bot_y=min([b[1] for b in bot_fw], default=H)
    if top_fw: regions.append([0,0,W,int(top_y)])
    pad=8
    bounds=[0]+[int(s) for s in splits]+[W]  # column strip boundaries, left->right
    y0=max(0,int(top_y)-pad); y1=min(H,int(bot_y)+pad)
    for k in range(len(bounds)-1):
        regions.append([bounds[k], y0, bounds[k+1], y1])
    if bot_fw: regions.append([0,int(bot_y),W,H])
    return ncols, regions

ap=argparse.ArgumentParser(); ap.add_argument("--pages",required=True); ap.add_argument("--out",required=True)
a=ap.parse_args()
m=YOLOv10(MODEL)
pages=[l.strip() for l in open(a.pages) if l.strip()]
out={}
for img in pages:
    r=m.predict(img,imgsz=1024,conf=0.25,device="cpu",verbose=False)[0]
    H,W=r.orig_shape
    boxes=[[float(x) for x in b.xyxy[0]] for b in r.boxes if r.names[int(b.cls)] in CONTENT]
    ncols,regs=regions_for(boxes,W,H)
    out[img]={"ncols":ncols,"W":W,"H":H,"regions":regs}
json.dump(out, open(a.out,"w"))
import collections
print("pages:",len(out),"| ncols dist:",dict(collections.Counter(v['ncols'] for v in out.values())))
