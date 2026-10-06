"""
LLM client đa nhà cung cấp: Gemini -> Groq -> OpenRouter (model ':free').
- Nhớ trạng thái hết quota trên đĩa (quota_state.json), bỏ qua model đang bị khóa.
- Phân loại lỗi 429 theo phút (chờ rồi thử lại) và theo ngày (khóa, chuyển model khác).
- Sửa JSON cục bộ trước khi (tối đa 1 lần) gọi lại LLM.
"""
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError
from dotenv import load_dotenv

load_dotenv()

import core.storage as storage
from core.schemas import KnowledgeItem

logger = logging.getLogger(__name__)

# Giới hạn ký tự mỗi request theo nhà cung cấp
GEMINI_MAX_CHARS = 30000
GROQ_MAX_CHARS = 9000
OPENROUTER_MAX_CHARS = 60000

MAX_MINUTE_WAIT = 120          # giây: chờ nếu retryDelay nhỏ hơn mức này
FINAL_MESSAGE = ("Hôm nay hết lượt miễn phí ở mọi nguồn, các tài liệu đã lưu vẫn xem bình thường, "
                 "thử lại sau {h} giờ.")


class LLMUnavailable(Exception):
    """Mọi nguồn đều hết lượt hoặc lỗi. Message đã là tiếng Việt, hiển thị thẳng cho người dùng."""


# ── Tiện ích chung ────────────────────────────────────────────────────────────

def _fill(template: str, **kwargs) -> str:
    """Thay {key} an toàn (không bị lỗi bởi dấu { } của JSON schema trong prompt)."""
    out = template
    for k, v in kwargs.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _is_model_available(model_name: str) -> bool:
    state = storage.get_quota_state()
    info = state.get(model_name)
    if not info:
        return True
    if time.time() < info.get("unlock_time", 0):
        return False
    storage.reset_quota(model_name)
    return True


def _parse_retry_seconds(err: str) -> float:
    """Lấy thời gian chờ gợi ý từ thông báo lỗi 429 (giây). 0 nếu không tìm thấy."""
    m = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s", err)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(\d+(?:\.\d+)?)s", err)
    if m:
        h, mi, s = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(s)
    return 0.0


def _classify(err: str) -> str:
    """Trả về: 'day' | 'minute' | 'toolarge' | 'overload' | 'notfound' | 'auth' | 'other'."""
    low = err.lower()
    if "429" in err or "resource_exhausted" in low or "rate limit" in low or "rate_limit" in low:
        delay = _parse_retry_seconds(err)
        if "PerDay" in err or "per day" in low or delay >= MAX_MINUTE_WAIT:
            return "day"
        return "minute"
    if "413" in err or "too large" in low or "tokens per minute" in low or "request_too_large" in low:
        return "toolarge"
    if "503" in err or "overloaded" in low or "unavailable" in low or "high demand" in low:
        return "overload"
    if "404" in err or "not_found" in low or "no longer available" in low:
        return "notfound"
    if "401" in err or "403" in err or "permission" in low or "api key" in low:
        return "auth"
    return "other"


# ── Sửa JSON cục bộ ───────────────────────────────────────────────────────────

def _repair_json(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", (raw or "").strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned


def _parse_json_local(raw: str) -> Dict:
    """Thử parse, tự sửa các lỗi thường gặp (\\ sai, dấu phẩy thừa). Ném ValueError nếu không được."""
    text = _repair_json(raw)
    attempts = [
        text,
        re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text),               # \alpha, \sum... chưa escape
        re.sub(r",\s*([}\]])", r"\1", re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)),
    ]
    last = None
    for t in attempts:
        try:
            data = json.loads(t)
            if isinstance(data, (dict, list)):
                return {"items": data} if isinstance(data, list) else data
        except json.JSONDecodeError as e:
            last = e
    raise ValueError(f"JSON không hợp lệ: {last}")


def _call_with_json_repair(api_call_fn, prompt: str) -> Dict:
    """Gọi API; lỗi JSON thì sửa cục bộ, chưa được mới gọi lại LLM đúng 1 lần."""
    try:
        return _parse_json_local(api_call_fn(prompt))
    except ValueError:
        retry_prompt = prompt + "\n\n(LƯU Ý: lần trước JSON bị lỗi. Chỉ trả JSON hợp lệ, escape dấu \\ thành \\\\.)"
        return _parse_json_local(api_call_fn(retry_prompt))


# ── Gemini ────────────────────────────────────────────────────────────────────

