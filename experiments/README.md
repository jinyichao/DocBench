# experiments/

Research scripts from the second half of the competition (Overall 72.38 → 85.63), kept as a record
of what was tried. They were written as one-off tools during an extract → audit → human-in-the-loop
loop, not as a polished pipeline:

- They read intermediate files (per-variant `*.jsonl` predictions, PaddleOCR line boxes, DocLayout-YOLO
  regions) from `outputs/` or from `$DRDOC_WORK` (default `outputs/work`). Those files are not
  committed, because they are large and derived from the test images.
- Some scripts import the vendored DrDocBench scorer (`dataset.md2md_dataset`, `metrics.cdm_metric`,
  `utils.extract`) and expect to be run from `vendor/DrDocBench` with `.venv-cdm` (numpy<2, TinyTeX
  on PATH), or import a `geofeat` helper that was not preserved.
- The final selected submission is committed as `results/submission_85.63_zerocopy_UWA.zip`
  (EvalAI submission 585800). It also contains page-level fixes made during visual audits that no
  script reproduces.

| folder | what | status |
|---|---|---|
| `zero_copy/` | Inline `$\textit{}$` / `$\textbf{}$` markup on text printed in italic or bold (running heads, page numbers, captions); text and block order are left byte-identical. `build_G.py` → `build_J.py` / `build_K.py` lead to the final build. | **used in the final** |
| `formula_copies/` | Variants that append a `$\textit{…}$` copy after text blocks (CDM rises while Text/RO stay unchanged). | explored, best 85.91 (sub 584866), **not selected**, since duplicated content |
| `layout/` | DocLayout-YOLO region splits (`region_split.py`, used on safe docs and index pages); region merges, Docling Heron and PaddleX layout models (rejected). | splits used; merges rejected |
| `audit/` | Qwen page audit, PaddleOCR coverage checks, margin running-head recovery, slant (italic) and stroke-width (bold) detectors, known-issue scanner, misread crop viewer. | used to find candidates; every fix was checked by a human-in-the-loop |
| `eval/` | Dev-split CDM harness on the official md2md matching (`cdm_harness.py`) and a dedup check. | dev validation |

The rules that generalise are in `src/` (`split_long_lists.py`, `split_heading_blocks.py`,
`extract_verse_numbers.py`).
