"""
Practice Tab: Luyện tập hằng ngày với câu hỏi do AI tạo, chấm điểm từng câu.
"""
import streamlit as st

import core.llm_client as llm
import core.storage as storage
from core.grading import grade_mcq
from ui.components import render_section_header, render_empty_state, show_loading_spinner


def _get_content(subject_id: str, max_chars: int = 0) -> str:
    docs = storage.get_docs(subject_id)
    text = "\n".join(
        storage.get_document_text(subject_id, d["hash"]) for d in docs if d.get("extracted")
    )
    return text[:max_chars] if max_chars else text


def render_practice_tab(subject_id: str):
    """Render toàn bộ tab luyện tập hằng ngày."""
    docs = storage.get_docs(subject_id)
    all_knowledge = storage.get_all_knowledge(subject_id)

    if not docs:
        render_empty_state("📤", "Hãy tải tài liệu lên ở tab Tổng quan trước")
        return

    if not all_knowledge:
        render_empty_state("🔬", "Hãy trích xuất kiến thức ở tab Tổng quan trước")
        return

    # ── Cài đặt bài tập ──────────────────────────────────────────────────────
    render_section_header("⚙️", "Cài đặt bài luyện tập")

    col1, col2 = st.columns(2)
    with col1:
        num_q = st.slider("Số câu hỏi", min_value=3, max_value=15, value=5,
                          key=f"num_q_{subject_id}")
    with col2:
        q_type_label = st.selectbox(
            "Loại câu hỏi",
            ["Trắc nghiệm", "Tự luận", "Hỗn hợp"],
            key=f"q_type_{subject_id}",
        )

    q_type_map = {
        "Trắc nghiệm": "trắc nghiệm (multiple choice, 4 lựa chọn A/B/C/D)",
        "Tự luận":     "tự luận (open-ended, yêu cầu giải thích)",
        "Hỗn hợp":     "hỗn hợp (kết hợp trắc nghiệm và tự luận)",
    }

    if st.button("🎲 Tạo bài luyện tập mới", type="primary", key=f"gen_practice_{subject_id}"):
        _generate_practice(subject_id, num_q, q_type_map[q_type_label])

    # ── Hiển thị bài tập ─────────────────────────────────────────────────────
    questions_key = f"practice_questions_{subject_id}"
    if questions_key not in st.session_state:
        render_empty_state("📝", "Nhấn 'Tạo bài luyện tập mới' để bắt đầu")
        return

    questions = st.session_state[questions_key]
    render_section_header("📝", f"Bài luyện tập – {len(questions)} câu")
    _render_questions(subject_id, questions)


def _generate_practice(subject_id: str, num_q: int, q_type: str):
    """Gọi LLM tạo câu hỏi và lưu vào session state."""
    content = _get_content(subject_id)
    if not content:
        st.error("Chưa có nội dung tài liệu nào được trích xuất.")
        return

    try:
        with show_loading_spinner(f"AI đang tạo {num_q} câu hỏi..."):
            result = llm.generate_practice(content, num_q, q_type)

        questions = result.get("questions", [])
        if not questions:
            st.error("Không tạo được câu hỏi. Thử lại sau.")
            return

        st.session_state[f"practice_questions_{subject_id}"] = questions
        st.session_state[f"practice_answers_{subject_id}"] = {}
        st.session_state[f"practice_graded_{subject_id}"] = {}
        st.success(f"✅ Đã tạo {len(questions)} câu hỏi!")
        st.rerun()
    except Exception as e:
        st.error(str(e))


