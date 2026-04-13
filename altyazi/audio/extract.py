"""FFmpeg ile ses cikarma: 16kHz mono WAV (Whisper icin ideal format)."""
from __future__ import annotations

import os
import subprocess


def extract_audio(video_path: str, output_path: str | None = None) -> str:
    """Video dosyasindan 16kHz mono WAV cikarir.

    Args:
        video_path: Giris video dosyasi.
        output_path: Cikti WAV yolu. None ise video yaninda `_audio.wav` uretir.

    Returns:
        Cikti WAV dosya yolu.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video dosyasi bulunamadi: {video_path}")

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = base + "_audio.wav"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatasi: {result.stderr[-400:]}")

    return output_path
