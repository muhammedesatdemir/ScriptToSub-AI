"""
Script-to-Sub: Streamlit Arayuzu
=================================
Video + Script yukleyerek otomatik altyazi olusturma.
Altyaziyi videoya gomme ve indirme destegi.
"""

import streamlit as st
import tempfile
import subprocess
import os
import json
from pathlib import Path

from script_to_sub import (
    extract_audio,
    isolate_vocals,
    transcribe_with_timestamps,
    tokenize_script,
    enhanced_align_words,
    create_segments,
    optimize_segments,
    generate_srt,
    DEFAULT_PHONETIC_DICT,
)

# --- Sayfa Ayarlari ---
st.set_page_config(page_title="Script-to-Sub", page_icon="CC", layout="wide")
st.title("Script-to-Sub")
st.markdown("Video metninden otomatik altyazi olusturma sistemi")

# --- Session State Baslangic ---
if "srt_content" not in st.session_state:
    st.session_state.srt_content = None
if "segments" not in st.session_state:
    st.session_state.segments = None
if "aligned" not in st.session_state:
    st.session_state.aligned = None
if "sub_video_bytes" not in st.session_state:
    st.session_state.sub_video_bytes = None


def burn_subtitles(video_bytes: bytes, srt_content: str, video_name: str) -> bytes:
    """FFmpeg ile altyaziyi videoya gomup bytes olarak dondurur."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")
        srt_path = os.path.join(tmpdir, "subs.srt")
        output_path = os.path.join(tmpdir, "output.mp4")

        with open(video_path, "wb") as f:
            f.write(video_bytes)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # FFmpeg: altyaziyi videoya gom (hardcoded subtitles)
        # Windows'ta yol icindeki \ ve : icin escape gerekiyor (libass formati)
        srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_escaped}':force_style='Fontname=Arial,FontSize=8,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BackColour=&H80000000,Bold=1,Outline=0,Shadow=0,MarginV=60,Alignment=2,MarginL=20,MarginR=20,BorderStyle=4'",
            "-c:a", "copy",
            "-preset", "fast",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg hatasi: {result.stderr[-500:]}")

        with open(output_path, "rb") as f:
            return f.read()


# --- Sidebar: Ayarlar ---
with st.sidebar:
    st.header("Ayarlar")

    model_size = st.selectbox(
        "Whisper Modeli",
        ["large-v3-turbo", "large-v3", "medium", "small", "base"],
        index=0,
        help="large-v3-turbo: En hizli ve isabetli."
    )

    vocal_isolation = st.checkbox(
        "Vokal Izolasyonu (Demucs)",
        value=True,
        help="Arka plan muzigi/beat varken aktif edin."
    )

    st.divider()
    st.subheader("Fonetik Sozluk")

    use_custom_dict = st.checkbox("Ozel sozluk kullan", value=False)
    custom_dict = None
    if use_custom_dict:
        dict_file = st.file_uploader("Sozluk JSON dosyasi", type=["json"])
        if dict_file:
            custom_dict = json.loads(dict_file.read().decode("utf-8"))
            st.success(f"Sozluk yuklendi: {len(custom_dict)} girdi")

    st.divider()
    with st.expander("Varsayilan fonetik eslestirmeler"):
        for name, variants in DEFAULT_PHONETIC_DICT.items():
            st.text(f"{name}: {', '.join(variants)}")

# --- Ana Panel: Girdi ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Video Dosyasi")
    video_file = st.file_uploader(
        "Video yukle (MP4, MKV, AVI, MOV)",
        type=["mp4", "mkv", "avi", "mov", "webm"]
    )
    if video_file:
        st.video(video_file)

with col2:
    st.subheader("Script Metni")
    script_input_mode = st.radio("Script girisi", ["Dosya yukle", "Manuel yaz"], horizontal=True)

    script_text = ""
    if script_input_mode == "Dosya yukle":
        script_file = st.file_uploader("Script dosyasi (TXT)", type=["txt"])
        if script_file:
            script_text = script_file.read().decode("utf-8")
            st.text_area("Script onizleme", script_text, height=200, disabled=True)
    else:
        script_text = st.text_area(
            "Script metnini yazin",
            height=200,
            placeholder="Video metnini buraya yapistirin..."
        )

# --- Altyazi Olustur Butonu ---
st.divider()

if st.button("Altyazi Olustur", type="primary", use_container_width=True):
    if not video_file:
        st.error("Lutfen bir video dosyasi yukleyin.")
    elif not script_text.strip():
        st.error("Lutfen script metnini girin.")
    else:
        # Onceki sonuclari temizle
        st.session_state.srt_content = None
        st.session_state.segments = None
        st.session_state.aligned = None
        st.session_state.sub_video_bytes = None

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, video_file.name)
            with open(video_path, "wb") as f:
                f.write(video_file.getbuffer())

            srt_path = os.path.join(tmpdir, "output.srt")
            progress = st.progress(0, text="Baslatiliyor...")

            try:
                # Katman 0: Vokal izolasyonu veya duz ses cikarma
                whisper_input = None
                if vocal_isolation:
                    progress.progress(5, text="Vokal izolasyonu (Demucs)... (1-2 dk surebilir)")
                    vocal_path = isolate_vocals(video_path, tmpdir)
                    if vocal_path:
                        whisper_input = vocal_path

                if whisper_input is None:
                    progress.progress(10, text="Ses cikariliyor...")
                    whisper_input = extract_audio(video_path)

                # Katman 1: Whisper STT
                progress.progress(40, text=f"Whisper ({model_size}) calisiyor...")
                whisper_data = transcribe_with_timestamps(
                    whisper_input, language="tr", model_size=model_size
                )

                # Temizlik
                if os.path.exists(whisper_input):
                    try:
                        os.remove(whisper_input)
                    except OSError:
                        pass

                progress.progress(60, text="Metin eslestirme yapiliyor...")

                # Katman 2-3: Eslestirme
                script_tokens = tokenize_script(script_text)
                phonetic_dict = custom_dict if custom_dict else DEFAULT_PHONETIC_DICT
                aligned = enhanced_align_words(
                    script_tokens, whisper_data["all_words"], phonetic_dict
                )

                progress.progress(80, text="Segmentler olusturuluyor...")

                # Katman 4: Segmentasyon + SRT
                segments = create_segments(aligned)
                segments = optimize_segments(segments)
                generate_srt(segments, srt_path)

                progress.progress(100, text="Tamamlandi!")

                # Sonuclari session_state'e kaydet
                with open(srt_path, "r", encoding="utf-8") as f:
                    st.session_state.srt_content = f.read()
                st.session_state.segments = segments
                st.session_state.aligned = aligned

                st.rerun()

            except Exception as e:
                progress.progress(0, text="Hata olustu!")
                st.error(f"Hata: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# --- Sonuclar ---
if st.session_state.srt_content and st.session_state.segments:
    segments = st.session_state.segments
    aligned = st.session_state.aligned
    srt_content = st.session_state.srt_content

    st.success(f"Altyazi hazir! {len(segments)} segment, {len(aligned)} kelime eslesti.")

    # Istatistikler
    col_s1, col_s2, col_s3 = st.columns(3)
    match_types = {}
    for a in aligned:
        mt = a["match_type"]
        match_types[mt] = match_types.get(mt, 0) + 1

    exact = match_types.get("exact", 0) + match_types.get("stem", 0)
    total = len(aligned)

    col_s1.metric("Toplam Kelime", f"{total}")
    col_s2.metric("Dogrudan Eslestirme", f"{exact}/{total} ({100*exact//max(total,1)}%)")
    col_s3.metric("Segment Sayisi", f"{len(segments)}")

    # --- Indirme Butonlari ---
    st.divider()
    st.subheader("Indirme")

    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        st.download_button(
            label="SRT Dosyasini Indir",
            data=srt_content,
            file_name=f"{Path(video_file.name).stem}.srt" if video_file else "output.srt",
            mime="text/plain",
            use_container_width=True
        )

    with dl_col2:
        if video_file:
            # Altyazili video olustur butonu
            if st.session_state.sub_video_bytes:
                st.download_button(
                    label="Altyazili Videoyu Indir",
                    data=st.session_state.sub_video_bytes,
                    file_name=f"{Path(video_file.name).stem}_altyazili.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )
            else:
                if st.button("Altyaziyi Videoya Gom", use_container_width=True):
                    with st.spinner("Video olusturuluyor... (FFmpeg calisiyor)"):
                        try:
                            video_bytes = video_file.getbuffer().tobytes()
                            result_bytes = burn_subtitles(
                                video_bytes, srt_content,
                                video_file.name
                            )
                            st.session_state.sub_video_bytes = result_bytes
                            st.rerun()
                        except Exception as e:
                            st.error(f"Video olusturma hatasi: {str(e)}")

    # Altyazili video onizleme
    if st.session_state.sub_video_bytes:
        st.divider()
        st.subheader("Altyazili Video Onizleme")
        st.video(st.session_state.sub_video_bytes)

    # --- Altyazi Onizleme ---
    st.divider()
    st.subheader("Altyazi Onizleme")

    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        cps = seg.get("chars_per_sec", len(seg["text"]) / max(dur, 0.1))
        time_str = f"{seg['start']:.1f}s - {seg['end']:.1f}s ({dur:.1f}s)"
        st.markdown(f"**#{i}** `{time_str}` | {cps:.0f} chr/s")
        st.text(seg["text"])

    # Ham SRT
    with st.expander("Ham SRT Dosyasi"):
        st.code(srt_content, language=None)
