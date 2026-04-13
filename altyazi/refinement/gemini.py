"""Gemini 3 Flash ile Whisper cikisi duzeltme.

Ham Whisper segmentlerini (word timestamps + text) alir, Gemini'ye JSON olarak gonderir:
 - Fonetik hatalari ozel isimlerle duzeltir (Kutinyo -> Coutinho, Icardi -> Icardi)
 - TDK noktalama kurallari
 - Sayisal ifadeleri (2026, 3-1) format eder
 - Kullanicinin verdigi video baglami system prompt olarak enjekte edilir

Kelime timestamp'leri DEGISTIRILMEZ — sadece text/noktalama/ozel isim duzeltilir.
Segment sayisi ve sira korunur; cikti yine {segments: [...]}.
"""
from __future__ import annotations

from ..core.config import GEMINI_MODELS


FULL_TEXT_SYSTEM_INSTRUCTION = """Sen profesyonel bir Turkce altyazi editorusun.
Gorevin: Whisper STT'den gelen HAM Turkce metni temizleyip dogal cumlelere
donusturmek. Cikti daha sonra kelime-seviye hizalamada referans olarak kullanilacak.

KURALLAR:
1. Fonetik hatalari duzelt. Ornek duzeltmeler:
   - 'Diris Mertens'   -> 'Dries Mertens'
   - 'Kutinyo'         -> 'Coutinho'
   - 'Ikardi/Icardi'   -> 'Icardi'
   - 'Ziyes / Ziyeş'   -> 'Ziyech'
   - 'Ara gumruk'      -> 'Karagumruk'
   - 'Doran top'       -> 'duran top'
   - 'Lipteki'         -> 'Ligdeki'
   - Ozel isimleri her zaman dogru resmi yazim ile yaz.
2. TDK noktalama ve buyuk/kucuk harf kurallarini uygula
   (virgul, nokta, soru, unlem, kesme isareti, bag tireleri).
3. Sayilari normalize et: 'iki bin yirmi dort' -> '2024',
   'uc bir' (skor baglami) -> '3-1', 'yuzde elli' -> '%50'.
4. Kelime sayisini mumkun oldugunca koru — sadece anlami netlestiren kucuk
   eklemeler/cikarmalar yap. Kelime SIRASINI asla degistirme.
5. Ham metinde bolunmus olan ayni cumleyi birlestir — dogal cumle sinirlari
   olusturmak amaci bu.
6. Cikti SADECE duzeltilmis metin olmalidir. JSON, aciklama, markdown YAZMA.
   Paragraf bolmeye gerek yok, tek blok metin yeterli.
"""


def _get_api_keys() -> list[str]:
    """secrets.toml'dan Gemini API key listesini okur.

    Once `GEMINI_API_KEYS` listesine bakar (cok-key fallback).
    Yoksa tek key `GEMINI_API_KEY`'e dusar.
    Placeholder ('YOUR_..._HERE') girdileri otomatik atlanir.
    """
    try:
        import streamlit as st
    except Exception as e:
        raise RuntimeError("Streamlit secrets okunamadi.") from e

    keys: list[str] = []
    try:
        raw = st.secrets["GEMINI_API_KEYS"]
        if isinstance(raw, (list, tuple)):
            keys = [str(k).strip() for k in raw if k]
    except Exception:
        pass

    if not keys:
        try:
            single = st.secrets["GEMINI_API_KEY"]
            if single:
                keys = [str(single).strip()]
        except Exception:
            pass

    # Placeholder filtrele
    keys = [k for k in keys if k and not k.startswith("YOUR_")]

    if not keys:
        raise RuntimeError(
            "Gemini API key bulunamadi. .streamlit/secrets.toml dosyasina ekleyin:\n"
            'GEMINI_API_KEYS = ["AIza...", "AIza..."]'
        )
    return keys


# Hata siniflandirma etiketleri
_QUOTA_TAGS = ("429", "RESOURCE_EXHAUSTED")
_OVERLOAD_TAGS = ("503", "504", "UNAVAILABLE", "DEADLINE")


