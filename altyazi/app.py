"""Script-to-Sub v2: Streamlit arayuz giris noktasi.

Tum agir is mantigi alt modullerde (audio, transcription, alignment, refinement,
segmentation, rendering, pipeline). Bu dosya sadece UI orkestrasyonu yapar:

  1. Tema + sidebar toggle enjeksiyonu
  2. Sidebar (mod secimi, whisper, demucs, gemini, fonetik)
  3. Girdi paneli (video + script veya video baglami)
  4. Altyazi Olustur butonu -> ilgili pipeline (mod_a veya mod_b)
  5. Sonuclar paneli (metrikler, indirme, onizleme)

Calistirma:  streamlit run altyazi/app.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Streamlit bu dosyayi dogrudan calistirir — paketin parent dizinini path'e ekle
_PARENT = str(Path(__file__).resolve().parent.parent)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

import streamlit as st

from altyazi.pipeline import run_autonomous_transcription, run_script_aware_alignment
from altyazi.rendering import generate_srt
from altyazi.ui import (
    InputState,
    SidebarState,
    inject_sidebar_toggle,
    inject_theme,
    render_hero,
    render_inputs,
    render_results,
    render_sidebar,
)


# ============================================================
# Sayfa konfigu (query param ile sidebar durumu)
# ============================================================
_qp = st.query_params
_sidebar_qp = _qp.get("sb", "open")
_sidebar_default = "collapsed" if _sidebar_qp == "closed" else "expanded"

st.set_page_config(
    page_title="Script-to-Sub",
    page_icon="\U0001F3AC",
    layout="wide",
    initial_sidebar_state=_sidebar_default,
)

if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = (_sidebar_default == "expanded")

# ============================================================
# Session state
# ============================================================
for key in ("srt_content", "segments", "aligned",
            "sub_video_path", "sub_video_filename"):
    st.session_state.setdefault(key, None)

if "work_dir" not in st.session_state:
    st.session_state.work_dir = tempfile.mkdtemp(prefix="script2sub_")

# ============================================================
# UI: Tema + Hero + Sidebar + Girdiler
# ============================================================
inject_theme()
inject_sidebar_toggle()
render_hero()

sidebar: SidebarState = render_sidebar()
inputs: InputState = render_inputs(sidebar.mode)


# ============================================================
# Altyazi Olustur
# ============================================================
st.markdown("<div style='margin: 2rem 0 1rem 0;'></div>", unsafe_allow_html=True)

if st.button("\u2728  Altyazi Olustur", type="primary", use_container_width=True):
    if not inputs.video_file:
        st.error("Lutfen bir video dosyasi yukleyin.")
    elif sidebar.mode == "A" and not inputs.script_text.strip():
        st.error("Mod A icin script metni zorunludur.")
    else:
        # Onceki sonuclari temizle
        st.session_state.srt_content = None
        st.session_state.segments = None
        st.session_state.aligned = None
        old_path = st.session_state.get("sub_video_path")
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
        st.session_state.sub_video_path = None
        st.session_state.sub_video_filename = None

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, inputs.video_file.name)
            with open(video_path, "wb") as f:
                f.write(inputs.video_file.getbuffer())

            srt_path = os.path.join(tmpdir, "output.srt")
            progress = st.progress(0, text="Baslatiliyor...")

            def tick(p: int, msg: str) -> None:
                progress.progress(p, text=msg)

            try:
                if sidebar.mode == "A":
                    result = run_script_aware_alignment(
                        video_path=video_path,
                        script_text=inputs.script_text,
                        work_dir=tmpdir,
                        model_size=sidebar.model_size,
                        vocal_isolation=sidebar.vocal_isolation,
                        phonetic_dict=sidebar.custom_dict,
                        progress=tick,
                    )
                    segments = result.segments
                    aligned = result.aligned
                else:
                    result = run_autonomous_transcription(
                        video_path=video_path,
                        work_dir=tmpdir,
                        video_context=inputs.video_context,
                        model_size=sidebar.model_size,
                        vocal_isolation=sidebar.vocal_isolation,
                        use_gemini=sidebar.use_gemini,
                        progress=tick,
                    )
                    segments = result.segments
                    aligned = None

                generate_srt(segments, srt_path)
                with open(srt_path, "r", encoding="utf-8") as f:
                    st.session_state.srt_content = f.read()
                st.session_state.segments = segments
                st.session_state.aligned = aligned
                st.rerun()

            except Exception as e:
                progress.progress(0, text="Hata olustu!")
                st.error(f"Hata: {e}")
                import traceback
                st.code(traceback.format_exc())


# ============================================================
# Sonuclar
# ============================================================
if st.session_state.srt_content and st.session_state.segments:
    render_results(
        mode=sidebar.mode,
        segments=st.session_state.segments,
        srt_content=st.session_state.srt_content,
        aligned=st.session_state.aligned,
        video_file=inputs.video_file,
        work_dir=st.session_state.work_dir,
    )
