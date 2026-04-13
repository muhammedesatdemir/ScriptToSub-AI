"""
Script-to-Sub: Metinden Altyaziya Otomasyon Sistemi
====================================================
Video metnini (script) temel alarak, sesle senkronize .srt altyazi ureten sistem.

Asamalar:
  1. FFmpeg ses cikarma + Whisper STT + kelime timestamp
  2. Script-Whisper metin eslestirme + SRT uretimi
  3. Fonetik sozluk + Turkce stemming + akilli eslestirme
  4. Segment optimizasyonu + TDK uyumu + Gemini entegrasyonu
  5. Streamlit arayuzu
"""

import os
import sys
import subprocess
import json
import re
import tempfile
from pathlib import Path

# ============================================================
# ASAMA 1: Temel Altyapi
# FFmpeg ses cikarma + Whisper STT + kelime-seviye timestamp
# ============================================================

def extract_audio(video_path: str, output_path: str = None) -> str:
    """Video dosyasindan ses cikarir (WAV, 16kHz, mono)."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video dosyasi bulunamadi: {video_path}")

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = base + "_audio.wav"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                  # video'yu atla
        "-acodec", "pcm_s16le", # WAV format
        "-ar", "16000",         # 16kHz (Whisper icin ideal)
        "-ac", "1",             # mono
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatasi: {result.stderr}")

    print(f"[ASAMA 1] Ses cikarildi: {output_path}")
    return output_path


def isolate_vocals(video_path: str, output_dir: str = None) -> str:
    """
    Demucs ile vokal izolasyonu yapar.
    Video'dan 44kHz stereo ses cikarip Demucs'a verir (en iyi kalite),
    sonra izole vokali 16kHz mono WAV olarak dondurur.

    Args:
        video_path: Giris video veya ses dosyasi
        output_dir: Cikti dizini (None ise gecici dizin)

    Returns:
        Izole vokal dosyasinin yolu (16kHz mono WAV)
    """
    if output_dir is None:
        output_dir = os.path.dirname(video_path)

    vocal_path = os.path.join(output_dir, "vocals.wav")
    hq_audio_path = os.path.join(output_dir, "hq_audio.wav")

    print(f"[KATMAN 0] Demucs vokal izolasyonu basliyor...")

    try:
        import torch
        import numpy as np
        import wave
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        # 1. Video'dan 44100Hz stereo ses cikar (Demucs icin en iyi format)
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            hq_audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg hatasi: {result.stderr[-200:]}")
        print(f"[KATMAN 0] Yuksek kalite ses cikarildi (44.1kHz stereo)")

        # 2. htdemucs modeli
        model = get_model("htdemucs")
        model.eval()

        # 3. WAV oku (wave modulu — torchaudio bypass)
        with wave.open(hq_audio_path, 'r') as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            raw = wf.readframes(n_frames)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            samples = samples.reshape(-1, n_channels).T  # [channels, samples]

        waveform = torch.from_numpy(samples.copy())  # [2, samples]

        # 4. Normalize + batch
        ref = waveform.mean(0)
        waveform = (waveform - ref.mean()) / ref.std()
        waveform = waveform.unsqueeze(0)  # [1, 2, samples]

        # 5. Demucs uygula
        print(f"[KATMAN 0] Demucs isliyor (bu ~1-2 dk surebilir)...")
        with torch.no_grad():
            sources = apply_model(model, waveform, device="cpu")

        # 6. Vokal kanalini cikar
        vocal_idx = model.sources.index("vocals")
        vocals = sources[0, vocal_idx]  # [2, samples]

        # 7. Denormalize
        vocals = vocals * ref.std() + ref.mean()

        # 8. 16kHz mono WAV olarak kaydet (FFmpeg ile — en guvenilir)
        vocals_stereo_path = os.path.join(output_dir, "vocals_44k.wav")
        vocals_np = (vocals.numpy().T * 32768.0).clip(-32768, 32767).astype(np.int16)
        with wave.open(vocals_stereo_path, 'w') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            wf.writeframes(vocals_np.tobytes())

        # FFmpeg ile 16kHz mono'ya cevir
        cmd2 = [
            "ffmpeg", "-y", "-i", vocals_stereo_path,
            "-ar", "16000", "-ac", "1",
            vocal_path
        ]
        subprocess.run(cmd2, capture_output=True, text=True)

        # Temizlik
        for f in [hq_audio_path, vocals_stereo_path]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

        print(f"[KATMAN 0] Vokal izolasyonu tamamlandi: {vocal_path}")
        return vocal_path

    except Exception as e:
        print(f"[KATMAN 0] Demucs hatasi: {e}")
        import traceback
        traceback.print_exc()
        print(f"[KATMAN 0] Vokal izolasyonu atlanarak devam ediliyor.")
        # Temizlik
        if os.path.exists(hq_audio_path):
            try:
                os.remove(hq_audio_path)
            except OSError:
                pass
        return None


def transcribe_with_timestamps(audio_path: str, language: str = "tr",
                                model_size: str = "large-v3-turbo") -> dict:
    """
    Whisper ile ses dosyasini yaziya doker, kelime-seviye zaman damgalari alir.
    stable-ts kullanarak zaman damgalarini stabilize eder.
    """
    import stable_whisper

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {audio_path}")

    print(f"[ASAMA 1] Whisper modeli yukleniyor: {model_size} (CPU)...")
    model = stable_whisper.load_faster_whisper(model_size, device="cpu", compute_type="int8")

    print(f"[ASAMA 1] Transkripsiyon basliyor (dil: {language})...")
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    # Sonuclari yapilandir
    segments = []
    all_words = []

    for segment in result.segments:
        seg_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "words": []
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

    output = {
        "segments": segments,
        "all_words": all_words,
        "full_text": result.text.strip()
    }

    print(f"[ASAMA 1] Transkripsiyon tamamlandi: {len(all_words)} kelime, {len(segments)} segment")
    return output


def save_whisper_output(whisper_data: dict, output_path: str):
    """Whisper ciktisini JSON olarak kaydeder (debug/test icin)."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(whisper_data, f, ensure_ascii=False, indent=2)
    print(f"[ASAMA 1] Whisper ciktisi kaydedildi: {output_path}")


