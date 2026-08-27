"""Qwen (DashScope, OpenAI-compatible) backend: one page image -> Markdown.

Uses model config.QWEN_MODEL (default qwen3.8-max) via the DashScope
international OpenAI-compatible endpoint. Shares the scorer-tuned prompt in
prompt.py so output conventions match the api backend.
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
    # Downscale if larger than max_edge; optionally UPSCALE small/low-res scans up to
    # max_edge so dense text clears the VLM encoder's visual-token floor (dev-validated).
    if max_edge and (max(img.size) > max_edge
                     or (config.IMAGE_UPSCALE and max(img.size) < max_edge)):
        scale = max_edge / max(img.size)
        img = img.resize((round(img.size[0] * scale), round(img.size[1] * scale)),
                         Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=config.IMAGE_JPEG_QUALITY,
                            subsampling=config.IMAGE_JPEG_SUBSAMPLING)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _strip_fenced_wrapper(text):
    t = text.strip()
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
    # Per-request timeout so a hung connection (more common with larger upscaled
    # payloads) aborts and retries instead of blocking a worker indefinitely.
    return OpenAI(api_key=config.get_qwen_key(), base_url=config.QWEN_BASE_URL,
                  timeout=120.0, max_retries=0)


def parse_page(client, image_path, model=None, max_tokens=None):
    """Return (markdown, usage_dict) for one page image via Qwen."""
    model = model or config.QWEN_MODEL
    max_tokens = max_tokens or config.QWEN_MAX_TOKENS
    user_prompt = get_user_prompt(config.PROMPT_VARIANT)
    data_url = _encode_image_dataurl(image_path)

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
                # Disable Qwen internal reasoning: faster + cheaper, and parsing
                # doesn't benefit from a hidden scratchpad.
                extra_body={"enable_thinking": False},
            )
            md = _strip_fenced_wrapper(resp.choices[0].message.content or "")
            u = resp.usage
            usage = {
                "input_tokens": getattr(u, "prompt_tokens", 0),
                "output_tokens": getattr(u, "completion_tokens", 0),
                "stop_reason": resp.choices[0].finish_reason,
            }
            return md, usage
        except Exception as e:  # noqa: BLE001 - broad retry on transient API errors
            last_err = e
            msg = str(e)
            # Non-retryable content-safety / bad-request 400s: DashScope hard-blocks
            # some images (data_inspection_failed). Don't burn retries — return empty
            # markdown so the page is still written (scores 0, submission stays complete).
            if "data_inspection_failed" in msg or "DataInspectionFailed" in msg:
                return "", {"input_tokens": 0, "output_tokens": 0,
                            "stop_reason": "content_filter"}
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"qwen parse_page failed for {image_path}: {last_err}")
