"""Sidebar ayarlar paneli: mod secimi, whisper, demucs, gemini, fonetik sozluk."""
from __future__ import annotations

import json
from dataclasses import dataclass

import streamlit as st

from ..core.phonetic import DEFAULT_PHONETIC_DICT


@dataclass
class SidebarState:
    mode: str  # "A" veya "B"
    model_size: str
    vocal_isolation: bool
    use_gemini: bool
    custom_dict: dict | None


def render_sidebar() -> SidebarState:
    """Sidebar'i cizer ve kullanici secimlerini dondurur."""
    with st.sidebar:
        hdr_l, hdr_r = st.columns([4, 1])
        with hdr_l:
            st.markdown(
                "<h2 style='margin:0;padding:0;font-size:1rem;'>"
                "\u2699\ufe0f Ayarlar</h2>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            if st.button("\u2715", key="close_sidebar_btn", help="Ayarlari gizle"):
                st.session_state.sidebar_open = False
                st.query_params["sb"] = "closed"
                st.rerun()

        st.markdown("### Mod Secimi")
        mode_label = st.radio(
            "Calisma modu",
            options=[
                "A — Script-Aware (Referansli)",
                "B — Autonomous AI (Metinsiz)",
            ],
            index=0,
            label_visibility="collapsed",
            help=(
                "A: Elindeki metni sese gore hizalar (en dogru).\n"
                "B: Metin olmadan, Whisper + Gemini ile sifirdan uretir."
            ),
        )
        mode = "A" if mode_label.startswith("A") else "B"

        st.markdown("### Transkripsiyon")
        model_size = st.selectbox(
            "Whisper Modeli",
            ["large-v3-turbo", "large-v3", "medium", "small", "base"],
            index=0,
            help="large-v3-turbo: en hizli ve isabetli secenek.",
        )

        vocal_isolation = st.checkbox(
            "Beat Separation (Demucs)",
            value=True,
            help="Arka planda muzik/beat varken etkinlestirin. GPU varsa CUDA kullanir.",
        )

        use_gemini = False
        if mode == "B":
            st.markdown("### AI Refinement")
            use_gemini = st.checkbox(
                "Gemini 3 Flash ile duzelt",
                value=True,
                help=(
                    "Ozel isim / TDK / sayi duzeltmesi icin Gemini 3 Flash kullanir. "
                    "API key .streamlit/secrets.toml'dan okunur."
                ),
            )

        custom_dict: dict | None = None
        if mode == "A":
            st.markdown("### Fonetik Sozluk")
            use_custom_dict = st.checkbox("Ozel sozluk kullan", value=False)
            if use_custom_dict:
                dict_file = st.file_uploader(
                    "Sozluk JSON dosyasi",
                    type=["json"],
                    label_visibility="collapsed",
                )
                if dict_file:
                    custom_dict = json.loads(dict_file.read().decode("utf-8"))
                    st.success(f"Sozluk yuklendi — {len(custom_dict)} girdi")

            with st.expander("Varsayilan fonetik eslestirmeler"):
                for name, variants in DEFAULT_PHONETIC_DICT.items():
                    st.markdown(
                        f"<div style='font-size:0.82rem;padding:0.25rem 0;"
                        f"border-bottom:1px solid rgba(148,163,184,0.08);'>"
                        f"<span style='color:#2DD4BF;font-weight:600;'>{name}</span> "
                        f"<span style='color:#64748B;'>\u2192 {', '.join(variants)}</span></div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("---")
        st.markdown(
            "<div style='font-size:0.72rem;color:#64748B;text-align:center;"
            "line-height:1.5;'>Script-to-Sub v2<br/>Hibrit STT + AI Refinement</div>",
            unsafe_allow_html=True,
        )

    return SidebarState(
        mode=mode,
        model_size=model_size,
        vocal_isolation=vocal_isolation,
        use_gemini=use_gemini,
        custom_dict=custom_dict,
    )
