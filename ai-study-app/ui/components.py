"""
Tái sử dụng các UI components dùng chung trong toàn ứng dụng.
"""
import streamlit as st
import time
from typing import List, Dict, Optional


def render_app_header(subject_name: Optional[str] = None):
    """Render header chính của ứng dụng."""
    if subject_name:
        title = f"📚 {subject_name}"
        subtitle = "Bảng kiến thức cốt lõi · Luyện tập · Ôn thi"
    else:
        title = "📚 AI Học Tập"
        subtitle = "Hệ thống lấy lại gốc kiến thức thông minh"

    st.markdown(f"""
    <div class="app-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_row(metrics: List[Dict]):
    """
    Render hàng metric cards.
    metrics: [{"label": str, "value": str/int, "icon": str}, ...]
    """
    cols_html = ""
    for m in metrics:
        cols_html += f"""
        <div class="metric-card">
            <div class="metric-value">{m.get('icon', '')} {m['value']}</div>
            <div class="metric-label">{m['label']}</div>
        </div>"""

    st.markdown(f'<div class="metric-row">{cols_html}</div>', unsafe_allow_html=True)


def render_subject_badge(name: str, color: str = "#7c3aed"):
    """Render badge tên môn học."""
    st.markdown(
        f'<div class="subject-badge">🎓 {name}</div>',
        unsafe_allow_html=True,
    )


def render_formula_table(formulas: List[Dict]):
    """
    Render bảng công thức dạng HTML đẹp.
    Mỗi formula: {id, name, formula, meaning, example}
    """
    if not formulas:
        render_empty_state("🔬", "Chưa có công thức nào được trích xuất")
        return

    rows = ""
    for f in formulas:
        formula_display = f.get("formula", "N/A")
        rows += f"""
        <tr>
            <td class="num-col">{f.get('id', '?')}</td>
            <td><strong>{f.get('name', 'Không tên')}</strong></td>
            <td><span class="formula-cell">{formula_display}</span></td>
            <td class="meaning-text">{f.get('meaning', '')}</td>
        </tr>"""

    st.markdown(f"""
    <table class="formula-table">
        <thead>
            <tr>
                <th>#</th>
                <th>Tên Khái Niệm / Công Thức</th>
                <th>Công Thức</th>
                <th>Ý Nghĩa Cốt Lõi</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)


def render_empty_state(icon: str, message: str):
    """Render trạng thái rỗng."""
    st.markdown(f"""
    <div class="empty-state">
        <span class="empty-icon">{icon}</span>
        <p>{message}</p>
    </div>
    """, unsafe_allow_html=True)


def render_feedback(is_correct: bool, feedback: str, explanation: str, related_formula: str = ""):
    """Render phản hồi chấm bài."""
    if is_correct:
        icon, cls, label = "✅", "feedback-correct", "Chính xác!"
    else:
        icon, cls, label = "❌", "feedback-wrong", "Chưa đúng"

    concept_html = ""
    if related_formula and not is_correct:
        concept_html = f'<div class="concept-link">📌 Xem lại khái niệm: <strong>{related_formula}</strong></div>'

    st.markdown(f"""
    <div class="{cls}">
        <div class="feedback-label">{icon} {label}</div>
        <div>{feedback}</div>
        <hr style="margin: 0.6rem 0; border-color: rgba(255,255,255,0.1);">
        <div style="font-size:0.87rem; opacity:0.9;"><strong>Giải thích:</strong> {explanation}</div>
        {concept_html}
    </div>
    """, unsafe_allow_html=True)


def render_topic_tags(topics: List[str]):
    """Render danh sách topic tags."""
    if not topics:
        return
    tags_html = "".join(f'<span class="topic-tag">🏷️ {t}</span>' for t in topics)
    st.markdown(f'<div style="margin-bottom:1rem;">{tags_html}</div>', unsafe_allow_html=True)


def render_section_header(icon: str, title: str):
    """Render tiêu đề section với icon."""
    st.markdown(f"""
    <div class="section-header">
        <span class="section-icon">{icon}</span>
        <h3>{title}</h3>
    </div>
    """, unsafe_allow_html=True)


def render_score_display(score: float, grade: str, percentage: float):
    """Render điểm số lớn sau khi thi."""
    color = "#10b981" if percentage >= 70 else "#f59e0b" if percentage >= 50 else "#ef4444"
    st.markdown(f"""
    <div class="score-circle-container">
        <div class="score-display" style="-webkit-text-fill-color: {color}; background: none;">
            {score:.1f}/10
        </div>
        <div class="grade-letter">Xếp loại: {grade}</div>
        <div style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.5rem;">
            Đạt {percentage:.0f}% số điểm
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_document_list(documents: List[Dict], on_delete=None):
    """Render danh sách tài liệu đã upload."""
    if not documents:
        render_empty_state("📄", "Chưa có tài liệu nào")
        return

    for doc in documents:
        col1, col2 = st.columns([5, 1])
        with col1:
            size_kb = doc.get("char_count", 0) // 1024
            st.markdown(f"""
            <div class="glass-card" style="padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
                <div style="font-weight:500; color: var(--text-primary); font-size:0.9rem;">
                    📄 {doc['filename']}
                </div>
                <div style="color: var(--text-muted); font-size: 0.78rem; margin-top: 0.2rem;">
                    ~{size_kb} KB văn bản đã trích xuất
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if on_delete:
                if st.button("🗑️", key=f"del_doc_{doc['id']}", help="Xoá tài liệu này"):
                    on_delete(doc["id"])
                    st.rerun()


def show_loading_spinner(message: str = "Đang xử lý..."):
    """Context manager spinner với message tiếng Việt."""
    return st.spinner(f"⚡ {message}")
