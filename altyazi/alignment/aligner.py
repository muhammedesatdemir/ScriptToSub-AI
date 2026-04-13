"""Gelistirilmis script-Whisper hizalama: fonetik + stem + blok tespiti + interpolasyon.

Bu fonksiyon `script_to_sub.enhanced_align_words` ile aynidir — Mod A'nin
kalbi oldugu icin davranisi byte-for-byte korunmustur.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from ..core.phonetic import DEFAULT_PHONETIC_DICT, build_reverse_phonetic
from ..core.utils import normalize_text, turkish_stem


def enhanced_align_words(
    script_tokens: list[dict],
    whisper_words: list[dict],
    phonetic_dict: dict | None = None,
) -> list[dict]:
    """Fonetik sozluk + Turkce stemming + blok tespiti ile kelime hizalama.

    Video'da script'in tamami olmayabilir (intro/outro). En yogun tutarli blok
    secilir; arada eslesmeyen kelimeler komsu zamanlarla interpolasyon yapilir.
    """
    from rapidfuzz import fuzz

    if phonetic_dict is None:
        phonetic_dict = DEFAULT_PHONETIC_DICT

    reverse_phonetic = build_reverse_phonetic(phonetic_dict)

    script_norm = [t["normalized"] for t in script_tokens]
    whisper_norm = [normalize_text(w["word"]) for w in whisper_words]
    script_stems = [turkish_stem(n) for n in script_norm]
    whisper_stems = [turkish_stem(n) for n in whisper_norm]

    matcher = SequenceMatcher(None, script_stems, whisper_stems)
    opcodes = matcher.get_opcodes()

    raw_aligned: list[dict | None] = [None] * len(script_tokens)

    for tag, s_start, s_end, w_start, w_end in opcodes:
        if tag == "equal":
            for i, j in zip(range(s_start, s_end), range(w_start, w_end)):
                raw_aligned[i] = {
                    "script_word": script_tokens[i]["original"],
                    "whisper_word": whisper_words[j]["word"],
                    "start": whisper_words[j]["start"],
                    "end": whisper_words[j]["end"],
                    "match_type": "exact",
                }
        elif tag == "replace":
            s_slice = list(range(s_start, s_end))
            w_slice = list(range(w_start, w_end))
            matched_w: set[int] = set()

            for si in s_slice:
                best_score = 0
                best_wj: int | None = None
                s_word_norm = script_norm[si]
                s_stem = script_stems[si]

                for wj in w_slice:
                    if wj in matched_w:
                        continue
                    w_word_norm = whisper_norm[wj]
                    w_stem = whisper_stems[wj]

                    # 1. Fonetik sozluk
                    if w_word_norm in reverse_phonetic:
                        phonetic_orig = normalize_text(reverse_phonetic[w_word_norm])
                        if phonetic_orig == s_word_norm or s_word_norm.startswith(phonetic_orig):
                            best_score = 100
                            best_wj = wj
                            break

                    # 2. Stem eslesmesi
                    if s_stem == w_stem and len(s_stem) >= 2:
                        score = 90
                        if score > best_score:
                            best_score = score
                            best_wj = wj
                            continue

                    # 3. Fuzzy
                    score = fuzz.ratio(s_word_norm, w_word_norm)
                    if score > best_score:
                        best_score = score
                        best_wj = wj

                if best_wj is not None and best_score >= 50:
                    matched_w.add(best_wj)
                    if best_score == 100:
                        mt = "phonetic"
                    elif best_score == 90:
                        mt = "stem"
                    else:
                        mt = "fuzzy"
                    raw_aligned[si] = {
                        "script_word": script_tokens[si]["original"],
                        "whisper_word": whisper_words[best_wj]["word"],
                        "start": whisper_words[best_wj]["start"],
                        "end": whisper_words[best_wj]["end"],
                        "match_type": mt,
                        "score": best_score,
                    }

    # Zamansal tutarlilik filtresi
    matched_indices = [i for i, a in enumerate(raw_aligned) if a is not None]
    if not matched_indices:
        return []

    clean_indices: list[int] = []
    last_time = -1.0
    for i in matched_indices:
        t = raw_aligned[i]["start"]
        if t >= last_time:
            clean_indices.append(i)
            last_time = t
        else:
            raw_aligned[i] = None
    matched_indices = clean_indices
    if not matched_indices:
        return []

    # Blok tespiti — max 8 kelimelik boslukla ardisik gruplar
    MAX_GAP = 8
    blocks: list[list[int]] = []
    current_block = [matched_indices[0]]
    for idx in matched_indices[1:]:
        if idx - current_block[-1] <= MAX_GAP:
            current_block.append(idx)
        else:
            blocks.append(current_block)
            current_block = [idx]
    blocks.append(current_block)

    best_block = None
    best_score = 0
    for block in blocks:
        if len(block) < 3:
            continue
        times = [raw_aligned[i]["start"] for i in block]
        monotonic_count = sum(1 for a, b in zip(times, times[1:]) if b >= a)
        score = len(block) * (monotonic_count + 1)
        if score > best_score:
            best_score = score
            best_block = block

    if best_block is None:
        return []

    block_start = best_block[0]
    block_end = best_block[-1]

    aligned: list[dict] = []
    for i in range(block_start, block_end + 1):
        if raw_aligned[i] is not None:
            aligned.append(raw_aligned[i])
            continue

        # Interpolasyon
        prev_end = None
        next_start = None
        for j in range(i - 1, block_start - 1, -1):
            if raw_aligned[j] is not None:
                prev_end = raw_aligned[j]["end"]
                break
        for j in range(i + 1, block_end + 1):
            if raw_aligned[j] is not None:
                next_start = raw_aligned[j]["start"]
                break

        if prev_end is not None and next_start is not None and next_start > prev_end:
            gap_start = i
            gap_end = i
            for j in range(i - 1, block_start - 1, -1):
                if raw_aligned[j] is not None:
                    break
                gap_start = j
            for j in range(i + 1, block_end + 1):
                if raw_aligned[j] is not None:
                    break
                gap_end = j

            gap_count = gap_end - gap_start + 1
            pos_in_gap = i - gap_start
            word_dur = (next_start - prev_end) / max(gap_count, 1)
            est_start = prev_end + pos_in_gap * word_dur
            est_end = est_start + word_dur
        elif prev_end is not None:
            est_start = prev_end
            est_end = prev_end + 0.3
        elif next_start is not None:
            est_start = max(0, next_start - 0.3)
            est_end = next_start
        else:
            continue

        aligned.append({
            "script_word": script_tokens[i]["original"],
            "whisper_word": None,
            "start": est_start,
            "end": est_end,
            "match_type": "interpolated",
        })

    return aligned
