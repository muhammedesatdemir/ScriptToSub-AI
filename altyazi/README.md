# Script-to-Sub

Türkçe video içerikleri için **script tabanlı otomatik altyazı üretim sistemi**. Elinizde hazır konuşma metni (script) ve seslendirilmiş video varken, sesi otomatik transkribe edip kelime seviyesinde zaman damgaları ile orijinal script metnine hizalar; TDK uyumlu, özel isimleri doğru yazılmış, okuma konforu optimize edilmiş `.srt` dosyası üretir.

> **Problem:** Whisper gibi STT modelleri yabancı kökenli özel isimleri, marka adlarını ve terimleri fonetik olarak yazar; kesme işaretleri ve büyük/küçük harf kuralları tutarsız olur. Üstelik arka plan müziği varken hata oranı 2-3 katına çıkar.
>
> **Çözüm:** Whisper'ın *duyduğunu* değil, kullanıcının yazdığı *script'i* altyazı metni olarak kullan; Whisper'ı yalnızca **zamanlama kaynağı** olarak değerlendir. Aradaki boşluğu fonetik sözlük, fuzzy matching ve Türkçe kök çıkarma ile kapat.

---

## Öne Çıkan Özellikler

- **5 Katmanlı Hibrit Pipeline** — Demucs vokal izolasyonu → Whisper STT → akıllı eşleştirme → segmentasyon → SRT üretimi.
- **Vokal İzolasyonu** — `htdemucs` modeli ile arka plan müziği/beat ayrıştırılır, Whisper temiz vokal üzerinde çalışır.
- **Kelime Seviyesinde Hizalama** — `faster-whisper` + `word_timestamps=True` ile her kelimenin başlangıç/bitiş zamanı.
- **Akıllı Metin Eşleştirme** — `difflib` + `rapidfuzz` fuzzy matching, Türkçe kök çıkarma (stemming) ve genişletilebilir fonetik sözlük ile yabancı kökenli isim ve terimlerin doğru yazılımı.
- **Script Sadakati** — Görüntülenen metin her zaman orijinal script'ten alınır; sadece zaman damgaları Whisper'dan gelir.
- **Segment Optimizasyonu** — Max 42 karakter/satır, max 21 chr/sn okuma hızı, 1-7sn segment süresi, doğal bölünme noktaları.
- **Altyazıyı Videoya Gömme (Hardcoded Subtitles)** — Üretilen `.srt`, `libass` stil şablonu ile FFmpeg üzerinden doğrudan video karelerine işlenir; çıktı olarak altyazısı gömülü tek parça `.mp4` elde edilir. Böylece oynatıcı desteği gerektirmeyen, sosyal medya ve kısa format video platformlarına doğrudan yüklenebilen son sürüm video üretilir.
- **Streamlit Arayüzü** — Video + script yükle, altyazıyı oluştur, tarayıcıda önizle, `.srt` olarak indir **veya tek tıkla videoya göm ve altyazılı `.mp4`'ü indir**.

---

## Mimari

```
[Video] ──► Katman 0: FFmpeg + Demucs (vokal izolasyonu)
              │
              ▼
            Katman 1: faster-whisper (large-v3-turbo)
                      → kelime + zaman damgaları
              │
[Script] ──► Katman 2: Akıllı Eşleştirme
                      → fonetik sözlük + fuzzy match + stemming
              │
              ▼
            Katman 3: Segmentasyon
                      → doğal bölünme, okuma hızı, satır uzunluğu
              │
              ▼
            Katman 4: SRT Üretimi ──► [output.srt]
              │
              ▼
            Katman 5 (opsiyonel): FFmpeg + libass
                      → altyazıyı videoya göm ──► [output_altyazili.mp4]
```

Detaylı mimari, teknoloji karşılaştırmaları ve tasarım kararları için: [SISTEM_ANALIZ_RAPORU.md](SISTEM_ANALIZ_RAPORU.md)

---

## Teknoloji Yığını

| Katman | Araç | Amaç |
|---|---|---|
| Ses İşleme | `ffmpeg`, `demucs` (htdemucs) | Ses çıkarma, vokal izolasyonu |
| STT | `faster-whisper` (large-v3-turbo) | Konuşma tanıma + kelime timestamp |
| Eşleştirme | `difflib`, `rapidfuzz` | Fuzzy string matching |
| Türkçe NLP | Özel stemmer + fonetik sözlük | Eklemeli yapı ve özel isim desteği |
| Arayüz | `streamlit` | Web tabanlı yükleme/önizleme |
| SRT Üretimi | Özel segmentasyon motoru | Standart `.srt` dosyası |
| Video Gömme | `ffmpeg` + `libass` filtresi | Altyazının doğrudan karelere işlendiği `.mp4` |

---

## Kurulum

**Gereksinimler:** Python 3.10+, FFmpeg (sistem PATH'inde), CUDA destekli GPU önerilir (CPU'da da çalışır).

```bash
git clone https://github.com/muhammedesatdemir/ScriptToSub-AI.git
cd ScriptToSub-AI

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install streamlit faster-whisper demucs torch rapidfuzz
```

`ffmpeg` kurulu mu kontrol:
```bash
ffmpeg -version
```

---

## Kullanım

### Web Arayüzü

```bash
streamlit run app.py
```

