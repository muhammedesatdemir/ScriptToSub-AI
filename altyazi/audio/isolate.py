"""Demucs v4 (htdemucs) ile vokal izolasyonu.

Beat / muzik gurultusu bulunan videolarda Whisper dogrulugunu ciddi sekilde artirir.
CUDA varsa GPU'da, yoksa CPU'da calisir. Demucs yukleme hatasi halinde None doner
ve cagriminda pipeline duz sesle devam eder.
"""
from __future__ import annotations

import os
import subprocess
import wave

from ..core.utils import safe_remove


def has_cuda() -> bool:
    """CUDA kullanilabilir mi? torch yoksa False."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def isolate_vocals(video_path: str, output_dir: str | None = None) -> str | None:
    """Demucs htdemucs ile vokal kanalini ayirir, 16kHz mono WAV dondurur.

    Args:
        video_path: Giris video dosyasi.
        output_dir: Gecici ciktilar icin dizin. None ise video dizini kullanilir.

    Returns:
        Izole vokal dosyasi (16kHz mono WAV) veya hata/yok durumunda None.
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(video_path))

    vocal_path = os.path.join(output_dir, "vocals.wav")
    hq_audio_path = os.path.join(output_dir, "hq_audio.wav")
    vocals_stereo_path = os.path.join(output_dir, "vocals_44k.wav")

    try:
        import torch
        import numpy as np
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        device = "cuda" if torch.cuda.is_available() else "cpu"

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            hq_audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg hatasi: {result.stderr[-200:]}")

        model = get_model("htdemucs")
        model.eval()
        if device == "cuda":
            model.cuda()

        with wave.open(hq_audio_path, "r") as wf:
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            raw = wf.readframes(n_frames)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            samples = samples.reshape(-1, n_channels).T

        waveform = torch.from_numpy(samples.copy())
        ref = waveform.mean(0)
        waveform = (waveform - ref.mean()) / ref.std()
        waveform = waveform.unsqueeze(0)
        if device == "cuda":
            waveform = waveform.cuda()

        with torch.no_grad():
            sources = apply_model(model, waveform, device=device)

        vocal_idx = model.sources.index("vocals")
        vocals = sources[0, vocal_idx].cpu()
        vocals = vocals * ref.std() + ref.mean()

        vocals_np = (vocals.numpy().T * 32768.0).clip(-32768, 32767).astype(np.int16)
        with wave.open(vocals_stereo_path, "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(vocals_np.tobytes())

        subprocess.run(
            ["ffmpeg", "-y", "-i", vocals_stereo_path,
             "-ar", "16000", "-ac", "1", vocal_path],
            capture_output=True, text=True,
        )

        safe_remove(hq_audio_path, vocals_stereo_path)
        return vocal_path

    except Exception as e:
        print(f"[Demucs] Vokal izolasyonu hatasi: {e}")
        safe_remove(hq_audio_path, vocals_stereo_path)
        return None