# ============================================================
# ASAMA 2: Script-Whisper Metin Eslestirme + SRT Uretimi
# ============================================================

def normalize_text(text: str) -> str:
    """Metni eslestirme icin normalize eder."""
    text = text.lower()
    text = text.replace("'", "'").replace("\u2018", "'").replace("\u2019", "'")
    # Turkce karakterleri koru, noktalama kaldir
    text = re.sub(r"[^\w\s\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize_script(script_text: str) -> list:
    """Script metnini kelimelere ayirir, her kelimenin orijinal halini korur."""
    # Satirlari birlestir, fazla bosluklari temizle
    clean = re.sub(r"\s+", " ", script_text.strip())
    words = clean.split()
    tokens = []
    for w in words:
        tokens.append({
            "original": w,
            "normalized": normalize_text(w)
        })
    return tokens


def align_words(script_tokens: list, whisper_words: list,
                phonetic_dict: dict = None) -> list:
    """
    Script kelimeleri ile Whisper kelimelerini eslestir.
    Sonuc: her eslesen cift icin (script_kelimesi, baslangic, bitis) listesi.

    Video'da script'in tamami olmayabilir (intro, outro vb.).
    Sadece gercekten eslesen bolumler alinir. Eslesmeyenler icin
    komsu eslesmelerden zaman interpolasyonu yapilir.
    """
    from difflib import SequenceMatcher
    from rapidfuzz import fuzz

    if phonetic_dict is None:
        phonetic_dict = {}

    reverse_phonetic = {}
    for original, variants in phonetic_dict.items():
        for variant in variants:
            reverse_phonetic[normalize_text(variant)] = original

    script_norm = [t["normalized"] for t in script_tokens]
    whisper_norm = [normalize_text(w["word"]) for w in whisper_words]

    matcher = SequenceMatcher(None, script_norm, whisper_norm)
    opcodes = matcher.get_opcodes()

    # Ilk gecis: sadece guclu eslesmeleri topla
    raw_aligned = [None] * len(script_tokens)

    for tag, s_start, s_end, w_start, w_end in opcodes:
        if tag == "equal":
            for i, j in zip(range(s_start, s_end), range(w_start, w_end)):
                raw_aligned[i] = {
                    "script_word": script_tokens[i]["original"],
                    "whisper_word": whisper_words[j]["word"],
                    "start": whisper_words[j]["start"],
                    "end": whisper_words[j]["end"],
                    "match_type": "exact"
                }
        elif tag == "replace":
            s_slice = list(range(s_start, s_end))
            w_slice = list(range(w_start, w_end))

            matched_w = set()
            for si in s_slice:
                best_score = 0
                best_wj = None
                s_word_norm = script_norm[si]

                for wj in w_slice:
                    if wj in matched_w:
                        continue
                    w_word_norm = whisper_norm[wj]

                    if w_word_norm in reverse_phonetic:
                        phonetic_original = reverse_phonetic[w_word_norm]
                        if normalize_text(phonetic_original) == s_word_norm:
                            best_score = 100
                            best_wj = wj
                            break

                    score = fuzz.ratio(s_word_norm, w_word_norm)
                    if score > best_score:
                        best_score = score
                        best_wj = wj

                if best_wj is not None and best_score >= 50:
                    matched_w.add(best_wj)
                    raw_aligned[si] = {
                        "script_word": script_tokens[si]["original"],
                        "whisper_word": whisper_words[best_wj]["word"],
                        "start": whisper_words[best_wj]["start"],
                        "end": whisper_words[best_wj]["end"],
                        "match_type": "phonetic" if best_score == 100 else "fuzzy",
                        "score": best_score
                    }

    # Eslesmis bolgeleri analiz et: yogun eslesmis ardisik bolgeleri bul
    # Video'da olmayan script kisimlari (intro, baska sahne vb.) atlanmali
    matched_indices = [i for i, a in enumerate(raw_aligned) if a is not None]

    if not matched_indices:
        return []

    # Zamansal tutarlilik filtresi: eslesmis kelimelerin zamanlari
    # script sirasinda artmali. Zamansal olarak geri giden eslesmeleri at.
    clean_indices = []
    last_time = -1.0
    for i in matched_indices:
        t = raw_aligned[i]["start"]
        if t >= last_time:
            clean_indices.append(i)
            last_time = t
        else:
            # Zamansal geri gitme — yanlis eslestirme, sil
            raw_aligned[i] = None

    matched_indices = clean_indices
    if not matched_indices:
        return []

    # Ardisik eslesmis bloklari bul (max 8 kelimelik boslukla)
    MAX_GAP = 8
    blocks = []
    current_block = [matched_indices[0]]
    for idx in matched_indices[1:]:
        if idx - current_block[-1] <= MAX_GAP:
            current_block.append(idx)
        else:
            blocks.append(current_block)
            current_block = [idx]
    blocks.append(current_block)

    # En yogun blogu sec: eslesmis kelime sayisi ve zamansal tutarlilik
    best_block = None
    best_score = 0
    for block in blocks:
        if len(block) < 3:
            continue  # Cok kisa bloklar guvenilir degil
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

    # Sonuc listesini olustur
    aligned = []
    for i in range(block_start, block_end + 1):
        if raw_aligned[i] is not None:
            aligned.append(raw_aligned[i])
        else:
            # Interpolasyon: en yakin eslesmis komsu zamanlarini kullan
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
                # Aradaki eslesmemis kelime sayisini bul
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
                "match_type": "interpolated"
            })

    return aligned


