"""List predicted text matched against EMPTY GT (pure extra) and GT matched against empty pred (pure missing) on a dev run."""
import sys, json, os, types, tempfile, shutil, io, contextlib, collections
m = types.ModuleType('evaluate'); m.load = lambda *a, **k: None; sys.modules['evaluate'] = m
sys.path.insert(0, 'vendor/DrDocBench')
import dataset.md2md_dataset as MD
run = sys.argv[1]
tmp = tempfile.mkdtemp(); g = os.path.join(tmp, 'gt'); p = os.path.join(tmp, 'pred'); os.makedirs(g); os.makedirs(p)
for l in open(f'outputs/{run}/index.jsonl'):
    r = json.loads(l)
    gtf = f"data/DrDocBench/dev/{r['subject']}/{r['document_id']}/mds/{r['document_id']}_{r['page']}.md"
    if os.path.exists(gtf) and os.path.exists(r['md_path']):
        n = f"{r['document_id']}_{r['page']}.md"; shutil.copy(gtf, os.path.join(g, n)); shutil.copy(r['md_path'], os.path.join(p, n))
with contextlib.redirect_stdout(io.StringIO()):
    ds = MD.Md2MdDataset({'dataset': {'ground_truth': {'data_path': g}, 'prediction': {'data_path': p}, 'match_method': 'quick_match'}})
extra = []; missing = []; tot_err = 0
import Levenshtein
for s in ds.samples['text_block'].samples:
    gt = s.get('norm_gt') or ''; pr = s.get('norm_pred') or ''
    tot_err += Levenshtein.distance(pr, gt)
    if not gt and pr: extra.append((len(pr), s['img_id'], (s.get('pred') or '')[:110].replace('\n', ' | ')))
    if gt and not pr: missing.append((len(gt), s['img_id'], (s.get('gt') or '')[:110].replace('\n', ' | ')))
print(f'total edit chars {tot_err}; pure-extra pred chars {sum(x[0] for x in extra)} ({len(extra)} samples); pure-missing GT chars {sum(x[0] for x in missing)} ({len(missing)} samples)')
print('--- largest pure-extra predicted text ---')
for x in sorted(extra, reverse=True)[:25]: print(x[0], x[1][:44], '|', x[2])
shutil.rmtree(tmp)
