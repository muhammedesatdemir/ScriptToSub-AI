# Script-to-Sub

Turkce video icerikleri icin **iki modlu altyazi uretim sistemi**. Elinizde
hazir script varken referansli hizalama yapar (Mod A), referans metin yoksa
Whisper + Gemini Flash ile sifirdan uretir (Mod B). Her iki modun ciktisi ayni
modern ASS stiline (Montserrat Black, sari vurgu, 9:16 safe-zone) yonlendirilir
ve FFmpeg uzerinden videoya gomulerek Reels/TikTok/Shorts icin hazir
`.mp4` olarak indirilir.

> **Mod A — Script-Aware Alignment:** Whisper sadece **zamanlama kaynagi**.
> Goruntulenen metin her zaman kullanicinin yazdigi script'tir. TDK/ozel isim
> sadakati maksimum.
>
> **Mod B — Autonomous AI Transcription:** Kullanici metin girmez. Whisper
> transkribe eder, **Gemini Flash** fonetik hatalari / TDK / sayi formatlarini
> duzeltir, kelime timestamp'leri ile yeniden hizalanir.

---

## One Cikan Ozellikler

- **Iki calisma modu** — Referansli (Mod A) veya bagimsiz AI (Mod B); UI uzerinden tek tiklamayla gecis.
- **Demucs v4 vokal izolasyonu** — `htdemucs` ile beat/muzik ayristirilir, Whisper temiz vokal uzerinde calisir. CUDA varsa otomatik GPU.
- **faster-whisper `large-v3-turbo`** — Kelime seviyesinde `word_timestamps=True`, `stable-ts` ile stabilizasyon.
- **Gemini Flash refinement (Mod B)** — Ozel isim fonetigi, TDK noktalama, sayi formatlama. Uc anahtar + uc model fallback matrisi (3×3 = 9 kombinasyon).
- **Akilli hata sinfilandirmasi** — 429 (quota) vs 503 (overload) vs kalici (auth) ayri politikalarla ele alinir; quota'da hemen model ilerletir, overload'da kisa backoff, auth hatasinda sonraki key'e atlar.
- **Mod A hizalama motoru** — `difflib` + `rapidfuzz` fuzzy matching, Turkce stem cikarma, genisletilebilir fonetik sozluk (Coutinho, Ziyech, Icardi, Karagumruk vb.), zamansal tutarlilik filtresi, en yogun ardisik blok secimi, bosluk interpolasyonu.
- **2-satir kurali** — Mod B kelime akisi orantili olarak bolunur: 42 kar / 8 kelime siniri asildiginda sure kelime sayisina gore dagitilarak ikiye ayrilir (recursive). Reels/Shorts'ta 3-satir tasma imkansiz.
- **Modern ASS render** — Montserrat Black 82pt, safe-zone MarginV 410px (1080×1920), ozel isim ve sayilar otomatik sari vurgu (`_highlight_words`), libass ile piksel-mukemmel.
- **Hardcoded subtitle** — FFmpeg + libass ile tek parca altyazili `.mp4`; oynatici destegi gerektirmez.
- **Modern Streamlit arayuzu** — Koyu tema, WCAG AA kontrasti, UTF-8 full Turkce karakter destegi, placeholder gorunurlugu, klavye erisilebilirligi (`focus-visible`), semantik durum renkleri.

---

## Mimari

```
                     ┌────────────── Mod A (Script-Aware) ──────────────┐
                     │                                                    │
[Video] ──► Demucs ──┤──► faster-whisper ──► enhanced_align_words ──► create_segments
            (htdemucs)     (large-v3-turbo)   (difflib + rapidfuzz +     │    │
                           word_timestamps     Turkce stem + fonetik)    │    ▼
                           = all_words)                                  │  optimize
                     │                                                    │    │
                     └───────── Mod B (Autonomous AI) ─────────┐          │    │
                                                                │         │    │
                                ┌──► full_text ──► Gemini Flash │         │    │
                                │                   refinement  │         │    │
                                │                  (3 key × 3 model)      │    │
                                │                       │                 │    │
                                └─► Whisper all_words ──┴──► enhanced_align_words
                                                              (refined text'i
                                                               script gibi kullanir)
                                                                │         │    │
                                                                ▼         │    ▼
                                                         create_segments ─┘  split_segment
                                                                               (2-satir)
                                                                                  │
                                                                                  ▼
                                                                          rendering/srt
                                                                                  │
                                                                    ┌─────────────┤
                                                                    ▼             ▼
                                                              [output.srt]   rendering/ass
                                                                             (Montserrat,
                                                                              sari vurgu,
                                                                              safe-zone)
                                                                                  │
                                                                                  ▼
                                                                            FFmpeg + libass
                                                                                  │
                                                                                  ▼
                                                                    [output_altyazili.mp4]
```

