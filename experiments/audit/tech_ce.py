"""TECH 7da538b6: express chemical formulas with \\ce{...} (Dr.DocBench chemistry convention). Strict, whole-token."""
import json, re, collections, sys
EL = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U'.split())
def valid(s):
    core = re.sub(r'[()·#=\d]', '', s)
    els = re.findall(r'[A-Z][a-z]?', core)
    return bool(els) and ''.join(els) == core and all(e in EL for e in els)
def latex_plain(t):   # C\(_{6}\)H\(_{11}\)NO or C_{5}H_{9}NO -> C6H11NO
    t = re.sub(r'\\\(_\{(\d+)\}\\\)', r'\1', t)
    return re.sub(r'_\{?(\d+)\}?', r'\1', t).replace('\\equiv', '#').replace(' ', '')
log = collections.Counter(); changes = []
def convert(md, page):
    parts = re.split(r'(```.*?```)', md, flags=re.S)        # never touch smiles/code
    for i, p in enumerate(parts):
        if i % 2: continue
        # (a) inline math that is purely a chemical formula: $NaNO_{2}$, $H_{2}O$, $C_{5}H_{9}NO$
        def m_math(m):
            body = m.group(1) if m.group(1) is not None else m.group(2)
            pl = latex_plain(body)
            if re.fullmatch(r'[A-Z][A-Za-z0-9()#·]*', pl) and valid(pl) and re.search(r'\d', pl) and len(re.findall(r'[A-Z]', pl)) >= 2:
                changes.append((page, m.group(0), f'\\ce{{{pl}}}')); log['math'] += 1; return f'\\ce{{{pl}}}'
            return m.group(0)
        p = re.sub(r'(?<!\$)\$([^$\n]+?)\$(?!\$)|\\\(([^)]*?_\{\d+\}[^)]*?)\\\)', m_math, p)
        # (b) fragment form CH\(_{3}\)CH\(_{2}\)CH\(_{2}\)C#N  (whole token)
        def m_frag(m):
            pl = latex_plain(m.group(0))
            if valid(pl) and re.search(r'\d', pl):
                changes.append((page, m.group(0), f'\\ce{{{pl}}}')); log['fragments'] += 1; return f'\\ce{{{pl}}}'
            return m.group(0)
        p = re.sub(r'(?<![\w\\{])(?:[A-Z][a-z]?(?:\\\(_\{\d+\}\\\)|\d+)?){2,}(?:#[A-Z])?(?![\w\\(])', lambda m: m_frag(m) if '\\(' in m.group(0) else m.group(0), p)
        # (c) plain whole tokens: MgCl2, Na2S2O3, Co(C2H3O2)2, NaCl, AgBr ; table-cell-only formulas: KOH, KCN
        def m_tok(m):
            tok = m.group(0)
            if not valid(tok): return tok
            has_digit = bool(re.search(r'\d', tok)); has_lower = bool(re.search(r'[a-z]', tok))
            ncap = len(re.findall(r'[A-Z]', tok))
            if (has_digit and ncap >= 1 and re.search(r'[A-Z][a-z]?\d', tok)) or (has_lower and ncap >= 2):
                changes.append((page, tok, f'\\ce{{{tok}}}')); log['plain'] += 1; return f'\\ce{{{tok}}}'
            return tok
        p = re.sub(r'(?<![\w\\{/.-])[A-Z][A-Za-z0-9()·]*[A-Za-z0-9)](?![\w}(\\])', m_tok, p)
        def m_cell(m):
            tok = m.group(1)
            if valid(tok) and len(re.findall(r'[A-Z]', tok)) >= 2 and len(tok) <= 6 and tok.isalpha():
                changes.append((page, tok, f'\\ce{{{tok}}}')); log['cell'] += 1; return f'<td>\\ce{{{tok}}}</td>'
            return m.group(0)
        p = re.sub(r'<td>([A-Z][A-Za-z]{1,5})</td>', m_cell, p)
        parts[i] = p
    return ''.join(parts)
if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    R = [json.loads(l) for l in open(src)]
    for r in R:
        if r['document_id'].startswith('7da538b6'): r['markdown'] = convert(r['markdown'], r['page'])
    print(dict(log))
    for p, a, b in changes: print(f'  p{p}: {a[:42]!r} -> {b}')
    with open(dst, 'w') as f:
        for r in R: f.write(json.dumps(r, ensure_ascii=False) + '\n')
