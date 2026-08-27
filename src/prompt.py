"""The page-parsing prompt for Dr.DocBench.

Output conventions are dictated by the DrDocBench scorer (see vendor/DrDocBench/
utils/extract.py :: md_tex_filter and the dataset README "Task Format" table):

  - Tables MUST be HTML wrapped in <table>...</table> (rowspan/colspan allowed).
    The scorer extracts <table> blocks for TEDS. Markdown pipe tables are also
    auto-converted, but native HTML is safest and preserves spans.
  - Isolated/display formulas MUST be LaTeX in display delimiters. The scorer
    treats $$...$$ and \\[...\\] as equation_isolated (scored by CDM + edit dist).
  - Inline formulas use \\(...\\) or $...$ (scored as text).
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
- Inline math: use \( ... \).
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

_READINGS = {"base": _READING_BASE, "v2": _READING_BASE}
_TABLES = {"base": _TABLES_BASE, "v2": _TABLES_V2}


def get_user_prompt(variant="v2"):
    r = _READINGS.get(variant, _READING_BASE)
    t = _TABLES.get(variant, _TABLES_BASE)
    return USER_PROMPT.replace("__READING__", r).replace("__TABLES__", t)


# Precompute for convenience / validation.
PROMPTS = {v: get_user_prompt(v) for v in ("base", "v2")}
