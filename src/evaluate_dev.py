"""Local self-evaluation on the dev split using the official DrDocBench metrics.

Reuses vendor/DrDocBench's End2EndDataset + metric registry (Edit_dist, TEDS) to
score our per-page markdown predictions against the dev ground-truth JSON. CDM
(formula render metric) needs a separate heavy environment, so locally we use
formula Edit_dist as a proxy; the real CDM is computed server-side on EvalAI.

It builds a temporary GT json (one entry per scored page, with a UNIQUE image
basename so predictions don't collide across documents) and a flat prediction
folder, then runs the official evaluation and prints a component + Overall-proxy
summary.

Usage:
    python src/evaluate_dev.py --run dev_opus48 [--limit N] [--subjects ART ...]
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = ROOT / "vendor" / "DrDocBench"
sys.path.insert(0, str(HERE))
import config  # noqa: E402


def gather_gt_pages(subjects=None, limit=0, keys=None):
    """Return list of (subject, document_id, page_no, page_dict) for annotated dev pages.

    keys: optional set of (subject, document_id, page_no) to restrict to.
    """
    pages = []
    for jpath in sorted(config.DEV_DIR.glob("*/*/json/*_page_*.json")):
        document_id = jpath.parent.parent.name
        subject = jpath.parent.parent.parent.name
        if subjects and subject not in subjects:
            continue
        try:
            rec = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not rec:  # blank page (empty list)
            continue
        page = rec[0]
        page_no = page["page_info"]["page_no"]
        if keys is not None and (subject, document_id, page_no) not in keys:
            continue
        pages.append((subject, document_id, page_no, page))
    if limit:
        pages = pages[:limit]
    return pages


def keys_from_pages_file(path):
    """Parse image paths like .../<subject>/<doc>/images/page_<N>.jpg into keys."""
    import re
    keys = set()
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        m = re.search(r"/([^/]+)/([^/]+)/images/page_(\d+)\.(?:jpg|jpeg|png)$", line)
        if m:
            keys.add((m.group(1), m.group(2), int(m.group(3))))
    return keys


def run_eval(run_name, subjects=None, limit=0, keys=None):
    run_dir = config.OUTPUTS_DIR / run_name
    mds_dir = run_dir / "mds"
    if not mds_dir.exists():
        raise FileNotFoundError(f"no predictions at {mds_dir}")

    pages = gather_gt_pages(subjects, limit, keys=keys)
    work = Path(tempfile.mkdtemp(prefix="drdoc_eval_"))
    pred_dir = work / "pred"
    pred_dir.mkdir()

    gt_list = []
    n_pred = 0
    for subject, document_id, page_no, page in pages:
        uniq = f"{document_id}_{page_no}"  # unique basename across all docs
        page = json.loads(json.dumps(page))  # deep copy
        page["page_info"]["image_path"] = f"../images/{document_id}/{uniq}.jpg"
        # Drop `truncated` relations whose endpoints aren't both on THIS page
        # (cross-page continuations use target_anno_id -1). The server's multipage
        # pipeline resolves these; single-page local scoring cannot, and the
        # vendor merge code crashes on the dangling id.
        present = {b.get("anno_id") for b in page.get("layout_dets", [])}
        rels = page.get("extra", {}).get("relation", [])
        page["extra"]["relation"] = [
            r for r in rels
            if not (r.get("relation_type") == "truncated"
                    and (r.get("source_anno_id") not in present
                         or r.get("target_anno_id") not in present))
        ]
        gt_list.append(page)
        # Copy our prediction to pred_dir/<uniq>.md (empty if we didn't predict it).
        src = mds_dir / subject / document_id / f"{page_no}.md"
        md = src.read_text(encoding="utf-8") if src.exists() else ""
        if src.exists():
            n_pred += 1
        (pred_dir / f"{uniq}.md").write_text(md, encoding="utf-8")

    gt_path = work / "gt.json"
    gt_path.write_text(json.dumps(gt_list, ensure_ascii=False), encoding="utf-8")
    print(f"Scoring {len(gt_list)} GT pages; {n_pred} have predictions.", flush=True)

    # Run the official evaluation from within the vendor dir so its relative
    # imports and ./result output path resolve.
    prev_cwd = os.getcwd()
    sys.path.insert(0, str(VENDOR))
    os.chdir(VENDOR)
    (VENDOR / "result").mkdir(exist_ok=True)
    try:
        # The vendor code `import evaluate` only for BLEU/METEOR (unused here);
        # the real package drags in a broken torch stack, so stub it out.
        import types
        if "evaluate" not in sys.modules:
            _stub = types.ModuleType("evaluate")
            _stub.load = lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError("evaluate stubbed"))
            sys.modules["evaluate"] = _stub
        import importlib
        for m in ["registry.registry", "utils.extract", "dataset.recog_dataset",
                  "dataset.end2end_dataset", "metrics.cal_metric",
                  "metrics.show_result", "task.end2end_run_eval"]:
            importlib.import_module(m)
        from registry.registry import DATASET_REGISTRY, EVAL_TASK_REGISTRY

        cfg = {
            "dataset": {
                "dataset_name": "end2end_dataset",
                "ground_truth": {"data_path": str(gt_path)},
                "prediction": {"data_path": str(pred_dir)},
                "match_method": "quick_match",
            }
        }
        metrics_list = {
            "text_block": {"metric": ["Edit_dist"]},
            # CDM_plain dumps matched formula gt/pred pairs to
            # result/local_<run>_display_formula_formula.json for offline CDM
            # scoring via src/score_cdm.py (needs the .venv-cdm render env).
            "display_formula": {"metric": ["Edit_dist", "CDM_plain"]},
            "table": {"metric": ["TEDS", "Edit_dist"]},
            "reading_order": {"metric": ["Edit_dist"]},
        }
        dataset = DATASET_REGISTRY.get("end2end_dataset")(cfg)
        save_name = f"local_{run_name}"
        EVAL_TASK_REGISTRY.get("end2end_eval")(
            dataset, metrics_list, str(gt_path), save_name)
        result_path = VENDOR / "result" / f"{save_name}_metric_result.json"
        results = json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        os.chdir(prev_cwd)

    summarize(results)
    return results


def _edit_all(comp):
    d = comp.get("all", {}).get("Edit_dist", {})
    for k in ("ALL_page_avg", "edit_whole", "edit_sample_avg"):
        if isinstance(d.get(k), (int, float)):
            return d[k]
    return None


def summarize(results):
    text_edit = _edit_all(results.get("text_block", {}))
    formula_edit = _edit_all(results.get("display_formula", {}))
    order_edit = _edit_all(results.get("reading_order", {}))
    teds = results.get("table", {}).get("all", {}).get("TEDS", {}).get("all")
    teds_s = results.get("table", {}).get("all", {}).get(
        "TEDS_structure_only", {}).get("all")

    def comp100(edit):
        return None if edit is None else (1 - edit) * 100

    parts = {
        "Text (1-edit)*100": comp100(text_edit),
        "Formula (1-edit)*100 [CDM proxy]": comp100(formula_edit),
        "Table TEDS*100": None if teds is None else teds * 100,
        "Reading order (1-edit)*100": comp100(order_edit),
    }
    print("\n================ LOCAL DEV SCORE (proxy) ================")
    print(f"  Text edit distance      : {fmt(text_edit)}   -> {fmt(parts['Text (1-edit)*100'])}")
    print(f"  Formula edit distance   : {fmt(formula_edit)}   -> {fmt(parts['Formula (1-edit)*100 [CDM proxy]'])}")
    print(f"  Table TEDS              : {fmt(teds)}   -> {fmt(parts['Table TEDS*100'])}")
    print(f"  Table TEDS-S            : {fmt(teds_s)}")
    print(f"  Reading-order edit dist : {fmt(order_edit)}   -> {fmt(parts['Reading order (1-edit)*100'])}")
    avail = [v for v in parts.values() if v is not None]
    overall = sum(avail) / len(avail) if avail else None
    print(f"  ---------------------------------------------")
    print(f"  OVERALL (proxy, equal-weight): {fmt(overall)}")
    print("  NOTE: real Overall uses per-page averaging + true CDM (server-side).")
    print("========================================================\n")


def fmt(x):
    return "  NaN " if x is None else f"{x:7.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--subjects", nargs="*")
    ap.add_argument("--pages-file", help="restrict scoring to image paths in this file")
    args = ap.parse_args()
    keys = keys_from_pages_file(args.pages_file) if args.pages_file else None
    run_eval(args.run, subjects=args.subjects, limit=args.limit, keys=keys)


if __name__ == "__main__":
    main()
