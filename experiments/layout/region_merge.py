"""Merge consecutive text blocks whose lines all map to the SAME DocLayout-YOLO region (and no line maps elsewhere)."""
import json, os, sys
S = os.environ.get('DRDOC_WORK', 'outputs/work')
sys.path.insert(0, S)
import region_split as rs
from geofeat import PageGeo
def block_region(b, geo, R):
    regs = {rs.region_of(geo.find(l), R) for l in b.split('\n') if l.strip()}
    regs.discard(None)
    return regs.pop() if len(regs) == 1 else None
def merge_page(md, img, conf=0.2):
    Y, O = rs.load(); k = rs.key(img); det = Y.get(k); ocr = O.get(k)
    if not det or not ocr or isinstance(ocr, dict): return md, 0
    R = rs.regions(det, conf); geo = PageGeo(ocr)
    bl = md.split('\n\n'); out = []; n = 0; prev_reg = None
    for b in bl:
        s = b.strip()
        texty = s and not s.startswith(('<', '#', '$$', '```', '|', '*', '-')) and not s[:1].isdigit()
        reg = block_region(b, geo, R) if texty else None
        if reg is not None and reg == prev_reg and out:
            out[-1] = out[-1] + '\n' + b; n += 1
        else:
            out.append(b)
        prev_reg = reg
    return '\n\n'.join(out), n
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; conf = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
    tot = 0; os.makedirs(f'outputs/{dst}', exist_ok=True)
    with open(f'outputs/{dst}/index.jsonl', 'w') as f:
        for l in open(f'outputs/{src}/index.jsonl'):
            r = json.loads(l)
            if not os.path.exists(r['md_path']): continue
            md, n = merge_page(open(r['md_path']).read(), r['image_path'], conf); tot += n
            p = r['md_path'].replace(f'/{src}/', f'/{dst}/'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(md); f.write(json.dumps(dict(r, md_path=p)) + '\n')
    print(dst, 'merges', tot)
