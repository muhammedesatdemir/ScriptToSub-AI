"""Mod A: Script-Aware Alignment pipeline'i."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..alignment import enhanced_align_words, tokenize_script
from ..audio import extract_audio, isolate_vocals
from ..core.phonetic import DEFAULT_PHONETIC_DICT
from ..core.utils import safe_remove
from ..segmentation import create_segments, optimize_segments
from ..transcription import transcribe_with_timestamps


ProgressFn = Callable[[int, str], None]


@dataclass
class ModeAResult:
    segments: list[dict]
    aligned: list[dict]
    whisper_data: dict = field(default_factory=dict)


def run_script_aware_alignment(
    video_path: str,
    script_text: str,
    work_dir: str,
    model_size: str = "large-v3-turbo",
    vocal_isolation: bool = True,
    phonetic_dict: dict | None = None,
    progress: ProgressFn | None = None,
) -> ModeAResult:
    """Mod A orkestrasyonu: ses -> Whisper -> hizalama -> segmentasyon."""
    def tick(p: int, msg: str) -> None:
        if progress:
            progress(p, msg)

    phonetic_dict = phonetic_dict or DEFAULT_PHONETIC_DICT

    whisper_input: str | None = None
    vocal_path: str | None = None

    try:
        if vocal_isolation:
            tick(5, "Vokal izolasyonu (Demucs)...")
            vocal_path = isolate_vocals(video_path, work_dir)
            if vocal_path:
                whisper_input = vocal_path

        if whisper_input is None:
            tick(10, "Ses cikariliyor...")
            whisper_input = extract_audio(video_path)

        tick(40, f"Whisper ({model_size}) calisiyor...")
        whisper_data = transcribe_with_timestamps(
            whisper_input, model_size=model_size
        )

        tick(60, "Kelimeler hizalaniyor...")
        script_tokens = tokenize_script(script_text)
        aligned = enhanced_align_words(
            script_tokens, whisper_data["all_words"], phonetic_dict
        )

        tick(80, "Segmentler olusturuluyor...")
        segments = create_segments(aligned)
        segments = optimize_segments(segments)

        tick(100, "Tamamlandi!")
        return ModeAResult(segments=segments, aligned=aligned, whisper_data=whisper_data)

    finally:
        safe_remove(whisper_input) if whisper_input else None
