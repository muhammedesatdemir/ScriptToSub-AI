# Script-to-Sub: Sistem Analiz Raporu ve Proje Plani

**Proje:** Metinden Altyaziya Otomasyonu (Script-to-Sub)  
**Tarih:** 11 Nisan 2026  
**Hazirlanma Amaci:** Icerik ureticisinin elindeki hazir video metnini temel alarak, sesle %100 senkronize, TDK uyumlu ve yabanci isimleri dogru yazan bir altyazi sistemi kurmak.

---

## Icindekiler

1. [Problem Tanimi ve Gercek Senaryo Analizi](#1-problem-tanimi-ve-gercek-senaryo-analizi)
2. [Teknoloji Analizi (Nisan 2026)](#2-teknoloji-analizi-nisan-2026)
3. [Mimari Karar: Hibrit Yaklasim](#3-mimari-karar-hibrit-yaklasim)
4. [Isim ve Terim Yonetimi: Context-Aware Yapi](#4-isim-ve-terim-yonetimi-context-aware-yapi)
5. [Arka Plan Muzigi / Beat Sorunu](#5-arka-plan-muzigi--beat-sorunu)
6. [Arac Seti (Stack)](#6-arac-seti-stack)
7. [Risk Analizi ve Cozumler](#7-risk-analizi-ve-cozumler)
8. [Gemini Onerisi Degerlendirmesi](#8-gemini-onerisi-degerlendirmesi)
9. [Proje Plani ve Yol Haritasi](#9-proje-plani-ve-yol-haritasi)

---

## 1. Problem Tanimi ve Gercek Senaryo Analizi

### 1.1. Kullanici Profili

Futbol icerik ureticisi. Hazir script yazarak video seslendirir, ardindan altyazi ekler. Videolar Shorts/Reels formatinda veya uzun format olabilir.

### 1.2. Ornek Metin Uzerinden Zorluk Haritasi

Asagidaki ornek metin, sistemin karsilasacagi **tum zorluk tiplerini** icermektedir:

> "Galatasaray'dan gozyaslariyla ayrilan Dries Mertens'in burada gecirdigi 3 yilda disini tirnagina taktigi cok zaman bulunsa da 2023-24 sezonu boyunca iyi performans verip ozellikle son duzlukte kurtarici modunu aktif etmisti. Ligdeki son 10 mucadelede 5 gol 10 asist kaydeden 10 numara skor katkilarinda Kerem Demirbay'in Rize'ye Hakim Ziyech'in de Alanya ve Adana Demirspor'a yolladigi fuzelerin pasini verdigi kadar kolay olmadigini Kasimpasa mucadelesinde perdenin acildigi enfes sayiyi kaydederek gostermis ayni macta serbest vurustan ve akabindeki Hatay karsilasmasinda kornerden Icardiye yazdirdigi sayilarda ise duran top da bizim isimiz demisti..."

#### Tespit Edilen Zorluk Kategorileri

| # | Zorluk Tipi | Metindeki Ornekler | Whisper'in Muhtemel Hatasi | Kritiklik |
|---|---|---|---|---|
| 1 | **Yabanci Ozel Isimler** | Dries Mertens, Hakim Ziyech, Icardi | "dris mertens", "ziyes", "ikardi" | KRITIK |
| 2 | **Turkce Ozel Isimler** | Kerem Demirbay, Kasimpasa | Genelde dogru, ama ek alinca sorun | ORTA |
| 3 | **Takim Isimleri** | Galatasaray, Adana Demirspor, Karagumruk | Genelde dogru | DUSUK |
| 4 | **Eklemeli Yapilar** | "Mertens'in", "Icardi'ye", "Ziyech'in" | Eki ayirabilir veya yanlis ekleyebilir | YUKSEK |
| 5 | **Deyimler / Mecazlar** | "disini tirnagina takti", "fuzelerin pasini" | Kelime kelime dogru duyabilir ama birlestiremeyebilir | ORTA |
| 6 | **Sayisal Ifadeler** | "3 yil", "2023-24 sezonu", "5 gol 10 asist" | "uc yil", "ikibin yirmiuc yirmidort" yazabilir | YUKSEK |
| 7 | **Uzun Cumle Yapilari** | "Kerem Demirbay'in Rize'ye..." (tek cumle ~45 kelime) | Cumle ortasinda segment bolunmesi | YUKSEK |
| 8 | **Futbol Terminolojisi** | "serbest vurus", "duran top", "10 numara" | Genelde dogru | DUSUK |
| 9 | **Hizli Konusma / Akim** | Tum metin hizli tempo ile okunuyor | Kelime birlesmesi, atlama | YUKSEK |
| 10 | **Arka Plan Muzigi** | Video'da beat var | SNR duserse WER artar | **KRITIK** |

### 1.3. Temel Ihtiyaclar

1. **Kelime Duzeyi Senkronizasyon:** Her kelimenin baslangic/bitis zamani bilinmeli.
2. **Script Sadakati:** Altyazi metni Whisper'in duydugu degil, script'teki metin olmali.
3. **Ozel Isim Dogrulugu:** "Kutinyo" degil "Coutinho", "Mertens" degil "Mertenz".
4. **TDK Uyumu:** Dogru noktalama, buyuk/kucuk harf, kesme isareti.
5. **Okuma Konforu:** Segment uzunlugu, okuma hizi, satirda bolunme optimizasyonu.
6. **Arka Plan Muzigine Dayaniklilik:** Beat/muzik varken bile dogru calismali.

---

## 2. Teknoloji Analizi (Nisan 2026)

### 2.1. STT Modelleri Karsilastirmasi

| Model | Turkce WER | Maliyet | Calisma Modu | Kelime Timestamp | Gurultu Direnci | Degerlendirme |
|---|---|---|---|---|---|---|
| **Whisper large-v3-turbo** (`faster-whisper`) | ~%8-12 | Ucretsiz (lokal) | Offline | Var (`word_timestamps=True`) | Orta | **Birincil tercih** |
| **Whisper large-v3** | ~%7-10 | Ucretsiz (lokal) | Offline | Var | Orta-Iyi | Daha yavas ama daha isabetli |
| **Gemini 2.5 Flash** | Iyi (multimodal) | Ucretsiz kota | Online API | Yok (segment duzeyi) | Iyi | Alignment icin degil, baglam duzeltme icin |
| **Gemini 2.5 Pro** | Cok iyi | Ucretli | Online API | Yok | Cok iyi | Maliyet/fayda orani dusuk |
| **Azure Speech SDK** | Cok iyi | Ucretli (dusuk) | Online API | Var (native) | Iyi | Alternatif alignment kaynagi |
| **Deepgram Nova-3** | Iyi | Ucretli | Online API | Var | Cok iyi | Muzikli icerik icin guclu |

> **Not:** "Gemini 3 Flash" Nisan 2026 itibariyle mevcut degildir. Gemini'nin analiz raporundaki bu referans hatalidir. Guncel olan Gemini 2.5 Flash/Pro modelleridir.

### 2.2. Forced Alignment Araclari

| Arac | Yaklasim | Turkce Destegi | Avantaj | Dezavantaj |
|---|---|---|---|---|
| **whisper-timestamped** | Whisper + DTW | Tum Whisper dilleri | Entegre, kelime-seviye | Whisper hatalari tasinir |
| **stable-ts** | Whisper cikti stabilizasyonu | Ayni | Daha kararli zaman damgalari | Ekstra katman |
| **CTC Forced Alignment (torchaudio)** | Wav2Vec2 tabanli | Turkce model gerekli | Cok hassas | Model bulmak/egitmek gerekebilir |
| **Aeneas** | DTW + TTS tabanli | Turkce TTS varsa calisir | Basit ve etkili | Kelime duzeyinde zayif |
| **NeMo Forced Aligner** | NVIDIA NeMo | Sinirli Turkce | Cok hassas | Kurulumu karmasik |

### 2.3. Ses Ayristirma (Source Separation) Araclari

Arka plan muzigi sorunu icin kritik:

| Arac | Yontem | Kalite | Hiz | Maliyet |
|---|---|---|---|---|
| **Demucs v4 (htdemucs)** | Hibrit derin ogrenme | Cok iyi | Orta | Ucretsiz (lokal) |
| **UVR (Ultimate Vocal Remover)** | Cesitli modeller | Iyi-Cok iyi | Degisken | Ucretsiz |
| **Spleeter** | U-Net tabanli | Orta | Hizli | Ucretsiz |

---

## 3. Mimari Karar: Hibrit Yaklasim

### 3.1. Neden Saf Forced Alignment Yetmez?

Gemini'nin onerisi olan saf Forced Alignment ("metnini capa olarak kullan, sadece zamanlama bul") teoride dogru ama **bu proje icin pratikte yetersiz**. Nedenleri:

1. **Dogaclama:** Kullanici metinden sapabilir — kelime atlar, ekler, sirasi degistirir.
2. **Eklemeli Dil:** "Icardi" → "Icardi'ye yazdirdigi" gibi donusumler forced alignment'i zorlar.
3. **Fonetik Uyumsuzluk:** "Mertens" yazili ama "mertenz" seslendiriliyor — dogrudan alignment tutmaz.
4. **Sayisal Ifadeler:** "2023-24" yazili ama "ikibin yirmiuc yirmidort" seslendiriliyor.
5. **Arka Plan Muzigi:** Beat varken forced alignment'in dogrulugu ciddi sekilde duser.

### 3.2. Onerilen Mimari: 5 Katmanli Hibrit Pipeline

```
GIRDI                          ISLEM HATTI                         CIKTI
=====                          ===========                         =====

                         +---------------------------+
[Video/Ses Dosyasi] ---->| KATMAN 0: On-Isleme       |
                         | FFmpeg: ses cikarma        |
                         | Demucs: vokal izolasyonu   |
                         | (arka plan muzigi ayirma)  |
                         +-------------+-------------+
                                       |
                                       v
                         +---------------------------+
                         | KATMAN 1: STT + Timestamp  |
                         | faster-whisper (large-v3-  |
                         | turbo) + stable-ts         |
                         | word_timestamps=True       |
                         | Cikti: kelime listesi +    |
                         |   baslangic/bitis zamanlari|
                         +-------------+-------------+
                                       |
                                       v
[Script Metni] -------->+---------------------------+
                         | KATMAN 2: Akilli Eslestirme|
                         | 1. Metin normalizasyonu    |
                         | 2. difflib SequenceMatcher |
                         | 3. rapidfuzz fuzzy match   |
                         | 4. Fonetik sozluk arama    |
                         | 5. Turkce stemming         |
                         | Cikti: eslesmis kelime     |
                         |   cifti + zaman damgalari  |
                         +-------------+-------------+
                                       |
                                       v
                         +---------------------------+
                         | KATMAN 3: Baglam Duzeltme  |
                         | Gemini 2.5 Flash API       |
                         | - Belirsiz eslesmeleri     |
                         |   dogrula                  |
                         | - TDK uyumu kontrol        |
                         | - Segment sinirlarini      |
                         |   optimize et              |
                         | - Sayi/tarih formatlama    |
                         +-------------+-------------+
                                       |
                                       v
                         +---------------------------+
                         | KATMAN 4: SRT Uretimi      |
                         | - Segment birlestirme      |
                         | - Satir uzunlugu (<42 chr) |
                         | - Okuma hizi (<21 chr/sn)  |
                         | - Min 1sn, Max 7sn kural   |
                         | - Dogal bolunme noktalari  |
                         +---------------------------+
                                       |
                                       v
                              [CIKTI: .srt dosyasi]
```

### 3.3. Neden Bu Siralamayla?

| Adim | Neden Bu Sirada? |
|---|---|
| **Katman 0 (Vokal Izolasyonu)** | Beat varken Whisper WER %8'den %20+'ya cikar. Temiz vokal uzerinde calismak tum alt katmanlarin isini kolaylastirir |
| **Katman 1 (Whisper STT)** | Once sesi kelime kelime yaziya dokup zaman damgalarini al. Script olmadan, sesin ne soyledigini ve **ne zaman** soyledigini ogren |
| **Katman 2 (Eslestirme)** | Simdi Whisper'in duyduklarini script ile karsila. "mertenz" → "Mertens", "ikardiye" → "Icardi'ye" donusumlerini yap |
| **Katman 3 (LLM Duzeltme)** | Emin olunamayan durumlarda Gemini'ye sor. TDK uyumunu kontrol et. Segmentleri optimize et |
| **Katman 4 (SRT)** | Her sey hazir, altyazi dosyasini formatla ve uret |

---

## 4. Isim ve Terim Yonetimi: Context-Aware Yapi

### 4.1. Ornek Metindeki Tum Ozel Isimler ve Fonetik Karsiliklari

Bu tablonun olusturulmasi sistemin en kritik adimidir:

| Script'teki Yazi | Seslendirmedeki Fonetik | Whisper'in Muhtemelen Yazacagi | Zorluk |
|---|---|---|---|
| Dries Mertens | "dris mertenz" | "Dries Mertens" veya "Dris Mertenz" | ORTA |
| Kerem Demirbay | "kerem demirbay" | "Kerem Demirbay" (dogru) | DUSUK |
| Hakim Ziyech | "hakim ziyes" | "Hakim Ziyeş" veya "Ziyes" | YUKSEK |
| Icardi | "ikardi" | "Ikardi" veya "İkardi" | ORTA |
| Galatasaray | "galatasaray" | "Galatasaray" (dogru) | DUSUK |
| Kasimpasa | "kasimpasa" | "Kasimpasa" veya "Kasımpaşa" | DUSUK |
| Adana Demirspor | "adana demirspor" | "Adana Demirspor" (dogru) | DUSUK |
| Karagumruk | "karagumruk" | "Karagümrük" (dogru) | DUSUK |

### 4.2. Uc Katmanli Eslestirme Sistemi

#### Katman A: Fonetik Eslestirme Sozlugu (Statik — Kullanici Tanimli)

Kullanici JSON formatinda bir sozluk olusturur. Sistem her videoda bu sozluge basvurur:

```json
{
  "futbol_isimleri": {
    "Dries Mertens": ["dris mertenz", "dris mertens", "driyes mertens"],
    "Hakim Ziyech": ["hakim ziyes", "ziyes", "ziyeş", "ziyec"],
    "Icardi": ["ikardi", "İkardi", "icardi"],
    "Philippe Coutinho": ["kutinyo", "filipi kutinyo", "koutinho"],
    "Kerem Demirbay": ["kerem demirbay"]
  },
  "takim_isimleri": {
    "Galatasaray": ["galatasaray"],
    "Adana Demirspor": ["adana demirspor"],
    "Karagumruk": ["karagümrük", "fatih karagümrük"]
  },
  "terimler": {
    "serbest vurus": ["serbest vuruş"],
    "duran top": ["duran top"]
  }
}
```

**Onemli:** Bu sozluk zamanla buyur. Kullanici her yeni video icin yeni isimler ekler. Sistem onceki videolardaki eslesmeleri hatirlar.

#### Katman B: Fuzzy + Fonetik Matching (Dinamik — Otomatik)

Sozlukte olmayan kelimeler icin:

1. **Levenshtein Distance:** Whisper ciktisi "mertenz" vs script "Mertens" → mesafe: 1 → esles
2. **Turkce Fonetik Kurallari:** s↔z, c↔j, ş↔s, ch↔ç donusumleri
3. **Kok Eslestirme:** "Icardi'ye" → kok "Icardi" → script'te "Icardi" var → esles, eki koru
4. **N-gram Benzerligi:** Uzun kelimelerde parcali karsilastirma

#### Katman C: LLM Dogrulama (Akilli — Gemini 2.5 Flash)

Belirsiz durumlarda Gemini'ye baglamla birlikte sor:

```
Baglam: Turkce futbol video altyazisi
Whisper ciktisi: "demirbay'in rize'ye hakim ziyes'in de alanya'ya"
Script metni: "Kerem Demirbay'in Rize'ye Hakim Ziyech'in de Alanya..."

Soru: Whisper'in "ziyes" kelimesi script'teki "Ziyech" ile mi eslesmeli?
Dogru altyazi metni ne olmali?
```

### 4.3. Sayi ve Tarih Formatlama

Ornek metinde "2023-24 sezonu", "3 yil", "5 gol 10 asist" gibi ifadeler var.

| Seslendirme | Whisper Yazabilir | Script'teki Hali | Altyazidaki Dogru Hali |
|---|---|---|---|
| "ikibin yirmiuc yirmidort" | "2023 24" veya "2023-24" | "2023-24 sezonu" | "2023-24 sezonu" |
| "uc yil" | "3 yil" veya "uc yil" | "3 yilda" | "3 yilda" |
| "bes gol on asist" | "5 gol 10 asist" | "5 gol 10 asist" | "5 gol 10 asist" |

**Cozum:** Sayisal ifadeler her zaman script'ten alinir. Whisper'in sayi formati ne olursa olsun, eslestirme sirasinda normalize edilip script karsiligi kullanilir.

---

## 5. Arka Plan Muzigi / Beat Sorunu

Bu, projenin **en kritik teknik zorluklarindan biri**. Detayli analiz:

### 5.1. Sorunun Boyutu

| Senaryo | Tahmini Whisper WER (Turkce) | Etki |
|---|---|---|
| Temiz ses (sadece vokal) | %8-12 | Sorunsuz |
| Dusuk seviye arka plan muzigi (SNR > 20dB) | %10-15 | Kabul edilebilir |
| Orta seviye beat (SNR 10-20dB) | %15-25 | Bazi kelimeler kaybolur |
| Yuksek seviye beat (SNR < 10dB) | %25-40+ | Sistem guvenilmez hale gelir |

> **SNR (Signal-to-Noise Ratio):** Sesin muzige orani. Dusukse muzik sesi bastirir.

### 5.2. Cozum: Vokal Izolasyonu (Katman 0)

**Demucs v4 (htdemucs)** modeli ile ses dosyasini 4 kanala ayirabiliriz:
- **Vocals (Vokal):** Sadece insan sesi ← BU KANALI KULLANIRIZ
- **Drums (Ritim):** Davul, perküsyon
- **Bass (Bas):** Bas gitar, dusuk frekanslar
- **Other (Diger):** Diger enstrumanlar

```
[Orijinal Ses] ---> Demucs v4 ---> [Vokal Kanali] ---> Whisper STT
(vokal + beat)                      (sadece vokal)      (temiz giris)
```

### 5.3. Uygulama Stratejisi: 3 Mod

Kullanicinin secebilecegi 3 mod:

| Mod | Aciklama | Ne Zaman Kullanilir | Islem Suresi |
|---|---|---|---|
| **Mod A: Temiz Ses** | Demucs atlanir, ses dogrudan Whisper'a gider | Arka plan muzigi yokken veya cok dusukken | En hizli |
| **Mod B: Beat Ayirma** | Demucs ile vokal izole edilir, temiz vokal Whisper'a gider | Arka plan muzigi/beat varken (VARSAYILAN) | +30-60sn (1dk video icin) |
| **Mod C: Cift Kanal** | Hem orijinal hem izole vokal Whisper'a verilir, sonuclar karsilas | Cok gurultulu veya kalabalik ses ortaminda | En yavas, en dogru |

### 5.4. Onemli Not: Beat Ne Zaman Ekleniyor?

Kullanicinin belirttigi senaryo:

> "Videonun son halinde ses'e ek olarak arka plan muzigi beat'i var. Eger bu durum cok sikinti yaratacaksa en son da eklenebilir."

**Ideal Workflow:**

```
1. Video'yu ONCESINDE altyazila (beat eklenmeden, temiz sesle)
   --> En dogru sonuc, Demucs'a gerek yok

2. Sonra beat'i video'ya ekle
   --> Altyazi zaten hazir, beat zamanlama'yi etkilemez

3. Eger beat onceden eklenmisse:
   --> Mod B (Demucs vokal izolasyonu) kullan
```

**Tavsiye:** Mumkunse beat eklenmeden onceki temiz ses dosyasini sisteme ver. Bu, tum pipeline'in en dogru calismasini saglar ve Demucs adimini tamamen atlar. Eger bu mumkun degilse, Demucs ile vokal izolasyonu %90+ basariyla temiz ses elde eder.

---

## 6. Arac Seti (Stack)

### 6.1. Temel Bilesenlerin Tablo Gorunumu

| Katman | Arac | Gorevi | Maliyet | Zorunlu mu? |
|---|---|---|---|---|
| **Ses Cikarma** | `ffmpeg` | Video'dan ses cikarma (mp4 → wav) | Ucretsiz | Evet |
| **Vokal Izolasyonu** | `demucs` (htdemucs) | Arka plan muzigini ayirma | Ucretsiz (lokal) | Beat varsa Evet |
| **STT + Timestamp** | `faster-whisper` (large-v3-turbo) | Konusmayi yaziya dokme + kelime zamanlari | Ucretsiz (lokal) | Evet |
| **Timestamp Stabilizasyonu** | `stable-ts` | Whisper zaman damgalarini duzeltme | Ucretsiz | Evet |
| **Metin Eslestirme** | `difflib` + `rapidfuzz` | Script-Whisper kelime eslestirme | Ucretsiz | Evet |
| **Turkce NLP** | `TurkishStemmer` / `zeyrek` | Kok cikarma, ek ayristirma | Ucretsiz | Evet |
| **Baglam Duzeltme** | `Gemini 2.5 Flash API` | Belirsiz eslesmeler, TDK, segmentasyon | Ucretsiz kota | Opsiyonel (tavsiye) |
| **SRT Uretimi** | `pysrt` veya `srt` | Altyazi dosyasi olusturma | Ucretsiz | Evet |
| **Arayuz** | `Streamlit` | Kullanici paneli | Ucretsiz | Faz 3'te |
| **Video Onizleme** | `ffmpeg` + Streamlit | Altyazili video onizleme | Ucretsiz | Faz 3'te |

### 6.2. Python Bagimliliklari

```
# Temel (Faz 1 - MVP)
faster-whisper       # Whisper STT (lokal, hizli)
stable-ts            # Zaman damgasi stabilizasyonu
rapidfuzz            # Fuzzy string matching
pysrt                # SRT dosya okuma/yazma
ffmpeg-python        # FFmpeg Python wrapper

# Genisletilmis (Faz 2)
google-genai         # Gemini 2.5 Flash API SDK
zeyrek               # Turkce morfolojik analiz
demucs               # Vokal izolasyonu (beat ayirma)

# Arayuz (Faz 3)
streamlit            # Web arayuzu
```

### 6.3. Donanim Gereksinimleri

| Bilesen | Minimum | Tavsiye |
|---|---|---|
| **RAM** | 8 GB | 16 GB |
| **GPU** | Gerekli degil (CPU calisir) | NVIDIA GPU (CUDA) → 5-10x hizlanma |
| **Disk** | ~5 GB (modeller icin) | 10 GB |
| **Internet** | Sadece Gemini API icin | Model indirme icin (bir kez) |

### 6.4. Maliyet Analizi

| Bilesen | Aylik Maliyet (haftada 5 video uretimi) |
|---|---|
| Whisper (lokal) | 0 TL |
| Demucs (lokal) | 0 TL |
| Gemini 2.5 Flash (ucretsiz kota: 1500 istek/gun) | 0 TL |
| Streamlit (lokal) | 0 TL |
| **Toplam** | **0 TL** |

> **Not:** Haftada 5 video bile uretsek, Gemini ucretsiz kotasi fazlasiyla yeterli. Her video icin 5-10 API cagrisi yapilsa, ayda ~200 cagri eder. Ucretsiz kota gunluk 1500 civarinda.

---

## 7. Risk Analizi ve Cozumler

### Risk 1: Turkce Eklemeli Yapi — Senkron Kaymasi

**Problem:** "Icardi" kelimesi script'te var, ama konusmaci "Icardi'ye yazdirdigi" diye seslendiriyor. Whisper bunu farkli sekillerde bolup yazabilir.

**Somut Ornek (Metin'den):**
- Script: `"Icardi'ye yazdirdigi sayilarda"`
- Whisper: `"ikardiye yazdırdığı sayılarda"` (zamanlama: 0:42.300 - 0:44.100)
- Sorun: "ikardiye" tek kelime olarak algiliyor, "Icardi'ye" ile eslestirme yapilmali

**Cozum:**
1. Turkce stemmer ile her iki taraftaki kokleri cikar: "ikardiye" → "ikardi", "Icardi'ye" → "Icardi"
2. Kok uzerinden eslesme yap
3. Goruntulenecek metni script'ten al: "Icardi'ye"
4. Zamanlamayi Whisper'dan al

### Risk 2: Hizli Konusma — Kelime Birlesmesi ve Atlama

**Problem:** Ornek metinde "Kerem Demirbay'in Rize'ye Hakim Ziyech'in de Alanya ve Adana Demirspor'a yolladigi fuzelerin pasini verdigi" gibi 20+ kelimelik kesintisiz cumle var. Hizli okunursa Whisper kelimeleri birlestirir veya atlar.

**Cozum:**
1. `stable-ts` zaman damgalarini stabilize eder
2. `condition_on_previous_text=True` parametresi baglam devamliligi saglar
3. Kelime duzeyi basarisiz olursa, **segment duzeyine** geri dus (cumle eslestirme)
4. Segment icindeki kelimeleri esit aralikla dagit (son care, ama %95 dogru sonuc verir)

### Risk 3: Dogaclama / Script Sapmasi

**Problem:** Kullanici script'te olmayan bir sey soyluyor veya bir cumleyi atliyor.

**Cozum:** Diff algoritmasi ile 3 durum tespit edilir:

| Durum | Tespit | Islem |
|---|---|---|
| **Eslesme** | Script kelimesi = Whisper kelimesi | Script metnini ve Whisper zamanini kullan |
| **Script'te var, seste yok** | Script kelimesi Whisper'da bulunamadi | Kelimeyi atla veya uyari ver |
| **Seste var, script'te yok** | Whisper kelimesi script'te yok (dogaclama) | Mod A: yoksay / Mod B: Whisper metnini kullan, isaretle |

### Risk 4: Uzun Cumleler — Segment Bolunmesi

**Problem:** Ornek metindeki cumle cok uzun. Altyazi segmenti olarak 7 saniyeden uzun veya 84 karakterden fazla olamaz.

**Somut Ornek:**
```
Script cumlesi:
"Kerem Demirbay'in Rize'ye Hakim Ziyech'in de Alanya ve Adana Demirspor'a 
yolladigi fuzelerin pasini verdigi kadar kolay olmadigini Kasimpasa 
mucadelesinde perdenin acildigi enfes sayiyi kaydederek gostermis"

Bu ~240 karakter = en az 6 segmente bolunmeli
```

**Cozum:** Akilli segmentasyon kurallari:
1. Virgul, nokta, "ve", "ama", "ise", "de/da" gibi dogal bolunme noktalarinda bol
2. Her segment max 84 karakter (2 satir x 42)
3. Her segment max 7 saniye
4. Okuma hizi max 21 karakter/saniye
5. Anlam butunlugunu koru (ozneyi fiilden ayirma)

### Risk 5: Arka Plan Muzigi — WER Artisi

**Problem:** Beat varken Whisper hata orani 2-3x artabilir.

**Cozum:**
1. **Birincil:** Beat eklenmeden onceki temiz ses dosyasini kullan (ideal)
2. **Ikincil:** Demucs v4 ile vokal izolasyonu (Katman 0)
3. **Ucuncul:** Gemini 2.5 Flash'a hem sesi hem script'i vererek dogrulama

**Demucs Performansi (Beklenen):**
| Senaryo | Demucs Oncesi WER | Demucs Sonrasi WER |
|---|---|---|
| Hafif beat | %12-18 | %8-12 (temiz ses seviyesi) |
| Orta beat | %18-25 | %10-15 |
| Agir beat | %25-40 | %12-20 |

### Risk 6: API Bagimliligi

**Problem:** Gemini API kotasi biterse veya hizmet kesintisi olursa.

**Cozum:**
- Gemini sadece **Katman 3** (opsiyonel baglam duzeltme) icin kullaniliyor
- API olmadan sistem calisir — belirsiz eslesmelerde manuel onay gerekir
- Fallback siralama: Gemini 2.5 Flash → Gemini 2.5 Pro → Manuel onay

---

## 8. Gemini Onerisi Degerlendirmesi

Gemini'nin analiz raporundaki onerilere dair detayli degerlendirme:

| Gemini'nin Onerisi | Durum | Degerlendirme |
|---|---|---|
| "Gemini 3 Flash kullan" | **YANLIS** | Bu model mevcut degil. Guncel olan Gemini 2.5 Flash'tir |
| "Forced Alignment tek basina yeterli" | **EKSIK** | Turkce eklemeli yapi, yabanci isimler ve dogaclama nedeniyle tek basina yetersiz. Hibrit yaklasim sart |
| "Awasu veya PyTorch Alignment" | **BELIRSIZ** | "Awasu" dogrulanamadi, muhtemelen Aeneas kastediliyor. torchaudio forced alignment ise gecerli ama Turkce model gerektirir |
| "Whisper-v3-Turbo lokal calisir, ucretsiz" | **DOGRU** | faster-whisper implementasyonu ile en iyi lokal secim |
| "Streamlit ile 5 dakikada panel" | **DOGRU** | Arayuz icin ideal secim |
| "Tek Python dosyasinda yaz" | **KISMEN DOGRU** | MVP icin dogru, ama olceklendirilebilirlik icin moduler yapi gerekecek |
| "Ucretsiz kota yeterli" | **DOGRU** | Shorts/icerik uretim hacmi icin Gemini ucretsiz kotasi fazlasiyla yeterli |
| "Hibrit Mod gerekebilir (dogaclama icin)" | **DOGRU** | Bu tam olarak onerdigimiz mimari |
| Arka plan muzigi/beat konusu | **ATLANMIS** | Gemini bu konuya hic deginmemis, en kritik teknik zorluklardan biri |

---

## 9. Proje Plani ve Yol Haritasi

### Faz 1 — Cekirdek Motor (MVP)

**Hedef:** Komut satirindan calisan, tek dosyalik, temiz ses icin .srt ureten sistem.

| Adim | Gorev | Arac |
|---|---|---|
| 1.1 | Video'dan ses cikarma (mp4 → wav) | ffmpeg |
| 1.2 | Whisper STT + kelime-seviye timestamp | faster-whisper + stable-ts |
| 1.3 | Script-Whisper metin eslestirme | difflib + rapidfuzz |
| 1.4 | Temel fonetik sozluk (JSON) | Ozel modul |
| 1.5 | SRT dosyasi uretimi | pysrt |

**Girdi:** Video dosyasi + script metni + (opsiyonel) fonetik sozluk  
**Cikti:** .srt dosyasi  
**Calisma Modu:** CLI (komut satiri)

### Faz 2 — Akilli Katman

**Hedef:** TDK uyumu, baglam duyarliligi, arka plan muzigi destegi.

| Adim | Gorev | Arac |
|---|---|---|
| 2.1 | Demucs entegrasyonu (vokal izolasyonu) | demucs |
| 2.2 | Turkce stemming / morfolojik analiz | zeyrek |
| 2.3 | Gemini API entegrasyonu (baglam duzeltme) | google-genai |
| 2.4 | Sayi/tarih normalizasyonu | Ozel modul |
| 2.5 | Gelismis segment optimizasyonu | Ozel modul |
| 2.6 | 3 mod destegi (Temiz / Beat Ayirma / Cift Kanal) | Pipeline yonetimi |

### Faz 3 — Arayuz ve Kullanilabilirlik

**Hedef:** Kullanici dostu web arayuzu.

| Adim | Gorev | Arac |
|---|---|---|
| 3.1 | Streamlit arayuzu (video/ses yukleme, script girisi) | Streamlit |
| 3.2 | Fonetik sozluk yonetim paneli | Streamlit |
| 3.3 | Altyazi onizleme (video uzerinde) | ffmpeg + Streamlit |
| 3.4 | Manuel duzeltme arayuzu (segment editor) | Streamlit |
| 3.5 | Toplu islem (batch processing) | Pipeline |

### Faz 4 — Iyilestirme ve Ogrenme

**Hedef:** Sistemin zamanla kendini gelistirmesi.

| Adim | Gorev |
|---|---|
| 4.1 | Kullanici duzeltmelerinden ogrenme (sozluk otomatik guncelleme) |
| 4.2 | Dogaclama tespiti ve hibrit mod (script disi konusma) |
| 4.3 | Performans optimizasyonu (onbellekleme, paralel isleme) |
| 4.4 | Farkli icerik turleri icin profiller (futbol, teknoloji, vlog vb.) |

---

## Sonuc

Bu proje, dogru mimariye oturtuldugunda haftada saatlerce suren manuel altyazi isini **dakikalara** indirebilir. Kritik basari faktorleri:

1. **Hibrit yaklasim:** Saf STT veya saf forced alignment degil, ikisinin guclU yanlarini birlestiren pipeline.
2. **Vokal izolasyonu:** Arka plan muzigi/beat varken Demucs ile temiz ses elde etmek.
3. **Baglam duyarliligi:** Fonetik sozluk + fuzzy matching + LLM dogrulama ile ozel isimleri dogru yazmak.
4. **Turkce'ye ozel cozumler:** Eklemeli yapi, kok cikarma ve dogal segment bolunme noktalari.

**Bir sonraki adim:** Onay verildiginde Faz 1 (MVP) kodlamasina baslanacak — tek Python dosyasinda calisan, script + ses alip .srt ureten en basit versiyon.
