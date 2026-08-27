# Dr.DocBench — Document Parsing Pipeline

Submission pipeline for the **Dr.DocBench** shared task (DocInsights 2026 / EvalAI challenge 2717):
convert single document-page images into structurally faithful Markdown, scored on Text edit
distance, Table TEDS, Formula CDM, and Reading Order (per-page-averaged Overall).

## Result

Best leaderboard **Overall = 71.33** (Public Validation, 509-page set):
Text edit distance 0.194, Table TEDS 69.35, Reading Order 69.05.

Key levers: v2 HTML table prompt, Gemini table-page ensemble, and — the biggest gains —
higher-fidelity images (upscale to 2000px + JPEG q100), since the test scans are
low-resolution (median 968px) and the model was resolution-starved, not capability-limited.

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
```

Key knobs (env or `config.py`): `IMAGE_MAX_EDGE=2000`, `IMAGE_UPSCALE=1`,
`IMAGE_JPEG_QUALITY=100`, `PROMPT_VARIANT=v2`.
