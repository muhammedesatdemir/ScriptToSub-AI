"""Segment uretimi, optimizasyon ve 2-satir kurali bolunmesi.

- `create_segments` + `optimize_segments`: Mod A (hizalanmis kelimelerden) icin.
- `segments_from_whisper`: Mod B (ham Whisper ciktisi) icin kelime akisini segmentlere cevirir.
- `split_segment`: 42 karakter / 8 kelime limitini asan segmentleri oransal olarak boler.
"""
from __future__ import annotations

import re

from ..core.config import (
    BREAK_AFTER_PUNCT,
    BREAK_AFTER_WORDS,
    SEG_MAX_CHARS,
    SEG_MAX_DURATION,
    SEG_MIN_DURATION,
    SENTENCE_END_CHARS,
    SUB_MAX_CHARS_PER_CUE,
    SUB_MAX_WORDS_PER_CUE,
)


# ============================================================
# Mod A: Hizalanmis kelimelerden segment olusturma
# ============================================================

def create_segments(
    aligned_words: list[dict],
    max_chars: int = SEG_MAX_CHARS,
    max_duration: float = SEG_MAX_DURATION,
    min_duration: float = SEG_MIN_DURATION,
) -> list[dict]:
    """Eslesmis kelimeleri altyazi segmentlerine boler."""
    if not aligned_words:
        return []

    segments: list[dict] = []
    current_words: list[dict] = []
    current_text = ""
    seg_start: float | None = None

    for word_info in aligned_words:
        word = word_info["script_word"]
        w_start = word_info["start"]
        w_end = word_info["end"]

        if seg_start is None:
            seg_start = w_start

        test_text = (current_text + " " + word).strip() if current_text else word
        current_duration = w_end - seg_start

        if (len(test_text) > max_chars or current_duration > max_duration) and current_words:
            segments.append({
                "start": seg_start,
                "end": current_words[-1]["end"],
                "text": current_text,
            })
            current_words = []
            current_text = ""
            seg_start = w_start

        current_words.append(word_info)
        current_text = (current_text + " " + word).strip() if current_text else word
        current_duration = w_end - seg_start

        last_char = word[-1] if word else ""
        if last_char in SENTENCE_END_CHARS:
            segments.append({
                "start": seg_start,
                "end": w_end,
                "text": current_text,
            })
            current_words = []
            current_text = ""
            seg_start = None
            continue

        word_clean = word.rstrip(".,!?;:'\"").lower()
        if (last_char in BREAK_AFTER_PUNCT or word_clean in BREAK_AFTER_WORDS) and \
                len(current_text) > 35 and current_duration > 1.8:
            segments.append({
                "start": seg_start,
                "end": w_end,
                "text": current_text,
            })
            current_words = []
            current_text = ""
            seg_start = None

    if current_words:
        segments.append({
            "start": seg_start,
            "end": current_words[-1]["end"],
            "text": current_text,
        })

    # Minimum sure kontrolu
    merged: list[dict] = []
    for seg in segments:
        duration = seg["end"] - seg["start"]
        if merged and duration < min_duration:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] += " " + seg["text"]
        else:
            merged.append(seg)

    return merged


def optimize_segments(segments: list[dict]) -> list[dict]:
    """TDK uyumu + okuma hizi metadatasi (chars_per_sec) ekler."""
    optimized: list[dict] = []
    for seg in segments:
        text = re.sub(r"\s+", " ", seg["text"].strip())
        duration = seg["end"] - seg["start"]
        cps = len(text) / max(duration, 0.1)
        optimized.append({
            **seg,
            "text": text,
            "chars_per_sec": round(cps, 1),
        })
    return optimized


# ============================================================
# Mod B: Ham Whisper segment/kelime akisindan segment olusturma
# ============================================================

def segments_from_whisper(whisper_data: dict) -> list[dict]:
    """Whisper segmentlerini (words + text) standart segment listesine cevirir.

    Whisper'in dogal segmentasyonunu kullanir; boyut/sure limitleri
    `split_segment` tarafindan sonradan zorlanir.
    """
    segments: list[dict] = []
    for seg in whisper_data.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        segments.append({
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "text": text,
            "words": seg.get("words", []),
        })
    return segments


# ============================================================
# 2-Satir Kurali: Orantili Bolme
# ============================================================

def split_segment(
    segment: dict,
    max_chars: int = SUB_MAX_CHARS_PER_CUE,
    max_words: int = SUB_MAX_WORDS_PER_CUE,
) -> list[dict]:
    """42 karakter / 8 kelime sinirini asan segmenti oransal olarak boler.

    Bolunme sureleri kelime sayisina gore orantilanir. Fonksiyon recursive'dir:
    parcalar hala uzunsa tekrar bolunur.
    """
    text = segment["text"].strip()
    start = float(segment["start"])
    end = float(segment["end"])
    words = text.split()

    if not words:
        return []
    if len(text) <= max_chars and len(words) <= max_words:
        return [{**segment, "text": text, "start": start, "end": end}]

    # En iyi bolme noktasini bul — ortalanma tercih edilir
    n = len(words)
    best_idx = max(1, n // 2)
    left_words = words[:best_idx]
    right_words = words[best_idx:]

    duration = max(end - start, 0.001)
    left_ratio = len(left_words) / n
    mid = start + duration * left_ratio

    left_seg = {**segment, "text": " ".join(left_words), "start": start, "end": mid}
    right_seg = {**segment, "text": " ".join(right_words), "start": mid, "end": end}

    return (
        split_segment(left_seg, max_chars, max_words)
        + split_segment(right_seg, max_chars, max_words)
    )