def _render_questions(subject_id: str, questions: list):
    """Render từng câu hỏi với ô nhập và nút chấm."""
    answers_key = f"practice_answers_{subject_id}"
    graded_key = f"practice_graded_{subject_id}"
    st.session_state.setdefault(answers_key, {})
    st.session_state.setdefault(graded_key, {})

    snippet = _get_content(subject_id, max_chars=5000)

    for q in questions:
        qid = str(q.get("id"))
        qtype = q.get("type", "multiple_choice")
        kind = "Trắc nghiệm" if qtype == "multiple_choice" else "Tự luận"

        st.markdown(f"**Câu {qid}** · _{kind}_")
        st.markdown(q.get("question", ""))

        if qtype == "multiple_choice" and q.get("choices"):
            choices = q["choices"]
            if isinstance(choices, dict):
                opts = list(choices.keys())
                fmt = lambda x, c=choices: f"{x}. {c[x]}"  # noqa: E731
            else:
                opts = list(range(len(choices)))
                fmt = lambda i, c=choices: str(c[i])  # noqa: E731
            pick = st.radio("Chọn đáp án:", opts, format_func=fmt, index=None,
                            key=f"ans_{subject_id}_{qid}")
            if pick is not None:
                st.session_state[answers_key][qid] = pick
        else:
            st.session_state[answers_key][qid] = st.text_area(
                "Câu trả lời của bạn:", key=f"ans_{subject_id}_{qid}",
                placeholder="Nhập câu trả lời tại đây...",
            )

        graded = st.session_state[graded_key].get(qid)
        is_mcq = qtype == "multiple_choice" and q.get("choices")
        if graded is None:
            if st.button("Kiểm tra", key=f"grade_{subject_id}_{qid}"):
                student = st.session_state[answers_key].get(qid)
                if not student:
                    st.warning("Hãy trả lời trước.")
                elif is_mcq:
                    st.session_state[graded_key][qid] = grade_mcq(q, student)   # cục bộ, không tốn lượt AI
                    st.rerun()
                else:
                    _grade_single(subject_id, qid, q, student, snippet)
        else:
            if graded.get("is_correct"):
                st.success(f"✅ Đúng! Điểm: {graded.get('score', 0)}/10")
            else:
                st.error(f"❌ Chưa đúng. Điểm: {graded.get('score', 0)}/10")
            if graded.get("feedback"):
                st.markdown(f"💬 {graded['feedback']}")
            if graded.get("explanation"):
                with st.expander("💡 Xem giải thích"):
                    st.markdown(graded["explanation"])
            if graded.get("related_formula"):
                st.caption(f"📚 Nên xem lại: {graded['related_formula']}")
        st.divider()

    pending = [q for q in questions if str(q.get("id")) not in st.session_state[graded_key]]
    if len(pending) > 1:
        if st.button("✅ Nộp tất cả & Chấm điểm", type="primary", key=f"grade_all_{subject_id}"):
            _grade_all(subject_id, pending, snippet)


def _correct_of(q: dict) -> str:
    return str(q.get("correct_answer") or q.get("sample_answer") or q.get("answer") or "")


def _concept_of(q: dict) -> str:
    return str(q.get("related_concept") or q.get("key_concept") or q.get("concept") or "")


def _grade_single(subject_id, qid, question, student, snippet):
    """Chấm một câu tự luận bằng AI và lưu kết quả vào session state."""
    try:
        with show_loading_spinner("AI đang chấm bài..."):
            result = llm.grade_answer(
                question.get("question", ""), _correct_of(question), str(student),
                _concept_of(question), snippet,
            )
        st.session_state[f"practice_graded_{subject_id}"][qid] = result
        st.rerun()
    except llm.LLMUnavailable as e:
        st.error(str(e))
    except Exception as e:
        st.error("Lỗi chấm bài. Chi tiết bên dưới:")
        st.exception(e)


def _grade_all(subject_id, pending, snippet):
    """Chấm tất cả câu chưa chấm: trắc nghiệm cục bộ, tự luận bằng AI (mỗi câu lưu ngay)."""
    answers = st.session_state.get(f"practice_answers_{subject_id}", {})
    graded = st.session_state.setdefault(f"practice_graded_{subject_id}", {})
    try:
        with show_loading_spinner(f"Đang chấm {len(pending)} câu còn lại..."):
            for q in pending:
                qid = str(q.get("id"))
                student = answers.get(qid) or ""
                if q.get("type") == "multiple_choice" and q.get("choices"):
                    graded[qid] = grade_mcq(q, student)
                elif student:
                    graded[qid] = llm.grade_answer(
                        q.get("question", ""), _correct_of(q), str(student), _concept_of(q), snippet,
                    )
                else:
                    graded[qid] = {"is_correct": False, "score": 0, "feedback": "Bạn chưa trả lời câu này.",
                                   "explanation": q.get("explanation", ""), "related_formula": _concept_of(q)}
        st.rerun()
    except llm.LLMUnavailable as e:
        st.error(str(e))
    except Exception as e:
        st.error("Lỗi chấm bài. Chi tiết bên dưới:")
        st.exception(e)
