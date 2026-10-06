"""
Cấu hình toàn cục cho ứng dụng AI Học Tập
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Đường dẫn ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
# ── LLM API Providers ────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL     = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")   # Model hoạt động ổn định trên Groq

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# ── Upload ─────────────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".pptx", ".ipynb", ".txt"]
MAX_FILE_SIZE_MB   = 20

# ── LLM params ─────────────────────────────────────────────────────────────────
LLM_TEMPERATURE        = 0.3
LLM_MAX_TOKENS         = 4096
LLM_EXTRACTION_TOKENS  = 6000

# ── App metadata ────────────────────────────────────────────────────────────────
APP_NAME    = "📚 AI Học Tập – Lấy Lại Gốc"
APP_VERSION = "1.0.0"
