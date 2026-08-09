import math

import streamlit as st

from data_loader import load_team_matches, render_footer
from stats import league_table, list_seasons

st.set_page_config(page_title="Tabelas | Futebol BI", page_icon="🏆", layout="wide")
st.title("🏆 Tabelas dos Campeonatos")

team_matches = load_team_matches()

if team_matches.empty:
    st.warning(
        "Nenhum dado carregado ainda. Volte à página inicial e clique em "
        "**Atualizar dados agora**."
    )
    render_footer()
    st.stop()

leagues_df = (
    team_matches[["country", "league_code", "league_name", "tier"]]
    .drop_duplicates()
    .sort_values(["country", "league_name"])
)

col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    countries = sorted(leagues_df["country"].unique().tolist())
    sel_country = st.selectbox("País", countries)
with col2:
    league_options = leagues_df[leagues_df["country"] == sel_country]
    league_labels = {row.league_name: row.league_code for row in league_options.itertuples()}
    sel_league_label = st.selectbox("Liga", list(league_labels.keys()))
    sel_league_code = league_labels[sel_league_label]
with col3:
    seasons = list_seasons(team_matches, sel_country, sel_league_code)
    sel_season = st.selectbox("Temporada", seasons)
with col4:
    venue = st.radio("Mandante/Visitante", ["todos", "casa", "fora"], horizontal=True)

table = league_table(team_matches, sel_country, sel_league_code, sel_season, venue=venue)

if table.empty:
    st.info("Sem jogos suficientes para montar a tabela com esses filtros.")
else:
    n = len(table)
    zone_size = max(1, math.ceil(n * 0.15))

    def highlight_zone(row):
        if row["posicao"] <= zone_size:
            return ["background-color: rgba(46, 160, 67, 0.25)"] * len(row)
        if row["posicao"] > n - zone_size:
            return ["background-color: rgba(219, 68, 55, 0.25)"] * len(row)
        return [""] * len(row)

    st.caption(
        f"🟩 Top {zone_size} = zona de acesso/classificação (aproximado) · "
        f"🟥 Últimos {zone_size} = zona de rebaixamento (aproximado). "
        "Os cortes reais variam por competição."
    )
    styled = table.style.apply(highlight_zone, axis=1).format({"aproveitamento_pct": "{:.1f}%"})
    st.dataframe(styled, width="stretch", hide_index=True, height=min(38 * (n + 1) + 10, 900))

render_footer()