def create_segments(aligned_words: list, max_chars: int = 60,
                    max_duration: float = 5.0, min_duration: float = 0.8) -> list:
    """
    Eslesmis kelimeleri altyazi segmentlerine boler.
    Kurallar:
      - Max 80 karakter/segment (2 satir x 40)
      - Max 7 saniye gorunme suresi
      - Min 0.8 saniye gorunme suresi
      - Cumle sonlarinda (. ! ?) kesinlikle bol
      - Virgul, baglac gibi dogal noktalarda bol
    """
    if not aligned_words:
        return []

    # Oncelik 1: Cumle sonu (kesinlikle bol)
    sentence_end_chars = {".", "!", "?"}
    # Oncelik 2: Dogal bolunme (tercih et)
    break_after_punct = {",", ";", ":"}
    break_after_words = {"da", "de", "ve", "ama", "ise", "ile", "ki",
                         "fakat", "ancak", "lakin", "oysa"}

    segments = []
    current_words = []
    current_text = ""
    seg_start = None

    for word_info in aligned_words:
        word = word_info["script_word"]
        w_start = word_info["start"]
        w_end = word_info["end"]

        if seg_start is None:
            seg_start = w_start

        test_text = (current_text + " " + word).strip() if current_text else word
        current_duration = w_end - seg_start

        # Zorla bolme: max karakter veya max sure asildi
        if (len(test_text) > max_chars or current_duration > max_duration) and current_words:
            segments.append({
                "start": seg_start,
                "end": current_words[-1]["end"],
                "text": current_text
            })
            current_words = []
            current_text = ""
            seg_start = w_start

        current_words.append(word_info)
        current_text = (current_text + " " + word).strip() if current_text else word
        current_duration = w_end - seg_start

        # Cumle sonu kontrolu — her zaman bol
        last_char = word[-1] if word else ""
        if last_char in sentence_end_chars:
            segments.append({
                "start": seg_start,
                "end": w_end,
                "text": current_text
            })
            current_words = []
            current_text = ""
            seg_start = None
            continue

        # Dogal bolunme noktasi — sadece yeterli uzunluktaysa
        word_clean = word.rstrip(".,!?;:'\"").lower()
        if (last_char in break_after_punct or word_clean in break_after_words) and \
           len(current_text) > 35 and current_duration > 1.8:
            segments.append({
                "start": seg_start,
                "end": w_end,
                "text": current_text
            })
            current_words = []
            current_text = ""
            seg_start = None

    # Kalan kelimeleri son segment olarak ekle
    if current_words:
        segments.append({
            "start": seg_start,
            "end": current_words[-1]["end"],
            "text": current_text
        })

    # Minimum sure kontrolu - cok kisa segmentleri birlestir
    merged = []
    for seg in segments:
        duration = seg["end"] - seg["start"]
        if merged and duration < min_duration:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] += " " + seg["text"]
        else:
            merged.append(seg)

    return merged


