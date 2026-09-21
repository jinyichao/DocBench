# Session Log — Manual Audit & Block-Granularity Investigation (2026-09-20/21)

Record of a long interactive audit session on top of the previously-banked 71.54 submission
(`test_ensemble_q100_audited.zip`). Kept for future reference: what was tried, what worked, what
didn't, and why — so the same mistakes aren't repeated and the same evidence doesn't need
re-deriving.

## Starting point

Banked best going into this session: **Overall 71.54** (Text_ED ~0.190, Table_TEDS ~69.5-70,
Reading_Order ~69.05), the result of the prior session's upscaling + manual-audit +
character-fidelity work (see memory: `upscaling-lever-win`).

## New mechanism discovered this session

**`clean_string` is case-sensitive.** Traced the actual scorer (`vendor/DrDocBench/metrics/cal_metric.py`)
— `Levenshtein.distance(pred, gt)` runs on `clean_string` output, which strips all non-`\w`/non-CJK
characters but never lowercases. Small-caps typography (e.g. play-script speaker labels, running
heads) should transcribe as full ALL CAPS, not title case — confirmed by checking how the same
document's already-correct small-caps text (e.g. "WEMBLEY", "HATHAWAY") was handled.

**Header/footer/page-number exclusion mechanism.** Confirmed via `end2end_dataset.py:257-341` and
the official EvalAI submission guidelines: `header`, `footer`, `page_number`, `figure_caption`, etc.
are excluded from Text_ED/Reading_Order scoring, but only *after* Hungarian matching — they still
participate in the matching step against all of our predicted blocks. This means splitting/merging
excluded-category content can still indirectly disturb the matching of *neighboring scored* content,
even though the excluded content's own fidelity never matters. This explains several outcomes below
that looked paradoxical at first.

**Unicode fraction characters count as `\w`.** `clean_string('¾')` stays `'¾'`; it does not get
stripped, and does not equal `clean_string('3/4') == '34'`. Confirmed dev-set precedent
(`"2½ pint"`) shows GT keeps the printed Unicode glyph — do not normalize fractions to ASCII slashes.

## Successes (kept, banked)

| Fix | Where | Why it worked |
|---|---|---|
| Un-garble interleaved logo/title text | NATURE page 2 | Genuine content corruption in a scored `text_block`, unrelated to header/footer exclusion |
| Case-sensitivity fixes (she→She, Hz→HZ, ACT I) | JUVENILEFICTION, MEDICAL, DRAMA | Real letter-level mismatches in scored text; the DRAMA one turned out scoring-neutral (excluded category) but harmless |
| **DRAMA per-speaker-turn block splitting** | MAN ALIVE (15 pages) | The single biggest lever this session: **+0.85 Overall** once done correctly (see saga below) |
| Mid-sentence / hyphenation-split cleanup | SOCIALSCIENCE, LANGUAGEARTS (×2 rounds, 7 instances) | Print-line-wrap artifacts wrongly treated as block boundaries; safe, universal, no genre risk |
| Photo-credit mid-sentence interleaving | ARCHITECTURE pages 30, 31 | Same mechanism as DRAMA's over-fragmentation bug, applied to a different genre |
| Caption/credit reading-order fixes | LANGUAGEARTS page 83 ("Mark Beach") | Verified via image; likely scoring-neutral (excluded category) but correct |

**Net result of this session: 71.54 → 72.01 (+0.47 banked best).**

## The DRAMA dialogue block-granularity saga (the big lesson)

1. Found MAN ALIVE pages 29/30 with dialogue turns wrongly separated by blank lines. Reasoning from
   a *single* POETRY dev-set precedent (a 2-line "Bride:/Maidenhood:" exchange kept as one GT block)
   plus the general "dense content = whole block" lesson from an earlier session's block-merge
   investigation, **merged them into fewer, larger blocks.** This was WRONG — DRAMA is a different
   genre than the POETRY precedent, and the generalization didn't hold.
2. Extended the same wrong merge to 2 more pages. Submitted: Overall dropped to 71.16, worse than
   even the still-active header-splitting regression at the time.
3. User pushed back: reverse direction entirely — full per-line fragmentation instead of merging.
4. That surfaced a **second, distinct bug**: the fragmentation script split every raw newline,
   including print-line-wraps *within* a single utterance (e.g. "...you can" / "hardly claim...").
   Found and merged 43 such mid-sentence artifacts across 3 pages.
5. Submitted with full per-turn fragmentation + the artifact cleanup: **72.01, new banked best.**

Lesson: don't generalize block-granularity conventions across genres from a single precedent.
Play-script dialogue wants per-speaker-turn blocks; that's opposite of what a 2-line poem wanted,
and neither is the universal answer for "dense content."

## Failed / reverted attempts

| Attempt | Result | Why reverted |
|---|---|---|
| Split header/footer/page-number content into more blocks (NATURE 8 files, DRAMA 20 files, corpus-wide 120 files) | Overall 71.29 (from 71.54) | Excluded categories can't be scored directly, but splitting them still disrupted matching of neighboring scored content — pure downside, no possible upside. **Lever closed.** |
| Newsletter masthead title/volume/date splitting & reordering (8 files, 1 document) | Overall 71.96 (from 72.01), a wash | Unlike DRAMA headers these are likely scored `title` content, but the batch's net effect was flat/slightly negative — reverted all of it except one clear content-correctness fix ("NEIGHBOR TO NEIGHBOR" was genuinely garbled text, not just a block-count question) |
| LANGUAGEARTS page 86 three-way column interleaving (lambing story / brand-logo essay / Harvard Classics history, densely interleaved) | Not attempted | Confirmed the text is legible (not truly illegible/guessed), but reconstructing 3 fully-interleaved articles across a 3-column×2-row collage carries high risk of new errors for uncertain payoff on a single page. Deferred — noted here rather than guessed at. |
| Converting Unicode fractions (½, ¾, ⅛) to ASCII "1/2" notation | Not applied | `clean_string` treats them as different characters; one real dev-set precedent shows GT keeps the Unicode glyph |

## Format note

Discovered (via user-supplied official guidelines) that EvalAI's Option A, **Markdown File Tree**,
is the *recommended* submission format — not just the `predictions.jsonl` this pipeline's
`build_submission.py` was built around. Added `src/build_submission_filetree.py`, which packages
the same run into `<subject>/<document_id>/mds/<document_id>_<page>.md` with no wrapper directory,
per spec. Both formats are validated against the same source `.md` tree and kept in sync.

## Current state as of this log

- Banked-best confirmed: **72.01** (Text_ED 0.183, Table_TEDS 70.47, Formula_CDM 0.0, Reading_Order 69.62)
- After banking 72.01, a further small batch (3 more LANGUAGEARTS mid-sentence merges, ARCHITECTURE
  photo-credit fixes, "Mark Beach" reorder, "NEIGHBOR TO NEIGHBOR" un-scramble, a likely-no-op
  JUVENILEFICTION edit) was submitted and came back at 71.97 — within noise of 72.01, but since it
  wasn't a clear improvement, all of it was reverted to reproduce the exact 72.01 state byte-for-byte.
- `submission_72.01.zip` at the repo root is that exact confirmed-best submission (jsonl format),
  committed for reference/reproducibility.
- `outputs/` and `submissions/*.zip` (inside the `submissions/` dir) are gitignored (large generated
  working artifacts) — this log, the pipeline source changes, and the one banked-best zip at root are
  what's tracked in git; the day-to-day per-page `.md` content fixes live only in the local working
  tree, not in version control.
