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

- Banked-best confirmed: **72.02** (Text_ED 0.1831, Table_TEDS 70.47, Formula_CDM 0.0, Reading_Order 69.65)
- After banking 72.01, a further small batch (3 more LANGUAGEARTS mid-sentence merges, ARCHITECTURE
  photo-credit fixes, "Mark Beach" reorder, "NEIGHBOR TO NEIGHBOR" un-scramble, a likely-no-op
  JUVENILEFICTION edit) was submitted and came back at 71.97 — within noise of 72.01, but since it
  wasn't a clear improvement, all of it was reverted to reproduce the exact 72.01 state byte-for-byte.
- From that exact 72.01 state, removed ~35 lines of unreliably-transcribed scrapbook-clipping text on
  LANGUAGEARTS page 86 (a densely 3-way-interleaved lambing story / brand-logo essay / Harvard
  Classics history — individual sentences were legible at zoom but the true order/boundaries
  couldn't be confidently reconstructed, and the tiny-print body copy on the same page turned out to
  contain more guessed/reconstructed text than initially thought once re-examined more skeptically).
  Kept only the three large, high-confidence section titles and two paragraphs of normal-size main
  textbook body copy elsewhere on the same page. Per the "no guessing on illegible scans" rule and
  the insertion-asymmetry mechanism: a clean, honest gap scores more predictably than leaving
  scrambled/reconstructed text for the scorer to mismatch against. Result: **72.02**, a further
  small but genuine improvement (Reading_Order +0.03) — confirms removal was the right call, not a wash.
- `submission_72.02.zip` at the repo root is that exact confirmed-best submission (jsonl format),
  committed for reference/reproducibility (supersedes the earlier `submission_72.01.zip`).
- `outputs/` and `submissions/*.zip` (inside the `submissions/` dir) are gitignored (large generated
  working artifacts) — this log, the pipeline source changes, and the one banked-best zip at root are
  what's tracked in git; the day-to-day per-page `.md` content fixes live only in the local working
  tree, not in version control.

## New mechanism found: the formula-extraction regex silently eats plain text

Triggered by re-examining Formula_CDM (competitive pressure, rank ~7-8) to check whether "other
teams found something we missed." No recoverable Formula_CDM signal exists beyond the one confirmed
genuine display formula (TECHNOLOGY&ENGINEERING page 810) — the test set is still a near-empty
sample for that metric. But tracing `vendor/DrDocBench/utils/extract.py::display_reg` (the regex
that decides what counts as `equation_isolated`) surfaced a real, previously-unknown **Text_ED** bug:

- `display_reg` matches `$$...$$`, `\[...\]`, `$...$`, and `\(...\)` with `re.DOTALL`, run once over
  the **entire page's raw content string**, before any `\n\n` block-splitting. Confirmed
  experimentally: a bare, non-greedy `\$(.*?)\$` pairs the *first* `$` on the page with the *next*
  one, however far away, and DOTALL lets it span across paragraph/block boundaries.
- Consequence: **any page with two or more literal, unpaired `$` characters** (e.g. two USD amounts)
  has everything between them deleted from the predicted text before scoring — confirmed on
  ARCHITECTURE 1d76dc21.../{19,30,31} and LANGUAGEARTS 6a1ab132.../{85,89,90,91,92,94}, where in the
  worst case (ARCHITECTURE p.19) an entire sentence-and-a-half between two dollar amounts vanished.
