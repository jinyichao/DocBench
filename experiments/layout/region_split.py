"""Split our text blocks where consecutive lines fall in different DocLayout-YOLO regions (line->region via PaddleOCR boxes)."""
import json, glob, os, re, sys
S = os.environ.get('DRDOC_WORK', 'outputs/work')
sys.path.insert(0, S)
from geofeat import PageGeo
SOURCE = os.environ.get('REGION_SOURCE', 'yolo')          # yolo | heron | heron_nolist
TEXTY = {'plain text', 'title', 'figure_caption', 'table_caption', 'table_footnote', 'formula_caption', 'abandon',
         'text', 'section_header', 'caption', 'footnote', 'page_header', 'page_footer', 'document_index', 'list_item'}
if SOURCE == 'heron_nolist': TEXTY = TEXTY - {'list_item'}
_Y = _O = None
def load():
    global _Y, _O
    if _Y is None:
        _Y = json.load(open(f"{S}/{'yolo_all' if SOURCE == 'yolo' else 'heron_all'}.json")); _O = {}
        for f in glob.glob(f'{S}/ocr_*.json'):
            try: _O.update(json.load(open(f)))
            except Exception: pass
    return _Y, _O
def key(img):
    return img.replace('', '')
def regions(det, conf):
    R = [b for n, c, b in det.get('dets', []) if n in TEXTY and c >= conf]
    return R
def region_of(box, R):
    if box is None: return None
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    best = None
    for i, b in enumerate(R):
        if b[0] - 3 <= cx <= b[2] + 3 and b[1] - 3 <= cy <= b[3] + 3:
            a = (b[2] - b[0]) * (b[3] - b[1])
            if best is None or a < best[1]: best = (i, a)
    return None if best is None else best[0]
def split_page(md, img, conf=0.5, minlen=1):
    Y, O = load(); k = key(img)
    det = Y.get(k); ocr = O.get(k)
    if not det or not ocr or isinstance(ocr, dict): return md, 0
    # OCR boxes are in original-image pixels; YOLO boxes too (both from the same image file)
    R = regions(det, conf); geo = PageGeo(ocr)
    out = []; n = 0
    for b in md.split('\n\n'):
        s = b.strip()
        if not s or s.startswith(('<', '#', '$$', '```', '|')) or '\n' not in s: out.append(b); continue
        L = b.split('\n'); regs = [region_of(geo.find(l), R) for l in L]
        cur = [L[0]]
        for i in range(1, len(L)):
            a, c = regs[i - 1], regs[i]
            if a is not None and c is not None and a != c and len(cur) >= minlen:
                out.append('\n'.join(cur)); cur = []; n += 1
            cur.append(L[i])
        out.append('\n'.join(cur))
    return '\n\n'.join(out), n
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; conf = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    tot = 0; os.makedirs(f'outputs/{dst}', exist_ok=True)
    with open(f'outputs/{dst}/index.jsonl', 'w') as f:
        for l in open(f'outputs/{src}/index.jsonl'):
            r = json.loads(l)
            if not os.path.exists(r['md_path']): continue
            md, n = split_page(open(r['md_path']).read(), r['image_path'], conf); tot += n
            p = r['md_path'].replace(f'/{src}/', f'/{dst}/'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(md); f.write(json.dumps(dict(r, md_path=p)) + '\n')
    print(dst, 'splits', tot)
