"""Batch-run the page parser over a split (dev/test), with caching + resume.

Usage:
    python src/run_infer.py --split dev --run dev_opus48 [--limit N] [--subjects ART ...]
    python src/run_infer.py --images-root /path/to/evalai/test --run test_opus48

Outputs go to outputs/<run>/mds/<subject>/<document_id>/<N>.md and an index.jsonl
mapping each page to (subject, document_id, page, md_path). Re-running skips pages
whose .md already exists (resume-safe).
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config          # noqa: E402

PAGE_RE = re.compile(r"page_(\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)


def discover_pages(images_root: Path):
    """Yield dicts {subject, document_id, page, image_path} for a split tree.

    Expected layout: <root>/<SUBJECT>/<DOC_UUID>/images/page_<N>.jpg
    """
    pages = []
    for img in sorted(images_root.glob("*/*/images/page_*.*")):
        m = PAGE_RE.search(img.name)
        if not m:
            continue
        document_id = img.parent.parent.name
        subject = img.parent.parent.parent.name
        pages.append({
            "subject": subject,
            "document_id": document_id,
            "page": int(m.group(1)),
            "image_path": str(img),
        })
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], help="use data/DrDocBench/<split>")
    ap.add_argument("--images-root", help="explicit split root (overrides --split)")
    ap.add_argument("--run", required=True, help="run name -> outputs/<run>/")
    ap.add_argument("--limit", type=int, default=0, help="cap number of pages (debug)")
    ap.add_argument("--subjects", nargs="*", help="restrict to these subjects")
    ap.add_argument("--pages-file", help="restrict to image paths listed in this file")
    ap.add_argument("--backend", choices=["qwen", "gemini"], default="qwen",
                    help="qwen = DashScope qwen3.8-max (primary); gemini = table-page ensemble")
    ap.add_argument("--model", default=None, help="override model id")
    ap.add_argument("--concurrency", type=int, default=config.CONCURRENCY)
    args = ap.parse_args()

    # Select backend: (parse_fn, client, default_model)
    if args.backend == "qwen":
        import parse_page_qwen as backend
        default_model = config.QWEN_MODEL
    else:
        import parse_page_gemini as backend
        default_model = config.GEMINI_MODEL
    client = backend.make_client()
    parse_page = backend.parse_page
    model = args.model or default_model

    if args.images_root:
        images_root = Path(args.images_root)
    elif args.split:
        images_root = config.DATA_DIR / args.split
    else:
        ap.error("provide --split or --images-root")

    pages = discover_pages(images_root)
    if args.subjects:
        keep = set(args.subjects)
        pages = [p for p in pages if p["subject"] in keep]
    if args.pages_file:
        wanted = {line.strip() for line in open(args.pages_file) if line.strip()}
        # match on image path suffix so relative/absolute both work
        pages = [p for p in pages
                 if p["image_path"] in wanted
                 or any(p["image_path"].endswith(w) or w.endswith(p["image_path"])
                        for w in wanted)]
    if args.limit:
        pages = pages[: args.limit]
    if not pages:
        print(f"No pages found under {images_root}", file=sys.stderr)
        sys.exit(1)

    run_dir = config.OUTPUTS_DIR / args.run
    mds_dir = run_dir / "mds"
    run_dir.mkdir(parents=True, exist_ok=True)

    lock = threading.Lock()
    stats = {"done": 0, "skipped": 0, "failed": 0,
             "input_tokens": 0, "output_tokens": 0}
    t0 = time.time()

    def md_path_for(p):
        return mds_dir / p["subject"] / p["document_id"] / f"{p['page']}.md"

    def worker(p):
        out = md_path_for(p)
        if out.exists():
            with lock:
                stats["skipped"] += 1
            return
        try:
            md, usage = parse_page(client, p["image_path"], model=model)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(md, encoding="utf-8")
            with lock:
                stats["done"] += 1
                stats["input_tokens"] += usage["input_tokens"]
                stats["output_tokens"] += usage["output_tokens"]
                n = stats["done"] + stats["skipped"] + stats["failed"]
                if stats["done"] % 10 == 0 or n == len(pages):
                    el = time.time() - t0
                    print(f"[{n}/{len(pages)}] done={stats['done']} "
                          f"skip={stats['skipped']} fail={stats['failed']} "
                          f"in_tok={stats['input_tokens']} out_tok={stats['output_tokens']} "
                          f"{el:.0f}s", flush=True)
        except Exception as e:  # noqa: BLE001
            with lock:
                stats["failed"] += 1
            print(f"FAIL {p['subject']}/{p['document_id']}/{p['page']}: {e}",
                  file=sys.stderr, flush=True)

    print(f"Parsing {len(pages)} pages -> {run_dir} (backend={args.backend} "
          f"model={model}, "
          f"concurrency={args.concurrency})", flush=True)
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(worker, pages))

    # Write the page index (used by build_submission).
    index_path = run_dir / "index.jsonl"
    with index_path.open("w", encoding="utf-8") as f:
        for p in pages:
            rec = dict(p)
            rec["md_path"] = str(md_path_for(p))
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nComplete. done={stats['done']} skipped={stats['skipped']} "
          f"failed={stats['failed']}", flush=True)
    print(f"Tokens: in={stats['input_tokens']} out={stats['output_tokens']}", flush=True)
    print(f"Index: {index_path}", flush=True)


if __name__ == "__main__":
    main()
