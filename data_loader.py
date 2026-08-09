"""Camada de cache/carregamento de dados compartilhada entre as paginas do app."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from data_pipeline import FIXTURES_PATH, MATCHES_PATH, META_PATH, run_pipeline
from stats import build_team_matches

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 horas


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_matches() -> pd.DataFrame:
    if not MATCHES_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(MATCHES_PATH)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_fixtures() -> pd.DataFrame:
    if not FIXTURES_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(FIXTURES_PATH)


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_team_matches() -> pd.DataFrame:
    matches = load_matches()
    if matches.empty:
        return pd.DataFrame()
    return build_team_matches(matches)


def load_meta() -> dict:
    if not META_PATH.exists():
        return {}
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def refresh_now() -> dict:
    """Roda o pipeline de novo e limpa o cache do Streamlit."""
    meta = run_pipeline()
    st.cache_data.clear()
    return meta


def render_footer() -> None:
    st.markdown("---")
    st.caption(
        "⚠️ Esta ferramenta serve apenas para análise estatística de dados históricos. "
        "Não é garantia de resultado nem recomendação de aposta. Jogue com responsabilidade."
    )