---

## Paket Yapisi

```
altyazi/
├── app.py                       # Thin Streamlit entry (~140 satir)
├── fonts/                       # Montserrat Black .ttf
├── core/
│   ├── config.py                # ASS stili, safe-zone, limitler, Gemini model listesi
│   ├── utils.py                 # Zaman ceviri, Turkce stem, normalize, safe_remove
│   └── phonetic.py              # DEFAULT_PHONETIC_DICT, reverse map builder
├── audio/
│   ├── extract.py               # ffmpeg 16kHz mono WAV
│   └── isolate.py               # Demucs htdemucs (CUDA auto-detect, graceful fallback)
├── transcription/
│   └── whisper_stt.py           # faster-whisper + stable-ts wrapper
├── alignment/
│   ├── tokenize.py              # Script → token listesi
│   └── aligner.py               # enhanced_align_words: fonetik + stem + blok + interpolation
├── refinement/
│   └── gemini.py                # Gemini Flash full-text refinement, multi-key/model fallback
├── segmentation/
│   └── segments.py              # create_segments, optimize_segments, split_segment
├── rendering/
│   ├── srt.py                   # SRT uretimi
│   └── ass.py                   # ASS render, _highlight_words, _split_long_cue, burn_subtitles
├── pipeline/
│   ├── mode_a.py                # run_script_aware_alignment
│   └── mode_b.py                # run_autonomous_transcription
└── ui/
    ├── theme.py                 # CSS + sidebar toggle enjektoru
    ├── sidebar.py               # Mod secimi + Whisper + Demucs + Gemini ayarlari
    ├── inputs.py                # Video + script/context girdileri
    └── results.py               # Metrikler, indirme, segment onizleme, burn
```

Toplam ~2,500 satir Python, semantik olarak ayrilmis 9 alt modul. Tum
yapilandirilabilir sabitler [altyazi/core/config.py](altyazi/core/config.py)
icinde tek yerde toplandi.

---

## Teknoloji Yigini

| Katman | Arac | Amaç |
|---|---|---|
| Ses on-isleme | `ffmpeg`, `demucs` (htdemucs v4) | Ses cikarma, vokal izolasyonu |
| STT | `faster-whisper` + `stable-ts` (large-v3-turbo) | Konusma tanima, kelime timestamp stabilizasyonu |
| Mod B refinement | `google-genai` (Gemini 2.5 Flash / Flash Lite) | Fonetik, TDK, sayi normalize |
| Hizalama | `difflib.SequenceMatcher`, `rapidfuzz` | Script-Whisper eslestirme |
| Turkce NLP | Ozel stemmer + fonetik sozluk | Eklemeli yapi, ozel isim sadakati |
| Render | `libass` (FFmpeg filter) | ASS stilizasyonu, hardcoded subtitle |
| Arayuz | `streamlit` | Web tabanli yukleme / onizleme / indirme |

---

## Kurulum

```bash
git clone https://github.com/muhammedesatdemir/ScriptToSub-AI.git
cd ScriptToSub-AI
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**FFmpeg gereklidir**. Windows: `winget install Gyan.FFmpeg` veya
`choco install ffmpeg`. macOS: `brew install ffmpeg`.

### Gemini API anahtarlari (sadece Mod B icin)

`.streamlit/secrets.toml` olustur:

```toml
GEMINI_API_KEYS = [
    "AIza...birinci",
    "AIza...ikinci",
    "AIza...ucuncu",
]
```

Listede birden fazla key olabilir; biri quota / 503 yerse siradaki otomatik
devreye girer. Ornek sablon: [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example).

API key: [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Calistirma

```bash
streamlit run altyazi/app.py
```

Sonra tarayicida `http://localhost:8501`.

### Mod A kullanimi (referansli)

1. Sidebar'dan **"A — Script-Aware (Referansli)"**.
2. Video + script metnini (TXT dosyasi veya manuel) yukle.
3. Istege bagli: `Beat Separation (Demucs)` ac (muzik/beat varsa onerilir).
4. **Altyaziyi Olustur** → SRT hazir. **Altyaziyi Videoya Gom** → `.mp4` indir.

