"""Dev CDM harness: official Md2MdDataset matching + vendor CDM F1 on dev pages whose GT has display formulas.
usage: python harness.py VARIANT [VARIANT...]   (run from vendor/DrDocBench, .venv-cdm, TinyTeX on PATH)"""
import sys,os,json,re,glob,hashlib,shutil
sys.path.insert(0,'.')
import dataset.md2md_dataset as M
from metrics.cdm_metric import CDM
import copies
W=os.path.dirname(os.path.abspath(__file__)); DOC='.'
PRED_RUN=f'{DOC}/outputs/dev_full_marginR3'
cache_f=f'{W}/cdm_cache.json'; cache=json.load(open(cache_f)) if os.path.exists(cache_f) else {}
def build_sets():
    gt=f'{W}/gt'
    if os.path.isdir(gt): return
    os.makedirs(gt); os.makedirs(f'{W}/base')
    idx=[json.loads(l) for l in open(f'{PRED_RUN}/index.jsonl')]
    for r in idx:
        g=glob.glob(f"{DOC}/data/DrDocBench/dev/*/{r['document_id']}/mds/{r['document_id']}_{r['page']}.md")
        if not g: continue
        md=open(g[0]).read(); has=False
        if re.search(r'\$\$.+?\$\$|\\\[.+?\\\]',md,flags=re.S): has=True
        for b in re.split(r'\n\s*\n',md):
            s=b.strip()
            if s.startswith('$') and s.endswith('$') and s.replace('$','').strip(): has=True
        if not has or not os.path.exists(r['md_path']): continue
        name=f"{r['document_id']}_{r['page']}.md"
        shutil.copy(g[0],f'{gt}/{name}'); shutil.copy(r['md_path'],f'{W}/base/{name}')
def make_variant(v):
    d=f'{W}/{v}'
    if v=='base' or v=='gt': return d
    shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    for f in os.listdir(f'{W}/base'):
        open(f'{d}/{f}','w').write(copies.VARIANTS[v](open(f'{W}/base/{f}').read()))
    return d
cdm=CDM(output_root=f'{W}/cdm_out')
def score(g,p):
    if not p: return 0.0
    k=hashlib.md5((g+'\x00'+p).encode()).hexdigest()
    if k not in cache:
        try: cache[k]=cdm.evaluate(g,p,k[:12])['F1_score']
        except Exception as e: cache[k]=0.0
        json.dump(cache,open(cache_f,'w'))
    return cache[k]
build_sets()
for v in sys.argv[1:]:
    d=make_variant(v)
    cfg={'dataset':{'ground_truth':{'data_path':f'{W}/gt'},'prediction':{'data_path':d},'match_method':'quick_match'}}
    ds=M.Md2MdDataset(cfg).samples
    fo=ds['display_formula'].samples if hasattr(ds['display_formula'],'samples') else list(ds['display_formula'])
    tb=ds['text_block'].samples if hasattr(ds['text_block'],'samples') else list(ds['text_block'])
    ro=ds['reading_order'].samples if hasattr(ds['reading_order'],'samples') else list(ds['reading_order'])
    f1=[score(x['gt'].strip('$').strip(),(x.get('pred') or '').strip('$').strip()) for x in fo]
    print(f"{v:14s} GT formulas {len(fo):4d} | CDM mean F1 {100*sum(f1)/max(1,len(f1)):6.2f} | text edit {sum(x.get('edit',0) for x in tb)/max(1,len(tb)):.4f} | RO edit {sum(x['edit'] for x in ro)/max(1,len(ro)):.4f}",flush=True)
