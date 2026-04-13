"""Sonuc paneli: metrikler, indirme butonlari, altyazili video onizleme, segment listesi."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from ..rendering import burn_subtitles


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_results(
    mode: str,
    segments: list[dict],
    srt_content: str,
    aligned: list[dict] | None,
    video_file,
    work_dir: str,
) -> None:
    """Tamamlanmis pipeline sonrasi sonuclar panelini cizer."""
    if not segments or not srt_content:
        return

    st.markdown("<hr/>", unsafe_allow_html=True)

    # ---------- Ozet serit ----------
    if mode == "A" and aligned:
        match_types: dict[str, int] = {}
        for a in aligned:
            mt = a["match_type"]
            match_types[mt] = match_types.get(mt, 0) + 1
        exact = match_types.get("exact", 0) + match_types.get("stem", 0)
        total = len(aligned)
        pct = 100 * exact // max(total, 1)
        summary_html = (
            f"<span style='color:#2DD4BF;font-weight:700;'>{len(segments)}</span> segment, "
            f"<span style='color:#2DD4BF;font-weight:700;'>{total}</span> kelime eslesti "
            f"(<span style='color:#2DD4BF;font-weight:700;'>{pct}%</span> dogrudan)."
        )
    else:
        summary_html = (
            f"<span style='color:#2DD4BF;font-weight:700;'>{len(segments)}</span> segment — "
            "Whisper + Gemini 3 Flash ile uretildi."
        )

    st.markdown(
        f"""
<div style='background:linear-gradient(135deg,rgba(45,212,191,0.12),rgba(45,212,191,0.04));
border:1px solid rgba(45,212,191,0.35);border-radius:14px;padding:1.1rem 1.35rem;
margin-bottom:1.5rem;display:flex;align-items:center;gap:0.75rem;'>
<span style='font-size:1.25rem;'>\u2705</span>
<span style='color:#F1F5F9;font-weight:500;'>Altyazi hazir — {summary_html}</span>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---------- Metrikler ----------
    if mode == "A" and aligned:
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Kelime", f"{len(aligned)}")
        exact = sum(1 for a in aligned if a["match_type"] in ("exact", "stem"))
        pct = 100 * exact // max(len(aligned), 1)
        m2.metric("Dogrudan Eslesme", f"{pct}%",
                  delta=f"{exact}/{len(aligned)}", delta_color="off")
        m3.metric("Segment Sayisi", f"{len(segments)}")
    else:
        total_words = sum(len(s["text"].split()) for s in segments)
        avg_dur = sum(s["end"] - s["start"] for s in segments) / max(len(segments), 1)
        m1, m2, m3 = st.columns(3)
        m1.metric("Segment", f"{len(segments)}")
        m2.metric("Kelime", f"{total_words}")
        m3.metric("Ort. Sure", f"{avg_dur:.1f}s")

    # ---------- Indirme ----------
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title"><span class="icon">\u2B07\uFE0F</span>Indirme</div>',
        unsafe_allow_html=True,
    )

    if video_file and not st.session_state.get("sub_video_filename"):
        st.session_state.sub_video_filename = Path(video_file.name).stem
    display_stem = st.session_state.get("sub_video_filename") or (
        Path(video_file.name).stem if video_file else "output"
    )

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="\U0001F4C4  SRT Dosyasini Indir",
            data=srt_content,
            file_name=f"{display_stem}.srt",
            mime="text/plain",
            use_container_width=True,
            key="dl_srt",
        )

    with dl2:
        sub_path = st.session_state.get("sub_video_path")
        if sub_path and os.path.exists(sub_path):
            with open(sub_path, "rb") as f:
                video_data = f.read()
            st.download_button(
                label="\U0001F3A5  Altyazili Videoyu Indir",
                data=video_data,
                file_name=f"{display_stem}_altyazili.mp4",
                mime="video/mp4",
                use_container_width=True,
                key="dl_burned_video",
            )
        elif video_file:
            if st.button("\U0001F525  Altyaziyi Videoya Gom",
                         use_container_width=True, key="btn_burn"):
                with st.spinner("Video olusturuluyor... (FFmpeg calisiyor)"):
                    try:
                        video_bytes = video_file.getbuffer().tobytes()
                        output_path = os.path.join(
                            work_dir, f"{display_stem}_altyazili.mp4"
                        )
                        burn_subtitles(video_bytes, srt_content, output_path)
                        st.session_state.sub_video_path = output_path
                        st.rerun()
                    except Exception as e:
                        st.error(f"Video olusturma hatasi: {e}")

    # ---------- Altyazili video onizleme ----------
    sub_path = st.session_state.get("sub_video_path")
    if sub_path and os.path.exists(sub_path):
        st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title"><span class="icon">\u25B6\uFE0F</span>Altyazili Video Onizleme</div>',
            unsafe_allow_html=True,
        )
        _, pv_mid, _ = st.columns([1, 2, 1])
        with pv_mid:
            st.video(sub_path)

    # ---------- Segment onizleme ----------
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title"><span class="icon">\U0001F4CB</span>Segment Onizleme</div>',
        unsafe_allow_html=True,
    )
    segments_html: list[str] = []
    for i, seg in enumerate(segments, 1):
        dur = seg["end"] - seg["start"]
        cps = seg.get("chars_per_sec", len(seg["text"]) / max(dur, 0.1))
        safe_text = _escape_html(seg["text"])
        segments_html.append(
            f"""<div class="segment-row">
    <div class="segment-meta">
        <span class="seg-num">#{i:02d}</span>
        <span class="seg-time">{seg['start']:.1f}s \u2192 {seg['end']:.1f}s \u00B7 {dur:.1f}s</span>
        <span class="seg-cps">{cps:.0f} chr/s</span>
    </div>
    <div class="segment-text">{safe_text}</div>
</div>"""
        )
    st.markdown("".join(segments_html), unsafe_allow_html=True)

    with st.expander("\U0001F4DC  Ham SRT Dosyasi"):
        st.code(srt_content, language=None)