_GEMINI_MODELS: List[str] = []
_GEMINI_MODELS_AT = 0.0
_GEMINI_FALLBACK = ["gemini-flash-lite-latest", "gemini-flash-latest"]
_EXCLUDE = ("embedding", "tts", "image", "live", "robotics", "computer", "audio", "aqa", "veo", "imagen")


def _get_gemini_models(api_key: str) -> List[str]:
    """Lấy model thật từ API, chỉ giữ model hỗ trợ generateContent; flash-lite trước, rồi flash."""
    global _GEMINI_MODELS, _GEMINI_MODELS_AT
    if _GEMINI_MODELS and time.time() - _GEMINI_MODELS_AT < 3600:
        return _GEMINI_MODELS
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        names = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            if actions and "generateContent" not in actions:
                continue
            name = m.name.replace("models/", "")
            if not name.startswith("gemini") or any(x in name for x in _EXCLUDE):
                continue
            names.append(name)
        lite = [n for n in names if "flash-lite" in n]
        flash = [n for n in names if "flash" in n and "lite" not in n]
        ordered = (lite + flash)[:8]
        _GEMINI_MODELS = ordered or _GEMINI_FALLBACK
    except Exception as e:
        logger.warning(f"Không lấy được danh sách model Gemini: {e}")
        _GEMINI_MODELS = _GEMINI_FALLBACK
    _GEMINI_MODELS_AT = time.time()
    return _GEMINI_MODELS


def _call_gemini(key: str, model: str, sys_p: str, usr_p: str) -> Dict:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        system_instruction=sys_p,
        temperature=0.3,
        response_mime_type="application/json",
    )
    return _call_with_json_repair(
        lambda p: client.models.generate_content(model=model, contents=p, config=config).text or "",
        usr_p,
    )


# ── Groq ──────────────────────────────────────────────────────────────────────

def _groq_models() -> List[str]:
    models = []
    env_model = os.environ.get("GROQ_MODEL", "").strip()
    if env_model:
        models.append(env_model)
    for m in ("llama-3.3-70b-versatile", "openai/gpt-oss-20b", "llama-3.1-8b-instant"):
        if m not in models:
            models.append(m)
    return models


def _call_groq(key: str, model: str, sys_p: str, usr_p: str) -> Dict:
    from groq import Groq
    client = Groq(api_key=key)

    def call_fn(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    return _call_with_json_repair(call_fn, usr_p)


# ── OpenRouter ────────────────────────────────────────────────────────────────

_OR_MODELS: List[str] = []
_OR_MODELS_AT = 0.0


def _get_openrouter_free_models(key: str) -> List[str]:
    global _OR_MODELS, _OR_MODELS_AT
    if _OR_MODELS and time.time() - _OR_MODELS_AT < 3600:
        return _OR_MODELS
    fallback = ["meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-27b-it:free"]
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                     headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        free = [m for m in data.get("data", []) if str(m.get("id", "")).endswith(":free")]
        free.sort(key=lambda m: m.get("context_length", 0), reverse=True)
        _OR_MODELS = [m["id"] for m in free] or fallback
    except Exception as e:
        logger.warning(f"Không lấy được model OpenRouter: {e}")
        _OR_MODELS = fallback
    _OR_MODELS_AT = time.time()
    return _OR_MODELS


def _call_openrouter(key: str, model: str, sys_p: str, usr_p: str) -> Dict:
    def call_fn(prompt: str) -> str:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": prompt}],
            "temperature": 0.3,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{e.code} {e.read().decode('utf-8', 'ignore')[:300]}")
        return out["choices"][0]["message"]["content"] or ""

    return _call_with_json_repair(call_fn, usr_p)


# ── Điều phối chuỗi dự phòng ──────────────────────────────────────────────────

def _get_api_keys() -> Dict[str, str]:
    """Lấy API keys từ session_state (nếu có người dùng tự nhập) hoặc từ os.environ."""
    keys = {}
    try:
        from streamlit import session_state as st_state
        if "api_keys" in st_state:
            keys = st_state["api_keys"]
    except ImportError:
        pass
    return keys

def _provider_chain() -> List[Tuple[str, List[str], Any, int]]:
    """[(tên nhà cung cấp, danh sách model, hàm gọi, giới hạn ký tự)] theo thứ tự ưu tiên."""
    chain = []
    keys = _get_api_keys()
    
    gkey = keys.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "").strip()
    if gkey:
        chain.append(("Gemini", _get_gemini_models(gkey), lambda m, s, u, k=gkey: _call_gemini(k, m, s, u),
                      GEMINI_MAX_CHARS))
    
    qkey = keys.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "").strip()
    if qkey:
        chain.append(("Groq", _groq_models(), lambda m, s, u, k=qkey: _call_groq(k, m, s, u), GROQ_MAX_CHARS))
        
    okey = keys.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if okey:
        chain.append(("OpenRouter", _get_openrouter_free_models(okey)[:6],
                      lambda m, s, u, k=okey: _call_openrouter(k, m, s, u), OPENROUTER_MAX_CHARS))
    return chain


