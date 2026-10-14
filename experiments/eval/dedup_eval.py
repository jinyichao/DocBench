"""Dev per-page Overall proxy (Text, RO, CDM where GT has formulas) for formula-only conversion rules.
Run from vendor/DrDocBench with .venv-cdm and TinyTeX on PATH."""
import sys,os,json,glob,shutil,re,hashlib,collections
sys.path.insert(0,'.')
import dataset.md2md_dataset as M
from metrics.cdm_metric import CDM
import Levenshtein
W='outputs/dedup_dev'; DOC='.'
RUN=f'{DOC}/outputs/dev_full_marginR3'
if not os.path.isdir(f'{W}/gt'):
    os.makedirs(f'{W}/gt'); os.makedirs(f'{W}/base')
    for r in map(json.loads,open(f'{RUN}/index.jsonl')):
        g=glob.glob(f"{DOC}/data/DrDocBench/dev/*/{r['document_id']}/mds/{r['document_id']}_{r['page']}.md")
        if g and os.path.exists(r['md_path']):
            n=f"{r['document_id']}_{r['page']}.md"; shutil.copy(g[0],f'{W}/gt/{n}'); shutil.copy(r['md_path'],f'{W}/base/{n}')
def esc(s):
    s=re.sub(r'[*`#>]|\\','',s); s=re.sub(r'\s+',' ',s).strip()
    for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('{',r'\{'),('}',r'\}')]: s=s.replace(a,b)
    return s
def mk(maxlen):
    E=re.compile(r'(\*\*[^*\n]{1,%d}\*\*|\*[^*\n]{1,%d}\*)'%(maxlen,maxlen))
    def f(md):
        out=[]
        for b in md.split('\n\n'):
            s=b.strip()
            if s and '<' not in s and not s.startswith(('$','#')) and len(s)<=maxlen+4 and E.fullmatch(s): out.append('$\\textit{'+esc(s)+'}$')
            else: out.append(b)
        return '\n\n'.join(out)
    return f
EMPH=re.compile(r'(\*\*[^*\n]{1,150}\*\*|\*[^*\n]{1,150}\*)')
def ruleA(md):
    out=[]
    for b in md.split('\n\n'):
        s=b.strip()
        if s and '<' not in s and not s.startswith(('$','#')) and len(s)<=150 and EMPH.fullmatch(s):
            out.append('$\\textit{'+esc(s)+'}$')
        else: out.append(b)
    return '\n\n'.join(out)
def ruleB(md):
    out=[]
    for b in ruleA(md).split('\n\n'):
        s=b.strip()
        if re.fullmatch(r'\d{1,4}',s): out.append('$\\textit{'+s+'}$')
        else: out.append(b)
    return '\n\n'.join(out)

def short(maxlen,headings):
    def f(md):
        out=[]
        for b in md.split('\n\n'):
            s=b.strip()
            ok=s and '<' not in s and not s.startswith('$') and len(s)<maxlen and '\n' not in s
            if ok and (headings or not s.startswith('#')): out.append('$\\textit{'+esc(s)+'}$')
            else: out.append(b)
        return '\n\n'.join(out)
    return f


def ital(maxlen):
    E=re.compile(r'\*(?!\*)[^*\n]{1,%d}(?<!\*)\*'%maxlen)
    def f(md):
        out=[]
        for b in md.split('\n\n'):
            s=b.strip()
            if s and '<' not in s and not s.startswith(('$','#')) and E.fullmatch(s): out.append('$\\textit{'+esc(s)+'}$')
            else: out.append(b)
        return '\n\n'.join(out)
    return f


ITS=re.compile(r'(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)')
def tailit(md):
    bl=md.split('\n\n'); n=len(bl)
    for i in range(max(0,n-3),n):
        s=bl[i].strip()
        if not s or len(s)>80 or '<' in s or s.startswith('$') or not ITS.search(s): continue
        parts=[]; rest=ITS.sub(lambda m:(parts.append('$\\textit{'+esc(m.group(1))+'}$') or ' '),s)
        rest=re.sub(r'\s+',' ',rest).strip()
        bl[i]='\n\n'.join(([rest] if re.search(r'\w',rest) else [])+parts)
    return '\n\n'.join(bl)

RULES={'TAILIT':tailit,'I150':ital(150),'I50':ital(50),'I30':ital(30),'I20':ital(20),'S30':short(30,False),'S30h':short(30,True),'ruleA':ruleA,'ruleB':ruleB,'A100':mk(100),'A50':mk(50),'A30':mk(30)}
cache_f=f'{W}/cdm_cache.json'; cache=json.load(open(cache_f)) if os.path.exists(cache_f) else {}
cdm=CDM(output_root=f'{W}/cdm_out')
def cscore(g,p):
    if not p: return 0.0
    k=hashlib.md5((g+'\x00'+p).encode()).hexdigest()
    if k not in cache:
        try: cache[k]=cdm.evaluate(g,p,k[:12])['F1_score']
        except Exception: cache[k]=0.0
        json.dump(cache,open(cache_f,'w'))
    return cache[k]
def evaluate(v):
    d=f'{W}/{v}'
    if v not in ('base',):
        shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
        for f in os.listdir(f'{W}/base'): open(f'{d}/{f}','w').write(RULES[v](open(f'{W}/base/{f}').read()))
    ds=M.Md2MdDataset({'dataset':{'ground_truth':{'data_path':f'{W}/gt'},'prediction':{'data_path':d},'match_method':'quick_match'}}).samples
    page=collections.defaultdict(dict)
    T=collections.defaultdict(lambda:[0,0])
    for s in ds['text_block'].samples:
        g=s.get('norm_gt') or ''; p=s.get('norm_pred') or ''
        if g or p: T[s['img_id']][0]+=Levenshtein.distance(g,p); T[s['img_id']][1]+=max(len(g),len(p))
    for k,(e,u) in T.items(): page[k]['text']=100*(1-e/u)
    for s in ds['reading_order'].samples: page[s['img_id']]['ro']=100*(1-s['edit'])
    C=collections.defaultdict(list)
    for s in ds['display_formula'].samples: C[s['img_id']].append(cscore(s['gt'].strip('$').strip(),(s.get('pred') or '').strip('$').strip()))
    for k,v_ in C.items(): page[k]['cdm']=100*sum(v_)/len(v_)
    per=[sum(c.values())/len(c) for c in page.values() if c]
    t=[c['text'] for c in page.values() if 'text' in c]; ro=[c['ro'] for c in page.values() if 'ro' in c]; cd=[c['cdm'] for c in page.values() if 'cdm' in c]
    print(f"{v:6s} pages {len(per)} | Overall proxy {sum(per)/len(per):.3f} | Text {sum(t)/len(t):.2f} | RO {sum(ro)/len(ro):.2f} | CDM {sum(cd)/max(1,len(cd)):.2f} on {len(cd)} pages",flush=True)
for v in sys.argv[1:]: evaluate(v)
