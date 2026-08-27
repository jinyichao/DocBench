"""Assemble the final ensemble from per-backend runs.

Starts from the Qwen run (primary), routes table pages to Gemini when Gemini's
output is a valid table (guarded), and fills any remaining empty pages from an
optional recovery run (used for pages DashScope content-filter blocks). Writes a
new run tree + index.jsonl that build_submission.py can package.

Usage:
    python src/build_ensemble.py \
        --qwen  outputs/test_qwen \
        --gemini outputs/test_gemini_tables \
        --table-pages outputs/test_table_pages.txt \
        --recover outputs/test_recover \
        --out    outputs/test_ensemble
"""
import argparse
import json
import shutil
from pathlib import Path


def _pages(run):
    """Map (subject, doc, page) -> md path for every .md under <run>/mds."""
    return {(f.parts[-3], f.parts[-2], f.stem): f
            for f in (Path(run) / "mds").glob("*/*/*.md")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qwen", required=True, help="Qwen run dir (primary base)")
    ap.add_argument("--gemini", help="Gemini run dir (table-page ensemble)")
    ap.add_argument("--table-pages", help="file listing image paths to route to Gemini")
    ap.add_argument("--recover", help="run dir to fill still-empty pages from")
    ap.add_argument("--out", required=True, help="output ensemble run dir")
    ap.add_argument("--guard-ratio", type=float, default=0.6,
                    help="Gemini page must be >= this fraction of the Qwen page length")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(Path(args.qwen) / "mds", out / "mds")   # start from Qwen

    qwen = _pages(args.qwen)
    gemini = _pages(args.gemini) if args.gemini else {}
    recover = _pages(args.recover) if args.recover else {}

    # 1) route table pages to Gemini when its output is a real, non-truncated table
    replaced = 0
    table_keys = set()
    if args.table_pages and gemini:
        for line in open(args.table_pages):
            line = line.strip()
            if not line:
                continue
            p = line.split("/")
            key = (p[-4], p[-3], p[-1].split("_")[-1].split(".")[0])
            table_keys.add(key)
        for key in table_keys:
            g, q = gemini.get(key), qwen.get(key)
            if not g or not q:
                continue
            gt, qt = g.read_text(), q.read_text()
            if (gt.strip() and "<table" in gt.lower()
                    and len(gt.strip()) >= args.guard_ratio * max(1, len(qt.strip()))):
                (out / "mds" / key[0] / key[1] / f"{key[2]}.md").write_text(gt)
                replaced += 1

    # 2) fill still-empty pages from the recovery run
    recovered = 0
    for f in out.glob("mds/*/*/*.md"):
        if f.read_text().strip():
            continue
        key = (f.parts[-3], f.parts[-2], f.stem)
        r = recover.get(key)
        if r and r.read_text().strip():
            f.write_text(r.read_text())
            recovered += 1

    # 3) write the page index for build_submission
    recs = []
    for f in sorted(out.glob("mds/*/*/*.md")):
        subj, doc, pg = f.parts[-3], f.parts[-2], int(f.stem)
        recs.append({"subject": subj, "document_id": doc, "page": pg,
                     "image_path": f"data/DrDocBench/test/{subj}/{doc}/images/page_{pg}.jpg",
                     "md_path": str(f)})
    with (out / "index.jsonl").open("w") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    empty = sum(1 for f in out.glob("mds/*/*/*.md") if not f.read_text().strip())
    print(f"ensemble -> {out}: {len(recs)} pages | Gemini table splices={replaced} "
          f"| recovered={recovered} | empty(blank)={empty}")


if __name__ == "__main__":
    main()