def has_any_key() -> bool:
    keys = _get_api_keys()
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        if keys.get(k) or os.environ.get(k, "").strip():
            return True
    return False


def call_llm(system_prompt: str, user_prompt: str) -> Tuple[Dict, str]:
    """Thử lần lượt các nguồn. Trả về (json_dict, "nhà cung cấp/model"). Ném LLMUnavailable nếu hết cách."""
    chain = _provider_chain()
    if not chain:
        raise LLMUnavailable("Chưa cấu hình API Key. Hãy thêm GEMINI_API_KEY, GROQ_API_KEY hoặc "
                             "OPENROUTER_API_KEY vào file .env.")

    total_len = len(system_prompt) + len(user_prompt)
    for provider, models, call_fn, max_chars in chain:
        if total_len > max_chars + 6000:   # prompt hệ thống ~ vài nghìn ký tự
            continue
        for model in models:
            if not _is_model_available(f"{provider}:{model}"):
                continue
            tag = f"{provider}:{model}"
            for attempt in (1, 2):
                try:
                    return call_fn(model, system_prompt, user_prompt), tag
                except Exception as e:
                    err = str(e)
                    kind = _classify(err)
                    delay = _parse_retry_seconds(err)
                    if kind == "minute" and attempt == 1:
                        time.sleep(min(max(delay, 5), MAX_MINUTE_WAIT) + 1)   # chờ rồi thử lại 1 lần
                        continue
                    if kind in ("day", "minute"):
                        storage.update_quota_state(tag, wait_seconds=int(delay) if delay else 0, is_day_ban=True) \
                            if kind == "day" else storage.update_quota_state(tag, wait_seconds=300)
                    elif kind == "toolarge":
                        storage.update_quota_state(tag, wait_seconds=120)
                    elif kind == "overload":
                        storage.update_quota_state(tag, wait_seconds=120)
                    elif kind == "notfound":
                        storage.update_quota_state(tag, wait_seconds=6 * 3600)
                    elif kind == "auth":
                        storage.update_quota_state(tag, wait_seconds=3600)
                    else:
                        storage.update_quota_state(tag, wait_seconds=600)
                        logger.warning(f"{tag} lỗi: {err[:200]}")
                    break

    hours = storage.earliest_unlock_hours()
    raise LLMUnavailable(FINAL_MESSAGE.format(h=max(1, round(hours))) if hours else
                         "Không gọi được AI ở bất kỳ nguồn nào. Vui lòng thử lại sau ít phút.")


def estimate_extraction(texts: List[str]) -> Tuple[int, str]:
    """(số request ước tính, nhãn model sẽ dùng) để hiển thị trước khi chạy."""
    n = sum(len(_chunk_text(t, GEMINI_MAX_CHARS)) for t in texts)
    for provider, models, _, _ in _provider_chain():
        for m in models:
            if _is_model_available(f"{provider}:{m}"):
                return n, f"{provider}:{m}"
    return n, "chưa có model khả dụng"


# ── Trích xuất kiến thức ──────────────────────────────────────────────────────

_STR_FIELDS = ("title", "plain", "analogy", "formula_latex", "formula_words", "example", "pitfall", "exam_tip")
_LIST_FIELDS = ("prereq", "steps", "keywords")


def _fix_latex_escapes(s: str) -> str:
    """JSON hiểu nhầm \\beta -> backspace+eta, \\frac -> formfeed+rac, \\times -> tab+imes... Khôi phục lại."""
    if not s:
        return s
    s = s.replace("\x08", "\\b").replace("\x0c", "\\f").replace("\t", "\\t").replace("\r", "\\r")
    s = re.sub(r"\n(?=[a-zA-Z])", r"\\n", s)
    return s


