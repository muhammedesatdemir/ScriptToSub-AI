"""Tema CSS'i, hero basligi ve sidebar toggle enjektoru.

CSS ve sidebar injection mantigi orijinal `app.py`'den byte-for-byte korunmustur.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as _components


CUSTOM_CSS = """
<style>
/* Inter — Latin + Latin Extended + Turkce karakterleri kapsar.
   'latin-ext' subset'i c,g,i,o,s,u harflerini garantiler. */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap&subset=latin,latin-ext');

:root {
    --accent: #2DD4BF;
    --accent-hover: #5EEAD4;
    --accent-dim: rgba(45, 212, 191, 0.14);
    --accent-border: rgba(45, 212, 191, 0.45);
    --bg-primary: #0B1220;
    --bg-secondary: #0E1626;
    --bg-card: #111B2E;
    --bg-elevated: #17233A;
    --border: rgba(148, 163, 184, 0.18);
    --border-strong: rgba(148, 163, 184, 0.32);
    /* Kontrast artirildi — onceki degerler cok silikti */
    --text-primary: #F8FAFC;
    --text-secondary: #CBD5E1;
    --text-dim: #94A3B8;
}

html, body, [class*="css"], .stApp, .stMarkdown, .stText, button, input, textarea, select {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', sans-serif !important;
    -webkit-font-feature-settings: "kern", "liga", "calt";
    font-feature-settings: "kern", "liga", "calt";
}
body { color: var(--text-primary); }
p, span, div, li { color: var(--text-primary); }

.stApp {
    background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(45, 212, 191, 0.08), transparent),
                linear-gradient(180deg, #0B1220 0%, #0A0F1C 100%);
    color: var(--text-primary);
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 0.75rem !important; padding-bottom: 2rem !important; max-width: 1200px; }

.hero {
    text-align: center;
    padding: 0.25rem 0 1rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.85rem;
    background: var(--accent-dim);
    border: 1px solid var(--accent-border);
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--accent);
    margin-bottom: 0.6rem;
    letter-spacing: 0.02em;
}
.hero-badge .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 10px var(--accent);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.hero h1 {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0 0 0.4rem 0;
    background: linear-gradient(135deg, #F1F5F9 0%, #2DD4BF 60%, #5EEAD4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.05;
}
.hero p {
    font-size: 0.95rem;
    color: var(--text-secondary);
    max-width: 620px;
    margin: 0 auto;
    font-weight: 400;
    line-height: 1.5;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 1rem 0;
    letter-spacing: -0.01em;
}
.section-title .icon {
    width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-dim);
    border: 1px solid var(--accent-border);
    border-radius: 8px;
    font-size: 0.85rem;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    transition: border-color 0.2s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--border-strong) !important;
}

section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}
/* Sidebar icerigi daha kompakt olsun — scroll olmasin */
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 0.1rem !important;
    padding-bottom: 0.5rem !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 0.25rem !important; }
section[data-testid="stSidebar"] h2 {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin: 0 0 0.75rem 0 !important;
    letter-spacing: -0.01em;
}
section[data-testid="stSidebar"] h3 {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    /* Onceki --text-dim cok silikti — daha parlak bir tona cekildi */
    color: #A5B4C4 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.85rem !important;
    margin-bottom: 0.4rem !important;
}
section[data-testid="stSidebar"] hr {
    border-color: var(--border);
    margin: 0.75rem 0 !important;
}
/* Sidebar icindeki widget'larin dikey bosluklarini sikistir */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.45rem !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { margin-bottom: 0 !important; }
section[data-testid="stSidebar"] .stRadio > label,
section[data-testid="stSidebar"] .stCheckbox > label,
section[data-testid="stSidebar"] .stSelectbox > label {
    font-size: 0.75rem !important;
    margin-bottom: 0.2rem !important;
    color: var(--text-secondary) !important;
}
/* Sidebar'daki select/input yukseklikleri */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    min-height: 34px !important;
    padding: 2px 8px !important;
}
section[data-testid="stSidebar"] .stCheckbox { margin: 0.2rem 0 !important; }
section[data-testid="stSidebar"] .stCheckbox label p {
    font-size: 0.8rem !important;
    color: var(--text-primary) !important;
}
/* Radio: Mod secimi butonlari kompakt */
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
    padding: 0.35rem 0.7rem !important;
    font-size: 0.78rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label p {
    color: var(--text-primary) !important;
    font-size: 0.78rem !important;
}
/* Sidebar kapatma butonu (X) */
section[data-testid="stSidebar"] .stButton > button {
    padding: 0.3rem 0.65rem !important;
    font-size: 0.95rem !important;
    min-height: 32px !important;
    line-height: 1 !important;
    color: var(--text-primary) !important;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-strong) !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    color: var(--state-error) !important;
    border-color: var(--state-error) !important;
    background: var(--state-error-bg) !important;
}
/* Expander icindeki fonetik sozluk listesi kucuk */
section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 0.45rem 0.75rem !important;
    font-size: 0.78rem !important;
}
[data-testid="stToolbar"],
[data-testid="stDeployButton"],
[data-testid="stStatusWidget"],
header [data-testid="stMainMenu"],
.stDeployButton,
button[kind="headerNoPadding"] {
    display: none !important;
    visibility: hidden !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] button,
