"""
Script-to-Sub: Modern Streamlit Arayüzü
========================================
Video + script yükleyerek otomatik altyazı oluşturma.
Altyazıyı videoya gömme ve indirme desteği.
"""

import streamlit as st
import tempfile
import subprocess
import os
import re
import json
from pathlib import Path

from script_to_sub import (
    extract_audio,
    isolate_vocals,
    transcribe_with_timestamps,
    tokenize_script,
    enhanced_align_words,
    create_segments,
    optimize_segments,
    generate_srt,
    DEFAULT_PHONETIC_DICT,
)

# ============================================================
# Sayfa Ayarları
# ============================================================
st.set_page_config(
    page_title="Script-to-Sub",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Modern Tema — Turkuaz Accent + Koyu Arkaplan
# ============================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --accent: #2DD4BF;
    --accent-hover: #5EEAD4;
    --accent-dim: rgba(45, 212, 191, 0.12);
    --accent-border: rgba(45, 212, 191, 0.35);
    --bg-primary: #0B1220;
    --bg-secondary: #111827;
    --bg-card: #0F1A2E;
    --bg-elevated: #162033;
    --border: rgba(148, 163, 184, 0.12);
    --border-strong: rgba(148, 163, 184, 0.22);
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
    --text-dim: #64748B;
}

