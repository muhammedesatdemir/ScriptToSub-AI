"""Mod B: Autonomous AI Transcription pipeline'i.

Akis:
  1. Video -> (Demucs) -> 16kHz vokal
  2. faster-whisper -> {all_words, full_text}
  3. Gemini Flash, full_text'i fonetik/TDK/sayi olarak duzeltir -> refined_text
  4. refined_text kullanici script'i gibi davranir; enhanced_align_words
     Whisper kelime timestamps'i ile kelime-seviye hizalar
  5. create_segments/optimize_segments dogal cumle sinirlarinda segmentler uretir
  6. split_segment 2-satir (42 kar / 8 kelime) kuralini zorlar

Gemini basarisiz olursa: refined_text = full_text (ayni mantik, sadece ham metin).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..alignment import enhanced_align_words, tokenize_script
from ..audio import extract_audio, isolate_vocals
from ..core.utils import safe_remove
from ..refinement import refine_full_text
from ..segmentation import (
    create_segments,
    optimize_segments,
    split_segment,
)
from ..transcription import transcribe_with_timestamps


ProgressFn = Callable[[int, str], None]


@dataclass
class ModeBResult:
    segments: list[dict]
    whisper_data: dict = field(default_factory=dict)
    refined_text: str = ""
    refined: bool = False


def run_autonomous_transcription(
    video_path: str,
    work_dir: str,
    video_context: str = "",
    model_size: str = "large-v3-turbo",
    vocal_isolation: bool = True,
    use_gemini: bool = True,
    progress: ProgressFn | None = None,
) -> ModeBResult:
    """Mod B orkestrasyonu."""
    def tick(p: int, msg: str) -> None:
        if progress:
            progress(p, msg)

    whisper_input: str | None = None

    try:
        if vocal_isolation:
            tick(5, "Vokal izolasyonu (Demucs)...")
            vocal = isolate_vocals(video_path, work_dir)
            if vocal:
                whisper_input = vocal

        if whisper_input is None:
            tick(10, "Ses cikariliyor...")
            whisper_input = extract_audio(video_path)

        tick(35, f"Whisper ({model_size}) calisiyor...")
        whisper_data = transcribe_with_timestamps(
            whisper_input, model_size=model_size
        )

        full_text = whisper_data.get("full_text", "").strip()
        if not full_text or not whisper_data.get("all_words"):
            raise RuntimeError("Whisper hic kelime uretemedi.")

        # --- Gemini full-text refinement ---
        refined_text = full_text
        refined = False
        if use_gemini:
            tick(55, "Gemini Flash metni duzeltiyor...")
            try:
                refined_text = refine_full_text(full_text, video_context=video_context)
                refined = True
            except Exception as e:
                print(f"[Mod B] Gemini refinement atlandi: {e}")
                refined_text = full_text

        # --- Duzeltilmis metni kelime-seviye Whisper'a hizala ---
        tick(75, "Metin kelime-seviye hizalaniyor...")
        script_tokens = tokenize_script(refined_text)
        aligned = enhanced_align_words(
            script_tokens, whisper_data["all_words"], phonetic_dict=None
        )

        # Eger hizalama cok zayifsa (orn. Gemini metni fazla degistirdi)
        # ham full_text'e dus.
        if not aligned:
            print("[Mod B] Refined metin hizalanamadi, ham full_text'e donuluyor.")
            script_tokens = tokenize_script(full_text)
            aligned = enhanced_align_words(
                script_tokens, whisper_data["all_words"], phonetic_dict=None
            )
            refined = False
            refined_text = full_text

        tick(88, "Segmentler olusturuluyor...")
        segments = create_segments(aligned)
        segments = optimize_segments(segments)

        # 2-satir kurali (42 kar / 8 kelime)
        split_out: list[dict] = []
        for seg in segments:
            split_out.extend(split_segment(seg))
        split_out = optimize_segments(split_out)

        tick(100, "Tamamlandi!")
        return ModeBResult(
            segments=split_out,
            whisper_data=whisper_data,
            refined_text=refined_text,
            refined=refined,
        )

    finally:
        if whisper_input:
            safe_remove(whisper_input)
