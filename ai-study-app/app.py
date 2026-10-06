import io
import os
import time
import zipfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import core.storage as storage  # noqa: E402
from ui.components import render_app_header  # noqa: E402
from ui.dashboard import render_dashboard  # noqa: E402
from ui.exam import render_exam_tab  # noqa: E402
from ui.practice import render_practice_tab  # noqa: E402
from ui.styles import inject_css  # noqa: E402

st.set_page_config(
    page_title="Ôn Tập Lấy Lại Gốc",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(inject_css(), unsafe_allow_html=True)


# ── Sao lưu / khôi phục ───────────────────────────────────────────────────────

def _make_backup_zip() -> bytes:
    buf = io.BytesIO()
    root = storage.DATA_DIR
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file() and not p.name.endswith(".tmp"):
                zf.write(p, p.relative_to(root).as_posix())
    return buf.getvalue()


def _restore_backup(data: bytes) -> int:
    """Giải nén an toàn (chặn đường dẫn thoát khỏi data/). Trả về số file đã khôi phục."""
    root = storage.DATA_DIR.resolve()
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        if zf.testzip() is not None:
            raise ValueError("File zip bị hỏng.")
        names = zf.namelist()
        if "subjects.json" not in names:
            raise ValueError("Không phải bản sao lưu hợp lệ (thiếu subjects.json).")
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = (root / info.filename).resolve()
            if root not in target.parents:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            count += 1
    return count


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar():
    st.sidebar.title("🧠 Ôn Tập Mất Gốc")

    subjects = storage.get_subjects()
    subject_id = None

    if not subjects:
        st.sidebar.info("Chưa có môn học nào. Hãy tạo môn mới bên dưới.")
    else:
        ids = [s["id"] for s in subjects]
        names = {s["id"]: s["name"] for s in subjects}
        last = storage.get_last_subject()
        idx = ids.index(last) if last in ids else 0
        subject_id = st.sidebar.selectbox("📚 Môn học", ids, index=idx, format_func=lambda i: names[i])
        if subject_id != last:
            storage.set_last_subject(subject_id)

        with st.sidebar.expander("✏️ Đổi tên / Xóa môn này"):
            new_name = st.text_input("Tên mới", value=names[subject_id], key=f"rn_{subject_id}")
            if st.button("Đổi tên", key=f"rn_btn_{subject_id}"):
                if new_name.strip():
                    storage.rename_subject(subject_id, new_name.strip())
                    st.rerun()
            st.markdown("---")
            confirm = st.checkbox("Tôi chắc chắn muốn xóa môn này cùng toàn bộ dữ liệu", key=f"cf_{subject_id}")
            if st.button("🗑️ Xóa môn học", key=f"del_btn_{subject_id}", disabled=not confirm):
                storage.delete_subject(subject_id)
                st.rerun()

    with st.sidebar.expander("➕ Thêm môn học mới", expanded=not subjects):
        new_subject_name = st.text_input("Tên môn học", key="new_subject_name")
        if st.button("Tạo môn", key="create_subject"):
            if new_subject_name.strip():
                subj = storage.create_subject(new_subject_name.strip())
                storage.set_last_subject(subj["id"])
                st.rerun()
            else:
                st.warning("Hãy nhập tên môn.")

    st.sidebar.divider()
    
    # ── Cài đặt API Key ───────────────────────────────────────────────────────
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {}
        
    with st.sidebar.expander("⚙️ Cài đặt API Key của bạn", expanded=False):
        st.markdown("<small>Nhập Key để dùng riêng nếu muốn. Không lưu trên máy, mất khi đóng trình duyệt.</small>", unsafe_allow_html=True)
        
        gemini = st.text_input("Gemini API Key", value=st.session_state.api_keys.get("GEMINI_API_KEY", ""), type="password")
        groq = st.text_input("Groq API Key", value=st.session_state.api_keys.get("GROQ_API_KEY", ""), type="password")
        openrouter = st.text_input("OpenRouter API Key", value=st.session_state.api_keys.get("OPENROUTER_API_KEY", ""), type="password")
        
        if st.button("Lưu Key", key="save_keys"):
            st.session_state.api_keys["GEMINI_API_KEY"] = gemini.strip()
            st.session_state.api_keys["GROQ_API_KEY"] = groq.strip()
            st.session_state.api_keys["OPENROUTER_API_KEY"] = openrouter.strip()
            st.success("Đã lưu vào bộ nhớ tạm!")
            st.rerun()

    # Trạng thái nguồn AI
    st.sidebar.markdown("### 📊 Trạng thái AI")
    keys = {"Gemini": "GEMINI_API_KEY", "Groq": "GROQ_API_KEY", "OpenRouter": "OPENROUTER_API_KEY"}
    for label, env in keys.items():
        has_key = bool(st.session_state.api_keys.get(env)) or bool(os.environ.get(env, "").strip())
        st.sidebar.caption(f"{'🟢' if has_key else '⚪'} {label}"
                           f"{'' if has_key else ' (chưa có key)'}")
    now = time.time()
    locked = {m: s for m, s in storage.get_quota_state().items() if s.get("unlock_time", 0) > now}
    if locked:
        for model, s in locked.items():
            left = s["unlock_time"] - now
            h, m = int(left // 3600), int(left % 3600 // 60)
            st.sidebar.error(f"**{model}**\n\nhết đến {time.strftime('%H:%M %d/%m', time.localtime(s['unlock_time']))}"
                             f" (còn {h}h{m}p)")
    else:
        st.sidebar.success("Mọi model đang còn dùng được.")

    st.sidebar.divider()

    # Sao lưu & khôi phục
    st.sidebar.markdown("### 💾 Sao lưu")
    st.sidebar.download_button("⬇️ Tải bản sao lưu (.zip)", data=_make_backup_zip(),
                               file_name=f"sao_luu_{time.strftime('%Y%m%d_%H%M')}.zip",
                               mime="application/zip")
    up = st.sidebar.file_uploader("Khôi phục từ sao lưu (.zip)", type=["zip"], key="restore_zip")
    if up is not None and st.sidebar.button("Khôi phục (ghi đè dữ liệu trùng)", key="restore_btn"):
        try:
            n = _restore_backup(up.getvalue())
            st.sidebar.success(f"Đã khôi phục {n} file.")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Không khôi phục được: {e}")

    return subject_id


# ── Đăng nhập ─────────────────────────────────────────────────────────────────

def check_password():
    """Kiểm tra mật khẩu trước khi cho phép vào app."""
    if st.session_state.get("authenticated", False):
        return True

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='glass-card' style='text-align: center; padding: 2.5rem 2rem;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='margin-bottom: 1rem;'>🔒 Không Gian Học Tập</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: var(--text-secondary); margin-bottom: 2rem;'>Vui lòng nhập mật khẩu nhóm để tiếp tục.</p>", unsafe_allow_html=True)
        
        pwd = st.text_input("Mật khẩu", type="password", label_visibility="collapsed", placeholder="Nhập mật khẩu...")
        if st.button("Mở khóa", use_container_width=True):
            if pwd == os.environ.get("APP_PASSWORD", "ghuce7"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Mật khẩu không đúng!")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# ── Vòng lặp chính ────────────────────────────────────────────────────────────

def main():
    if not check_password():
        return

    storage.init_dirs()
    subject_id = render_sidebar()

    if not subject_id:
        render_app_header()
        st.info("👈 Hãy tạo một môn học ở thanh bên trái để bắt đầu.")
        return

    name = next((s["name"] for s in storage.get_subjects() if s["id"] == subject_id), None)
    render_app_header(name)

    tab1, tab2, tab3 = st.tabs(["📚 Tổng quan", "📝 Luyện tập hằng ngày", "🔥 Ôn thi cấp tốc"])
    with tab1:
        render_dashboard(subject_id)
    with tab2:
        render_practice_tab(subject_id)
    with tab3:
        render_exam_tab(subject_id)


main()
