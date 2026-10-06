"""
Dashboard Tab: Hiển thị thẻ kiến thức (cards), tóm tắt, và upload tài liệu.
"""
import streamlit as st

import core.llm_client as llm
import core.storage as storage
from core.document_parser import parse_file
from core.latex_utils import clean_latex, is_valid_latex


def render_dashboard(subject_id: str):
    """Main dashboard cho một môn học."""
    docs = storage.get_docs(subject_id)
    progress = storage.get_progress(subject_id)
    all_knowledge = storage.get_all_knowledge(subject_id)

    # ── Upload tài liệu ───────────────────────────────────────────────────────
    with st.expander("➕ Tải lên tài liệu mới", expanded=(len(docs) == 0)):
        uploaded_files = st.file_uploader(
            "Kéo thả tài liệu (.pdf, .docx, .pptx, .ipynb, .txt)",
            accept_multiple_files=True,
            type=["pdf", "docx", "pptx", "ipynb", "txt"],
            key=f"uploader_{subject_id}",
        )

        if st.button("Lưu tài liệu", type="primary", key=f"save_docs_{subject_id}"):
            if not uploaded_files:
                st.warning("Vui lòng chọn ít nhất một file.")
            else:
                added, duplicated, unreadable = 0, [], []
                for f in uploaded_files:
                    file_bytes = f.getvalue()
                    text_content = parse_file(f.name, file_bytes)
                    if not text_content:
                        unreadable.append(f.name)
                    elif storage.add_document(subject_id, f.name, file_bytes, text_content):
                        added += 1
                    else:
                        duplicated.append(f.name)

                if duplicated:
                    st.info("Tài liệu này đã có, dùng lại kết quả cũ: " + ", ".join(duplicated))
                if unreadable:
                    st.error("Không đọc được nội dung (file rỗng, PDF dạng ảnh scan hoặc bị hỏng): "
                             + ", ".join(unreadable))
                if added:
                    st.success(f"✅ Đã lưu {added} tài liệu mới! Bấm 'Trích xuất' để AI phân tích.")
                    st.rerun()

    # ── Danh sách tài liệu ──────────────────────────────────────────────────
    if docs:
        st.markdown("### 📂 Tài liệu của môn học")

        pending_docs = []
        for doc in docs:
            col1, col2, col3 = st.columns([5, 2, 2])
            with col1:
                st.markdown(f"📄 **{doc['filename']}** ({doc['char_count']} ký tự)")
            with col2:
                if doc.get("extracted"):
                    st.success(f"✅ Đã lưu ({doc.get('model_used', 'AI')})")
                else:
                    st.warning("⏳ Chưa trích xuất")
                    pending_docs.append(doc)
            with col3:
                if st.button("🗑️ Xoá", key=f"del_{doc['hash']}"):
                    st.session_state[f"confirm_del_{doc['hash']}"] = True
                if st.session_state.get(f"confirm_del_{doc['hash']}"):
                    st.warning("Xoá tài liệu này?")
                    if st.button("Chắc chắn xoá", key=f"yes_del_{doc['hash']}"):
                        storage.delete_document(subject_id, doc["hash"], doc["filename"])
                        st.session_state.pop(f"confirm_del_{doc['hash']}", None)
                        st.rerun()

                if doc.get("extracted"):
                    if st.button("🔄 Lấy lại", key=f"re_ext_{doc['hash']}"):
                        st.session_state[f"confirm_re_{doc['hash']}"] = True
                    if st.session_state.get(f"confirm_re_{doc['hash']}"):
                        st.warning("Sẽ tốn lượt miễn phí, chắc chắn?")
                        if st.button("Đồng ý", key=f"yes_re_{doc['hash']}"):
                            storage.mark_document_unextracted(subject_id, doc["hash"])
                            st.session_state.pop(f"confirm_re_{doc['hash']}", None)
                            st.rerun()

        if pending_docs:
            texts = [storage.get_document_text(subject_id, d["hash"]) for d in pending_docs]
            n_req, model_label = llm.estimate_extraction(texts)
            st.caption(f"Ước tính {n_req} request, dùng model {model_label}.")
            if st.button("✨ Trích xuất các file chưa xử lý", type="primary", key=f"extract_{subject_id}"):
                done = 0
                try:
                    for d, text in zip(pending_docs, texts):
                        with st.spinner(f"Đang xử lý {d['filename']}..."):
                            items, model_used = llm.extract_knowledge(text)
                        storage.save_knowledge(subject_id, d["hash"], items)          # lưu ngay từng tài liệu
                        storage.mark_document_extracted(subject_id, d["hash"], model_used)
                        done += 1
                except llm.LLMUnavailable as e:
                    st.error(str(e))
                    if done:
                        st.info(f"Đã lưu kết quả của {done} tài liệu trước đó.")
                except Exception as e:
                    st.error("Lỗi khi trích xuất. Chi tiết bên dưới:")
                    st.exception(e)
                else:
                    st.success("✅ Đã trích xuất xong!")
                    st.rerun()

    st.divider()

    # ── Bảng kiến thức ───────────────────────────────────────────────────────
    st.markdown("### 🔬 Cẩm Nang Kiến Thức")

    if not all_knowledge:
        st.info("Chưa có kiến thức nào. Hãy upload và trích xuất tài liệu.")
        return

    col_search, col_filter, col_toggle = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("🔍 Tìm kiếm kiến thức...", "")
    with col_filter:
        type_filter = st.selectbox("Lọc theo loại", ["Tất cả", "formula", "concept", "process", "fact", "compare"])
    with col_toggle:
        subjects = storage.get_subjects()
        current_subj = next((s for s in subjects if s["id"] == subject_id), None)
        is_mat_goc = current_subj.get("mat_goc_mode", True) if current_subj else True

        new_mat_goc = st.toggle("Chế độ mất gốc", value=is_mat_goc)
        if new_mat_goc != is_mat_goc:
            storage.toggle_mat_goc(subject_id, new_mat_goc)
            st.rerun()

    all_keywords = []
    for item in all_knowledge:
        for kw in item.get("keywords", []):
            if kw not in all_keywords:
                all_keywords.append(kw)
    if all_keywords:
        chips = ", ".join(
            f"<span style='background:rgba(124,58,237,0.15); padding:0.2rem 0.5rem; border-radius:12px;'>{k}</span>"
            for k in all_keywords[:15]
        )
        st.markdown(f"<div style='margin-bottom:1rem; font-size:0.9rem;'>🏷️ Từ khóa: {chips}</div>",
                    unsafe_allow_html=True)

    filtered_items = all_knowledge
    if search_query:
        sq = search_query.lower()
        filtered_items = [i for i in filtered_items
                          if sq in i.get("title", "").lower() or sq in i.get("plain", "").lower()]
    if type_filter != "Tất cả":
        filtered_items = [i for i in filtered_items if i.get("type") == type_filter]

    st.markdown(f"**Đã nhớ: {len(progress)}/{len(all_knowledge)}**")

    for item in filtered_items:
        _render_knowledge_card(subject_id, item, progress, new_mat_goc)


