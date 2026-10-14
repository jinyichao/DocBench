"""Qwen (Token Plan) page audit: image + our markdown -> JSON list of concrete suspected issues.
usage: python qwen_audit.py <predictions.jsonl> <out.json> [limit] [pages-file]"""
import json, os, sys, time, re
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, 'src')
import config
from parse_page_qwen import make_client, _encode_image_dataurl

PROMPT = """You are auditing a Markdown transcription of the scanned book page shown in the image.
Conventions the transcription MUST follow:
- Running heads (book/chapter title repeated in the margin), page numbers and page footers go at the VERY END
  of the transcription (running-head text first, then the page number). They must NOT appear at the start.
- A section or chapter title printed at the top of the body text belongs at the START, in reading order.
- Text that is part of a photograph, illustration, map, instrument/computer screen, sticker, stamp or a
  scribbled/masked area should NOT be transcribed. Printed captions, labels and chart text SHOULD be.
- Multi-column pages are transcribed column by column (top to bottom, then next column).
- Tabular data should be an HTML table; ordinary prose/lists should be text.
Find CONCRETE problems only (do not nitpick punctuation, spacing, bold/italic or markdown style):
  "missing"   : printed text clearly visible on the page that is absent from the transcription (quote it)
  "extra"     : transcribed text that is not printed text on the page or sits inside a photo/screen/sticker
  "misplaced" : running head / page number / footer not at the end, or a title not at the start, or blocks
                out of reading order
  "format"    : table that should be text, or text that should be a table
  "misread"   : a word or number transcribed wrongly (give the wrong and the correct form)
Return ONLY JSON: {"issues": [{"type": ..., "snippet": "<short quote from transcription or page>",
"fix": "<what should change>"}]}. Return {"issues": []} if the transcription is fine.

Transcription:
"""


def audit(client, img, md):
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model=config.QWEN_MODEL, max_tokens=2000,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": _encode_image_dataurl(img)}},
                    {"type": "text", "text": PROMPT + md[:24000]}]}],
                extra_body={"enable_thinking": False}, response_format={"type": "json_object"})
            t = resp.choices[0].message.content or ''
            m = re.search(r'\{.*\}', t, re.S)
            return json.loads(m.group(0)) if m else {'issues': [], 'raw': t[:300]}
        except Exception as e:  # noqa: BLE001
            err = str(e)
            if 'data_inspection_failed' in err: return {'issues': [], 'error': 'content_filter'}
            time.sleep(2 ** attempt)
    return {'issues': [], 'error': 'failed'}


if __name__ == '__main__':
    pred, out = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    only = set(l.strip() for l in open(sys.argv[4])) if len(sys.argv) > 4 else None
    res = json.load(open(out)) if os.path.exists(out) else {}
    R = [json.loads(l) for l in open(pred)]
    todo = []
    for r in R:
        key = f"{r['subject']}/{r['document_id']}/{r['page']}"
        if key in res or (only and key not in only): continue
        if not r['markdown'].strip(): continue
        img = f"data/DrDocBench/test/{r['subject']}/{r['document_id']}/images/page_{r['page']}.jpg"
        todo.append((key, img, r['markdown']))
    todo = todo[:limit]
    client = make_client(); done = 0
    def work(t):
        return t[0], audit(client, t[1], t[2])
    with ThreadPoolExecutor(6) as ex:
        for key, a in ex.map(work, todo):
            res[key] = a; done += 1
            if done % 25 == 0: json.dump(res, open(out, 'w'), ensure_ascii=False); print(done, len(todo), flush=True)
    json.dump(res, open(out, 'w'), ensure_ascii=False); print('done', done)
