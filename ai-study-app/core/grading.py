"""
Chấm trắc nghiệm cục bộ (không tốn lượt gọi AI).
"""
import re
from typing import Dict, Any


def _norm_choice(v: Any) -> str:
    """'A', 'a)', 'A. xxx', 'Đáp án: A' -> 'A'. Không nhận ra thì trả chuỗi rỗng."""
    s = str(v or "").strip().upper()
    m = re.match(r"^(?:ĐÁP ÁN|CHỌN|ANSWER)?[\s:.\-]*([ABCD])(?![A-ZÀ-Ỹ])", s)
    return m.group(1) if m else ""


def grade_mcq(question: Dict[str, Any], picked: Any) -> Dict[str, Any]:
    """So đáp án đã chọn với correct_answer; giải thích lấy từ lúc AI tạo đề."""
    correct = _norm_choice(question.get("correct_answer"))
    picked_n = _norm_choice(picked)
    ok = bool(correct) and picked_n == correct
    choices = question.get("choices") or {}
    correct_text = choices.get(correct, "") if isinstance(choices, dict) else ""
    if ok:
        feedback = "Chính xác!"
    elif correct:
        feedback = f"Đáp án đúng là {correct}" + (f": {correct_text}" if correct_text else "") + "."
    else:
        feedback = "Đề này thiếu đáp án đúng."
    return {
        "is_correct": ok,
        "score": 10 if ok else 0,
        "feedback": feedback,
        "explanation": question.get("explanation") or "",
        "related_formula": question.get("related_concept") or question.get("key_concept") or "",
        "correct_answer": correct,
        "picked": picked_n,
    }
