"""PSYCHOLOGY 719d86a2 counselling-exercise pages: convert numbered dialogue text into the p313 table structure
[item | speaker | text]; explanations append to the previous row's text with <br><br>."""
import os
import json, re, sys, zipfile, collections
S = os.environ.get('DRDOC_WORK', 'outputs/work')
SPK = r'(Client|Your Answer|Therapist|Counselor|Counsellor)'
ITEM = re.compile(rf'^\**\s*(\d+\.\d+)\s*\**\s*\**\s*{SPK}\s*:\s*\**\s*(.*)$', re.S)
SPKL = re.compile(rf'^\**\s*{SPK}\s*:\s*\**\s*(.*)$', re.S)
def clean(t): return re.sub(r'\s+', ' ', t.replace('**', '').replace('*', '')).strip()
def convert(md):
    bl = md.split('\n\n'); out = []; rows = []; started = False
    def flush():
        nonlocal rows
        if rows:
            out.append('<table>\n' + ''.join(f'<tr>\n<td>{a}</td>\n<td>{b}</td>\n<td>{c}</td>\n</tr>\n' for a, b, c in rows) + '</table>')
            rows = []
    for i, b in enumerate(bl):
        s = b.strip()
        tail = i >= len(bl) - 3 and (len(s) <= 80 and ('Exercises for Effective' in s or re.fullmatch(r'\d{1,4}', s) or 'activity unit' in s.lower()))
        if not s or s.startswith(('#', '<')) or tail or re.match(r'^(Original|Improved) response', s):
            flush(); out.append(b); continue
        # normalise "2.13\n*Client:* ..." -> one unit
        s2 = re.sub(r'^(\**\d+\.\d+\**)\s*\n', r'\1 ', s)
        lines = [l for l in s2.split('\n') if l.strip()]
        consumed = False
        for l in lines:
            m = ITEM.match(l.strip()); m2 = SPKL.match(l.strip())
            if m: rows.append((m.group(1), m.group(2) + ':', clean(m.group(3)))); consumed = started = True
            elif m2: rows.append(('', m2.group(1) + ':', clean(m2.group(2)))); consumed = started = True
            elif l.strip().startswith('Choose the most appropriate response'): rows.append(('', '', clean(l))); consumed = started = True
            elif started and rows: rows[-1] = (rows[-1][0], rows[-1][1], rows[-1][2] + '<br><br>' + clean(l)); consumed = True
            else: break
        if not consumed: flush(); out.append(b)
    flush()
    return '\n\n'.join(out)
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    R = [json.loads(l) for l in open(src)]; A = {(r['document_id'], r['page']): r['markdown'] for r in R}
    for r in R:
        if r['document_id'].startswith('719d86a2') and r['page'] in (314, 315, 316, 317, 318, 319, 325):
            r['markdown'] = convert(r['markdown'])
    w = lambda s: collections.Counter(re.findall(r'[A-Za-z0-9]+', re.sub(r'<[^>]+>', ' ', s)))
    lost = {p: dict(w(A[p]) - w(m)) for p, m in ((k, next(x['markdown'] for x in R if (x['document_id'], x['page']) == k)) for k in A if k[0].startswith('719d86a2')) if w(A[p]) - w(m)}
    print('lost words:', lost)
    for r in R:
        if r['document_id'].startswith('719d86a2') and r['page'] in (314, 325):
            print('=== p', r['page']); print(r['markdown'][:900])
    with open(dst, 'w') as f:
        for r in R: f.write(json.dumps(r, ensure_ascii=False) + '\n')
