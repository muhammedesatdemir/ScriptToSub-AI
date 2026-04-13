"""Fonetik sozluk: Whisper'in Turkce'de yanlis duydugu isimler icin duzeltme haritasi."""
from __future__ import annotations

import json
import os

from .utils import normalize_text


DEFAULT_PHONETIC_DICT: dict[str, list[str]] = {
    "Dries Mertens": ["dris mertens", "dris mertenz", "dries mertens", "driyes mertens"],
    "Hakim Ziyech": ["hakim ziyes", "ziyes", "ziye\u015f", "ziyec", "hakim ziye\u015f"],
    "Kerem Demirbay": ["kerem demirbay"],
    "Icardi": ["ikardi", "\u0130kardi", "icardi", "ikard\u0131"],
    "Philippe Coutinho": ["kutinyo", "filipi kutinyo", "koutinho", "kutinho"],
    "Galatasaray": ["galatasaray"],
    "Fenerbah\u00e7e": ["fenerbah\u00e7e"],
    "Be\u015fikta\u015f": ["be\u015fikta\u015f"],
    "Kas\u0131mpa\u015fa": ["kas\u0131mpa\u015fa", "kasimpasa"],
    "Adana Demirspor": ["adana demirspor"],
    "Karag\u00fcmr\u00fck": ["karag\u00fcmr\u00fck", "karagumruk"],
}


def load_phonetic_dict(path: str | None = None) -> dict[str, list[str]]:
    """Fonetik sozlugu yukler. path None veya dosya yoksa default'u dondurur."""
    if not path or not os.path.exists(path):
        return DEFAULT_PHONETIC_DICT

    with open(path, "r", encoding="utf-8") as f:
        user_dict = json.load(f)

    merged = DEFAULT_PHONETIC_DICT.copy()
    if isinstance(user_dict, dict):
        for key, val in user_dict.items():
            if isinstance(val, dict):
                merged.update(val)
            elif isinstance(val, list):
                merged[key] = val
    return merged


def build_reverse_phonetic(phonetic_dict: dict[str, list[str]]) -> dict[str, str]:
    """Fonetik sozlukten ters eslestirme sozlugu: normalize(variant) -> original."""
    reverse: dict[str, str] = {}
    for original, variants in phonetic_dict.items():
        for variant in variants:
            norm = normalize_text(variant)
            reverse[norm] = original
            for part in norm.split():
                if len(part) >= 3:
                    reverse[part] = original
    return reverse
