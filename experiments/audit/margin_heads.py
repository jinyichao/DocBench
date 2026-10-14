"""Recover printed running heads / footers we dropped: OCR lines in the top/bottom page margin whose text is absent
from our markdown get appended near the tail (before trailing bare page numbers), GT order = header text then number."""
import json, glob, os, re, sys
S = os.environ.get('DRDOC_WORK', 'outputs/work')
_O = None
def ocr():
    global _O
    if _O is None:
        _O = {}
        for f in glob.glob(f'{S}/ocr_*.json'):
            try: _O.update(json.load(open(f)))
            except Exception: pass
    return _O
_Y = json.load(open(f'{S}/yolo_all.json'))
def k(s): return re.sub(r'[^0-9a-z]', '', (s or '').lower())
BARE = re.compile(r'^\**\s*([0-9]{1,4}|[ivxlcdmIVXLCDM]{1,7})\s*\**$')
def recover(md, img, top=0.08, bottom=0.94, minchars=4):
    key = img.replace('', '')
    lines = ocr().get(key); det = _Y.get(key)
    if not lines or isinstance(lines, dict) or not det: return md, []
    H = det['h']; have = k(md); add = []
    for t, b in lines:
        cy = (b[1] + b[3]) / 2
        if not (cy < top * H or cy > bottom * H): continue
        kt = k(t)
        if len(re.sub(r'[0-9]', '', kt)) < minchars: continue          # need real words (numbers handled elsewhere)
        if kt in have: continue
        txt = re.sub(r'\s*\b\d{1,4}\s*$', '', re.sub(r'^\s*\d{1,4}\b\s*', '', t)).strip()   # strip page numbers fused in OCR line
        if len(k(txt)) >= minchars and k(txt) not in have: add.append(txt); have += k(txt)
    if not add: return md, []
    bl = md.split('\n\n'); j = len(bl)
    while j > 0 and BARE.match(bl[j - 1].strip()): j -= 1
    return '\n\n'.join(bl[:j] + add + bl[j:]), add
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    tot = 0; os.makedirs(f'outputs/{dst}', exist_ok=True)
    with open(f'outputs/{dst}/index.jsonl', 'w') as f:
        for l in open(f'outputs/{src}/index.jsonl'):
            r = json.loads(l)
            if not os.path.exists(r['md_path']): continue
            md, add = recover(open(r['md_path']).read(), r['image_path']); tot += len(add)
            p = r['md_path'].replace(f'/{src}/', f'/{dst}/'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(md); f.write(json.dumps(dict(r, md_path=p)) + '\n')
    print(dst, 'added', tot)

def margin_texts(img, top=0.08, bottom=0.94):
    key = img.replace('', '')
    lines = ocr().get(key); det = _Y.get(key)
    if not lines or isinstance(lines, dict) or not det: return []
    H = det['h']; out = []
    for t, b in lines:
        cy = (b[1] + b[3]) / 2
        if cy < top * H or cy > bottom * H:
            txt = re.sub(r'\s*\b\d{1,4}\s*$', '', re.sub(r'^\s*\d{1,4}\b\s*', '', t)).strip()
            if len(k(txt)) >= 4: out.append(txt)
    return out
def recover_recurring(pages, minpages=3):
    """pages: list of (md, img) for ONE doc -> list of new md; only margin texts recurring on >= minpages pages."""
    from collections import Counter
    cnt = Counter()
    for md, img in pages:
        for t in {k(x) for x in margin_texts(img)}: cnt[t] += 1
    good = {t for t, v in cnt.items() if v >= minpages}
    out = []; added = 0
    for md, img in pages:
        have = k(md); add = []
        for t in margin_texts(img):
            if k(t) in good and k(t) not in have: add.append(t); have += k(t)
        if add:
            bl = md.split('\n\n'); j = len(bl)
            while j > 0 and BARE.match(bl[j - 1].strip()): j -= 1
            md = '\n\n'.join(bl[:j] + add + bl[j:]); added += len(add)
        out.append(md)
    return out, added
