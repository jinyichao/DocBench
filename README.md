# Dr.DocBench — Document Parsing Pipeline

Submission pipeline for the **Dr.DocBench** shared task (DocInsights 2026 / EvalAI challenge 2717):
convert single document-page images into structurally faithful Markdown, scored on Text edit
distance, Table TEDS, Formula CDM, and Reading Order (per-page-averaged Overall).

## Result

**Final rank 3 — Overall 85.63** (Public Validation, 509-page set; EvalAI submission 585800,
`results/submission_85.63_zerocopy_UWA.zip`, no duplicated content):
Text edit distance 0.1399, Table TEDS 72.57, Formula CDM 48.80, Reading Order 87.97.
First submission was 69.26.

How the 16 points were earned, as an **extract → audit → human-in-the-loop** loop:

1. **Extractor (69.26 → 71.33).** One VLM (Qwen3.8-max) with a scorer-tuned prompt, Gemini on
   table pages behind a guard, and higher-fidelity input (upscale to 2000 px + JPEG q100; the
   scans have a median long edge of 968 px). Then the extractor hit a ceiling: new prompts,
   column crops, other engines and re-runs all failed.
2. **Auditor (the gray bars).** A second pass reads the page image *and* the extractor's Markdown
   and changes block structure, never words: running heads and page numbers moved to the page end
   (+4.25, once the dev harness was rebuilt on the official md2md protocol), gated list/heading
   splits, layout-region splits, index-column repair, overlay text dropped, tables vs. text. Every
   change is scored on a dev harness before it goes to the leaderboard.
3. **Human-in-the-loop at each ceiling.** When rounds stopped gaining, page-by-page checks found
   the next lever (e.g. a list that should be a table, running heads left at the page top, index
   pages as region chunks: 78.92 → 80.05), and decided what shipped.
4. **Formula CDM without metric gaming.** The reference wraps printed italic/bold heads, page
   numbers and captions as `$\textit{…}$`. We add that markup inline, only on text printed that
   way, on formula-free pages (82.15 → 85.63). A build that appended duplicate formula copies
   scored higher (85.91) but was not selected.

See [`experiments/README.md`](experiments/README.md) for the research scripts behind these steps.

## Engine

- **Primary:** Qwen `qwen3.8-max` via DashScope (OpenAI-compatible), thinking disabled.
- **Ensemble:** Gemini `gemini-3.7-flash` on table pages and to recover DashScope
  content-filter blocks.

## Layout

```
src/
  config.py            central config (models, image encoding, keys)
  prompt.py            scorer-tuned prompt (tables=HTML <td>, display=$$, chemistry=\ce/smiles)
  parse_page_qwen.py   Qwen backend (upscale + q100 encode, request timeout)
  parse_page_gemini.py Gemini backend (same prompt/conventions)
  parse_page_claude.py Claude backend (same prompt/conventions; --backend claude)
  run_infer.py         batch runner over a split (resume-safe, --pages-file, --backend)
  build_ensemble.py    Qwen base + guarded Gemini table splice + recovery fill -> ensemble run
  build_submission.py  ensemble run -> predictions.jsonl -> validated zip
  build_submission_filetree.py  ensemble run -> Markdown File Tree zip (EvalAI's recommended format)
  run_until_done.sh    self-healing supervisor (restarts on DashScope stalls)
  # dev evaluation (local, reuses vendored DrDocBench metrics)
  evaluate_dev.py      Text/TEDS/Reading-order on the dev split
  overall_dev.py       exact per-page Overall (with rendered CDM)
  score_cdm.py         offline Formula CDM (needs TinyTeX/xelatex + node on PATH)
  detect_columns.py    DocLayout-YOLO layout detector (table/column page selection)
experiments/           research scripts for 72.38 -> 85.63 (zero-copy markup, layout splits,
                       audits, dev CDM harness); see experiments/README.md
results/               final selected submission (85.63, EvalAI 585800)
paper/                 system-description paper (ACL template) and figures
```

## Run

```bash
# keys: write secrets/qwen_key.txt and secrets/gemini_key.txt (gitignored), or set
#   DASHSCOPE_API_KEY / GEMINI_API_KEY

# 1) primary pass
python src/run_infer.py --split test --backend qwen   --run test_qwen
# 2) Gemini on table pages
python src/run_infer.py --split test --backend gemini --run test_gemini_tables \
    --pages-file outputs/test_table_pages.txt
# 3) assemble + package
python src/build_ensemble.py --qwen outputs/test_qwen --gemini outputs/test_gemini_tables \
    --table-pages outputs/test_table_pages.txt --recover outputs/test_recover \
    --out outputs/test_ensemble
python src/build_submission.py --run test_ensemble --out submissions/test_ensemble.zip
# or, for EvalAI's recommended Markdown File Tree format:
python src/build_submission_filetree.py --run test_ensemble --out submissions/test_ensemble_filetree.zip
```

Key knobs (env or `config.py`): `IMAGE_MAX_EDGE=2000`, `IMAGE_UPSCALE=1`,
`IMAGE_JPEG_QUALITY=100`, `PROMPT_VARIANT=v2`.

The final selected submission is `results/submission_85.63_zerocopy_UWA.zip` (jsonl format). It
includes page-level fixes from visual audits that no script reproduces, so it is committed as the
reference artifact.

Two post-processing passes are applied on top of the audited ensemble run, each validated against
real ground truth on a 200-page dev sample before submission (`src/evaluate_dev.py`):

- `src/split_long_lists.py` — split an enumerated list into one block per item, but ONLY when the
  mean item length is >= 110 characters. Ground truth splits long-item lists (median item 109 chars)
  and keeps short/dense ones merged (median 56), so the length gate is what makes this safe; the
  ungated version regresses. Dev: 3 improvements, 0 regressions. Leaderboard: +0.22 Overall.
- `src/split_heading_blocks.py` — separate a leading heading line (markdown `#`, or a fully-bold
  line) from the body text that follows it in the same block; ground truth annotates heading and
  body separately. Dev: Reading_Order 6 improved / 0 regressed. Leaderboard: +0.14 Overall
  (Reading_Order 69.87 -> 70.29, at a small Text_ED cost 0.1807 -> 0.1819). 59 test pages.
- `src/extract_verse_numbers.py` — move marginal verse line-numbers into their own blocks (ground
  truth annotates them separately). Validated on dev; currently matches 0 test pages, kept for
  future runs.
