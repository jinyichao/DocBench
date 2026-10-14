import sys, io, base64, json
sys.path.insert(0, 'src')
import config, parse_page_qwen as Q
from PIL import Image
IMG = 'data/DrDocBench/test/LANGUAGEARTS&DISCIPLINES/6a1ab132-d620-4744-a221-a872044634a5/images/page_86.jpg'
P = ("This crop shows part of a reproduced newsletter page printed in a book. Transcribe ALL readable body text and "
     "captions exactly as printed, column by column (left column first), keeping paragraphs. Skip text you cannot read "
     "confidently instead of guessing. Plain text only, no commentary. Separate paragraphs with a blank line.")
im = Image.open(IMG).convert('RGB'); W, H = im.size
boxes = {'top_left': (0.08, 0.02, 0.50, 0.47), 'top_right': (0.50, 0.02, 0.92, 0.47),
         'art_1': (0.10, 0.49, 0.38, 0.77), 'art_2': (0.36, 0.49, 0.64, 0.77), 'art_3': (0.62, 0.49, 0.90, 0.77)}
client = Q.make_client(); out = {}
for k, (a, b, c, d) in boxes.items():
    cr = im.crop((int(a * W), int(b * H), int(c * W), int(d * H))); s = 2400 / max(cr.size)
    cr = cr.resize((round(cr.width * s), round(cr.height * s)), Image.LANCZOS)
    buf = io.BytesIO(); cr.save(buf, format='JPEG', quality=100, subsampling=0)
    url = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    r = client.chat.completions.create(model=config.QWEN_MODEL, max_tokens=6000, extra_body={'enable_thinking': False},
        messages=[{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': url}}, {'type': 'text', 'text': P}]}])
    out[k] = r.choices[0].message.content or ''; print('==', k, len(out[k])); print(out[k][:700])
json.dump(out, open('outputs/work/p86_read.json', 'w'), ensure_ascii=False)
