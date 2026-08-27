"""Offline Formula CDM scoring — run with the CDM venv:

    .venv-cdm/bin/python src/score_cdm.py --run <run>

Reads the matched formula gt/pred pairs that evaluate_dev dumps
(vendor/DrDocBench/result/local_<run>_display_formula_formula.json via the
CDM_plain metric), renders each with the vendored CDM (xelatex + PyMuPDF +
Hungarian character matching), and reports mean CDM F1 * 100 = Formula CDM,
directly comparable to the leaderboard's Formula CDM.

Requires: TinyTeX on PATH (xelatex), node (tokenizer), PyMuPDF, numpy<2 — all in
the dedicated .venv-cdm. The main evaluate_dev runs in the global env; this
scorer is intentionally separate because CDM needs numpy<2 / scikit-image<=0.20.
"""
import argparse
import importlib
import json
import os
import sys
import tempfile
import types
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "DrDocBench"
TINYTEX = os.path.expanduser("~/Library/TinyTeX/bin/universal-darwin")
if TINYTEX not in os.environ["PATH"]:
    os.environ["PATH"] = os.environ["PATH"] + ":" + TINYTEX


def _load_cdm():
    sys.path.insert(0, str(VENDOR))
    if "metrics" not in sys.modules:  # stub package: skip heavy metrics/__init__
        pkg = types.ModuleType("metrics")
        pkg.__path__ = [str(VENDOR / "metrics")]
        sys.modules["metrics"] = pkg
    return importlib.import_module("metrics.cdm_metric").CDM


def _score_one(args):
    idx, gt, pred = args
    CDM = _load_cdm()
    out = tempfile.mkdtemp(prefix=f"cdm_{idx}_")
    try:
        cdm = CDM(output_root=out)
        r = cdm.evaluate(gt or "", pred or "", str(idx))
        return r.get("F1_score", 0.0)
    except Exception:
        return 0.0
    finally:
        import shutil
        shutil.rmtree(out, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--pairs", help="explicit path to *_formula.json (else derived)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    pairs_path = Path(args.pairs) if args.pairs else (
        VENDOR / "result" / f"local_{args.run}_display_formula_formula.json")
    if not pairs_path.exists():
        sys.exit(f"formula pairs not found: {pairs_path}\n"
                 f"Run: python src/evaluate_dev.py --run {args.run} [...] first "
                 f"(it dumps the pairs via CDM_plain).")

    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))
    jobs = [(i, s.get("gt", ""), s.get("pred", "")) for i, s in enumerate(pairs)]
    print(f"Scoring {len(jobs)} formula pairs with CDM ({args.workers} workers)...",
          flush=True)

    f1s = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_score_one, j): j[0] for j in jobs}
        done = 0
        for fut in as_completed(futs):
            f1s.append(fut.result())
            done += 1
            if done % 10 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)

    cdm = sum(f1s) / len(f1s) if f1s else 0.0
    print("\n================ FORMULA CDM (offline, official renderer) ======")
    print(f"  formula pairs : {len(f1s)}")
    print(f"  mean CDM F1   : {cdm:.4f}")
    print(f"  FORMULA CDM   : {cdm * 100:.2f}   (0-100, higher better)")
    print("================================================================")


if __name__ == "__main__":
    main()
