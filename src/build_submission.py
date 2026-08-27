"""Assemble a Dr.DocBench EvalAI submission from a completed run.

Produces submissions/<run>.zip containing predictions.jsonl with one record per
page: {subject, document_id, page, markdown}.

Optionally validates the set of (subject, document_id, page) identifiers against a
required-identifiers manifest shipped in the EvalAI evaluation package, catching
missing / extra / duplicate predictions before upload.

Usage:
    python src/build_submission.py --run test_opus48
    python src/build_submission.py --run test_opus48 --required path/to/required.jsonl
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


def load_required(path: Path):
    """Required identifiers manifest: JSONL or JSON list of {subject,document_id,page}."""
    text = path.read_text(encoding="utf-8").strip()
    ids = set()
    if text.startswith("["):
        for r in json.loads(text):
            ids.add((r["subject"], r["document_id"], int(r["page"])))
    else:
        for line in text.splitlines():
            if line.strip():
                r = json.loads(line)
                ids.add((r["subject"], r["document_id"], int(r["page"])))
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--required", help="required-identifiers manifest from EvalAI package")
    ap.add_argument("--out", help="output zip path (default submissions/<run>.zip)")
    ap.add_argument("--allow-empty", action="store_true",
                    help="allow empty markdown for a page (else warn)")
    args = ap.parse_args()

    run_dir = config.OUTPUTS_DIR / args.run
    records = load_index(run_dir)

    preds = []
    seen = set()
    empty = 0
    dup = 0
    missing_md = 0
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
        preds.append({
            "subject": r["subject"],
            "document_id": r["document_id"],
            "page": int(r["page"]),
            "markdown": markdown,
        })

    problems = []
    if dup:
        problems.append(f"{dup} duplicate page identifiers (dropped)")
    if missing_md:
        problems.append(f"{missing_md} pages missing their .md output")
    if empty and not args.allow_empty:
        problems.append(f"{empty} pages have empty markdown")

    if args.required:
        required = load_required(Path(args.required))
        got = set(seen)
        miss = required - got
        extra = got - required
        if miss:
            problems.append(f"{len(miss)} MISSING required pages, e.g. {list(miss)[:3]}")
        if extra:
            problems.append(f"{len(extra)} EXTRA pages not in required set, e.g. {list(extra)[:3]}")

    print(f"Run: {args.run}")
    print(f"Predictions: {len(preds)} unique pages")
    print(f"Empty markdown: {empty}")
    if problems:
        print("\nVALIDATION ISSUES:")
        for p in problems:
            print("  - " + p)
    else:
        print("Validation: OK")

    out_zip = Path(args.out) if args.out else config.SUBMISSIONS_DIR / f"{args.run}.zip"
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    jsonl = "\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("predictions.jsonl", jsonl)
    print(f"\nWrote {out_zip} ({out_zip.stat().st_size/1e6:.2f} MB)")

    # Hard fail on required-set mismatch so bad submissions don't get uploaded.
    if args.required and problems and any("MISSING" in p or "EXTRA" in p for p in problems):
        sys.exit(2)


if __name__ == "__main__":
    main()
