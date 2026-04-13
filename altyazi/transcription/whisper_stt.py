"""faster-whisper (stable-ts) ile kelime-seviye timestamp uretimi."""
from __future__ import annotations

import os

from ..core.config import DEFAULT_WHISPER_MODEL, WHISPER_LANGUAGE


def transcribe_with_timestamps(
    audio_path: str,
    language: str = WHISPER_LANGUAGE,
    model_size: str = DEFAULT_WHISPER_MODEL,
    device: str = "cpu",
    compute_type: str = "int8",
) -> dict:
    """Ses dosyasini transkribe edip kelime-seviye zaman damgalari alir.

    Returns:
        {
            "segments": [{start, end, text, words: [{word, start, end}, ...]}, ...],
            "all_words": [{word, start, end}, ...],
            "full_text": str,
        }
    """
    import stable_whisper

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {audio_path}")

    model = stable_whisper.load_faster_whisper(
        model_size, device=device, compute_type=compute_type
    )
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    segments: list[dict] = []
    all_words: list[dict] = []
    for segment in result.segments:
        seg_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "words": [],
        }
        for word in segment.words:
            word_data = {
                "word": word.word.strip(),
                "start": word.start,
                "end": word.end,
            }
            seg_data["words"].append(word_data)
            all_words.append(word_data)
        segments.append(seg_data)

    return {
        "segments": segments,
        "all_words": all_words,
        "full_text": result.text.strip(),
    }
