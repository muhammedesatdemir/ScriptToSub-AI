"""SRT uretimi. Her iki mod da ayni formata yonlenir."""
from __future__ import annotations

from ..core.utils import seconds_to_srt_time


def _wrap_for_srt(text: str, max_chars: int = 32) -> str:
    """Uzun metni iki satira dengeli boler."""
    if len(text) <= max_chars:
        return text
    mid = len(text) // 2
    left = text.rfind(" ", 0, mid + 10)
    right = text.find(" ", mid - 10)
    if left == -1:
        split_pos = right
    elif right == -1:
        split_pos = left
    else:
        split_pos = left if (mid - left) <= (right - mid) else right
    if split_pos <= 0:
        return text
    return text[:split_pos] + "\n" + text[split_pos + 1:]


def segments_to_srt(segments: list[dict]) -> str:
    """Segment listesinden SRT string uretir."""
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = seconds_to_srt_time(seg["start"])
        end = seconds_to_srt_time(seg["end"])
        text = _wrap_for_srt(seg["text"])
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def generate_srt(segments: list[dict], output_path: str) -> str:
    """SRT'yi diske yazar."""
    content = segments_to_srt(segments)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