def _mask(key: str) -> str:
    """Log'da key'i maskelenmis goster: AIza...Ms"""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-2:]}"


def refine_full_text(
    raw_text: str,
    video_context: str = "",
    timeout_seconds: float = 90.0,
) -> str:
    """Whisper'in ham full_text'ini Gemini ile duzeltir.

    Fallback matrisi: her API key icin her model denenir. Gecici hatalarda
    (503/429/504/DEADLINE) bir sonraki (key, model) kombinasyonuna gecilir.
    Ilk basarili cevap dondurulur.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    from google import genai
    from google.genai import types

    api_keys = _get_api_keys()

    prompt_parts: list[str] = []
    if video_context.strip():
        prompt_parts.append(f"VIDEO BAGLAMI: {video_context.strip()}")
    prompt_parts.append(
        "Asagidaki ham Turkce transkripsiyonu yukaridaki kurallara gore duzelt "
        "ve SADECE duzeltilmis metni dondur:"
    )
    prompt_parts.append(raw_text.strip())
    user_prompt = "\n\n".join(prompt_parts)

    config = types.GenerateContentConfig(
        system_instruction=FULL_TEXT_SYSTEM_INSTRUCTION,
        temperature=0.2,
    )

    import time

    last_err: Exception | None = None

    for key_idx, api_key in enumerate(api_keys, 1):
        masked = _mask(api_key)
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
            )
        except Exception as e:
            last_err = e
            print(f"[Gemini] key#{key_idx} ({masked}) client olusturulamadi: {e}")
            continue

        skip_to_next_key = False

        for model_name in GEMINI_MODELS:
            if skip_to_next_key:
                break

            # 503/504 icin ic retry: bir kez hemen, bir kez 2s backoff ile
            overload_attempts = 2
            for overload_attempt in range(1, overload_attempts + 1):
                try:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        future = ex.submit(
                            lambda m=model_name: client.models.generate_content(
                                model=m, contents=user_prompt, config=config,
                            )
                        )
                        response = future.result(timeout=timeout_seconds)
                    refined = (response.text or "").strip()
                    if not refined:
                        raise RuntimeError("bos yanit")
                    print(
                        f"[Gemini] basarili: key#{key_idx} ({masked}) / {model_name}"
                    )
                    return refined

                except FuturesTimeout:
                    last_err = RuntimeError(
                        f"Gemini cagrisi {timeout_seconds:.0f}s icinde yanit vermedi."
                    )
                    print(f"[Gemini] timeout key#{key_idx} / {model_name}")
                    break  # siradaki modele

                except Exception as e:
                    last_err = e
                    msg = str(e)
                    is_quota = any(tag in msg for tag in _QUOTA_TAGS)
                    is_overload = any(tag in msg for tag in _OVERLOAD_TAGS)

                    if is_quota:
                        # 429/RESOURCE_EXHAUSTED: bu model+key quota dolu.
                        # Ayni key'de siradaki modele gec (model havuzlari ayri).
                        print(
                            f"[Gemini] quota    key#{key_idx} ({masked}) / {model_name}: "
                            f"{msg[:140]}"
                        )
                        break  # siradaki modele

                    if is_overload:
                        # 503/504: gercek overload — kisa backoff + ic retry.
                        print(
                            f"[Gemini] overload key#{key_idx} ({masked}) / {model_name} "
                            f"(deneme {overload_attempt}/{overload_attempts}): {msg[:120]}"
                        )
                        if overload_attempt < overload_attempts:
                            time.sleep(2.0)
                            continue
                        break  # ic retry tukendi, siradaki modele

                    # Kalici hata (401/403/INVALID_ARGUMENT/bozuk key):
                    # bu key'in diger modellerini denemek bosa, sonraki key'e atla.
                    print(
                        f"[Gemini] kalici   key#{key_idx} ({masked}) / {model_name}: "
                        f"{msg[:140]}"
                    )
                    skip_to_next_key = True
                    break

    assert last_err is not None
    raise last_err
