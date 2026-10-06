"""
Cấu trúc lưu trữ file vĩnh viễn trên đĩa, quản lý file, JSON nguyên tử, SHA256.
"""
import os
import json
import time
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUBJECTS_FILE = DATA_DIR / "subjects.json"
QUOTA_FILE = DATA_DIR / "quota_state.json"

def init_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SUBJECTS_FILE.exists():
        _write_json(SUBJECTS_FILE, {"last_subject": None, "subjects": []})
    if not QUOTA_FILE.exists():
        _write_json(QUOTA_FILE, {})

def _write_json(path: Path, data: Any):
    """Ghi file JSON an toàn (atomic write) để tránh hỏng file khi crash."""
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Lỗi ghi file {path}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()

def _read_json(path: Path, default: Any = None) -> Any:
    """Đọc file JSON, xử lý lỗi an toàn."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"File {path} bị hỏng cấu trúc JSON.")
        return default
    except Exception as e:
        logger.error(f"Lỗi đọc file {path}: {e}")
        return default

def get_file_hash(file_bytes: bytes) -> str:
    """Tính mã băm SHA256 để chống trùng lặp."""
    return hashlib.sha256(file_bytes).hexdigest()

# ── Quản lý Môn Học ────────────────────────────────────────────────────────────

def get_subjects_data() -> Dict:
    return _read_json(SUBJECTS_FILE, {"last_subject": None, "subjects": []})

def get_subjects() -> List[Dict]:
    return get_subjects_data().get("subjects", [])

def get_last_subject() -> Optional[str]:
    return get_subjects_data().get("last_subject")

def set_last_subject(subject_id: str):
    data = get_subjects_data()
    data["last_subject"] = subject_id
    _write_json(SUBJECTS_FILE, data)

def create_subject(name: str) -> Dict:
    data = get_subjects_data()
    subject_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:10]
    subj = {
        "id": subject_id,
        "name": name,
        "mat_goc_mode": True,
        "created_at": time.time()
    }
    data["subjects"].append(subj)
    _write_json(SUBJECTS_FILE, data)
    
    # Khởi tạo thư mục
    sdir = DATA_DIR / subject_id
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "files").mkdir(exist_ok=True)
    (sdir / "text").mkdir(exist_ok=True)
    (sdir / "knowledge").mkdir(exist_ok=True)
    (sdir / "exams").mkdir(exist_ok=True)
    _write_json(sdir / "docs.json", [])
    _write_json(sdir / "progress.json", [])
    
    return subj

def delete_subject(subject_id: str):
    data = get_subjects_data()
    data["subjects"] = [s for s in data["subjects"] if s["id"] != subject_id]
    if data.get("last_subject") == subject_id:
        data["last_subject"] = data["subjects"][0]["id"] if data["subjects"] else None
    _write_json(SUBJECTS_FILE, data)
    
    sdir = DATA_DIR / subject_id
    if sdir.exists():
        shutil.rmtree(sdir)

def rename_subject(subject_id: str, new_name: str):
    data = get_subjects_data()
    for s in data["subjects"]:
        if s["id"] == subject_id:
            s["name"] = new_name
            break
    _write_json(SUBJECTS_FILE, data)

def toggle_mat_goc(subject_id: str, is_on: bool):
    data = get_subjects_data()
    for s in data["subjects"]:
        if s["id"] == subject_id:
            s["mat_goc_mode"] = is_on
            break
    _write_json(SUBJECTS_FILE, data)

# ── Quản lý Tài Liệu ──────────────────────────────────────────────────────────

def get_docs(subject_id: str) -> List[Dict]:
    return _read_json(DATA_DIR / subject_id / "docs.json", [])

def add_document(subject_id: str, filename: str, file_bytes: bytes, text_content: str) -> bool:
    """Thêm tài liệu. Trả về True nếu thêm mới thành công, False nếu đã tồn tại."""
    file_hash = get_file_hash(file_bytes)
    docs = get_docs(subject_id)
    
    # Check trùng
    if any(d["hash"] == file_hash for d in docs):
        return False
        
    sdir = DATA_DIR / subject_id
    (sdir / "files").mkdir(parents=True, exist_ok=True)
    (sdir / "text").mkdir(parents=True, exist_ok=True)
    (sdir / "knowledge").mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name or "tai_lieu"
    stored_name = f"{file_hash[:10]}_{safe_name}"

    # Lưu file gốc
    with open(sdir / "files" / stored_name, "wb") as f:
        f.write(file_bytes)

    # Lưu text (ghi nguyên tử)
    tmp_txt = sdir / "text" / f"{file_hash}.txt.tmp"
    with open(tmp_txt, "w", encoding="utf-8") as f:
        f.write(text_content)
    os.replace(tmp_txt, sdir / "text" / f"{file_hash}.txt")

    docs.append({
        "hash": file_hash,
        "filename": safe_name,
        "stored_name": stored_name,
        "char_count": len(text_content),
        "added_at": time.time(),
        "extracted": False,
        "model_used": None
    })
    _write_json(sdir / "docs.json", docs)
    return True

def delete_document(subject_id: str, doc_hash: str, filename: str = ""):
    sdir = DATA_DIR / subject_id
    docs = get_docs(subject_id)
    target = next((d for d in docs if d["hash"] == doc_hash), None)
    docs = [d for d in docs if d["hash"] != doc_hash]
    _write_json(sdir / "docs.json", docs)

    stored = (target or {}).get("stored_name") or filename
    paths = [
        sdir / "text" / f"{doc_hash}.txt",
        sdir / "knowledge" / f"{doc_hash}.json",
    ]
    if stored:
        paths.append(sdir / "files" / Path(stored).name)
    for p in paths:
        if p.exists():
            p.unlink()

def get_document_text(subject_id: str, doc_hash: str) -> str:
    path = DATA_DIR / subject_id / "text" / f"{doc_hash}.txt"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def mark_document_extracted(subject_id: str, doc_hash: str, model_used: str):
    docs = get_docs(subject_id)
    for d in docs:
        if d["hash"] == doc_hash:
            d["extracted"] = True
            d["model_used"] = model_used
            break
    _write_json(DATA_DIR / subject_id / "docs.json", docs)

def mark_document_unextracted(subject_id: str, doc_hash: str):
    docs = get_docs(subject_id)
    for d in docs:
        if d["hash"] == doc_hash:
            d["extracted"] = False
            d["model_used"] = None
            break
    _write_json(DATA_DIR / subject_id / "docs.json", docs)

# ── Quản lý Kiến thức ─────────────────────────────────────────────────────────

def save_knowledge(subject_id: str, doc_hash: str, knowledge_items: List[Dict]):
    _write_json(DATA_DIR / subject_id / "knowledge" / f"{doc_hash}.json", knowledge_items)

def get_all_knowledge(subject_id: str) -> List[Dict]:
    """Gộp kiến thức từ mọi tài liệu (theo thứ tự thêm), bỏ trùng theo title + công thức."""
    sdir = DATA_DIR / subject_id / "knowledge"
    if not sdir.exists():
        return []

    all_items = []
    seen = set()
    for d in get_docs(subject_id):
        items = _read_json(sdir / f"{d['hash']}.json", [])
        if not isinstance(items, list):
            continue
        for item in items:
            key = (str(item.get("title", "")).strip().lower(),
                   str(item.get("formula_latex", "")).strip().replace(" ", ""))
            if key not in seen:
                seen.add(key)
                all_items.append(item)
    return all_items

# ── Quản lý Tiến độ (Đã nhớ) ────────────────────────────────────────────────

def get_progress(subject_id: str) -> List[str]:
    return _read_json(DATA_DIR / subject_id / "progress.json", [])

def toggle_progress(subject_id: str, title: str) -> List[str]:
    prog = get_progress(subject_id)
    if title in prog:
        prog.remove(title)
    else:
        prog.append(title)
    _write_json(DATA_DIR / subject_id / "progress.json", prog)
    return prog

# ── Quản lý Đề thi ────────────────────────────────────────────────────────────

def save_exam(subject_id: str, exam_data: Dict, exam_id: Optional[int] = None) -> int:
    """Lưu đề (tạo mới nếu exam_id=None, ghi đè nếu đã có). Trả về exam_id."""
    exam_id = exam_id or int(time.time())
    exam_data["id"] = exam_id
    exam_data.setdefault("created_at", exam_id)
    edir = DATA_DIR / subject_id / "exams"
    edir.mkdir(parents=True, exist_ok=True)
    _write_json(edir / f"{exam_id}.json", exam_data)
    return exam_id

def get_exams(subject_id: str) -> List[Dict]:
    sdir = DATA_DIR / subject_id / "exams"
    if not sdir.exists():
        return []
    exams = []
    for path in sorted(sdir.glob("*.json"), reverse=True):
        data = _read_json(path, None)
        if isinstance(data, dict) and data:
            data.setdefault("id", int(path.stem) if path.stem.isdigit() else 0)
            exams.append(data)
    return exams

# ── Quản lý Quota ────────────────────────────────────────────────────────────

def get_quota_state() -> Dict:
    return _read_json(QUOTA_FILE, {})

def update_quota_state(model_name: str, wait_seconds: int = 0, is_day_ban: bool = False):
    """Khóa model. is_day_ban: dùng wait_seconds nếu >0, mặc định 24h."""
    state = get_quota_state()
    now = time.time()
    if is_day_ban:
        secs = wait_seconds if wait_seconds > 0 else 86400
        state[model_name] = {"unlock_time": now + secs, "reason": "Hết lượt trong ngày"}
    else:
        state[model_name] = {"unlock_time": now + wait_seconds, "reason": "Tạm khóa"}
    _write_json(QUOTA_FILE, state)

def earliest_unlock_hours() -> float:
    """Số giờ tới khi có model mở lại (0 nếu không có model nào bị khóa)."""
    now = time.time()
    times = [v["unlock_time"] - now for v in get_quota_state().values() if v.get("unlock_time", 0) > now]
    return (min(times) / 3600) if times else 0.0

def reset_quota(model_name: str):
    state = get_quota_state()
    if model_name in state:
        del state[model_name]
        _write_json(QUOTA_FILE, state)

def migrate_legacy() -> int:
    """Nhập tài liệu từ cấu trúc cũ data/subjects/<id>/ (meta.json + documents.json) sang cấu trúc mới.
    Chỉ nhập một lần (đánh dấu .migrated). Bỏ qua môn thử nghiệm quá ngắn.
    Kiến thức cũ khác khuôn nên cần trích xuất lại."""
    legacy_root = DATA_DIR / "subjects"
    if not legacy_root.is_dir():
        return 0
    moved = 0
    for ldir in legacy_root.iterdir():
        marker = ldir / ".migrated"
        if not ldir.is_dir() or marker.exists():
            continue
        meta = _read_json(ldir / "meta.json", None)
        docs = _read_json(ldir / "documents.json", None)
        if not isinstance(meta, dict) or not isinstance(docs, list):
            continue
        real_docs = [d for d in docs if len(str(d.get("content", ""))) >= 500]
        if real_docs:
            subj = create_subject(str(meta.get("name") or "Môn cũ"))
            for d in real_docs:
                content = str(d["content"])
                add_document(subj["id"], f"{d.get('filename', 'tai_lieu')}.txt", content.encode("utf-8"), content)
            moved += 1
        try:
            marker.write_text("done", encoding="utf-8")
        except OSError:
            pass
    return moved


init_dirs()
migrate_legacy()
