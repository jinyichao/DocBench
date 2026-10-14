import sys,json,re,collections,io,contextlib
sys.path.insert(0,'vendor/DrDocBench')
from utils.extract import md_tex_filter
F=sys.argv[1]
R=[json.loads(l) for l in open(F)]
iss=collections.defaultdict(list)
def add(k,r,s): iss[k].append(f"{r['subject'][:10]} {r['document_id'][:8]} p{r['page']}: {s}")
for r in R:
    md=r['markdown']; nocode=re.sub(r'```.*?```','',md,flags=re.S)
    # 1 odd $ count
    n=nocode.replace('\\$','').count('$')
    if n%2: add('1 odd $ count (lone $ may pair with a formula)',r,f'{n} $ signs')
    # 2 bare latex outside math
    t=re.sub(r'<table.*?</table>','',nocode,flags=re.S)
    t2=re.sub(r'\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)|\$[^$]*\$','',t,flags=re.S)
    for m in re.finditer(r'\\[a-zA-Z]+',t2): add('2 bare LaTeX command outside math',r,repr(t2[max(0,m.start()-20):m.end()+15]))
    for m in re.finditer(r'\\_',t2): add('2b escaped underscore outside math (scored _)',r,repr(t2[max(0,m.start()-20):m.end()+10]))
    # 3 unpaired \( \[ 
    a,b=t.count(chr(92)+'('),t.count(chr(92)+')')
    if a!=b: add('3 unpaired \\( \\)',r,str(a)+' vs '+str(b))
    a,b=t.count(chr(92)+'['),t.count(chr(92)+']')
    if a!=b: add('3 unpaired \\[ \\]',r,str(a)+' vs '+str(b))
    # 4 html tags / entities outside tables
    for m in re.finditer(r'</?(sup|sub|u|b|i|br|span|em|strong)\b[^>]*>',t): add('4 HTML tag outside table',r,m.group(0))
    for m in re.finditer(r'&(amp|lt|gt|nbsp|quot|#\d+);',t): add('4 HTML entity',r,m.group(0))
    # 5 underscore emphasis leftovers
    for m in re.finditer(r'(?<![\w_])_[A-Za-z][^_\n]{0,60}[A-Za-z.!?]_(?![\w_])',t2): add('5 underscore emphasis (scored _)',r,repr(m.group(0)[:50]))
    # 6 markdown artifacts
    for l in t.split('\n'):
        s=l.strip()
        if re.fullmatch(r'[-*_]{3,}',s): add('6 horizontal rule line',r,s)
        if s.startswith('|') and s.endswith('|') and s.count('|')>=3: add('6 markdown pipe table',r,s[:40])
    # 7 scorer view: formula candidates + text blocks
    with contextlib.redirect_stdout(io.StringIO()):
        d=md_tex_filter(md)
    for x in d.get('equation_isolated',[]):
        c=x['content']
        if len(c)>250 or c.count('\n')>3: add('7 suspicious long formula candidate',r,repr(c[:70]))
        inner=re.sub(r'^\\\[|\\\]$|^\$+|\$+$','',c.strip())
        if re.search(r'\b(the|and|of|with|for)\b',inner) and not re.search(r'\\text(it|bf)|\\mathrm|\\text\{',inner): add('7 prose captured as formula (no textit)',r,repr(c[:70]))
    # 8 blocks that are pure formula although they hold words (text removed from scoring)
    for b in t.split('\n\n'):
        s=b.strip()
        if s.startswith('$') and s.endswith('$') and not s.startswith('$$') and re.search(r'\\text(it|bf)\{[^}]*[A-Za-z]{3}',s): add('8 pure-formula block holding words (text not scored)',r,repr(s[:60]))
for k in sorted(iss):
    v=iss[k]; print(f'\n### {k}: {len(v)}')
    for x in v[:15]: print('   ',x)
    if len(v)>15: print('    ...')
