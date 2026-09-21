"""Assemble a Dr.DocBench EvalAI submission as a Markdown File Tree (Option A).

Produces submissions/<run>_filetree.zip with one .md file per page at the required
path pattern (no wrapper directory):

    <subject>/<document_id>/mds/<document_id>_<page>.md

Usage:
    python src/build_submission_filetree.py --run test_ensemble_q100_audited
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def load_index(run_dir: Path):
    idx = run_dir / "index.jsonl"
    if not idx.exists():
        raise FileNotFoundError(f"missing {idx}; run run_infer.py first")
    with idx.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", help="output zip path (default submissions/<run>_filetree.zip)")
    ap.add_argument("--allow-empty", action="store_true")
    args = ap.parse_args()

    run_dir = config.OUTPUTS_DIR / args.run
    records = load_index(run_dir)

    seen = set()
    empty = 0
    dup = 0
    missing_md = 0
    entries = []  # (zip_path, content)
    for r in records:
        key = (r["subject"], r["document_id"], int(r["page"]))
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        md_path = Path(r["md_path"])
        if not md_path.exists():
            missing_md += 1
            markdown = ""
        else:
            markdown = md_path.read_text(encoding="utf-8")
        if not markdown.strip():
            empty += 1
        zip_path = f"{r['subject']}/{r['document_id']}/mds/{r['document_id']}_{r['page']}.md"
        entries.append((zip_path, markdown))

    problems = []
    if dup:
        problems.append(f"{dup} duplicate page identifiers (dropped)")
    if missing_md:
        problems.append(f"{missing_md} pages missing their .md output")
    if empty and not args.allow_empty:
        problems.append(f"{empty} pages have empty markdown")

    print(f"Run: {args.run}")
    print(f"Predictions: {len(entries)} unique pages")
    print(f"Empty markdown: {empty}")
    if problems:
        print("\nVALIDATION ISSUES:")
        for p in problems:
            print("  - " + p)
    else:
        print("Validation: OK")

    out_zip = Path(args.out) if args.out else config.SUBMISSIONS_DIR / f"{args.run}_filetree.zip"
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for zip_path, markdown in entries:
            z.writestr(zip_path, markdown)
    print(f"\nWrote {out_zip} ({out_zip.stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