def _render_knowledge_card(subject_id: str, item: dict, progress: list, mat_goc_mode: bool):
    title = item.get("title", "Không tên")
    itype = item.get("type", "concept")
    is_memorized = title in progress

    type_meta = {
        "formula": ("📐", "Công thức"),
        "concept": ("🧠", "Khái niệm"),
        "process": ("🔄", "Quy trình"),
        "fact":    ("📌", "Sự thật"),
        "compare": ("⚖️", "So sánh"),
    }.get(itype, ("📄", itype))

    with st.container(border=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"#### {type_meta[0]} {title}  \n`{type_meta[1]}`")
        with col2:
            btn_label = "✅ Đã nhớ" if is_memorized else "Đánh dấu nhớ"
            if st.button(btn_label, key=f"mem_{subject_id}_{title}", use_container_width=True):
                storage.toggle_progress(subject_id, title)
                st.rerun()

        if item.get("plain"):
            st.markdown(f"**💬 Giải thích:** {item['plain']}")

        if mat_goc_mode:
            if item.get("analogy"):
                st.info(f"🧠 **Hình dung:** {item['analogy']}")
            if item.get("prereq"):
                st.markdown(f"*Cần biết trước:* {', '.join(item['prereq'])}")

        latex_str = item.get("formula_latex", "")
        if latex_str:
            clean_str = clean_latex(latex_str)
            if clean_str and is_valid_latex(clean_str):
                st.latex(clean_str)
                if item.get("formula_words"):
                    st.caption(f"🗣️ Đọc là: {item['formula_words']}")
            else:
                st.warning("⚠ công thức lỗi hiển thị")
                if item.get("formula_words"):
                    st.markdown(f"🗣️ Đọc là: {item['formula_words']}")

        symbols = item.get("symbols", [])
        if symbols and mat_goc_mode:
            st.markdown("**🔤 Bảng ký hiệu:**")
            for sym in symbols:
                s_clean = clean_latex(sym.get("symbol", ""))
                meaning = sym.get("meaning", "")
                if s_clean and is_valid_latex(s_clean):
                    st.markdown(f"- $\\displaystyle {s_clean}$ : {meaning}")
                else:
                    st.markdown(f"- {sym.get('symbol', '')} : {meaning}")

        steps = item.get("steps", [])
        if steps and mat_goc_mode:
            st.markdown("**➜ Các bước:** " + " ➜ ".join(f"**[{s}]**" for s in steps))

        if item.get("example") and mat_goc_mode:
            st.success(f"🧮 **Ví dụ:** {item['example']}")
        if item.get("pitfall") and mat_goc_mode:
            st.error(f"⚠️ **Dễ nhầm:** {item['pitfall']}")
        if item.get("exam_tip") and mat_goc_mode:
            st.warning(f"🎯 **Mẹo thi:** {item['exam_tip']}")
