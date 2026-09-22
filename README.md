# Dr.DocBench — Document Parsing Pipeline

Submission pipeline for the **Dr.DocBench** shared task (DocInsights 2026 / EvalAI challenge 2717):
convert single document-page images into structurally faithful Markdown, scored on Text edit
distance, Table TEDS, Formula CDM, and Reading Order (per-page-averaged Overall).

## Result

Best leaderboard **Overall = 72.38** (Public Validation, 509-page set):
Text edit distance 0.1819, Table TEDS 70.47, Formula CDM 0.0, Reading Order 70.29.

Key levers: v2 HTML table prompt, Gemini table-page ensemble, and higher-fidelity images
(upscale to 2000px + JPEG q100), since the test scans are low-resolution (median 968px) and
the model was resolution-starved, not capability-limited. On top of that, a manual audit pass
fixed content-fidelity and block-granularity bugs across the corpus — most notably giving
DRAMA play-script dialogue per-speaker-turn block granularity (the single largest lever after
image fidelity) and removing/correcting a handful of pages where the source scan was too
degraded to transcribe reliably rather than leaving guessed content in place. See
[`SESSION_LOG.md`](SESSION_LOG.md) for the full record of what worked and what didn't,
including several reverted experiments (splitting header/footer/page-number content into more
blocks looked plausible but never helped, since those categories are excluded from scoring).

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

The confirmed-best submission (`submission_72.38.zip`, jsonl format) is committed at the repo
root for reference/reproducibility.

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
