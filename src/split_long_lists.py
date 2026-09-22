"""Post-process: split long-item enumerated lists into one block per item.

The scorer (vendor/DrDocBench/utils/extract.py::md_tex_filter) segments a page on
blank lines, so a markdown list emitted as consecutive single-newline lines becomes
ONE block. When the ground truth annotates each item separately, our single block can
match only one GT item and the rest count as unmatched deletions -- expensive for both
Text_ED and Reading_Order.

Whether GT splits a list is NOT determined by the marker type (bullet vs number vs
letter) -- measured on the dev set, it is determined by ITEM LENGTH:

    GT kept as ONE block : mean item length  p25=27  median=56   p75=80   (n=33)
    GT split PER ITEM    : mean item length  p25=93  median=109  p75=116  (n=20)

So this only fires when the mean marked-item length is >= --min-len (default 110),
which is the regime where GT genuinely splits. An ungated version of this rule was
measured and is strictly worse (it fires on 18 dev files and regresses several);
gating at 110 gave 3 improvements and ZERO regressions on both metrics.

Dev A/B (200-page sample, 185 scored):
    baseline    Text_ED 0.078  Reading_Order 0.104  Overall-proxy 85.32
    gated >=110 Text_ED 0.071  Reading_Order 0.097  Overall-proxy 85.68

The edit is pure whitespace: no characters are added or removed, only blank lines
inserted between list items.

Usage:
    python src/split_long_lists.py --run test_ensemble_q100_audited --out test_pp_g110
"""
import argparse, glob, os, re, shutil, statistics
from pathlib import Path

MARK = re.compile(r'^\s*([-*•]|\d+[.)]|[a-zA-Z][.)])\s+\S')


def split_long_enumerated(text: str, min_len: int) -> str:
    out = []
    for block in text.split('\n\n'):
        lines = block.split('\n')
        marked = [l for l in lines if MARK.match(l)]
        if (len(lines) >= 3 and len(marked) >= 2
                and statistics.mean(len(l) for l in marked) >= min_len):
            cur = []
            for l in lines:
                if MARK.match(l) and cur:
                    out.append('\n'.join(cur)); cur = [l]
                else:
                    cur.append(l)
            if cur:
                out.append('\n'.join(cur))
        else:
            out.append(block)
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-len', type=int, default=110)
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
        nt = split_long_enumerated(t, a.min_len)
        if nt != t:
            n += 1
            print(f"  {'would split' if a.dry_run else 'split'}: {p.split('/mds/')[1]}")
            if not a.dry_run:
                Path(p).write_text(nt, encoding='utf-8')

    if not a.dry_run:
        # index.jsonl stores md_path per page; repoint it at the new run or
        # build_submission.py will silently package the ORIGINAL files.
        idx = Path(f'{dst}/index.jsonl')
        if idx.exists():
            idx.write_text(idx.read_text(encoding='utf-8').replace(
                f'outputs/{a.run}/', f'outputs/{a.out}/'), encoding='utf-8')
    print(f"{n} files {'would be ' if a.dry_run else ''}modified (min-len={a.min_len})")


if __name__ == '__main__':
    main()