section[data-testid="stSidebar"] button[kind="header"],
section[data-testid="stSidebar"] [data-testid="baseButton-headerNoPadding"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
button[kind="header"],
[aria-label="Open sidebar"],
[aria-label="open sidebar"],
[aria-label="Close sidebar"],
[aria-label="close sidebar"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
    height: 0 !important;
}

div[data-baseweb="select"] > div,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="input"] input {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s ease;
}
div[data-baseweb="select"] > div:hover,
div[data-testid="stTextInput"] input:hover,
div[data-testid="stTextArea"] textarea:hover {
    border-color: var(--border-strong) !important;
}
div[data-baseweb="select"] > div:focus-within,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}

label, .stRadio label, .stCheckbox label {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}
/* Widget label metinleri daha belirgin */
label p, [data-testid="stWidgetLabel"] p {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}

.stCheckbox > label > div[data-testid="stCheckbox"] > div {
    background: var(--bg-elevated);
    border: 1px solid var(--border-strong);
    border-radius: 6px;
}

div[data-testid="stRadio"] > div { gap: 0.5rem; }
div[data-testid="stRadio"] label {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.45rem 0.9rem;
    transition: all 0.15s ease;
}
div[data-testid="stRadio"] label p {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}
div[data-testid="stRadio"] label:hover { border-color: var(--accent-border); }
/* Checkbox label metni — koyu arkaplanda okunur olsun */
.stCheckbox label p,
.stCheckbox label div {
    color: var(--text-primary) !important;
}

