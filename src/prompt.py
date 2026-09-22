"""The page-parsing prompt for Dr.DocBench.

Output conventions are dictated by the DrDocBench scorer (see vendor/DrDocBench/
utils/extract.py :: md_tex_filter and the dataset README "Task Format" table):

  - Tables MUST be HTML wrapped in <table>...</table> (rowspan/colspan allowed).
    The scorer extracts <table> blocks for TEDS. Markdown pipe tables are also
    auto-converted, but native HTML is safest and preserves spans.
  - Isolated/display formulas MUST be LaTeX in display delimiters. The scorer
    treats $$...$$ and \\[...\\] as equation_isolated (scored by CDM + edit dist).
  - CAUTION: the scorer's formula regex runs on the WHOLE page before block
    splitting and is naive: `\$(.*?)\$` and `\\(...\\)` match ANY pair of $ or
    \(\) on the page, even across paragraphs, and delete everything between
    them from the text that gets scored (confirmed both experimentally and by
    reading vendor/DrDocBench/utils/extract.py::display_reg). Consequences:
      * NEVER use a literal $ for currency (e.g. "$18 billion"). Two dollar
        amounts on one page silently deletes all the text between them.
        Write the number with no $ sign at all -- clean_string strips $ from
        the ground truth too, so omitting it is scoring-equivalent and safe.
      * NEVER wrap a plain alphanumeric label/abbreviation in \(...\) or $...$
        just because it has a subscript-looking part (e.g. ECG leads "aVL",
        "V1"; "B12"). Write these as plain text. Reserve inline math
        delimiters for genuine mathematical notation only.
  - Inline formulas use \\(...\\) or $...$, but ONLY for actual math notation.
  - Chemistry: \\ce{...} (mhchem); SMILES verbatim in a ```smiles block.
  - Code / pseudocode: fenced block with a language tag.
  - Music: MusicXML in a ```musicxml block (no <?xml?> / <score-partwise> wrapper).
  - Figures: purely visual figures are ignored; transcribe embedded labels/axis
    text as plain text. Do NOT emit image markdown (it is stripped anyway).
  - Text: original language/script, no translation, natural reading order across
    columns (left-to-right, top-to-bottom). Do not hallucinate illegible text.
"""

SYSTEM_PROMPT = (
    "You are an expert document-parsing engine. You convert a single scanned "
    "document page image into faithful, structurally accurate Markdown. You "
    "transcribe exactly what is on the page: no translation, no summarizing, no "
    "commentary, no invented content. You never omit body content and never add "
    "content that is not visible."
)

# The core instruction block. Kept explicit and format-locked to match the scorer.
USER_PROMPT = r"""Convert this document page into a single Markdown document that preserves both its text content and its structure. Follow these rules EXACTLY.

__READING__

TEXT
- Transcribe the original language and script verbatim. Do not translate or normalize spelling.
- Preserve paragraphs; separate distinct blocks with a blank line.
- Use Markdown headings (#, ##, ...) for titles/section headings.
- For illegible characters, transcribe your best reading of what is visible; do not guess whole words that are not there.

FORMULAS
- Isolated / display equations: wrap in display delimiters on their own line, e.g.
  $$ E = mc^2 $$
- Inline math: use \( ... \), but only for genuine mathematical notation.
- Never write a literal $ for a currency amount (write "18 billion", not "$18 billion").
- Never wrap a plain label/abbreviation that merely has a subscript-looking part
  (e.g. ECG lead "aVL", "V1"; vitamin "B12") in \( ... \) or $ ... $ -- write it
  as plain text.
- Use standard LaTeX. Do not wrap formulas in code fences.

__TABLES__

CHEMISTRY
- Chemical reactions/equations: use mhchem, e.g. \ce{2H2 + O2 -> 2H2O}.
- Drawn 2D molecular structure diagrams (skeletal/ring structures, e.g. under a "Structural Formula" heading): output the molecule as a SMILES string inside a ```smiles fenced block. Do NOT redraw it as ASCII art, and do NOT skip it. If the compound is also named on the page, use the name to produce the correct SMILES.
- Molecular structures already given as SMILES text: put the SMILES string verbatim in a ```smiles fenced block.

CODE / PSEUDOCODE
- Put code or algorithm listings in a fenced code block with a language tag, e.g. ```python or ```pseudocode.

MUSIC
- Transcribe musical scores as MusicXML inside a ```musicxml fenced block. Do not include the <?xml?> declaration or the <score-partwise> wrapper element.

FIGURES / IMAGES
- Do not output image markdown or describe purely pictorial figures.
- DO transcribe any text embedded in a figure (labels, axis ticks, legends, callouts) as plain text at the figure's position.

OUTPUT
- Output ONLY the Markdown for the page. No preamble, no explanation, no ``` fence around the whole answer.
- If the page is blank, output nothing."""

