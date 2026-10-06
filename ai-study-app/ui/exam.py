"""
Exam Tab: tạo đề, làm bài, chấm (trắc nghiệm cục bộ, tự luận bằng AI), xem lại đề cũ, ôn câu sai.
Mọi đề được LƯU NGAY vào data/<mon>/exams/. Xem lại / làm lại / ôn câu sai không tốn lượt AI.
"""
import time

import streamlit as st

import core.llm_client as llm
import core.storage as storage
from core.grading import grade_mcq
from ui.components import render_empty_state, render_score_display, render_section_header, show_loading_spinner


def _f(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _letter(pct: float) -> str:
    return "A" if pct >= 85 else "B" if pct >= 70 else "C" if pct >= 55 else "D" if pct >= 40 else "F"


def _doc_content(subject_id: str) -> str:
    return "\n".join(storage.get_document_text(subject_id, d["hash"])
                     for d in storage.get_docs(subject_id) if d.get("extracted"))


def render_exam_tab(subject_id: str):
    """Render toàn bộ tab ôn thi cấp tốc."""
    if not storage.get_docs(subject_id):
        render_empty_state("📤", "Hãy tải tài liệu lên ở tab Tổng quan trước")
        return

    tab_new, tab_old, tab_wrong = st.tabs(["🚀 Làm bài", "📂 Đề cũ", "⚠️ Ôn lại câu đã sai"])
    with tab_new:
        active = st.session_state.get(f"active_exam_{subject_id}")
        if active is None:
            _render_exam_setup(subject_id)
        elif active.get("result") and not active.get("retaking"):
            _render_exam_result(active["result"], active["exam_data"])
            c1, c2 = st.columns(2)
            if c1.button("🔁 Làm lại đề này (không tốn lượt AI)", key=f"retry_{subject_id}"):
                active["retaking"] = True
                active["answers"] = {}
                _clear_answer_widgets(subject_id, active["exam_data"])
                st.rerun()
            if c2.button("➕ Tạo đề mới", type="primary", key=f"newexam_{subject_id}"):
                st.session_state.pop(f"active_exam_{subject_id}", None)
                st.rerun()
        else:
            _render_exam_in_progress(subject_id, active)
    with tab_old:
        _render_old_exams(subject_id)
    with tab_wrong:
        _render_wrong_questions(subject_id)


def _clear_answer_widgets(subject_id: str, exam_data: dict):
    for q in exam_data.get("questions", []):
        st.session_state.pop(f"q_{subject_id}_{q.get('id')}", None)


def _render_exam_setup(subject_id: str):
    render_section_header("📋", "Tạo đề thi theo yêu cầu")
    st.caption('Ví dụ: "10 câu trắc nghiệm về hồi quy", "3 câu tự luận", "5 trắc nghiệm + 2 tự luận".')
    col1, col2 = st.columns([3, 1])
    with col1:
        exam_request = st.text_input("Mô tả đề thi", key=f"req_{subject_id}",
                                     placeholder="VD: 10 câu trắc nghiệm về các khái niệm cơ bản")
    with col2:
        duration = st.number_input("Thời gian (phút)", min_value=5, max_value=180, value=15,
                                   key=f"dur_{subject_id}")

    if st.button("Tạo đề ngay", type="primary", key=f"mk_{subject_id}"):
        if not exam_request.strip():
            st.warning("Vui lòng nhập mô tả đề thi.")
            return
        content = _doc_content(subject_id)
        if not content:
            st.error("Chưa có tài liệu nào được trích xuất.")
            return
        try:
            with show_loading_spinner("AI đang soạn đề thi..."):
                exam_data = llm.generate_exam(content, exam_request, int(duration))
            if not exam_data.get("questions"):
                st.error("Không tạo được đề thi. Hãy thử mô tả lại yêu cầu.")
                return
            record = {"exam_data": exam_data, "answers": {}, "result": None, "attempts": []}
            exam_id = storage.save_exam(subject_id, record)          # LƯU NGAY
            record["id"] = exam_id
            st.session_state[f"active_exam_{subject_id}"] = record
            st.rerun()
        except llm.LLMUnavailable as e:
            st.error(str(e))
        except Exception as e:
            st.error("Lỗi tạo đề. Chi tiết bên dưới:")
            st.exception(e)


def load_exam_into_session(subject_id: str, record: dict):
    rec = dict(record)
    rec["retaking"] = True
    rec["answers"] = {}
    _clear_answer_widgets(subject_id, rec.get("exam_data", {}))
    st.session_state[f"active_exam_{subject_id}"] = rec


def _render_exam_in_progress(subject_id: str, active: dict):
    exam_data = active["exam_data"]
    questions = exam_data.get("questions", [])
    st.markdown(f"### 📋 {exam_data.get('exam_title', 'Đề thi')}")
    st.caption(f"⏱️ {exam_data.get('duration_minutes', '?')} phút · 📊 {exam_data.get('total_points', 10)} điểm · "
               f"❓ {len(questions)} câu")

    answers = active.setdefault("answers", {})
    for q in questions:
        qid = str(q.get("id"))
        st.markdown(f"**Câu {qid}** ({q.get('points', '?')} điểm)")
        st.markdown(q.get("question", ""))
        choices = q.get("choices")
        if q.get("type") == "multiple_choice" and isinstance(choices, dict) and choices:
            opts = list(choices.keys())
            pick = st.radio("Chọn đáp án:", opts, index=None, key=f"q_{subject_id}_{qid}",
                            format_func=lambda x, c=choices: f"{x}. {c[x]}")
            answers[qid] = pick
        else:
            answers[qid] = st.text_area("Bài làm của bạn:", key=f"q_{subject_id}_{qid}")
        st.divider()

    if st.button("Nộp bài & chấm điểm", type="primary", key=f"submit_{subject_id}"):
        _submit_exam(subject_id, active)


def _submit_exam(subject_id: str, active: dict):
    exam_data = active["exam_data"]
    answers = active.get("answers", {})
    questions = exam_data.get("questions", [])
    n = max(len(questions), 1)
    default_pts = _f(exam_data.get("total_points"), 10) / n

    results, essays = {}, []
    for q in questions:
        qid = str(q.get("id"))
        pts = _f(q.get("points"), default_pts) or default_pts
        ans = answers.get(qid)
        if q.get("type") == "multiple_choice" and q.get("choices"):
            g = grade_mcq(q, ans)
            results[qid] = {"question_id": qid, "student_answer": ans or "(bỏ trống)", "points": pts,
                            "is_correct": g["is_correct"], "points_earned": pts if g["is_correct"] else 0,
                            "feedback": g["feedback"], "explanation": g["explanation"]}
        else:
            results[qid] = {"question_id": qid, "student_answer": ans or "(bỏ trống)", "points": pts,
                            "is_correct": False, "points_earned": 0, "feedback": "Bạn chưa làm câu này.",
                            "explanation": q.get("sample_answer") or ""}
            if ans and str(ans).strip():
                essays.append({"id": qid, "points": pts, "question": q.get("question", ""),
                               "sample_answer": q.get("sample_answer") or q.get("correct_answer") or ""})

    extra = {}
    try:
        if essays:
            with show_loading_spinner("AI đang chấm các câu tự luận..."):
                ai = llm.grade_essays(essays, {e["id"]: answers.get(e["id"]) for e in essays})
            by_id = {str(r.get("question_id")): r for r in ai.get("results", []) if isinstance(r, dict)}
            for e in essays:
                r = by_id.get(e["id"])
                if r:
                    results[e["id"]]["points_earned"] = max(0.0, min(_f(r.get("points_earned")), e["points"]))
                    results[e["id"]]["is_correct"] = bool(r.get("is_correct")) or \
                        results[e["id"]]["points_earned"] >= 0.7 * e["points"]
                    results[e["id"]]["feedback"] = r.get("feedback", "")
            extra = {k: ai.get(k) for k in ("weak_points", "strong_points", "overall_feedback")}
    except llm.LLMUnavailable as e:
        st.error(f"{e}\n\nBài làm của bạn vẫn còn đó, hãy nhấn nộp lại sau.")
        return
    except Exception as e:
        st.error("Lỗi chấm bài tự luận. Chi tiết bên dưới:")
        st.exception(e)
        return

    total_pts = sum(r["points"] for r in results.values()) or 1
    earned = sum(r["points_earned"] for r in results.values())
    pct = earned / total_pts * 100
    result = {
        "total_score": round(earned / total_pts * 10, 2),
        "percentage": round(pct, 1),
        "grade_letter": _letter(pct),
        "results": list(results.values()),
        "weak_points": extra.get("weak_points") or [],
        "strong_points": extra.get("strong_points") or [],
        "overall_feedback": extra.get("overall_feedback") or "",
    }

    record = {"exam_data": exam_data, "answers": answers, "result": result,
              "attempts": active.get("attempts", []) + [{"at": time.time(), "score": result["total_score"]}],
              "created_at": active.get("created_at") or active.get("id")}
    storage.save_exam(subject_id, record, exam_id=active.get("id"))   # LƯU NGAY kèm bài làm + điểm
    record["id"] = active.get("id")
    st.session_state[f"active_exam_{subject_id}"] = record
    st.rerun()


def _render_exam_result(result: dict, exam_data: dict):
    render_section_header("🏆", "Kết quả bài thi")
    render_score_display(_f(result.get("total_score")), str(result.get("grade_letter", "?")),
                         _f(result.get("percentage")))
    if result.get("overall_feedback"):
        st.info(result["overall_feedback"])

    questions = {str(q.get("id")): q for q in (exam_data or {}).get("questions", [])}
    for r in result.get("results", []):
        qid = str(r.get("question_id"))
        q = questions.get(qid, {})
        icon = "✅" if r.get("is_correct") else "❌"
        with st.expander(f"{icon} Câu {qid}: {_f(r.get('points_earned')):g}/{_f(r.get('points')):g} điểm"):
            st.markdown(q.get("question", ""))
            st.markdown(f"**Bài làm:** {r.get('student_answer', '')}")
            if r.get("feedback"):
                st.markdown(f"💬 {r['feedback']}")
            if r.get("explanation"):
                st.markdown(f"💡 **Giải thích:** {r['explanation']}")

    c1, c2 = st.columns(2)
    if result.get("strong_points"):
        c1.success("**Điểm mạnh:**\n\n" + "\n".join(f"- {s}" for s in result["strong_points"]))
    if result.get("weak_points"):
        c2.warning("**Cần ôn thêm:**\n\n" + "\n".join(f"- {s}" for s in result["weak_points"]))


def _fmt_time(ts) -> str:
    try:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return "?"


def _render_old_exams(subject_id: str):
    exams = storage.get_exams(subject_id)
    if not exams:
        st.info("Chưa có đề nào được lưu.")
        return
    for ex in exams:
        title = ex.get("exam_data", {}).get("exam_title", "Đề thi")
        res = ex.get("result")
        score = f"{_f(res.get('total_score')):.1f}/10" if res else "chưa nộp"
        with st.expander(f"🕒 {_fmt_time(ex.get('created_at'))} · {title} · {score}"):
            if res:
                _render_exam_result(res, ex.get("exam_data", {}))
            else:
                st.caption("Đề này chưa được nộp bài.")
            if st.button("🔁 Làm lại đề này (không tốn lượt AI)", key=f"redo_{subject_id}_{ex.get('id')}"):
                load_exam_into_session(subject_id, ex)
                st.rerun()


def _render_wrong_questions(subject_id: str):
    wrong = []
    for ex in storage.get_exams(subject_id):
        res = ex.get("result") or {}
        questions = {str(q.get("id")): q for q in ex.get("exam_data", {}).get("questions", [])}
        for r in res.get("results", []):
            if not r.get("is_correct"):
                q = questions.get(str(r.get("question_id")))
                if q:
                    wrong.append((ex, q, r))

    if not wrong:
        st.success("Chưa có câu nào sai trong các đề đã nộp. 🎉")
        return

    st.markdown(f"**{len(wrong)} câu đã làm sai** (xem lại hoàn toàn miễn phí, không gọi AI):")
    for i, (ex, q, r) in enumerate(wrong, 1):
        with st.container(border=True):
            st.markdown(f"**{i}.** {q.get('question', '')}")
            choices = q.get("choices")
            if isinstance(choices, dict):
                for k, v in choices.items():
                    st.markdown(f"- {k}. {v}")
            st.markdown(f"❌ Bạn đã trả lời: {r.get('student_answer', '')}")
            if q.get("correct_answer"):
                st.markdown(f"✅ Đáp án đúng: **{q['correct_answer']}**")
            elif q.get("sample_answer"):
                st.markdown(f"✅ Đáp án mẫu: {q['sample_answer']}")
            if q.get("explanation"):
                st.markdown(f"💡 {q['explanation']}")
