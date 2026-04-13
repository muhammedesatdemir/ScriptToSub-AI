"""ASS render motoru: modern stil, sari vurgu, 2-satir kurali, FFmpeg burn.

Stil sabitleri `core/config.py` icindedir — istege gore orada duzenleyin.
"""
from __future__ import annotations

import os
import re
import subprocess

from ..core.config import (
    ASS_COLOR_WHITE,
    ASS_COLOR_YELLOW,
    FONTS_DIR,
    SPLIT_CONJUNCTIONS,
    SUBTITLE_FONT_NAME,
    SUB_FONT_SIZE,
    SUB_MARGIN_LR,
    SUB_MARGIN_V,
    SUB_MAX_CHARS_PER_CUE,
    SUB_MAX_CHARS_PER_LINE,
    SUB_MAX_WORDS_PER_CUE,
    SUB_PLAY_RES_X,
    SUB_PLAY_RES_Y,
    TR_STOPWORDS,
)
from ..core.utils import seconds_to_ass_time, srt_time_to_seconds


# ============================================================
# Satir bolme + vurgu
# ============================================================

def _split_long_cue(text: str, start: float, end: float) -> list[tuple[float, float, str]]:
    """Cue'yu karakter/kelime sinirina gore boler, sureyi oranlar.

    Bolme oncelikleri:
      0 — onceki kelime ',' / ';' / ':' ile bitiyor
      1 — sonraki kelime bir baglac
      2 — orta nokta
    """
    text = text.strip()
    words = text.split()
    if not words:
        return []
    if len(text) <= SUB_MAX_CHARS_PER_CUE and len(words) <= SUB_MAX_WORDS_PER_CUE:
        return [(start, end, text)]

    n = len(words)

    def score(idx: int) -> tuple[int, int]:
        prev_word = words[idx - 1]
        next_word = words[idx]
        if prev_word.endswith((",", ";", ":")):
            priority = 0
        elif next_word.lower().strip(",.;:!?'\"") in SPLIT_CONJUNCTIONS:
            priority = 1
        else:
            priority = 2
        center_penalty = abs(idx - n / 2)
        return (priority, int(center_penalty * 10))

    best_idx = min(range(1, n), key=score)
    left_words = words[:best_idx]
    right_words = words[best_idx:]

    duration = max(end - start, 0.001)
    left_ratio = len(left_words) / n
    mid = start + duration * left_ratio

    return (
        _split_long_cue(" ".join(left_words), start, mid)
        + _split_long_cue(" ".join(right_words), mid, end)
    )


def _smart_wrap(text: str, max_chars: int = SUB_MAX_CHARS_PER_LINE) -> list[str]:
    """Tek satirlik metni en fazla iki satira dengeli boler."""
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
    """Buyuk harfle baslayan ozel isimleri ve sayilari sari yapar.

    Mevcut davranis byte-for-byte korunmustur — hem Mod A hem Mod B icin calisir.
    """
    def repl(match: "re.Match[str]") -> str:
        word = match.group(0)
        if any(ch.isdigit() for ch in word):
            return f"{ASS_COLOR_YELLOW}{word}{ASS_COLOR_WHITE}"
        first = word[0]
        if first.isalpha() and first.upper() == first and first.lower() != first:
            stripped = word.rstrip("'\u2019`.,;:!?")
            base = stripped.split("'")[0].split("\u2019")[0]
            if base and base not in TR_STOPWORDS:
                return f"{ASS_COLOR_YELLOW}{word}{ASS_COLOR_WHITE}"
        return word

    return re.sub(r"[\w\u00c7\u011e\u0130\u0131\u00d6\u015e\u00dc\u00e7\u011f\u00f6\u015f\u00fc\u2019'\-]+", repl, text)


# ============================================================
# SRT -> ASS donusumu
# ============================================================

def srt_to_ass(srt_content: str) -> str:
    """SRT icerigini, vurgulu ve modern stilli bir ASS dosyasina cevirir."""
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

    events: list[str] = []
    blocks = re.split(r"\r?\n\r?\n", srt_content.strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        timing_idx = 0 if "-->" in lines[0] else 1
        if timing_idx >= len(lines):
            continue
        timing = lines[timing_idx]
        m = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            timing,
        )
        if not m:
            continue
        start_s = srt_time_to_seconds(m.group(1))
        end_s = srt_time_to_seconds(m.group(2))
        text_lines = lines[timing_idx + 1:]
        joined = " ".join(tl.strip() for tl in text_lines if tl.strip())

        sub_cues = _split_long_cue(joined, start_s, end_s)
        for s, e, txt in sub_cues:
            wrapped = _smart_wrap(txt)
            text = "\\N".join(_highlight_words(line) for line in wrapped)
            events.append(
                f"Dialogue: 0,{seconds_to_ass_time(s)},{seconds_to_ass_time(e)},"
                f"Modern,,0,0,0,,{text}"
            )

    return header + "\n".join(events) + "\n"


# ============================================================
# Videoya gommek (FFmpeg)
# ============================================================

def burn_subtitles(video_bytes: bytes, srt_content: str, output_path: str) -> str:
    """FFmpeg ile modern ASS altyazisini videoya gomer."""
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatasi: {result.stderr[-800:]}")

    for p in (video_path, ass_path):
        try:
            os.remove(p)
        except OSError:
            pass

    return output_path