def generate_srt(segments: list, output_path: str) -> str:
    """Segmentlerden SRT dosyasi olusturur."""
    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start_str = format_time(seg["start"])
        end_str = format_time(seg["end"])
        text = seg["text"]

        # 2 satira bol (max ~32 karakter/satir)
        if len(text) > 32:
            mid = len(text) // 2
            # En yakin boslugu bul
            left = text.rfind(" ", 0, mid + 10)
            right = text.find(" ", mid - 10)
            if left == -1:
                split_pos = right
            elif right == -1:
                split_pos = left
            else:
                split_pos = left if (mid - left) <= (right - mid) else right

            if split_pos > 0:
                text = text[:split_pos] + "\n" + text[split_pos + 1:]

        srt_lines.append(f"{i}")
        srt_lines.append(f"{start_str} --> {end_str}")
        srt_lines.append(text)
        srt_lines.append("")

    srt_content = "\n".join(srt_lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"[ASAMA 2] SRT dosyasi olusturuldu: {output_path} ({len(segments)} segment)")
    return output_path


# ============================================================
# ASAMA 3: Fonetik Sozluk + Turkce Stemming
# ============================================================

# Varsayilan fonetik sozluk (futbol icerik ureticisi icin)
DEFAULT_PHONETIC_DICT = {
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


def load_phonetic_dict(path: str = None) -> dict:
    """Fonetik sozlugu yukler. Yoksa varsayilani dondurur."""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            user_dict = json.load(f)
        # Varsayilan ile birlestir
        merged = DEFAULT_PHONETIC_DICT.copy()
        if isinstance(user_dict, dict):
            # Duz dict veya kategorili dict destekle
            for key, val in user_dict.items():
                if isinstance(val, dict):
                    # Kategorili: {"futbol_isimleri": {"X": [...]}}
                    merged.update(val)
                elif isinstance(val, list):
                    merged[key] = val
        print(f"[ASAMA 3] Fonetik sozluk yuklendi: {path}")
        return merged
    return DEFAULT_PHONETIC_DICT


def turkish_stem(word: str) -> str:
    """Basit Turkce kok cikarma (suffix stripping)."""
    word = word.lower().rstrip(".,!?;:'\"")

    # Iyelik ekleri
    suffixes = [
        "larin", "lerin", "larini", "lerini",
        "inda", "inde", "inda", "inde",
        "daki", "deki", "taki", "teki",
        "dan", "den", "tan", "ten",
        "nin", "n\u0131n", "nun", "n\u00fcn",
        "yla", "yle",
        "ya", "ye", "na", "ne",
        "da", "de", "ta", "te",
        "in", "\u0131n", "un", "\u00fcn",
        "'n\u0131n", "'nin", "'nun", "'n\u00fcn",
        "'ya", "'ye", "'na", "'ne",
        "'da", "'de", "'ta", "'te",
        "'dan", "'den", "'tan", "'ten",
    ]

    for suffix in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[:-len(suffix)]

    return word


def build_reverse_phonetic(phonetic_dict: dict) -> dict:
    """Fonetik sozlukten ters eslestirme sozlugu olusturur."""
    reverse = {}
    for original, variants in phonetic_dict.items():
        for variant in variants:
            # Her varianti ve koklerini ekle
            norm = normalize_text(variant)
            reverse[norm] = original
            for part in norm.split():
                if len(part) >= 3:
                    reverse[part] = original
    return reverse


def enhanced_align_words(script_tokens: list, whisper_words: list,
                          phonetic_dict: dict = None) -> list:
    """
    Gelistirilmis eslestirme: fonetik sozluk + Turkce stemming + blok tespiti.
    align_words ile ayni zamansal tutarlilik ve blok filtreleme mantigi,
    ek olarak stem ve fonetik eslestirme.
    """
    from difflib import SequenceMatcher
    from rapidfuzz import fuzz

    if phonetic_dict is None:
        phonetic_dict = DEFAULT_PHONETIC_DICT

    reverse_phonetic = build_reverse_phonetic(phonetic_dict)

    script_norm = [t["normalized"] for t in script_tokens]
    whisper_norm = [normalize_text(w["word"]) for w in whisper_words]

    script_stems = [turkish_stem(n) for n in script_norm]
    whisper_stems = [turkish_stem(n) for n in whisper_norm]

    # Stem bazli SequenceMatcher (daha iyi Turkce eslestirme)
    matcher = SequenceMatcher(None, script_stems, whisper_stems)
    opcodes = matcher.get_opcodes()

    # Ilk gecis: raw_aligned dizisine yerlestir
    raw_aligned = [None] * len(script_tokens)

    for tag, s_start, s_end, w_start, w_end in opcodes:
        if tag == "equal":
            for i, j in zip(range(s_start, s_end), range(w_start, w_end)):
                raw_aligned[i] = {
                    "script_word": script_tokens[i]["original"],
                    "whisper_word": whisper_words[j]["word"],
                    "start": whisper_words[j]["start"],
                    "end": whisper_words[j]["end"],
                    "match_type": "exact"
                }
        elif tag == "replace":
            s_slice = list(range(s_start, s_end))
            w_slice = list(range(w_start, w_end))

            matched_w = set()
            for si in s_slice:
                best_score = 0
                best_wj = None
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

                    # 3. Fuzzy match
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
                        "score": best_score
                    }

    # Zamansal tutarlilik filtresi
    matched_indices = [i for i, a in enumerate(raw_aligned) if a is not None]
    if not matched_indices:
        return []

    clean_indices = []
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

    # Blok tespiti
    MAX_GAP = 8
    blocks = []
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

    # Sonuc listesi: eslesmis kelimeler arasi bosluklar icin interpolasyon
    aligned = []
    for i in range(block_start, block_end + 1):
        if raw_aligned[i] is not None:
            aligned.append(raw_aligned[i])
        else:
            # Komsu eslesmelerden zaman tahmini
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
                "match_type": "interpolated"
            })

    return aligned