### Mod B kullanimi (referanssiz AI)

1. Sidebar'dan **"B — Autonomous AI (Metinsiz)"**.
2. Video yukle; script alani kaybolur, yerine **Video Baglami** (opsiyonel) gelir — orn. "Futbol analizi", "Teknoloji incelemesi".
3. `Gemini 3 Flash ile duzelt` isareti acik olsun (default).
4. **Altyaziyi Olustur**.

---

## Gemini Fallback Matrisi

Mod B'de refinement cagrisi **uc katmanli fallback** kullanir:

```
for key in GEMINI_API_KEYS:           # 3 anahtar
    for model in GEMINI_MODELS:       # 3 model
        for attempt in (1, 2):        # 503 icin ic retry (2s backoff)
            try: return response
            except Quota (429):       → siradaki modele
            except Overload (503):    → 2s backoff, sonra siradaki modele
            except Auth (401/403):    → siradaki key'e (bu key tamamen bypass)
            except Timeout:           → siradaki modele
```

Varsayilan model listesi (Nisan 2026):

```python
GEMINI_MODELS = (
    "gemini-2.5-flash-lite",   # en hizli, free-tier bol
    "gemini-2.5-flash",        # ikinci aday
    "gemini-2.0-flash",        # gecici fallback (2026-06-01'de retire)
)
```

Hepsi dusunce pipeline ham Whisper ciktisina gracefully duser — altyazi yine
uretilir, sadece AI refinement olmadan.

---

## Yapilandirma

Tum sabitler [altyazi/core/config.py](altyazi/core/config.py):

| Sabit | Varsayilan | Aciklama |
|---|---|---|
| `DEFAULT_WHISPER_MODEL` | `large-v3-turbo` | Whisper model boyutu |
| `WHISPER_LANGUAGE` | `tr` | Dil kodu |
| `GEMINI_MODELS` | 2.5-lite, 2.5, 2.0 | Fallback sirali tuple |
| `SUBTITLE_FONT_NAME` | `Montserrat Black` | ASS font adi |
| `SUB_PLAY_RES_X/Y` | 1080 × 1920 | 9:16 referans cozunurlugu |
| `SUB_MARGIN_V` | 410 | Alt safe-zone (px, PlayResY tabanli) |
| `SUB_FONT_SIZE` | 82 | ASS font boyu |
| `SUB_MAX_CHARS_PER_CUE` | 42 | Bir cue'da maks karakter |
| `SUB_MAX_WORDS_PER_CUE` | 8 | Bir cue'da maks kelime |
| `TR_STOPWORDS` | `{Ve, Bu, Ben, ...}` | `_highlight_words` icin istisna listesi |

---

## Render Ornegi — `_highlight_words`

```python
>>> _highlight_words("Icardi 2026 yilinda ve bir gol atti")
'{\\c&H00FFFF&}Icardi{\\c&HFFFFFF&} {\\c&H00FFFF&}2026{\\c&HFFFFFF&} yilinda ve bir gol atti'
```

`Icardi` ve `2026` sariya boyanir; `ve`, `bir` stopword oldugu icin beyaz kalir.

---

## Proje Felsefesi

- **Modular** — Her modul tek is yapar, public API'si `__init__.py`'de net.
- **Fonksiyonel** — Ic state tutulmaz, pipeline saf fonksiyonlardan olusur.
- **Graceful degradation** — Demucs yoksa duz ses, Gemini dusurse ham Whisper, bir fallback hep ayakta.
- **Tek kaynak yapilandirma** — Tum sabitler `core/config.py`; stil/limit degistirmek icin tek dosya.
- **WCAG-aware UI** — Koyu tema AA kontrasti, klavye focus-visible, semantik renkler.

---

## Yol Haritasi

- [ ] Ozel ASS stil onayarlari (preset'ler: Reels, Shorts, 16:9)
- [ ] Batch islem (bir klasordeki tum videolar icin CLI)
- [ ] Whisper model onbellegi (aynı video icin cache)
- [ ] Web-based phonetic dict editoru (Streamlit sidebar)
- [ ] Faster-whisper word confidence skoruyla interpolasyon kalite filtresi

---

## Lisans

MIT. Ayrintilar icin `LICENSE` dosyasina bakin.