Tarayıcıda açılan sayfada:
1. Video dosyasını yükle (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`)
2. Script metnini yapıştır veya `.txt` dosyası yükle
3. *(Opsiyonel)* Özel fonetik sözlük JSON'u yükle
4. **Altyazı Oluştur** butonuna bas — pipeline çalışır, segmentler ve istatistikler ekrana gelir
5. **SRT Dosyasını İndir** ile ham altyazıyı al, ya da
6. **Altyazıyı Videoya Göm** butonu ile FFmpeg pipeline'ını tetikleyip altyazılı video önizlemesini tarayıcıda gör ve **Altyazılı Videoyu İndir** ile `.mp4` olarak kaydet

### Programatik Kullanım

```python
from altyazi.script_to_sub import (
    extract_audio, isolate_vocals, transcribe_with_timestamps,
    tokenize_script, enhanced_align_words, create_segments,
    optimize_segments, generate_srt, DEFAULT_PHONETIC_DICT,
)

vocal = isolate_vocals("video.mp4", "out/")
whisper_data = transcribe_with_timestamps(vocal, language="tr", model_size="large-v3-turbo")

script_tokens = tokenize_script(open("script.txt", encoding="utf-8").read())
aligned = enhanced_align_words(script_tokens, whisper_data["all_words"], DEFAULT_PHONETIC_DICT)

segments = optimize_segments(create_segments(aligned))
generate_srt(segments, "output.srt")
```

### Fonetik Sözlük Formatı

```json
{
  "Nietzsche":  ["niçe", "niçi", "niçeyi"],
  "TensorFlow": ["tensörflov", "tensor flow", "tensorflov"],
  "Bordeaux":   ["bordo", "bordoyu", "bordonun"]
}
```

Sözlük anahtarı script'te görünecek doğru yazım; değerler Whisper'ın üretebileceği fonetik varyantlardır. Sistem çalışma anında ters indeks kurup eşleştirme sırasında fallback olarak kullanır. Böylece felsefe, teknoloji, spor, tarih, sinema gibi herhangi bir içerik alanında alan-özgün terim havuzunuzu JSON dosyasına ekleyerek sistemi kendi konunuza uyarlayabilirsiniz.

---

## Proje Yapısı

```
altyazi/
├── app.py                    # Streamlit arayüzü
├── script_to_sub.py          # Pipeline — 5 katmanlı hibrit motor
├── SISTEM_ANALIZ_RAPORU.md   # Mimari + teknoloji analizi
└── README.md
```

Ana modülün sunduğu fonksiyonlar:

| Fonksiyon | Görev |
|---|---|
| `extract_audio` | FFmpeg ile 16kHz mono WAV ses çıkarma |
| `isolate_vocals` | Demucs htdemucs ile vokal izolasyonu |
| `transcribe_with_timestamps` | faster-whisper + kelime-seviye timestamp |
| `tokenize_script` | Script metnini normalize edip token listesine çevirme |
| `turkish_stem` | Türkçe ek temizleyen basit stemmer |
| `enhanced_align_words` | Çok aşamalı eşleştirme (exact → stem → fonetik → fuzzy) |
| `create_segments` | Kelime listesinden altyazı segmentleri oluşturma |
| `optimize_segments` | Okuma hızı, süre ve satır uzunluğu optimizasyonu |
| `generate_srt` | Standart SRT formatında dosya üretme |
| `burn_subtitles` *(app.py)* | FFmpeg + libass ile altyazıyı videoya gömüp `.mp4` döndürme |

---

## Tasarım Notları

- **Neden hibrit?** Saf forced alignment, Türkçe'nin eklemeli yapısında (bir özel ismin ardından gelen "-ye", "-nin", "-dan" gibi çekim ekleriyle) ve doğaçlama konuşmada kırılır. Saf STT ise yabancı kökenli özel isimleri fonetik olarak yanlış yazar. İkisinin güçlü yanlarını birleştirmek zorunluydu.
- **Neden script metni otorite?** Kullanıcı script'i kendi yazıyor — TDK uyumu, kesme işaretleri ve özel isimler zaten doğru. Whisper'dan sadece *ne zaman söylendi* bilgisi alınıyor.
- **Neden Demucs?** Arka plan beat'i varken Whisper WER'ı %8'den %20+'ya çıkıyor. Vokal izolasyonu ilk katmana konularak tüm alt pipeline'ın girdi kalitesi sabitleniyor.
- **Neden Gemini yok?** İlk tasarımda Katman 3 olarak düşünülen LLM bağlam düzeltme, genişletilmiş fonetik sözlük + stemming + çok aşamalı fuzzy matching ile büyük oranda gereksiz hale geldi. API bağımlılığı olmayan tamamen lokal bir pipeline tercih edildi.
- **Neden altyazıyı videoya gömme seçeneği?** Sosyal medya platformlarının çoğu yan `.srt` dosyası kabul etmez; farklı oynatıcılarda altyazı stili tutarsız görünür. FFmpeg'in `libass` filtresi ile altyazı doğrudan karelere işlenir; font, kenarlık, arka plan ve alt kenar boşluğu sabitlenir, böylece çıktı her platformda aynı görünür ve kullanıcının ayrıca video düzenleme yazılımı açmasına gerek kalmaz.

---

## Lisans

MIT