# --- Table instruction variants (A/B tested against Table TEDS) ---
_TABLES_BASE = """TABLES
- Output every table as raw HTML wrapped in <table>...</table>.
- Use <tr>/<td>/<th> with rowspan and colspan to reflect merged cells.
- Transcribe the cell contents faithfully (including inline math as \\( ... \\) inside cells).
- Do NOT use Markdown pipe tables. Do NOT wrap the table in a code fence.
- If a table continues from/to an adjacent page, still emit the portion visible on THIS page as one <table>."""

# v2: targets the scorer's real TEDS penalties — the scorer normalizes away
# <th>/<thead>/<tbody>/styles, so the costly errors are wrong grid shape and
# in-cell <br>/word-splitting. Force <td>-only, exact grid, no in-cell breaks.
_TABLES_V2 = """TABLES
- Output every table as raw HTML: a single <table> containing <tr> rows, and <td> for EVERY cell (use <td> even for header cells — do not use <th>).
- Reproduce the exact grid you see: the same number of rows and the same number of columns. One <td> per visual cell. Represent an empty cell as <td></td>.
- Use rowspan / colspan ONLY where one cell visibly spans multiple rows or columns in the image; otherwise omit them. Never split one real cell into several <td>, and never merge separate cells into one.
- Put each cell's entire text on a single line. Do NOT place <br>, <p>, <div>, <span>, or newlines inside a cell. If a word or number is wrapped across two printed lines (often with a hyphen at the break), rejoin it into one continuous token (e.g. "product-order-\\nletter" -> "product-order-letter").
- Transcribe cell text exactly, including inline math as \\( ... \\). Do not add, drop, reorder, or re-align columns.
- Do NOT use Markdown pipe tables. Do NOT wrap the table in a code fence.
- If a table continues from/to an adjacent page, still emit the portion visible on THIS page as one <table>."""

# GT reads multi-column pages column-major (left column fully, then right); measured
# 35:3 on dev. This matches the model's default, so the instruction just reinforces it.
_READING_BASE = """READING ORDER
- Emit blocks in natural human reading order: for multi-column layouts, finish the left column top-to-bottom before the right column. Interleave captions/footnotes at the position they belong to in the flow."""

# v3: same as v2 but with reading-order rules targeting failure modes measured on a
# 200-page dev sample (2026-09-22): narrow margin/sidebar columns being interleaved into
# the main body instead of read as a unit, and boxed callouts being broken up.
#
# A third rule ("emit the top-of-page running head first") was tried and REMOVED. On a
# paired 77-page A/B it fixed 2 pages outright (0.40->0.00, 0.20->0.00) but broke a clean
# one on BOTH text and order (0.000->0.210 Text_ED, 0.000->0.143 RO). Base-rate check over
# all dev docs settled it: for genuine running heads (same text on 3+ pages of a doc), GT
# labels them `header`/`page_number` -- EXCLUDED from scoring -- 79.7% of the time, and a
# scored `title`/`text_block` only 20.3%. So emitting them is wrong ~4x more often than
# it is right; the apparent win came from the subset happening to contain one of the 4
# documents (of 34) where GT scores them. Our v2 default of omitting running heads is
# already correct ~80% of the time. Do not re-add this rule.
#
# STATUS: the two surviving rules are UNTESTED -- the A/B run died at 80/200 when the
# DashScope weekly quota was exhausted, and the subset contained none of the sidebar pages
# the first rule targets. v2 remains the default; re-run the A/B before adopting v3.
_READING_V3 = """READING ORDER
- Emit blocks in natural human reading order: for multi-column layouts, finish the left column top-to-bottom before the right column. Interleave captions/footnotes at the position they belong to in the flow.
- Treat a narrow margin or sidebar column as a column of its own: emit all of its blocks top-to-bottom as one contiguous run. Do not interleave them into the main body text.
- Keep a boxed or shaded callout contiguous: emit its heading first, then its contents, then return to the surrounding body text."""

_READINGS = {"base": _READING_BASE, "v2": _READING_BASE, "v3": _READING_V3}
_TABLES = {"base": _TABLES_BASE, "v2": _TABLES_V2, "v3": _TABLES_V2}


def get_user_prompt(variant="v2"):
    r = _READINGS.get(variant, _READING_BASE)
    t = _TABLES.get(variant, _TABLES_BASE)
    return USER_PROMPT.replace("__READING__", r).replace("__TABLES__", t)


# Precompute for convenience / validation.
PROMPTS = {v: get_user_prompt(v) for v in ("base", "v2", "v3")}