div[data-testid="stFileUploader"] section {
    background: var(--bg-elevated) !important;
    border: 2px dashed var(--border-strong) !important;
    border-radius: 14px !important;
    padding: 2rem 1rem !important;
    transition: all 0.2s ease;
}
div[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent) !important;
    background: var(--accent-dim) !important;
}
div[data-testid="stFileUploader"] section small { color: var(--text-dim) !important; }
div[data-testid="stFileUploader"] button {
    background: transparent !important;
    border: 1px solid var(--accent-border) !important;
    color: var(--accent) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
div[data-testid="stFileUploader"] button:hover {
    background: var(--accent-dim) !important;
    border-color: var(--accent) !important;
}

.stButton > button, .stDownloadButton > button {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    padding: 0.65rem 1.25rem;
    font-weight: 500;
    font-size: 0.9rem;
    font-family: 'Inter', sans-serif;
    transition: all 0.15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: var(--accent-dim);
    transform: translateY(-1px);
}
.stButton > button:focus, .stDownloadButton > button:focus {
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
    outline: none !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2DD4BF 0%, #14B8A6 100%);
    color: #0B1220;
    border: none;
    font-weight: 700;
    font-size: 1rem;
    padding: 0.9rem 1.5rem;
    box-shadow: 0 4px 20px rgba(45, 212, 191, 0.25);
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #5EEAD4 0%, #2DD4BF 100%);
    color: #0B1220;
    box-shadow: 0 6px 28px rgba(45, 212, 191, 0.4);
    transform: translateY(-2px);
}

div[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #2DD4BF, #5EEAD4) !important;
    border-radius: 999px !important;
}
div[data-testid="stProgress"] > div > div {
    background: var(--bg-elevated) !important;
    border-radius: 999px !important;
    height: 8px !important;
}

div[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1.25rem;
    transition: all 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    border-color: var(--accent-border);
    background: var(--bg-elevated);
}
div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] label {
    color: #B8C5D6 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
div[data-testid="stMetricValue"] {
    color: var(--accent) !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}
div[data-testid="stMetricDelta"] {
    color: var(--text-secondary) !important;
}

div[data-testid="stAlert"] {
    border-radius: 12px !important;
    border-width: 1px !important;
    padding: 0.9rem 1.1rem !important;
}
div[data-baseweb="notification"] { font-family: 'Inter', sans-serif !important; }

.streamlit-expanderHeader, div[data-testid="stExpander"] summary {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}
.streamlit-expanderHeader:hover, div[data-testid="stExpander"] summary:hover {
    border-color: var(--accent-border) !important;
}
div[data-testid="stExpander"] {
    border: none !important;
    background: transparent !important;
}

code, pre, .stCode {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

hr {
    border: none;
    height: 1px;
    background: var(--border);
    margin: 2rem 0;
}

video {
    border-radius: 12px !important;
    border: 1px solid var(--border);
    max-height: 460px !important;
    width: 100% !important;
    object-fit: contain;
    background: #000;
}
div[data-testid="stVideo"] {
    display: flex;
    justify-content: center;
}

.segment-row {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    transition: all 0.15s ease;
}
.segment-row:hover {
    border-color: var(--border-strong);
    border-left-color: var(--accent-hover);
    transform: translateX(2px);
}
.segment-meta {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    font-size: 0.72rem;
    color: #A5B4C4;
    margin-bottom: 0.35rem;
    font-family: 'JetBrains Mono', monospace;
}
.segment-meta .seg-num { color: var(--accent); font-weight: 700; }
.segment-meta .seg-time { color: #CBD5E1; }
.segment-meta .seg-cps {
    margin-left: auto;
    padding: 0.1rem 0.5rem;
    background: var(--accent-dim);
    border: 1px solid var(--accent-border);
    border-radius: 999px;
    color: var(--accent);
}
.segment-text {
    color: var(--text-primary);
    font-size: 0.92rem;
    line-height: 1.5;
}

.sub-label {
    font-size: 0.75rem;
    color: #A5B4C4;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.section-title {
    color: var(--text-primary) !important;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ================================================================
   UX/UI IYILESTIRME KATMANI
   - Placeholder kontrasti
   - Turkce font feature
   - Semantik durum renkleri
   - Erisilebilirlik (focus-visible, WCAG AA)
   ================================================================ */

:root {
    /* Semantik durum renkleri */
    --state-success: #34D399;
    --state-success-bg: rgba(52, 211, 153, 0.12);
    --state-warn: #FBBF24;
    --state-warn-bg: rgba(251, 191, 36, 0.12);
    --state-error: #F87171;
    --state-error-bg: rgba(248, 113, 113, 0.14);
    --state-info: #60A5FA;
    --state-info-bg: rgba(96, 165, 250, 0.12);
    /* Tek kaynak: placeholder tonu */
    --text-placeholder: #8A9BB0;
    /* Muted — helper text icin AA uyumlu */
    --text-muted: #B5C0D0;
}

/* --- Placeholder kontrasti (tum browser'lar) --- */
input::placeholder,
textarea::placeholder,
input::-webkit-input-placeholder,
textarea::-webkit-input-placeholder,
input::-moz-placeholder,
textarea::-moz-placeholder,
input:-ms-input-placeholder,
textarea:-ms-input-placeholder {
    color: var(--text-placeholder) !important;
    opacity: 1 !important;
    font-style: normal;
    font-weight: 400;
}
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: var(--text-placeholder) !important;
    opacity: 1 !important;
}
/* BaseWeb select'in "Choose an option" pseudo-placeholder'i */
div[data-baseweb="select"] [data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="select"] div[class*="placeholder"] {
    color: var(--text-placeholder) !important;
}

/* --- Focus-visible (klavye erisilebilirligi) --- */
input:focus-visible,
textarea:focus-visible,
button:focus-visible,
select:focus-visible,
[role="button"]:focus-visible {
    outline: 2px solid var(--accent) !important;
    outline-offset: 2px !important;
}

/* --- File uploader ic metinleri — "Drag and drop" vs --- */
div[data-testid="stFileUploader"] section small,
div[data-testid="stFileUploader"] section span,
div[data-testid="stFileUploader"] section div,
div[data-testid="stFileUploader"] section p {
    color: var(--text-muted) !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] {
    color: var(--text-secondary) !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] small {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
}

/* --- Helper text / caption / st.info, st.warning, st.error, st.success --- */
div[data-testid="stAlert"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] div,
div[data-testid="stAlert"] span {
    color: var(--text-secondary) !important;
}
/* Rol-bazli arkaplan (Streamlit ikon stringine bakmadigi icin attr selector) */
div[data-testid="stAlert"][data-baseweb="notification"] { /* generic */ }
div[data-testid="stAlert"] div[data-testid="stAlertContentInfo"],
div[role="alert"][aria-live="polite"] {
    background: var(--state-info-bg) !important;
    border-left: 3px solid var(--state-info) !important;
}
div[data-testid="stAlert"] div[data-testid="stAlertContentSuccess"] {
    background: var(--state-success-bg) !important;
    border-left: 3px solid var(--state-success) !important;
}
div[data-testid="stAlert"] div[data-testid="stAlertContentWarning"] {
    background: var(--state-warn-bg) !important;
    border-left: 3px solid var(--state-warn) !important;
}
div[data-testid="stAlert"] div[data-testid="stAlertContentError"] {
    background: var(--state-error-bg) !important;
    border-left: 3px solid var(--state-error) !important;
}

/* --- Input/textarea hover + focus state'leri (WCAG uyumlu gecis) --- */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {
    color: var(--text-primary) !important;
    background: var(--bg-elevated) !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
div[data-baseweb="input"]:hover input,
div[data-baseweb="textarea"]:hover textarea {
    background: #1D2A41 !important;
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}

/* --- Typography rafine ayarlar --- */
html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
body {
    line-height: 1.55;
    letter-spacing: -0.005em;
}
p, label, div[data-testid="stMarkdownContainer"] p {
    line-height: 1.55;
}
/* Helper/caption boyutu */
.sub-label, small {
    line-height: 1.5;
    font-weight: 600;
}

/* --- Hero baslik: gradient text'in Turkce harfleri dogru cizmesi icin --- */
.hero h1 {
    -webkit-text-fill-color: transparent;
    font-feature-settings: "kern", "liga", "calt", "ss01";
}

/* --- Card iceriginde dogal metin kontrasti --- */
div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] span,
div[data-testid="stVerticalBlockBorderWrapper"] label {
    color: var(--text-primary);
}
div[data-testid="stVerticalBlockBorderWrapper"] .sub-label {
    color: var(--text-muted) !important;
}

/* --- Progress bar label metni --- */
div[data-testid="stProgress"] p {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* --- Sidebar X butonu (kapatma) tekrar gorunur yap --- */
section[data-testid="stSidebar"] .stButton > button[kind="secondary"],
section[data-testid="stSidebar"] .stButton > button {
    color: var(--text-primary) !important;
}
</style>
"""


def inject_theme() -> None:
    """CSS'i dokumana enjekte eder."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def inject_sidebar_toggle() -> None:
    """Ayarlar butonunu sag ust koseye JS ile enjekte eder."""
    _components.html(
        """
        <script>
        (function() {
          const doc = window.parent.document;
          const old = doc.getElementById('s2s-open-sb-btn');
          if (old) old.remove();

          const sb = doc.querySelector('section[data-testid="stSidebar"]');
          if (sb) {
            const w = sb.getBoundingClientRect().width;
            const ariaExpanded = sb.getAttribute('aria-expanded');
            if (w > 50 && ariaExpanded !== 'false') { return; }
          }

          const btn = doc.createElement('button');
          btn.id = 's2s-open-sb-btn';
          btn.innerHTML = '\u2699\ufe0f Ayarlar';
          btn.style.cssText = `
            position: fixed; top: 14px; right: 18px; z-index: 999999;
            background: #00E5FF; color: #001014; border: none;
            padding: 10px 18px; border-radius: 10px; font-weight: 700;
            font-family: inherit; font-size: 14px; cursor: pointer;
            box-shadow: 0 4px 14px rgba(0,229,255,0.35);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
          `;
          btn.addEventListener('click', () => {
            try {
              const ls = window.parent.localStorage;
              for (let i = ls.length - 1; i >= 0; i--) {
                const k = ls.key(i);
                if (k && (k.toLowerCase().includes('sidebar') ||
                          k.toLowerCase().includes('stsidebar'))) {
                  ls.removeItem(k);
                }
              }
            } catch (e) {}
            const url = new URL(window.parent.location.href);
            url.searchParams.set('sb', 'open');
            window.parent.location.href = url.toString();
          });
          doc.body.appendChild(btn);
        })();
        </script>
        """,
        height=0,
    )


def render_hero() -> None:
    """Sayfanin ust kismindaki hero basligi."""
    st.markdown(
        """
<div class="hero">
    <div class="hero-badge"><span class="dot"></span>Hibrit Altyazi Motoru</div>
    <h1>Script-to-Sub</h1>
    <p>Referans metinle hizalama (Mod A) veya bagimsiz AI transkripsiyon (Mod B).
    Her iki mod da Demucs vokal izolasyonu ve modern ASS stiline yonlendirilir.</p>
</div>
""",
        unsafe_allow_html=True,
    )
