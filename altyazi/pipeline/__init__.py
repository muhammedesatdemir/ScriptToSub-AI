"""Pipeline: iki modun orkestrasyonu.

- Mod A: run_script_aware_alignment (referans metin + ses -> hizali altyazi)
- Mod B: run_autonomous_transcription (sadece ses -> AI-refined altyazi)
"""
from .mode_a import run_script_aware_alignment
from .mode_b import run_autonomous_transcription

__all__ = ["run_script_aware_alignment", "run_autonomous_transcription"]
