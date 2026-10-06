"""
CSS luxury dark-mode styling cho toàn bộ ứng dụng.
Phong cách Linear / Vercel (Minimalist, True Glassmorphism).
"""

LUXURY_CSS = """
<style>
/* ── Google Font ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Ẩn các thành phần mặc định của Streamlit ─────────────────── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stDecoration"] {display: none;}

/* ── Root Variables ─────────────────────────────────────────────── */
:root {
    --bg-primary:    #000000; /* Pure Black cho cảm giác cao cấp */
    --bg-secondary:  #0a0a0a;
    --bg-card:       rgba(10, 10, 10, 0.4);
    --bg-glass:      rgba(255, 255, 255, 0.02);
    --border-glass:  rgba(255, 255, 255, 0.08);
    --border-glow:   rgba(255, 255, 255, 0.15);
    
    --accent-purple: #9333ea;
    --accent-blue:   #2563eb;
    
    --text-primary:  #ffffff;
    --text-secondary:#a1a1aa;
    --text-muted:    #52525b;
    
    --radius-sm: 6px;
    --radius-md: 12px;
    --radius-lg: 20px;
    --transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Global Styles ──────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}

/* ── Headings ───────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

/* ── Glass Cards (Sang trọng) ───────────────────────────────────── */
.glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-md);
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.05), 0 4px 24px -4px rgba(0,0,0,0.5);
    transition: var(--transition);
}
.glass-card:hover {
    border-color: var(--border-glow);
    transform: translateY(-2px);
    box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.1), 0 8px 32px -8px rgba(0,0,0,0.6);
}

/* ── Buttons (Linear style) ─────────────────────────────────────── */
.stButton > button {
    background: rgba(255, 255, 255, 0.05) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1.2rem !important;
    transition: var(--transition) !important;
    box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.05) !important;
}
.stButton > button:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    border-color: var(--border-glow) !important;
    transform: scale(1.02) !important;
}
.stButton > button:active {
    transform: scale(0.98) !important;
}

/* ── Text Inputs ────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(0,0,0,0.5) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    padding: 0.5rem 1rem !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
    transition: var(--transition) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(255, 255, 255, 0.3) !important;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.1), inset 0 2px 4px rgba(0,0,0,0.2) !important;
}

/* ── Tabs (Apple style) ─────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.3rem !important;
    gap: 0.3rem !important;
    border: 1px solid var(--border-glass) !important;
    margin-bottom: 2rem !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: calc(var(--radius-sm) - 2px) !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1rem !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.1) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
}

/* ── Sidebar ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-glass) !important;
}
[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    background: -webkit-linear-gradient(45deg, #fff, #a1a1aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ── File Uploader ──────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.01) !important;
    border: 1px dashed rgba(255,255,255,0.15) !important;
    border-radius: var(--radius-md) !important;
    transition: var(--transition) !important;
}
[data-testid="stFileUploader"]:hover {
    background: rgba(255,255,255,0.03) !important;
    border-color: rgba(255,255,255,0.3) !important;
}

/* ── Code Blocks & Math ─────────────────────────────────────────── */
code {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 4px !important;
    color: #e2e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 0.15em 0.4em !important;
}
.katex { color: #f8fafc !important; font-size: 1.1em !important; }

/* ── Scrollbar ──────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.4); }

/* ── Topic Tags ─────────────────────────────────────────────────── */
.topic-tag {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 999px;
    padding: 0.2rem 0.8rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin: 0.2rem;
    letter-spacing: 0.02em;
}

/* ── Expander ───────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid var(--border-glass) !important;
    color: var(--text-primary) !important;
}
.streamlit-expanderContent {
    border: none !important;
    background: transparent !important;
}
</style>
"""


def inject_css() -> str:
    """Trả về tag style để inject vào Streamlit."""
    return LUXURY_CSS
