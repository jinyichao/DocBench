"""Post-process: move marginal verse line-numbers into their own blocks.

Scholarly verse editions print a line number in the margin every Nth line (4032,
4036, 4040...). Ground truth annotates each of those numbers as its OWN text_block,
spatially separate from the verse. Our transcription appends them inline to the end
of the verse line, so the number ends up inside the verse block -- which both
corrupts that block's text and costs a reading-order element.

Guards (each one added because it removed a measured false positive):
  * >=3 numbers, strictly increasing, constant stride -- a real line-number sequence
  * stride >= 2 -- verse marks every Nth line; a stride of 1 is a table of contents
  * numbers on <= 50% of lines -- TOC/index pages number nearly every line
  * no dot-leaders ('....') on the numbered lines -- that is a TOC, not verse

Dev A/B (200-page sample): fires on exactly 1 page, the genuine verse page, with
Reading_Order 0.889 -> 0.000 and Text_ED 0.675 -> 0.642; 0 regressions.
    baseline  Text_ED 0.0785  Reading_Order 0.1042  Overall-proxy 85.32
    with rule Text_ED 0.0780  Reading_Order 0.0993  Overall-proxy 85.45

Usage:
    python src/extract_verse_numbers.py --run <run> --out <newrun> [--dry-run]
"""
import argparse, glob, os, re, shutil
from pathlib import Path

NUM = re.compile(r'\s+(\d{3,5})\s*$')
DOT_LEADER = re.compile(r'\.{3,}')


def _is_verse_numbering(nums, n_lines):
    if len(nums) < 3:
        return False
    v = [int(x) for x in nums]
    if any(b <= a for a, b in zip(v, v[1:])):
        return False                              # must be strictly increasing
    d = [b - a for a, b in zip(v, v[1:])]
    if len(set(d)) != 1 or not (2 <= d[0] <= 10):
        return False                              # constant stride, and NOT stride 1 (TOC)
    return len(nums) <= 0.5 * n_lines             # only a minority of lines are numbered


def extract_verse_numbers(text: str) -> str:
    out = []
    for block in text.split('\n\n'):
        lines = block.split('\n')
        if len(lines) >= 4 and not block.lstrip().startswith(('<', '|', '```', '#')):
            numbered = [l for l in lines if NUM.search(l)]
            if numbered and not any(DOT_LEADER.search(l) for l in numbered):
                nums = [NUM.search(l).group(1) for l in numbered]
                if _is_verse_numbering(nums, len(lines)):
                    stripped = []
                    for l in lines:
                        m = NUM.search(l)
                        stripped.append(l[:m.start()].rstrip() if m else l)
                    out.append('\n'.join(stripped))
                    out.extend(nums)
                    continue
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
        nt = extract_verse_numbers(t)
        if nt != t:
            n += 1
            print(f"  {'would fix' if a.dry_run else 'fixed'}: {p.split('/mds/')[1]}")
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
