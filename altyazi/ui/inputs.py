"""Giris paneli: video + (moda gore) script veya video baglami."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass
class InputState:
    video_file: Any | None
    script_text: str
    video_context: str


def render_inputs(mode: str) -> InputState:
    """Mod A: video + script. Mod B: video + (opsiyonel) baglam."""
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.markdown(
                '<div class="section-title"><span class="icon">\U0001F3AC</span>Video Dosyasi</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="sub-label">Desteklenen formatlar: MP4, MKV, AVI, MOV, WEBM</div>',
                unsafe_allow_html=True,
            )
            video_file = st.file_uploader(
                "Video yukle",
                type=["mp4", "mkv", "avi", "mov", "webm"],
                label_visibility="collapsed",
            )
            if video_file:
                st.video(video_file)

    script_text = ""
    video_context = ""

    with col2:
        with st.container(border=True):
            if mode == "A":
                st.markdown(
                    '<div class="section-title"><span class="icon">\U0001F4DD</span>Script Metni</div>',
                    unsafe_allow_html=True,
                )
                script_input_mode = st.radio(
                    "Script girisi",
                    ["Dosya yukle", "Manuel yaz"],
                    horizontal=True,
                    label_visibility="collapsed",
                )
                if script_input_mode == "Dosya yukle":
                    st.markdown('<div class="sub-label">TXT dosyasi yukleyin</div>',
                                unsafe_allow_html=True)
                    script_file = st.file_uploader(
                        "Script dosyasi",
                        type=["txt"],
                        label_visibility="collapsed",
                    )
                    if script_file:
                        script_text = script_file.read().decode("utf-8")
                        st.text_area(
                            "Onizleme", script_text, height=180,
                            disabled=True, label_visibility="collapsed",
                        )
                else:
                    st.markdown('<div class="sub-label">Metni asagiya yazin veya yapistirin</div>',
                                unsafe_allow_html=True)
                    script_text = st.text_area(
                        "Script metni",
                        height=200,
                        placeholder="Video metnini buraya yapistirin...",
                        label_visibility="collapsed",
                    )
            else:
                st.markdown(
                    '<div class="section-title"><span class="icon">\U0001F9E0</span>Video Baglami</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="sub-label">Opsiyonel — Gemini refinement kalitesini artirir</div>',
                    unsafe_allow_html=True,
                )
                video_context = st.text_input(
                    "Baglam",
                    placeholder="Orn: Futbol analizi, Teknoloji incelemesi, Tarih belgeseli",
                    label_visibility="collapsed",
                    help=(
                        "Gemini'ye video turu hakkinda ipucu verir. "
                        "Ozel terim/isim dogrulugunu artirir."
                    ),
                )
                st.info(
                    "Mod B'de referans metne ihtiyac yok — Whisper sesi tanir, "
                    "Gemini ozel isim ve noktalamayi duzeltir.",
                    icon="\u2139\ufe0f",
                )

    return InputState(
        video_file=video_file,
        script_text=script_text,
        video_context=video_context,
    )
