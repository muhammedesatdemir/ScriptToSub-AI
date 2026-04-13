"""Script metnini kelime token'larina ayirir."""
from __future__ import annotations

import re

from ..core.utils import normalize_text


def tokenize_script(script_text: str) -> list[dict]:
    """Script'i kelimelere ayirir; her kelimenin orijinal ve normalize halini tutar."""
    clean = re.sub(r"\s+", " ", script_text.strip())
    return [
        {"original": w, "normalized": normalize_text(w)}
        for w in clean.split()
    ]