html, body, [class*="css"], .stApp, .stMarkdown, .stText, button, input, textarea, select {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.stApp {
    background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(45, 212, 191, 0.08), transparent),
                linear-gradient(180deg, #0B1220 0%, #0A0F1C 100%);
    color: var(--text-primary);
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 2.5rem !important; padding-bottom: 4rem !important; max-width: 1200px; }

/* ---------- Hero Başlık ---------- */
.hero {
    text-align: center;
    padding: 1.5rem 0 2.5rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2.5rem;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 1rem;
    background: var(--accent-dim);
    border: 1px solid var(--accent-border);
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--accent);
    margin-bottom: 1.25rem;
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
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0 0 0.75rem 0;
    background: linear-gradient(135deg, #F1F5F9 0%, #2DD4BF 60%, #5EEAD4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}
.hero p {
    font-size: 1.1rem;
    color: var(--text-secondary);
    max-width: 640px;
    margin: 0 auto;
    font-weight: 400;
    line-height: 1.6;
}

/* ---------- Section Başlıkları ---------- */
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

/* ---------- Card Wrapper ---------- */
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

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] > div { padding-top: 2rem; }
section[data-testid="stSidebar"] h2 {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 1.25rem;
    letter-spacing: -0.01em;
}
section[data-testid="stSidebar"] h3 {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
}
section[data-testid="stSidebar"] hr {
    border-color: var(--border);
    margin: 1.5rem 0 !important;
}
/* Sidebar kapalıyken görünen "geri aç" oku — her zaman görünür kalsın */
button[data-testid="stSidebarCollapsedControl"],
div[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: var(--accent-dim) !important;
    border: 1px solid var(--accent-border) !important;
    border-radius: 8px !important;
    color: var(--accent) !important;
    z-index: 999999 !important;
    top: 0.75rem !important;
    left: 0.75rem !important;
}

/* ---------- Inputs: selectbox, text input, textarea ---------- */
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

/* Label styling */
label, .stRadio label, .stCheckbox label {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* ---------- Checkbox ---------- */
.stCheckbox > label > div[data-testid="stCheckbox"] > div {
    background: var(--bg-elevated);
    border: 1px solid var(--border-strong);
    border-radius: 6px;
}

/* ---------- Radio ---------- */
div[data-testid="stRadio"] > div {
    gap: 0.5rem;
}
div[data-testid="stRadio"] label {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.5rem 1rem;
    transition: all 0.15s ease;
}
div[data-testid="stRadio"] label:hover {
    border-color: var(--accent-border);
}

/* ---------- File Uploader ---------- */
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
div[data-testid="stFileUploader"] section small {
    color: var(--text-dim) !important;
}
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

/* ---------- Buttons ---------- */
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

/* Primary button (Altyazı Oluştur) */
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

/* ---------- Progress Bar ---------- */
div[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #2DD4BF, #5EEAD4) !important;
    border-radius: 999px !important;
}
div[data-testid="stProgress"] > div > div {
    background: var(--bg-elevated) !important;
    border-radius: 999px !important;
    height: 8px !important;
}

/* ---------- Metrics ---------- */
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
div[data-testid="stMetricLabel"] {
    color: var(--text-dim) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
div[data-testid="stMetricValue"] {
    color: var(--accent) !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}

/* ---------- Alerts ---------- */
div[data-testid="stAlert"] {
    border-radius: 12px !important;
    border-width: 1px !important;
    padding: 0.9rem 1.1rem !important;
}
div[data-baseweb="notification"] {
    font-family: 'Inter', sans-serif !important;
}

/* ---------- Expander ---------- */
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

/* ---------- Code block ---------- */
code, pre, .stCode {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

/* ---------- Divider ---------- */
hr {
    border: none;
    height: 1px;
    background: var(--border);
    margin: 2rem 0;
}

/* ---------- Video Player ---------- */
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

/* ---------- Segment önizleme satırı ---------- */
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
    color: var(--text-dim);
    margin-bottom: 0.35rem;
    font-family: 'JetBrains Mono', monospace;
}
.segment-meta .seg-num {
    color: var(--accent);
    font-weight: 700;
}
.segment-meta .seg-time {
    color: var(--text-secondary);
}
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

/* ---------- Sub label (küçük etiket) ---------- */
.sub-label {
    font-size: 0.78rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* Scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ============================================================
# Session State
# ============================================================
for key in ("srt_content", "segments", "aligned", "sub_video_path", "sub_video_filename"):
    st.session_state.setdefault(key, None)


# Oturum boyunca kalıcı bir çalışma dizini — download sırasında
# dosyanın yaşaması gerektiği için TemporaryDirectory KULLANMIYORUZ.
if "work_dir" not in st.session_state:
    st.session_state.work_dir = tempfile.mkdtemp(prefix="script2sub_")


# ============================================================
# Yardımcı: Altyazıyı videoya göm
# ============================================================
# ---------- Modern altyazı stili (Reels/Shorts safe-zone) ----------
FONTS_DIR = Path(__file__).parent / "fonts"
SUBTITLE_FONT_NAME = "Montserrat Black"

# Sosyal medya safe-zone: TikTok/Reels alt UI ~%18, üst ~%12.
# 1080x1920 referansla altyazıyı %72 yükseklikte konumlandırıyoruz.
# PlayResY=1920 ile MarginV=540 → ekranın altından 540px yukarıda (yaklaşık y=1380, %72).
SUB_PLAY_RES_X = 1080
SUB_PLAY_RES_Y = 1920
SUB_MARGIN_V = 410   # Alt UI butonlarının üstünde, aksiyona daha az girer
SUB_MARGIN_LR = 60   # Yatay safe-zone — sağdan/soldan taşmayı engeller
SUB_FONT_SIZE = 82   # Reels için kalın, biraz daha kompakt
SUB_MAX_CHARS_PER_LINE = 28  # Akıllı satır kırma eşiği

# Türkçe küçük bağlaç/ek listesi — büyük harfle başlasa bile özel isim sayma
TR_STOPWORDS = {
    "Ve", "Veya", "Ama", "Fakat", "Lakin", "Çünkü", "Yani", "Ki", "Da", "De",
    "Bir", "Bu", "Şu", "O", "Ben", "Sen", "Biz", "Siz", "Onlar",
    "Ne", "Niye", "Neden", "Nasıl", "Hangi", "Her", "Bazı", "Bütün", "Tüm",
    "Çok", "Az", "Daha", "En", "Hem", "Ya", "İse", "İçin", "Gibi", "Kadar",
}


def _srt_time_to_ass(ts: str) -> str:
    """'00:01:23,456' -> '0:01:23.45' (ASS centisecond)."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    cs = int(round(int(ms) / 10))
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def _smart_wrap(text: str, max_chars: int = SUB_MAX_CHARS_PER_LINE) -> list[str]:
    """Tek satırlık metni en fazla iki satıra dengeli böler.

    - Uzunluk eşiğin altındaysa olduğu gibi döner.
    - Aksi halde kelime sınırlarında, iki satırın uzunluk farkı en az
      olacak biçimde böler (görsel denge).
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    if len(words) < 2:
        return [text]

    best_idx = 1
    best_diff = float("inf")
    for i in range(1, len(words)):
        left = " ".join(words[:i])
        right = " ".join(words[i:])
        # İki satır da eşiğe yakın olmalı; aşan kombinasyonlar cezalı
        penalty = 0
        if len(left) > max_chars:
            penalty += (len(left) - max_chars) * 4
        if len(right) > max_chars:
            penalty += (len(right) - max_chars) * 4
        diff = abs(len(left) - len(right)) + penalty
        if diff < best_diff:
            best_diff = diff
            best_idx = i

    return [" ".join(words[:best_idx]), " ".join(words[best_idx:])]


def _highlight_words(text: str) -> str:
    """Büyük harfle başlayan özel isimleri ve sayıları sarı renge boyar."""
    yellow_open = r"{\c&H00FFFF&}"
    white_close = r"{\c&HFFFFFF&}"

    def repl(match: "re.Match[str]") -> str:
        word = match.group(0)
        # Sayı içeriyorsa (100, 3-2, 90'ında vb.)
        if any(ch.isdigit() for ch in word):
            return f"{yellow_open}{word}{white_close}"
        # Büyük harfle başlıyor + stopword değilse
        first = word[0]
        if first.isalpha() and first.upper() == first and first.lower() != first:
            stripped = word.rstrip("'’`.,;:!?")
            base = stripped.split("'")[0].split("’")[0]
            if base and base not in TR_STOPWORDS:
                return f"{yellow_open}{word}{white_close}"
        return word

    # Token = harf/rakam/kesme işareti/tire dizisi
    return re.sub(r"[\wÇĞİıÖŞÜçğıöşü’'\-]+", repl, text)


def srt_to_ass(srt_content: str) -> str:
    """SRT içeriğini, vurgulu ve modern stilli bir ASS dosyasına dönüştürür."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {SUB_PLAY_RES_X}
PlayResY: {SUB_PLAY_RES_Y}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Modern,{SUBTITLE_FONT_NAME},{SUB_FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,2,0,1,5,2,2,{SUB_MARGIN_LR},{SUB_MARGIN_LR},{SUB_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    blocks = re.split(r"\r?\n\r?\n", srt_content.strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        # 1. satır index olabilir, ya da timing
        timing_idx = 0 if "-->" in lines[0] else 1
        if timing_idx >= len(lines):
            continue
        timing = lines[timing_idx]
        m = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", timing)
        if not m:
            continue
        start = _srt_time_to_ass(m.group(1))
        end = _srt_time_to_ass(m.group(2))
        text_lines = lines[timing_idx + 1:]
        # SRT'deki olası satır kırılımlarını birleştir, sonra akıllı yeniden böl
        joined = " ".join(tl.strip() for tl in text_lines if tl.strip())
        wrapped = _smart_wrap(joined)
        text = "\\N".join(_highlight_words(line) for line in wrapped)
        events.append(f"Dialogue: 0,{start},{end},Modern,,0,0,0,,{text}")

    return header + "\n".join(events) + "\n"


def burn_subtitles(video_bytes: bytes, srt_content: str, output_path: str) -> str:
    """FFmpeg ile modern ASS altyazısını videoya gömer."""
    work_dir = os.path.dirname(output_path)
    video_path = os.path.join(work_dir, "_burn_input.mp4")
    ass_path = os.path.join(work_dir, "_burn_subs.ass")

    with open(video_path, "wb") as f:
        f.write(video_bytes)

    ass_content = srt_to_ass(srt_content)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    fonts_escaped = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")

    vf = f"ass='{ass_escaped}':fontsdir='{fonts_escaped}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:a", "copy",
        "-preset", "fast",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {result.stderr[-800:]}")

    for p in (video_path, ass_path):
        try:
            os.remove(p)
        except OSError:
            pass

    return output_path


# ============================================================
# Hero Başlık
# ============================================================
st.markdown(
    """
<div class="hero">
    <div class="hero-badge"><span class="dot"></span>Script-Tabanlı Altyazı Motoru</div>
    <h1>Script-to-Sub</h1>
    <p>Videonuzu ve konuşma metninizi yükleyin; sistem sesi otomatik tanıyıp
    script'e kelime düzeyinde hizalayarak TDK uyumlu, profesyonel bir altyazı üretsin.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# Sidebar: Ayarlar
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️  Ayarlar")

    st.markdown("### Transkripsiyon")
    model_size = st.selectbox(
        "Whisper Modeli",
        ["large-v3-turbo", "large-v3", "medium", "small", "base"],
        index=0,
        help="large-v3-turbo: en hızlı ve isabetli seçenek.",
    )

    vocal_isolation = st.checkbox(
        "Vokal İzolasyonu (Demucs)",
        value=True,
        help="Arka plan müziği veya beat varken etkinleştirin.",
    )

    st.markdown("### Fonetik Sözlük")
    use_custom_dict = st.checkbox("Özel sözlük kullan", value=False)
    custom_dict = None
    if use_custom_dict:
        dict_file = st.file_uploader(
            "Sözlük JSON dosyası",
            type=["json"],
            label_visibility="collapsed",
        )
        if dict_file:
            custom_dict = json.loads(dict_file.read().decode("utf-8"))
            st.success(f"Sözlük yüklendi — {len(custom_dict)} girdi")

    with st.expander("Varsayılan fonetik eşleştirmeler"):
        for name, variants in DEFAULT_PHONETIC_DICT.items():
            st.markdown(
                f"<div style='font-size:0.82rem;padding:0.25rem 0;"
                f"border-bottom:1px solid rgba(148,163,184,0.08);'>"
                f"<span style='color:#2DD4BF;font-weight:600;'>{name}</span> "
                f"<span style='color:#64748B;'>→ {', '.join(variants)}</span></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.72rem;color:#64748B;text-align:center;"
        "line-height:1.5;'>Script-to-Sub<br/>Hibrit STT + Forced Alignment</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# Ana İçerik: Giriş Paneli
# ============================================================
col1, col2 = st.columns(2, gap="large")

with col1:
    with st.container(border=True):
        st.markdown(
            '<div class="section-title"><span class="icon">🎬</span>Video Dosyası</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sub-label">Desteklenen formatlar: MP4, MKV, AVI, MOV, WEBM</div>',
            unsafe_allow_html=True,
        )
        video_file = st.file_uploader(
            "Video yükle",
            type=["mp4", "mkv", "avi", "mov", "webm"],
            label_visibility="collapsed",
        )
        if video_file:
            st.video(video_file)

with col2:
    with st.container(border=True):
        st.markdown(
            '<div class="section-title"><span class="icon">📝</span>Script Metni</div>',
            unsafe_allow_html=True,
        )
        script_input_mode = st.radio(
            "Script girişi",
            ["Dosya yükle", "Manuel yaz"],
            horizontal=True,
            label_visibility="collapsed",
        )

        script_text = ""
        if script_input_mode == "Dosya yükle":
            st.markdown(
                '<div class="sub-label">TXT dosyası yükleyin</div>',
                unsafe_allow_html=True,
            )
            script_file = st.file_uploader(
                "Script dosyası",
                type=["txt"],
                label_visibility="collapsed",
            )
            if script_file:
                script_text = script_file.read().decode("utf-8")
                st.text_area(
                    "Önizleme",
                    script_text,
                    height=180,
                    disabled=True,
                    label_visibility="collapsed",
                )
        else:
            st.markdown(
                '<div class="sub-label">Metni aşağıya yazın veya yapıştırın</div>',
                unsafe_allow_html=True,
            )
            script_text = st.text_area(
                "Script metni",
                height=200,
                placeholder="Video metnini buraya yapıştırın...",
                label_visibility="collapsed",
            )

# ============================================================
# Altyazı Oluştur Butonu
# ============================================================
st.markdown("<div style='margin: 2rem 0 1rem 0;'></div>", unsafe_allow_html=True)

if st.button("✨  Altyazı Oluştur", type="primary", use_container_width=True):
    if not video_file:
        st.error("Lütfen bir video dosyası yükleyin.")
    elif not script_text.strip():
        st.error("Lütfen script metnini girin.")
    else:
        st.session_state.srt_content = None
        st.session_state.segments = None
        st.session_state.aligned = None
        # Önceki altyazılı video dosyasını da temizle
        old_path = st.session_state.get("sub_video_path")
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
        st.session_state.sub_video_path = None
        st.session_state.sub_video_filename = None

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, video_file.name)
            with open(video_path, "wb") as f:
                f.write(video_file.getbuffer())

            srt_path = os.path.join(tmpdir, "output.srt")
            progress = st.progress(0, text="Başlatılıyor...")

            try:
                whisper_input = None
                if vocal_isolation:
                    progress.progress(5, text="Vokal izolasyonu (Demucs)... (1-2 dk sürebilir)")
                    vocal_path = isolate_vocals(video_path, tmpdir)
                    if vocal_path:
                        whisper_input = vocal_path

                if whisper_input is None:
                    progress.progress(10, text="Ses çıkarılıyor...")
                    whisper_input = extract_audio(video_path)

                progress.progress(40, text=f"Whisper ({model_size}) çalışıyor...")
                whisper_data = transcribe_with_timestamps(
                    whisper_input, language="tr", model_size=model_size
                )

                if os.path.exists(whisper_input):
                    try:
                        os.remove(whisper_input)
                    except OSError:
                        pass

                progress.progress(60, text="Metin eşleştirme yapılıyor...")
                script_tokens = tokenize_script(script_text)
                phonetic_dict = custom_dict if custom_dict else DEFAULT_PHONETIC_DICT
                aligned = enhanced_align_words(
                    script_tokens, whisper_data["all_words"], phonetic_dict
                )

                progress.progress(80, text="Segmentler oluşturuluyor...")
                segments = create_segments(aligned)
                segments = optimize_segments(segments)
                generate_srt(segments, srt_path)

                progress.progress(100, text="Tamamlandı!")

                with open(srt_path, "r", encoding="utf-8") as f:
                    st.session_state.srt_content = f.read()
                st.session_state.segments = segments
                st.session_state.aligned = aligned

                st.rerun()

            except Exception as e:
                progress.progress(0, text="Hata oluştu!")
                st.error(f"Hata: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# ============================================================
# Sonuçlar
# ============================================================
if st.session_state.srt_content and st.session_state.segments:
    segments = st.session_state.segments
    aligned = st.session_state.aligned
    srt_content = st.session_state.srt_content

    st.markdown("<hr/>", unsafe_allow_html=True)

    match_types = {}
    for a in aligned:
        mt = a["match_type"]
        match_types[mt] = match_types.get(mt, 0) + 1
    exact = match_types.get("exact", 0) + match_types.get("stem", 0)
    total = len(aligned)
    pct = 100 * exact // max(total, 1)

    st.markdown(
        f"""
<div style='background:linear-gradient(135deg,rgba(45,212,191,0.12),rgba(45,212,191,0.04));
border:1px solid rgba(45,212,191,0.35);border-radius:14px;padding:1.1rem 1.35rem;
margin-bottom:1.5rem;display:flex;align-items:center;gap:0.75rem;'>
<span style='font-size:1.25rem;'>✅</span>
<span style='color:#F1F5F9;font-weight:500;'>Altyazı hazır —
<span style='color:#2DD4BF;font-weight:700;'>{len(segments)}</span> segment,
<span style='color:#2DD4BF;font-weight:700;'>{len(aligned)}</span> kelime eşleşti.</span>
</div>
""",
        unsafe_allow_html=True,
    )

    # İstatistikler
    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Kelime", f"{total}")
    m2.metric("Doğrudan Eşleşme", f"{pct}%", delta=f"{exact}/{total}", delta_color="off")
    m3.metric("Segment Sayısı", f"{len(segments)}")

    # İndirme
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title"><span class="icon">⬇️</span>İndirme</div>',
        unsafe_allow_html=True,
    )

    dl1, dl2 = st.columns(2)

    # Video dosya adını session'a kaydet — re-run'larda kaybolmasın
    if video_file and not st.session_state.sub_video_filename:
        st.session_state.sub_video_filename = Path(video_file.name).stem

    display_stem = st.session_state.sub_video_filename or (
        Path(video_file.name).stem if video_file else "output"
    )

    with dl1:
        st.download_button(
            label="📄  SRT Dosyasını İndir",
            data=srt_content,
            file_name=f"{display_stem}.srt",
            mime="text/plain",
            use_container_width=True,
            key="dl_srt",
        )

    with dl2:
        sub_path = st.session_state.sub_video_path
        if sub_path and os.path.exists(sub_path):
            # Dosyadan oku — Streamlit büyük bytes'ı burada cache'ler
            with open(sub_path, "rb") as f:
                video_data = f.read()
            st.download_button(
                label="🎥  Altyazılı Videoyu İndir",
                data=video_data,
                file_name=f"{display_stem}_altyazili.mp4",
                mime="video/mp4",
                use_container_width=True,
                key="dl_burned_video",
            )
        elif video_file:
            if st.button("🔥  Altyazıyı Videoya Göm", use_container_width=True, key="btn_burn"):
                with st.spinner("Video oluşturuluyor... (FFmpeg çalışıyor)"):
                    try:
                        video_bytes = video_file.getbuffer().tobytes()
                        output_path = os.path.join(
                            st.session_state.work_dir,
                            f"{display_stem}_altyazili.mp4",
                        )
                        burn_subtitles(video_bytes, srt_content, output_path)
                        st.session_state.sub_video_path = output_path
                        st.rerun()
                    except Exception as e:
                        st.error(f"Video oluşturma hatası: {str(e)}")

    # Altyazılı video önizleme
    if st.session_state.sub_video_path and os.path.exists(st.session_state.sub_video_path):
        st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title"><span class="icon">▶️</span>Altyazılı Video Önizleme</div>',
            unsafe_allow_html=True,
        )
        pv_left, pv_mid, pv_right = st.columns([1, 2, 1])
        with pv_mid:
            # Dosya yolundan göster — bytes bellekte tutmuyoruz
            st.video(st.session_state.sub_video_path)

    # Segment önizleme
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title"><span class="icon">📋</span>Segment Önizleme</div>',
        unsafe_allow_html=True,
    )

    segments_html = []
    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        cps = seg.get("chars_per_sec", len(seg["text"]) / max(dur, 0.1))
        # HTML içinde güvenli gösterim için temel escape
        safe_text = (
            seg["text"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        segments_html.append(
            f"""<div class="segment-row">
    <div class="segment-meta">
        <span class="seg-num">#{i:02d}</span>
        <span class="seg-time">{seg['start']:.1f}s → {seg['end']:.1f}s · {dur:.1f}s</span>
        <span class="seg-cps">{cps:.0f} chr/s</span>
    </div>
    <div class="segment-text">{safe_text}</div>
</div>"""
        )
    st.markdown("".join(segments_html), unsafe_allow_html=True)

    with st.expander("📜  Ham SRT Dosyası"):
        st.code(srt_content, language=None)
