"""Split where line regions change under BOTH detectors (and) or EITHER (or)."""
import json, os, sys, importlib
S = os.environ.get('DRDOC_WORK', 'outputs/work')
sys.path.insert(0, S)
from geofeat import PageGeo
def mk(source):
    os.environ['REGION_SOURCE'] = source
    import region_split; m = importlib.reload(region_split); m.load(); return m
Y = mk('yolo'); YD, O = Y._Y, Y._O
H = mk('heron'); HD = H._Y
def boundaries(L, det, conf, geo, mod):
    R = mod.regions(det, conf); regs = [mod.region_of(geo.find(l), R) for l in L]
    return {i for i in range(1, len(L)) if regs[i-1] is not None and regs[i] is not None and regs[i-1] != regs[i]}
def split(md, img, mode, cy, ch):
    k = img.replace('', ''); ocr = O.get(k)
    if not ocr or isinstance(ocr, dict) or k not in YD or k not in HD: return md, 0
    geo = PageGeo(ocr); out = []; n = 0
    for b in md.split('\n\n'):
        s = b.strip()
        if not s or s.startswith(('<', '#', '$$', '```', '|')) or '\n' not in s: out.append(b); continue
        L = b.split('\n'); by = boundaries(L, YD[k], cy, geo, Y); bh = boundaries(L, HD[k], ch, geo, H)
        cut = (by & bh) if mode == 'and' else (by | bh)
        cur = [L[0]]
        for i in range(1, len(L)):
            if i in cut: out.append('\n'.join(cur)); cur = []; n += 1
            cur.append(L[i])
        out.append('\n'.join(cur))
    return '\n\n'.join(out), n
if __name__ == '__main__':
    src, dst, mode, cy, ch = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    tot = 0; os.makedirs(f'outputs/{dst}', exist_ok=True)
    with open(f'outputs/{dst}/index.jsonl', 'w') as f:
        for l in open(f'outputs/{src}/index.jsonl'):
            r = json.loads(l)
            if not os.path.exists(r['md_path']): continue
            md, n = split(open(r['md_path']).read(), r['image_path'], mode, cy, ch); tot += n
            p = r['md_path'].replace(f'/{src}/', f'/{dst}/'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(md); f.write(json.dumps(dict(r, md_path=p)) + '\n')
    print(dst, 'splits', tot)