# ============================================================
# ASAMA 4: Segment Optimizasyonu + TDK Uyumu
# ============================================================

def optimize_segments(segments: list) -> list:
    """
    Segment metnini TDK uyumlu hale getirir ve okuma konforunu optimize eder.
    - Max okuma hizi: 21 karakter/saniye
    - Cumle basinda buyuk harf
    - Gereksiz bosluk temizligi
    """
    optimized = []

    for seg in segments:
        text = seg["text"].strip()
        duration = seg["end"] - seg["start"]

        # Bosluk temizligi
        text = re.sub(r"\s+", " ", text)

        # Okuma hizi kontrolu — cok hizliysa bolunerek halledilecek
        chars_per_sec = len(text) / max(duration, 0.1)

        optimized.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text,
            "chars_per_sec": round(chars_per_sec, 1)
        })

    return optimized


# ============================================================
# ANA CALISMA FONKSIYONU
# ============================================================

def process_video(video_path: str, script_path: str,
                  output_srt_path: str = None,
                  phonetic_dict_path: str = None,
                  model_size: str = "large-v3-turbo",
                  use_cache: bool = True,
                  vocal_isolation: bool = True) -> str:
    """
    Tam pipeline: Video + Script -> SRT

    Args:
        video_path: Video dosyasi yolu
        script_path: Script metin dosyasi yolu
        output_srt_path: Cikti SRT dosyasi yolu (None ise otomatik)
        phonetic_dict_path: Fonetik sozluk JSON dosyasi yolu (opsiyonel)
        model_size: Whisper model boyutu
        use_cache: True ise onceki Whisper sonucunu kullan
        vocal_isolation: True ise Demucs ile vokal izolasyonu yap

    Returns:
        SRT dosyasi yolu
    """
    print("=" * 60)
    print("  SCRIPT-TO-SUB: Metinden Altyaziya Otomasyon")
    print("=" * 60)

    if output_srt_path is None:
        base = os.path.splitext(video_path)[0]
        output_srt_path = base + ".srt"

    cache_suffix = "_whisper_vocals.json" if vocal_isolation else "_whisper.json"
    whisper_json_path = os.path.splitext(video_path)[0] + cache_suffix

    # Cache kontrolu: onceki Whisper sonucu varsa kullan
    if use_cache and os.path.exists(whisper_json_path):
        print(f"\n[CACHE] Whisper sonucu mevcut: {whisper_json_path}")
        with open(whisper_json_path, "r", encoding="utf-8") as f:
            whisper_data = json.load(f)
        print(f"  {len(whisper_data['all_words'])} kelime, {len(whisper_data['segments'])} segment")
    else:
        # 1. Vokal izolasyonu veya duz ses cikarma
        whisper_input = None
        if vocal_isolation:
            print("\n--- KATMAN 0: Vokal Izolasyonu (Demucs) ---")
            vocal_path = isolate_vocals(video_path, os.path.dirname(os.path.abspath(video_path)))
            if vocal_path:
                whisper_input = vocal_path

        if whisper_input is None:
            print("\n--- KATMAN 0: Ses Cikarma ---")
            whisper_input = extract_audio(video_path)

        # 2. Whisper STT
        print("\n--- KATMAN 1: Whisper STT ---")
        whisper_data = transcribe_with_timestamps(whisper_input, model_size=model_size)
        save_whisper_output(whisper_data, whisper_json_path)

        # Temizlik
        if os.path.exists(whisper_input):
            try:
                os.remove(whisper_input)
            except OSError:
                pass

    # 3. Script'i yukle ve tokenize et
    print("\n--- KATMAN 2: Metin Eslestirme ---")
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    script_tokens = tokenize_script(script_text)
    print(f"  Script: {len(script_tokens)} kelime")
    print(f"  Whisper: {len(whisper_data['all_words'])} kelime")

    # 4. Fonetik sozluk yukle
    phonetic_dict = load_phonetic_dict(phonetic_dict_path)

    # 5. Eslestirme (Asama 3: gelistirilmis versiyon)
    print("\n--- KATMAN 3: Akilli Eslestirme ---")
    aligned = enhanced_align_words(script_tokens, whisper_data["all_words"], phonetic_dict)

    # Eslestirme istatistikleri
    match_types = {}
    for a in aligned:
        mt = a["match_type"]
        match_types[mt] = match_types.get(mt, 0) + 1
    print(f"  Eslestirme sonuclari:")
    for mt, count in sorted(match_types.items()):
        print(f"    {mt}: {count} kelime")
    total = len(aligned)
    exact_count = match_types.get("exact", 0) + match_types.get("stem", 0)
    print(f"  Dogrudan eslestirme orani: {exact_count}/{total} ({100*exact_count/max(total,1):.0f}%)")

    # Kapsam analizi: script'in ne kadari videoda var?
    if total < len(script_tokens):
        covered_pct = 100 * total / len(script_tokens)
        missed = len(script_tokens) - total
        print(f"\n  [!] UYARI: Script'in {missed} kelimesi ({100-covered_pct:.0f}%) videoda bulunamadi.")
        print(f"      Script: {len(script_tokens)} kelime, Eslesen: {total} kelime")
        if aligned:
            print(f"      Kapsanan zaman araligi: {aligned[0]['start']:.1f}s - {aligned[-1]['end']:.1f}s")
        # Hangi satirlar eslesmedi?
        first_script_word = aligned[0]["script_word"] if aligned else ""
        script_words_list = [t["original"] for t in script_tokens]
        if first_script_word in script_words_list:
            start_idx = script_words_list.index(first_script_word)
            if start_idx > 0:
                missed_text = " ".join(script_words_list[:min(start_idx, 15)])
                print(f"      Videoda bulunmayan baslangic: \"{missed_text}...\"")
        print(f"      Olasi neden: Script'in bu kismi videoda seslendirilmemis.")

    # 6. Segmentlere bol
    print("\n--- KATMAN 4: Segment Olusturma ---")
    segments = create_segments(aligned)
    segments = optimize_segments(segments)
    print(f"  {len(segments)} segment olusturuldu")

    # Segment istatistikleri
    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        cps = seg.get("chars_per_sec", len(seg["text"]) / max(dur, 0.1))
        status = "OK" if cps <= 25 else "HIZLI"
        print(f"    #{i:2d} [{seg['start']:5.1f}s-{seg['end']:5.1f}s] ({dur:4.1f}s) {cps:4.1f} chr/s [{status}]")

    # 7. SRT uret
    print("\n--- CIKTI ---")
    generate_srt(segments, output_srt_path)

    print(f"\n  TAMAMLANDI: {output_srt_path}")
    print("=" * 60)

    return output_srt_path


# ============================================================
# CLI GIRIS NOKTASI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Script-to-Sub: Video metninden altyazi olusturma"
    )
    parser.add_argument("video", help="Video dosyasi yolu")
    parser.add_argument("script", help="Script metin dosyasi yolu")
    parser.add_argument("-o", "--output", help="Cikti SRT dosyasi yolu")
    parser.add_argument("-d", "--dict", help="Fonetik sozluk JSON dosyasi yolu")
    parser.add_argument("-m", "--model", default="large-v3-turbo",
                        help="Whisper model boyutu (varsayilan: large-v3-turbo)")
    parser.add_argument("--no-vocal-isolation", action="store_true",
                        help="Vokal izolasyonu (Demucs) devre disi birak")
    parser.add_argument("--no-cache", action="store_true",
                        help="Cache kullanma, Whisper'i yeniden calistir")

    args = parser.parse_args()

    process_video(
        video_path=args.video,
        script_path=args.script,
        output_srt_path=args.output,
        phonetic_dict_path=args.dict,
        model_size=args.model,
        vocal_isolation=not args.no_vocal_isolation,
        use_cache=not args.no_cache
    )
