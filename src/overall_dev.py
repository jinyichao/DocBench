"""Exact per-page Overall on dev, per the challenge spec:

  - Each component -> 0..100 on each page:
      Text   = (1 - edit) * 100
      Order  = (1 - edit) * 100
      Table  = mean(TEDS on page) * 100
      Formula= mean(CDM F1 on page) * 100
  - Per page: average ONLY the components present on that page.
  - Overall = mean of per-page scores over all scorable pages (>=1 component).

Reads the per-page result files evaluate_dev already wrote to
vendor/DrDocBench/result/local_<run>_*, and computes CDM per formula pair with
the official renderer. Run with the CDM venv:

  .venv-cdm/bin/python src/overall_dev.py --run dev_qwen_v2
"""
import argparse
import importlib
import json
import os
import re
import sys
import tempfile
import types
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "DrDocBench"
RESULT = VENDOR / "result"
TINYTEX = os.path.expanduser("~/Library/TinyTeX/bin/universal-darwin")
if TINYTEX not in os.environ["PATH"]:
    os.environ["PATH"] += ":" + TINYTEX


def _page_key(name):
    """Normalise any id to '<doc>_<page>' (drop .jpg, table _[i], formula _<i>)."""
    m = re.match(r"(.+?_\d+)\.jpg", name)
    return m.group(1) if m else name


def _load_cdm():
    sys.path.insert(0, str(VENDOR))
    if "metrics" not in sys.modules:
        pkg = types.ModuleType("metrics")
        pkg.__path__ = [str(VENDOR / "metrics")]
        sys.modules["metrics"] = pkg
    return importlib.import_module("metrics.cdm_metric").CDM


def _cdm_one(args):
    idx, gt, pred = args
    CDM = _load_cdm()
    out = tempfile.mkdtemp(prefix=f"ov_{idx}_")
    try:
        return CDM(output_root=out).evaluate(gt or "", pred or "", str(idx)).get("F1_score", 0.0)
    except Exception:
        return 0.0
    finally:
        import shutil
        shutil.rmtree(out, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    base = f"local_{args.run}"

    def load(name):
        p = RESULT / f"{base}_{name}"
        return json.loads(p.read_text()) if p.exists() else {}

    text = {_page_key(k): (1 - v) * 100 for k, v in load("text_block_per_page_edit.json").items()}
    order = {_page_key(k): (1 - v) * 100 for k, v in load("reading_order_per_page_edit.json").items()}

    # tables: per-table TEDS -> mean per page
    table_pp = defaultdict(list)
    for k, v in load("table_per_table_TEDS.json").items():
        table_pp[_page_key(k)].append(v["TEDS"])
    table = {p: sum(x) / len(x) * 100 for p, x in table_pp.items()}

    # formulas: CDM per pair (rendered) -> mean per page
    pairs = load("display_formula_formula.json")
    jobs = [(i, s.get("gt", ""), s.get("pred", "")) for i, s in enumerate(pairs)]
    print(f"Rendering {len(jobs)} formula pairs for CDM...", flush=True)
    f1_by_page = defaultdict(list)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_cdm_one, j): i for i, j in enumerate(jobs)}
        for fut in as_completed(futs):
            i = futs[fut]
            pg = _page_key(pairs[i].get("image_name") or pairs[i].get("img_name", ""))
            f1_by_page[pg].append(fut.result())
    formula = {p: sum(x) / len(x) * 100 for p, x in f1_by_page.items()}

    # assemble per-page Overall
    pages = set(text) | set(order) | set(table) | set(formula)
    per_page = {}
    n_comp = defaultdict(int)
    for pg in pages:
        comps = []
        for d, nm in ((text, "text"), (order, "order"), (table, "table"), (formula, "formula")):
            if pg in d:
                comps.append(d[pg]); n_comp[nm] += 1
        if comps:
            per_page[pg] = sum(comps) / len(comps)

    overall = sum(per_page.values()) / len(per_page) if per_page else 0.0

    def avg(d):
        return sum(d.values()) / len(d) if d else float("nan")

    print("\n============ EXACT PER-PAGE OVERALL (dev, run=%s) ============" % args.run)
    print(f"  scorable pages           : {len(per_page)}")
    print(f"  pages w/ text / order    : {n_comp['text']} / {n_comp['order']}")
    print(f"  pages w/ table / formula : {n_comp['table']} / {n_comp['formula']}")
    print(f"  component means (0-100)   : text {avg(text):.2f} | order {avg(order):.2f} "
          f"| table {avg(table):.2f} | formula(CDM) {avg(formula):.2f}")
    print(f"  ---------------------------------------------------------")
    print(f"  OVERALL (per-page averaged): {overall:.2f}")
    print("  (dev is prose-heavy -> higher than the paper's full-benchmark Overall)")
    print("=============================================================")


if __name__ == "__main__":
    main()