def _normalize_item(raw: Dict) -> Dict:
    item = dict(raw)
    for f in _STR_FIELDS:
        v = item.get(f)
        item[f] = "" if v is None else str(v)
    for f in _LIST_FIELDS:
        v = item.get(f)
        item[f] = [str(x) for x in v] if isinstance(v, list) else ([] if v in (None, "") else [str(v)])
    syms = []
    for s in item.get("symbols") or []:
        if isinstance(s, dict) and s.get("symbol"):
            syms.append({"symbol": _fix_latex_escapes(str(s["symbol"])), "meaning": str(s.get("meaning", ""))})
    item["symbols"] = syms
    item["formula_latex"] = _fix_latex_escapes(item["formula_latex"])
    if item.get("type") not in ("formula", "concept", "process", "fact", "compare"):
        item["type"] = "formula" if item["formula_latex"] else "concept"
    return item


def extract_knowledge(text: str) -> Tuple[List[Dict], str]:
    """Trích xuất kiến thức từ một tài liệu. Trả về (danh sách mục, model đã dùng)."""
    from core.prompts import EXTRACTION_SYSTEM, EXTRACTION_USER

    chunks = _chunk_text(text, GEMINI_MAX_CHARS)
    all_items: List[Dict] = []
    seen = set()
    used_model = "unknown"

    for i, chunk in enumerate(chunks):
        usr = _fill(EXTRACTION_USER, content=chunk)
        if len(chunks) > 1:
            usr = f"(PHẦN {i + 1}/{len(chunks)} của tài liệu)\n" + usr
        res, used_model = call_llm(EXTRACTION_SYSTEM, usr)

        for raw in res.get("items", []) if isinstance(res, dict) else []:
            if not isinstance(raw, dict):
                continue
            try:
                item = KnowledgeItem(**_normalize_item(raw)).model_dump()
            except (ValidationError, TypeError):
                continue
            key = (item["title"].strip().lower(), item["formula_latex"].replace(" ", ""))
            if key not in seen:
                seen.add(key)
                all_items.append(item)

    if not all_items:
        raise LLMUnavailable("AI không trả về kiến thức hợp lệ cho tài liệu này. Hãy thử lại sau.")
    return all_items, used_model


def _chunk_text(text: str, limit: int, overlap: int = 200) -> List[str]:
    """Chia theo ranh giới đoạn/câu, chồng lấn 200 ký tự. Luôn tiến về phía trước."""
    if len(text) <= limit:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = start + limit
        if end >= len(text):
            chunks.append(text[start:])
            break
        lo = start + limit // 2
        cut = max(text.rfind("\n\n", lo, end), text.rfind("\n", lo, end),
                  text.rfind(". ", lo, end) + 1 if text.rfind(". ", lo, end) != -1 else -1)
        if cut <= lo:
            cut = end
        chunks.append(text[start:cut])
        start = max(cut - overlap, start + 1)
    return chunks


# ── Luyện tập & ôn thi ────────────────────────────────────────────────────────

def generate_practice(content: str, num_questions: int, question_type: str) -> Dict[str, Any]:
    from core.prompts import PRACTICE_SYSTEM, PRACTICE_GENERATE_USER
    prompt = _fill(PRACTICE_GENERATE_USER, content=content[:GEMINI_MAX_CHARS],
                   num_questions=num_questions, question_type=question_type)
    res, _ = call_llm(PRACTICE_SYSTEM, prompt)
    return res


def grade_answer(question: str, correct_answer: str, student_answer: str, concept: str,
                 content_snippet: str) -> Dict[str, Any]:
    from core.prompts import PRACTICE_GRADE_SYSTEM, PRACTICE_GRADE_USER
    prompt = _fill(PRACTICE_GRADE_USER, question=question, correct_answer=correct_answer,
                   student_answer=student_answer, concept=concept, content_snippet=content_snippet[:3000])
    res, _ = call_llm(PRACTICE_GRADE_SYSTEM, prompt)
    return res


def generate_exam(content: str, exam_request: str, duration: int) -> Dict[str, Any]:
    from core.prompts import EXAM_SYSTEM, EXAM_GENERATE_USER
    prompt = _fill(EXAM_GENERATE_USER, content=content[:GEMINI_MAX_CHARS],
                   exam_request=exam_request, duration=duration)
    res, _ = call_llm(EXAM_SYSTEM, prompt)
    return res


def grade_essays(questions: List[Dict], student_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Chỉ chấm các câu tự luận bằng AI (trắc nghiệm đã chấm cục bộ, không tốn lượt)."""
    from core.prompts import EXAM_SYSTEM, EXAM_GRADE_USER
    prompt = _fill(EXAM_GRADE_USER,
                   exam_json=json.dumps(questions, ensure_ascii=False),
                   student_answers=json.dumps(student_answers, ensure_ascii=False))
    res, _ = call_llm(EXAM_SYSTEM, prompt)
    return res
