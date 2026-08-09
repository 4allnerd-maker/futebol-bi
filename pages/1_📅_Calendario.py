from datetime import timedelta

import streamlit as st

from data_loader import load_fixtures, render_footer

st.set_page_config(page_title="Calendário | Futebol BI", page_icon="📅", layout="wide")
st.title("📅 Calendário — próximos jogos")

fixtures = load_fixtures()

if fixtures.empty:
    st.warning(
        "Nenhum jogo futuro carregado ainda. Volte à página inicial e clique em "
        "**Atualizar dados agora**."
    )
    render_footer()
    st.stop()

st.caption(
    "Fonte: fixtures.csv (football-data.co.uk), atualizado pelo site às sextas e terças. "
    "Cobre apenas as ligas europeias principais."
)

leagues = sorted(fixtures["league_name"].dropna().unique().tolist())
teams = sorted(set(fixtures["home_team"]).union(fixtures["away_team"]))

col_a, col_b, col_c = st.columns([2, 2, 2])
with col_a:
    sel_leagues = st.multiselect("Liga", leagues, default=[])
with col_b:
    date_min, date_max = fixtures["date"].min().date(), fixtures["date"].max().date()
    date_range = st.date_input(
        "Intervalo de datas", value=(date_min, date_max), min_value=date_min, max_value=date_max
    )
with col_c:
    sel_team = st.selectbox("Time", ["Todos"] + teams)

df = fixtures.copy()
if sel_leagues:
    df = df[df["league_name"].isin(sel_leagues)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end + timedelta(days=0))]
if sel_team != "Todos":
    df = df[(df["home_team"] == sel_team) | (df["away_team"] == sel_team)]

df = df.sort_values(["date", "time"])

st.subheader(f"{len(df)} jogo(s) encontrado(s)")

display = df.rename(columns={
    "date": "data", "time": "hora", "country": "país", "league_name": "liga",
    "home_team": "mandante", "away_team": "visitante", "referee": "árbitro",
    "odds_home": "odd casa", "odds_draw": "odd empate", "odds_away": "odd fora",
    "odds_over25": "odd +2.5 gols", "odds_under25": "odd -2.5 gols",
})
display["data"] = display["data"].dt.strftime("%d/%m/%Y")

st.dataframe(
    display[["data", "hora", "país", "liga", "mandante", "visitante",
              "odd casa", "odd empate", "odd fora", "odd +2.5 gols", "odd -2.5 gols", "árbitro"]],
    width="stretch",
    hide_index=True,
)

render_footer()
