"""Yardimci fonksiyonlar: zaman cevirimi, metin normalize, dosya temizligi."""
from __future__ import annotations

import os
import re


# ---------- Metin normalize ----------

def normalize_text(text: str) -> str:
    """Metni eslestirme icin normalize eder (lowercase, noktalama temizligi)."""
    text = text.lower()
    text = text.replace("'", "'").replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(
        r"[^\w\s\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc']",
        " ",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def turkish_stem(word: str) -> str:
    """Basit Turkce kok cikarma (suffix stripping)."""
    word = word.lower().rstrip(".,!?;:'\"")
    suffixes = [
        "larin", "lerin", "larini", "lerini",
        "inda", "inde",
        "daki", "deki", "taki", "teki",
        "dan", "den", "tan", "ten",
        "nin", "n\u0131n", "nun", "n\u00fcn",
        "yla", "yle",
        "ya", "ye", "na", "ne",
        "da", "de", "ta", "te",
        "in", "\u0131n", "un", "\u00fcn",
        "'n\u0131n", "'nin", "'nun", "'n\u00fcn",
        "'ya", "'ye", "'na", "'ne",
        "'da", "'de", "'ta", "'te",
        "'dan", "'den", "'tan", "'ten",
    ]
    for suffix in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[: -len(suffix)]
    return word


# ---------- Zaman formatlari ----------

def seconds_to_srt_time(seconds: float) -> str:
    """83.456 -> '00:01:23,456'."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt_time_to_seconds(ts: str) -> float:
    """'00:01:23,456' -> 83.456."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def seconds_to_ass_time(t: float) -> str:
    """83.456 -> '0:01:23.45' (ASS centisecond)."""
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ---------- Dosya temizligi ----------

def safe_remove(*paths: str) -> None:
    """Dosyalari sessizce sil — OSError'lari yut."""
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
