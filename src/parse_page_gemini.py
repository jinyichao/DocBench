"""Gemini (Google, OpenAI-compatible) fallback backend: page image -> Markdown.

Used only for pages DashScope's content filter hard-blocks. Shares the same
scorer-tuned prompt (prompt.py) as the primary Qwen backend.
"""
import base64
import io
import time

from PIL import Image

from prompt import SYSTEM_PROMPT, get_user_prompt
import config


def _encode_image_dataurl(path, max_edge=config.IMAGE_MAX_EDGE):
    img = Image.open(path)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max_edge and (max(img.size) > max_edge
                     or (config.IMAGE_UPSCALE and max(img.size) < max_edge)):
        scale = max_edge / max(img.size)
        img = img.resize((round(img.size[0] * scale), round(img.size[1] * scale)),
                         Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=config.IMAGE_JPEG_QUALITY,
                            subsampling=config.IMAGE_JPEG_SUBSAMPLING)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _strip_fenced_wrapper(text):
    t = (text or "").strip()
    if t.startswith("```"):
        nl = t.find("\n")
        if nl != -1 and t[3:nl].strip().lower() in ("", "markdown", "md"):
            body = t[nl + 1:]
            if body.rstrip().endswith("```"):
                body = body.rstrip()[:-3]
            return body.strip()
    return t


def make_client():
    from openai import OpenAI
    return OpenAI(api_key=config.get_gemini_key(), base_url=config.GEMINI_BASE_URL)


def parse_page(client, image_path, model=None, max_tokens=None):
    model = model or config.GEMINI_MODEL
    max_tokens = max_tokens or config.GEMINI_MAX_TOKENS
    data_url = _encode_image_dataurl(image_path)
    user_prompt = get_user_prompt(config.PROMPT_VARIANT)

    last_err = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": user_prompt},
                    ]},
                ],
            )
            md = _strip_fenced_wrapper(resp.choices[0].message.content)
            u = resp.usage
            usage = {
                "input_tokens": getattr(u, "prompt_tokens", 0),
                "output_tokens": getattr(u, "completion_tokens", 0),
                "stop_reason": resp.choices[0].finish_reason,
            }
            return md, usage
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"gemini parse_page failed for {image_path}: {last_err}")
