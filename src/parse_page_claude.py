"""Claude (Anthropic SDK) backend: page image -> Markdown.

Same scorer-tuned prompt (prompt.py) and image encoding (upscale to IMAGE_MAX_EDGE, JPEG q100)
as the Qwen/Gemini backends. Claude Opus 5.5 cannot disable thinking, so depth is set with
`output_config.effort` (default "low" here to limit billed thinking tokens).

Credentials: ANTHROPIC_API_KEY env var, else secrets/claude_key.txt, else the SDK's own
resolution (ANTHROPIC_AUTH_TOKEN / `ant auth login` profile).
"""
import base64
import io
import os
import time

import anthropic
from PIL import Image

from prompt import SYSTEM_PROMPT, get_user_prompt
import config

DEFAULT_MODEL = os.environ.get("DRDOC_CLAUDE_MODEL", "claude-opus-5-5")
MAX_TOKENS = int(os.environ.get("DRDOC_CLAUDE_MAX_TOKENS", "16000"))
EFFORT = os.environ.get("DRDOC_CLAUDE_EFFORT", "low")


def _encode_image_b64(path, max_edge=config.IMAGE_MAX_EDGE):
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
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


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


def build_request(image_path, model=None, max_tokens=None):
    """Messages API params for one page (shared by live calls, token counting and batches)."""
    return {
        "model": model or DEFAULT_MODEL,
        "max_tokens": max_tokens or MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "output_config": {"effort": EFFORT},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": _encode_image_b64(image_path)}},
                {"type": "text", "text": get_user_prompt(config.PROMPT_VARIANT)},
            ],
        }],
    }


def make_client():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    keyfile = config.ROOT / "secrets" / "claude_key.txt"
    if not key and keyfile.exists():
        key = keyfile.read_text().strip()
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def parse_page(client, image_path, model=None, max_tokens=None):
    params = build_request(image_path, model, max_tokens)
    last_err = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = client.messages.create(**params)
            text = "".join(b.text for b in resp.content if b.type == "text")
            usage = {
                "input_tokens": resp.usage.input_tokens,
                # output_tokens includes billed thinking tokens
                "output_tokens": resp.usage.output_tokens,
                "stop_reason": resp.stop_reason,
            }
            if resp.stop_reason == "refusal":
                return "", usage
            return _strip_fenced_wrapper(text), usage
        except (anthropic.BadRequestError, anthropic.AuthenticationError,
                anthropic.PermissionDeniedError, anthropic.NotFoundError):
            raise
        except (anthropic.RateLimitError, anthropic.APIStatusError,
                anthropic.APIConnectionError) as e:
            last_err = e
            time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"claude parse_page failed for {image_path}: {last_err}")
