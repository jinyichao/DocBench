import os
import json, glob, re, difflib, sys
from PIL import Image, ImageDraw
S = os.environ.get('DRDOC_WORK', 'outputs/work')
O = {}
for f in glob.glob(f'{S}/ocr_*.json'):
    try: O.update(json.load(open(f)))
    except Exception: pass
C = json.load(open(f'{S}/misread_cands.json'))
k = lambda s: re.sub(r'[^0-9a-z]', '', s.lower())
tiles = []
for i, (key, snip, fix) in enumerate(C):
    subj, doc, page = key.split('/')
    img = f'data/DrDocBench/test/{subj}/{doc}/images/page_{page}.jpg'
    lines = O.get(img) or []
    best, bs = None, 0
    for t, b in (lines if isinstance(lines, list) else []):
        s = max(difflib.SequenceMatcher(None, k(snip), k(t)).ratio(), difflib.SequenceMatcher(None, k(fix), k(t)).ratio())
        if s > bs: best, bs = b, s
    im = Image.open(img).convert('RGB')
    if best is None: continue
    x0, y0, x1, y1 = best; pad = 12
    cr = im.crop((max(0, x0 - 60), max(0, y0 - pad), min(im.width, x1 + 60), min(im.height, y1 + pad)))
    sc = 900 / max(cr.width, 1); cr = cr.resize((900, max(20, int(cr.height * sc))))
    lab = Image.new('RGB', (900, 22), 'white'); ImageDraw.Draw(lab).text((4, 4), f'#{i} {subj[:10]} p{page}: ours={snip[:38]!r}', fill='black')
    t = Image.new('RGB', (900, lab.height + cr.height), 'white'); t.paste(lab, (0, 0)); t.paste(cr, (0, lab.height)); tiles.append(t)
for n in range(0, len(tiles), 9):
    group = tiles[n:n + 9]; H = sum(t.height for t in group) + 6 * len(group)
    m = Image.new('RGB', (900, H), (200, 200, 200)); y = 0
    for t in group: m.paste(t, (0, y)); y += t.height + 6
    m.save(f'{S}/misread_m{n // 9}.png')
print('tiles', len(tiles), 'montages', (len(tiles) + 8) // 9)
