"""Central configuration for the Dr.DocBench pipeline."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "DrDocBench"
DEV_DIR = DATA_DIR / "dev"
TEST_DIR = DATA_DIR / "test"          # populated from the EvalAI package
OUTPUTS_DIR = ROOT / "outputs"
SUBMISSIONS_DIR = ROOT / "submissions"

# --- Image encoding (shared by both backends) ---
# Long-edge to which page images are resized before upload (px). Keeps tokens/cost
# bounded while staying legible. 0 = no resize.
IMAGE_MAX_EDGE = int(os.environ.get("DRDOC_IMAGE_MAX_EDGE", "2000"))
# Upscale small images UP to IMAGE_MAX_EDGE (Lanczos) so dense/low-res scans get more
# visual tokens from the VLM encoder. Dev-validated net-positive across table, dense,
# and sparse pages (2026-08-26). 1 = upscale, 0 = only downscale (legacy).
IMAGE_UPSCALE = int(os.environ.get("DRDOC_IMAGE_UPSCALE", "1"))
# JPEG encode quality + chroma subsampling. q100/subsampling=0 preserves small-glyph
# detail; dev-validated flat-to-positive vs q90 on dense pages (token cost unchanged —
# billing is by resolution, not file size).
IMAGE_JPEG_QUALITY = int(os.environ.get("DRDOC_IMAGE_JPEG_QUALITY", "100"))
IMAGE_JPEG_SUBSAMPLING = int(os.environ.get("DRDOC_IMAGE_JPEG_SUBSAMPLING", "0"))
CONCURRENCY = int(os.environ.get("DRDOC_CONCURRENCY", "6"))
MAX_RETRIES = int(os.environ.get("DRDOC_MAX_RETRIES", "5"))


# --- Qwen (DashScope, OpenAI-compatible) primary backend ---
QWEN_MODEL = os.environ.get("DRDOC_QWEN_MODEL", "qwen3.8-max")
QWEN_BASE_URL = os.environ.get(
    "DRDOC_QWEN_BASE_URL",
    "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
)
QWEN_MAX_TOKENS = int(os.environ.get("DRDOC_QWEN_MAX_TOKENS", "8192"))

# Prompt variant: "base" or "v2" (table-boosted, +5 TEDS on dev). See src/prompt.py.
PROMPT_VARIANT = os.environ.get("DRDOC_PROMPT", "v2")

# --- Gemini (Google, OpenAI-compatible) ensemble backend ---
# Routed to table pages (wins TEDS) and used to recover pages DashScope's content
# filter hard-blocks (data_inspection_failed).
GEMINI_MODEL = os.environ.get("DRDOC_GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_BASE_URL = os.environ.get(
    "DRDOC_GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
GEMINI_MAX_TOKENS = int(os.environ.get("DRDOC_GEMINI_MAX_TOKENS", "16000"))


def get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    keyfile = ROOT / "secrets" / "gemini_key.txt"
    if keyfile.exists():
        return keyfile.read_text().strip()
    raise RuntimeError("No Gemini key. Set GEMINI_API_KEY or write secrets/gemini_key.txt")


def get_qwen_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    keyfile = ROOT / "secrets" / "qwen_key.txt"
    if keyfile.exists():
        return keyfile.read_text().strip()
    raise RuntimeError(
        "No Qwen/DashScope API key found. Set DASHSCOPE_API_KEY or write it to "
        f"{keyfile}"
    )
