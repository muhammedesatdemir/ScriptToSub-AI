"""Merkezi konfigurasyon: ASS stili, safe-zone, limitler, yol sabitleri.

Tum modullerin tek kaynagi. Degerleri degistirmek icin sadece burayi duzenle.
"""
from pathlib import Path

# ---------- Yollar ----------
PACKAGE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = PACKAGE_DIR / "fonts"

# ---------- Whisper ----------
DEFAULT_WHISPER_MODEL = "large-v3-turbo"
WHISPER_LANGUAGE = "tr"

# ---------- Gemini (Mod B refinement) ----------
# Gemini model fallback listesi (2026 Nisan itibariyle guncel).
#
# Siralama gerekcesi:
# 1) gemini-2.5-flash-lite — 2.5 ailesinin en hizli/ucuz varyanti; free-tier
#    erisilebilirligi yuksek, kalite refinement icin yeterli.
# 2) gemini-2.5-flash      — daha guclu, genel amacli; lite cekmezse ikinci aday.
# 3) gemini-2.0-flash      — deprecated, 1 Haziran 2026'da kapanacak. Sadece
#    gecici uyumluluk fallback'i olarak en sonda.
#
# Bilinerek DISARIDA birakilanlar:
# - gemini-1.5-flash / 1.5-flash-8b : 29 Eylul 2025'te retire edildiler.
GEMINI_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
)
GEMINI_MODEL = GEMINI_MODELS[0]  # geriye donuk uyumluluk (tek-model API'si icin)
GEMINI_SECRET_KEY = "GEMINI_API_KEY"  # .streamlit/secrets.toml

# ---------- ASS altyazi stili (Reels/Shorts safe-zone) ----------
SUBTITLE_FONT_NAME = "Montserrat Black"
SUB_PLAY_RES_X = 1080
SUB_PLAY_RES_Y = 1920
SUB_MARGIN_V = 410
SUB_MARGIN_LR = 60
SUB_FONT_SIZE = 82

# 2-satir kurali
SUB_MAX_CHARS_PER_LINE = 28
SUB_MAX_CHARS_PER_CUE = 42
SUB_MAX_WORDS_PER_CUE = 8

# Renkler (ASS BGR formati)
ASS_COLOR_WHITE = r"{\c&HFFFFFF&}"
ASS_COLOR_YELLOW = r"{\c&H00FFFF&}"

# ---------- Bolme oncelikleri ----------
SPLIT_CONJUNCTIONS = {"ve", "ama", "ise", "fakat", "ancak", "cunku", "ki", "ya", "veya"}

TR_STOPWORDS = {
    "Ve", "Veya", "Ama", "Fakat", "Lakin", "Cunku", "Yani", "Ki", "Da", "De",
    "Bir", "Bu", "Su", "O", "Ben", "Sen", "Biz", "Siz", "Onlar",
    "Ne", "Niye", "Neden", "Nasil", "Hangi", "Her", "Bazi", "Butun", "Tum",
    "Cok", "Az", "Daha", "En", "Hem", "Ya", "Ise", "Icin", "Gibi", "Kadar",
}

# ---------- Segment olusturma ----------
SEG_MAX_CHARS = 60
SEG_MAX_DURATION = 5.0
SEG_MIN_DURATION = 0.8

# Dogal bolunme
SENTENCE_END_CHARS = {".", "!", "?"}
BREAK_AFTER_PUNCT = {",", ";", ":"}
BREAK_AFTER_WORDS = {"da", "de", "ve", "ama", "ise", "ile", "ki",
                     "fakat", "ancak", "lakin", "oysa"}