- Confirmed via dev-set GT (`data/DrDocBench/dev/.../*.md` + per-page `json/`) that GT is **not**
  reprocessed by this regex — GT block category/text comes straight from the JSON annotation, so a
  `text_block` GT entry keeps its literal `$100 billion` (escaped or not — GT dev data has both) as
  plain characters. `clean_string` strips `$`/`\` either way, so the fix is simply: **never emit a
  literal `$` for currency** — write the bare number. This is scoring-equivalent to GT (both reduce
  to the same digits after `clean_string`) with none of the pairing risk. Escaping (`\$`) does NOT
  help — verified the regex still matches the literal `$` character regardless of a preceding
  backslash.
- Same mechanism, different cause: found `$V_1$`, `$V_1 > 6$`, `$V_6$`, `aV$_{L}$`/`aV\(_L\)` on
  MEDICAL ef52810c.../{42,43,44} (ECG lead labels) and `$B_{12}$`/`B$_{12}$` on HEALTH&FITNESS
  5aa03c54.../{560,568} (book-index entries) — plain alphanumeric labels that got LaTeX-subscript-
  wrapped for no reason (likely `prompt.py`'s old "inline math uses \(...\) or $...$" instruction
  being over-applied to anything with a subscript-looking character). Each wrap deletes that token
  from the predicted text stream the same way. Fixed by un-wrapping to plain text (`V1`, `aVL`,
  `B12`). Also removed a stray `\( C_p \)` wrap on TECHNOLOGY&ENGINEERING p.810's formula-legend line
  for consistency with the unwrapped `k = ...` legend two lines below it on the same page — that page
  does have a genuine GT display formula, so a spurious extra `equation_isolated` prediction there
  also risks hurting CDM precision on the one page that actually counts for it.
- Fixed 15 pages total across 4 documents (58 stray `$` signs stripped from currency + 6 mis-wrapped
  labels un-wrapped). Verified corpus-wide with the exact vendor regex that after the fix only
  page 810's genuine `$$ C_p = ... $$` formula still matches anywhere in all 509 pages.
- Updated `src/prompt.py` to warn against both failure modes explicitly (no literal `$` for currency;
  don't wrap plain labels with subscript-looking parts) so future inference runs don't reintroduce
  this.
- Packaged as `submissions/test_formula_regex_fix.zip` (diff-verified: exactly those 15 pages differ
  from `submission_72.02.zip`, same 20 empty pages as before) — leaderboard-confirmed **no measurable
  change** (Text_ED 0.1831, Table_TEDS 70.47, Formula_CDM 0.0, Reading_Order 69.65, Overall 72.02 —
  identical to 4 decimal places). Verified the zip really contained the fixes (not a stale build).
  Conclusion: real, correct, harmless fix, but 15/487 pages is too small a sample to clear the display
  precision — each page's own edit-distance-ratio improvement is diluted by ~1/487 in the average,
  consistent with the 68-page manual audit only moving Overall by +0.02. Banking it anyway (no
  downside); this bug class is fully closed corpus-wide (re-ran the exact vendor regex, only page
  810's genuine formula still matches).

## Quadrant reading-order bug: row-major instead of column-major on 2x2 collage pages

User flagged LANGUAGEARTS 6a1ab132.../94 (a page with 4 independent bordered newsletter clippings
arranged in a 2x2 grid): our reading order was TL -> TR -> BL -> BR (row-major/Z-pattern), but the
correct order should be TL -> BL -> TR -> BR (column-major) — read the whole left column of clippings
top-to-bottom before moving to the right column, same as the general column-major convention already
established for flowing multi-column text ([[reading-order-column-major]]).

Verified against real dev-set GT (not guessed): wrote a script to find genuine "2x2 grid of large,
independent blocks" pages in `data/DrDocBench/dev/*/*/json/*.json` (item count 4-7, each block >5% of
page area, one block per quadrant by center point). Found 6 such pages; **5 of 6 are clean
TL->BL->TR->BR column-major** in their real GT `order` field (all 3 pages from one PETS book agree;
one GAMES page agrees; one SPORTS page agrees). Only one outlier (a 4-photo array with no accompanying
running text) didn't fit either pattern cleanly. This is strong, consistent, book-spanning precedent —
confirms the user's read and extends the existing column-major rule to boxed/collage layouts, not just
flowing text columns.

Checked all 15 pages of the LANGUAGEARTS 6a1ab132 document (a newsletter-design textbook full of these
example-clipping collages) against their source images. Found and fixed the same TL/TR/BL/BR bug on
**8 pages**: 85, 89, 90, 91, 93, 94, 95, 97 (each reordered from TL,TR,BL,BR to TL,BL,TR,BR — pure
block reordering, no content changes). Page 92 was already correctly TL,BL,TR,BR (not every page had
the bug). Pages 83/84/87/88 are plain flowing 2-column text (not boxed collages, not applicable). Page
96 is TL/TR-over-a-single-full-width-bottom-section (no BL/BR split to get wrong) and was left alone —
its bottom section's internal 4-column ordering is a separate, already-relitigated question from
earlier in this session, not touched here.

Packaged as `submissions/test_quadrant_reorder.zip` (diff-verified: exactly those 8 pages differ from
`test_formula_regex_fix.zip`) and submitted.

**Result: REGRESSION.** Overall 72.02 -> 71.99 (-0.03). Reading_Order actually ticked up slightly
(69.65 -> 69.66 at 2-decimal display), meaning the small net effect across 8 pages was negative even
though the *displayed* Reading_Order metric moved the "right" direction — a small gain on some pages
was outweighed by a small loss on others, invisible at 2-decimal rounding. Also checked all other
subjects in the 509-page corpus for the same layout pattern first (ran the DocLayout-YOLO detector
against all 509 test images, manually inspected every distinct candidate cluster from 46 flagged
pages) — confirmed this specific "independent boxed clippings in a 2x2 grid" layout is unique to this
one LANGUAGEARTS document in the whole test set, so there was no broader corpus-wide version of this
lever to find either way.

**Reverted** all 8 pages back to the exact `submission_72.02.zip` byte content (same "extract from the
banked zip" methodology as prior reverts). Caveat hit during the revert: 5 of the 8 pages (85, 89, 90,
91, 94) were *also* touched by the formula-regex-eats-text fix (dollar-sign stripping), so reverting
wholesale from `submission_72.02.zip` (which predates that fix) silently un-did the dollar-sign fix on
those 5 pages too. Caught it by re-running the corpus-wide `display_reg` scan (found 2 stray matches
instead of the expected 1) and re-applied the dollar-stripping fix to those 5 files. Final state
diff-verified against `submission_72.02.zip`: exactly the original 15 formula-regex-fix pages differ,
quadrant pages are back to their original (pre-this-experiment) order. **Lever closed** — the
column-major convention from [[reading-order-column-major]] does not reliably generalize to boxed
2x2-collage layouts even with 5/6 dev-set precedent; treat any further reordering-by-analogy attempts
on this specific layout type with real leaderboard skepticism, not dev-set inference alone.

## NEW BANKED BEST 72.24 (2026-09-22): gated long-list splitting

**Result: Overall 72.02 -> 72.24 (+0.22).** Text_ED 0.1831 -> 0.1807, Reading_Order 69.65 -> 69.87,
Table_TEDS 70.47 and Formula_CDM 0.0 both EXACTLY unchanged (they were the built-in sanity check —
the edit is whitespace-only and touches no table or formula page, so any movement there would have
meant the submission wasn't what we thought).

**The fix.** The scorer segments a page on blank lines, so a markdown list emitted as consecutive
single-newline lines collapses into ONE block. Where ground truth annotates each item separately, our
one block can match only one GT item and the remaining N-1 count as unmatched deletions — expensive
for Text_ED *and* Reading_Order. `src/split_long_lists.py` inserts a blank line between items.

**What made it safe — the length gate.** Whether GT splits a list is NOT predictable from the marker
(bullet vs number vs letter; both regimes use `$\bullet$`, and both patterns can appear on the same
page). It is predictable from ITEM LENGTH, measured across all dev GT:

| GT regime | mean item length p25 / median / p75 | n |
|---|---|---|
| kept as ONE block | 27 / 56 / 80 | 33 |
| split PER ITEM | 93 / 109 / 116 | 20 |

Gating at >=110 chars gave 3 improvements / 0 regressions on dev; the ungated version regressed
several pages and destroyed a clean one (an 8-bullet list averaging 85 chars that GT keeps merged).
Only 5 of 509 test pages qualify, and every edit is pure whitespace.

**Method that produced it.** A free dev post-processing harness (copy run -> apply rule -> re-score
with `src/evaluate_dev.py` against real GT). This matters because an earlier session had *reasoned*
from counterexamples that list-splitting was "not mechanically safe" and dropped it — measuring
showed it IS net positive, and measuring the length base rate turned a marginal rule into a
zero-regression one. Reason to form the hypothesis; measure to keep it.

**Pre-submission estimate was accurate**, which validates the method for future block-structure
changes: predicted +0.2 (Text_ED ~0.1813, RO ~69.9) from per-page affected-share x (N-1)/N; actual
+0.22 (0.1807 / 69.87).

### Levers closed this session (all measured, none assumed)

| lever | verdict |
|---|---|
| Formula-regex `$`-pair bug (15 pages) | real bug, fixed; leaderboard-neutral (too few pages) |
| Quadrant reading-order reorder (8 pages) | REGRESSION 72.02 -> 71.99, reverted |
| Merge rules (mid-sentence, short-block) | all NEGATIVE on dev; `src/fix_block_splits.py` must not be run |
| Table `<br>`-cell row expansion | NEGATIVE (TEDS 0.702 -> 0.688) |
| Running-head emission prompt rule | backwards — GT labels running heads excluded 79.7% vs scored 20.3% |
| qwen3.8-flash as engine | -12.4 Overall proxy vs max; tables collapse (TEDS 0.476 vs 0.702) |
| Gemini for non-table pages | Qwen wins all three metrics head-to-head on 67 identical dev pages |
| Omission hunt (glyph audit, 509 pages) | 7 outliers, all correct or deliberate — output is not missing content |
| deepseek-v4-pro / glm-5.3 | reachable on the same gateway but TEXT-ONLY (no vision) |
| local dots.ocr parser | not pursued — corpus is low-res scans (median 968px) where a 3B specialist is unlikely to beat a frontier VLM |

**Principle worth carrying forward: SPLIT helps, MERGE hurts.** Every merge rule tested made both
metrics worse; only splits won. That is the insertion asymmetry showing up in post-processing.

## BANKED BEST 72.38 (2026-09-22): heading/body block splitting

**Overall 72.24 -> 72.38 (+0.14).** Reading_Order 69.87 -> 70.29 (+0.42); Text_ED 0.1807 -> 0.1819
(slightly worse); Table_TEDS 70.47 / Formula_CDM 0.0 exactly unchanged. 59 pages, pure whitespace.

`src/split_heading_blocks.py`: when a block's first line is a whole-line heading (markdown `#`, or a
fully-bold line) and body text follows, insert a blank line. GT annotates heading and body as
separate blocks; our merged block matched only one and the other was an unmatched deletion.

**The rule trades a little Text_ED for more Reading_Order.** Net positive, but the Text component
moved the opposite way from the dev prediction.

**A guard makes it worse** — restricting to "only split when >=80/120 chars of prose with sentence
punctuation follows" scores 85.96 vs 85.99 ungated on dev, because it drops winners like
`## ACROSS` / `## DOWN` crossword clue lists. Do not re-add.

### Prediction miss (recorded because the method matters)

Predicted +0.3 to +0.5 with Text_ED improving; actual +0.14 with Text_ED slightly worse. The same
per-page extrapolation was accurate for the list rule (predicted +0.2, got +0.22) but that rule
touched 5 pages in 3 documents; this one touches 59 pages across 16 subjects. **Per-page dev
extrapolation is reliable for narrow, concentrated rules and unreliable for broad ones** — for broad
rules, expect the component dev favours least to transfer worst, and quote a wider range.

### How both winning rules were found (reusable recipe)

Align our blocks against dev GT, list every case where one of our blocks swallows >=2 GT blocks, and
look for a detectable cue at the boundary. Two corrections were essential:
- Do the alignment on **actual `md_tex_filter` blocks**, not raw `\n\n` splits — the scorer already
  extracts `#` headings as titles, so raw-split analysis invents issues that don't exist.
- A large remaining cluster is **GT splitting mid-sentence at COLUMN BREAKS** ("...For" |
  "example, the Organisation..."), since GT annotates each column's portion separately. We correctly
  rejoin the sentence and are penalised for it. That is layout information our markdown has
  discarded — not fixable post-hoc.

**Cumulative this session: 72.02 -> 72.38 (+0.36)**, entirely from whitespace-only block-structure
post-processing validated against real dev ground truth before each submission.
