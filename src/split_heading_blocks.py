"""Post-process: separate a leading heading line from the body text that follows it.

The scorer segments on blank lines. When the model emits a heading and its body as
consecutive single-newline lines, they become ONE block -- but ground truth annotates
the heading and the body as separate blocks. Our single block can then match only one
of them, and the other counts as an unmatched deletion (expensive for Text_ED and
Reading_Order alike).

A "heading line" here is a whole line that is either a markdown heading (`# ... ######`)
or entirely bold (`**...**`, optionally as a list item `* **...**`). Partial emphasis
such as `**Note:** blah` does NOT match, because the bold must span the whole line.

Measured on the 200-page dev sample (on top of split_long_lists), real vendor scorer:
    before  Text_ED 0.071  Reading_Order 0.097  Overall-proxy 85.68
    after   Text_ED 0.068  Reading_Order 0.087  Overall-proxy 86.01
Per-page: Reading_Order 6 improved / 0 regressed; Text_ED 9 improved / 4 regressed
(gain 0.633 vs loss 0.117). 31 dev files / 59 test files touched; edits are pure
whitespace -- no characters are added or removed.

A guarded variant (only split when >=80 or >=120 chars of body with sentence
punctuation follows) was tested and is WORSE (proxy 85.96): the guard drops winners
such as `## ACROSS` / `## DOWN` crossword clue lists, whose bodies have no sentence
punctuation. Ungated is correct -- do not add that guard back.

Usage:
    python src/split_heading_blocks.py --run <run> --out <newrun> [--dry-run]
"""
import argparse, glob, os, re, shutil
from pathlib import Path

HEAD = re.compile(r'^\s*(#{1,6}\s+\S.*|\*\*[^*]+\*\*|\*\s+\*\*[^*]+\*\*)\s*$')


def split_heading_blocks(text: str) -> str:
    out = []
    for block in text.split('\n\n'):
        lines = block.split('\n')
        if len(lines) >= 2 and HEAD.match(lines[0]) and lines[1].strip():
            rest = '\n'.join(lines[1:]).strip()
            out.append(lines[0])
            if rest:
                out.append(rest)
        else:
            out.append(block)
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src, dst = f'outputs/{a.run}', f'outputs/{a.out}'
    if not a.dry_run:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    target = src if a.dry_run else dst
    n = 0
    for p in sorted(glob.glob(f'{target}/mds/*/*/*.md')):
        t = Path(p).read_text(encoding='utf-8')
        nt = split_heading_blocks(t)
        if nt != t:
            n += 1
            if not a.dry_run:
                Path(p).write_text(nt, encoding='utf-8')
    if not a.dry_run:
        idx = Path(f'{dst}/index.jsonl')
        if idx.exists():
            idx.write_text(idx.read_text(encoding='utf-8').replace(
                f'outputs/{a.run}/', f'outputs/{a.out}/'), encoding='utf-8')
    print(f"{n} files {'would be ' if a.dry_run else ''}modified")


if __name__ == '__main__':
    main()
