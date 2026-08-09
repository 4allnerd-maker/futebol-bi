import plotly.graph_objects as go
import streamlit as st

from data_loader import load_team_matches, render_footer
from stats import (
    current_streaks,
    filter_team_matches,
    goals_trend,
    league_table,
    list_seasons,
    list_teams,
    recent_form_summary,
)

st.set_page_config(page_title="Desempenho de Times | Futebol BI", page_icon="📊", layout="wide")
st.title("📊 Desempenho de Times")

team_matches = load_team_matches()

if team_matches.empty:
    st.warning(
        "Nenhum dado carregado ainda. Volte à página inicial e clique em "
        "**Atualizar dados agora**."
    )
    render_footer()
    st.stop()

leagues_df = (
    team_matches[["country", "league_code", "league_name"]]
    .drop_duplicates()
    .sort_values(["country", "league_name"])
)

# --- Filtros: liga / temporada / time(s) ---------------------------------
c1, c2, c3 = st.columns(3)
with c1:
    countries = sorted(leagues_df["country"].unique().tolist())
    sel_country = st.selectbox("País", countries, key="country")
with c2:
    league_options = leagues_df[leagues_df["country"] == sel_country]
    league_labels = {row.league_name: row.league_code for row in league_options.itertuples()}
    sel_league_label = st.selectbox("Liga", list(league_labels.keys()), key="league")
    sel_league_code = league_labels[sel_league_label]
with c3:
    seasons = list_seasons(team_matches, sel_country, sel_league_code)
    sel_season = st.selectbox("Temporada", ["Todas"] + seasons, key="season")
season_filter = None if sel_season == "Todas" else sel_season

teams = list_teams(team_matches, sel_country, sel_league_code, season_filter)
if not teams:
    st.info("Sem times disponíveis para esses filtros.")
    render_footer()
    st.stop()

t1, t2, t3 = st.columns([2, 1, 2])
with t1:
    team1 = st.selectbox("Time", teams, key="team1")
with t2:
    comparar = st.checkbox("Comparar com outro time", key="comparar")
team2 = None
with t3:
    if comparar:
        outros = [t for t in teams if t != team1]
        team2 = st.selectbox("Comparar com", outros, key="team2") if outros else None

st.markdown("---")

# --- Filtros de segmentação -------------------------------------------
f1, f2, f3, f4 = st.columns(4)
with f1:
    venue = st.radio("Mandante/Visitante/Todos", ["todos", "casa", "fora"], horizontal=True, key="venue")
with f2:
    n_label = st.selectbox("Últimos N jogos", ["5", "10", "15", "Temporada toda"], index=1, key="last_n")
    last_n = None if n_label == "Temporada toda" else int(n_label)
with f3:
    tier_filter = st.selectbox(
        "Contra adversários",
        ["Todos", "Metade de cima da tabela", "Metade de baixo da tabela"],
        key="tier_filter",
    )
with f4:
    date_range = st.date_input("Intervalo de datas (opcional)", value=(), key="date_range")

date_from = date_to = None
if isinstance(date_range, tuple) and len(date_range) == 2:
    date_from, date_to = date_range

opponent_in = None
if tier_filter != "Todos":
    table_season = sel_season if sel_season != "Todas" else (seasons[0] if seasons else None)
    if table_season:
        table = league_table(team_matches, sel_country, sel_league_code, table_season, venue="todos")
        half = max(1, len(table) // 2)
        if tier_filter == "Metade de cima da tabela":
            opponent_in = table.head(half)["time"].tolist()
        else:
            opponent_in = table.tail(len(table) - half)["time"].tolist()


def get_subset(team: str):
    return filter_team_matches(
        team_matches, team,
        venue=venue, league_code=sel_league_code, season=season_filter,
        last_n=last_n, date_from=date_from, date_to=date_to, opponent_in=opponent_in,
    )


def render_panel(col, team: str):
    subset = get_subset(team)
    summary = recent_form_summary(subset)
    streaks = current_streaks(team_matches, team, venue=venue)

    with col:
        st.subheader(team)
        if summary["jogos"] == 0:
            st.info("Sem jogos para esses filtros.")
            return subset
        st.caption(f"Sequência (mais recente à direita): `{summary['sequencia']}`")

        m1, m2, m3 = st.columns(3)
        m1.metric("Jogos", summary["jogos"])
        m2.metric("Pontos/jogo", summary["pontos_por_jogo"])
        m3.metric("Invicto há", streaks["invicto"])

        m4, m5, m6 = st.columns(3)
        m4.metric("Gols marcados/jogo", summary["media_gols_marcados"])
        m5.metric("Gols sofridos/jogo", summary["media_gols_sofridos"])
        m6.metric("Sem sofrer gol há", streaks["sem_sofrer_gol"])

        m7, m8, m9 = st.columns(3)
        m7.metric("Taxa +2.5 gols", f"{summary['taxa_over25_pct']}%")
        m8.metric("Taxa ambas marcam", f"{summary['taxa_btts_pct']}%")
        m9.metric("Taxa clean sheet", f"{summary['taxa_clean_sheet_pct']}%")

        st.markdown("**Splits casa vs. fora** _(demais filtros aplicados, exceto mandante/visitante)_")
        casa = filter_team_matches(
            team_matches, team, venue="casa", league_code=sel_league_code, season=season_filter,
            last_n=last_n, date_from=date_from, date_to=date_to, opponent_in=opponent_in,
        )
        fora = filter_team_matches(
            team_matches, team, venue="fora", league_code=sel_league_code, season=season_filter,
            last_n=last_n, date_from=date_from, date_to=date_to, opponent_in=opponent_in,
        )
        casa_s, fora_s = recent_form_summary(casa), recent_form_summary(fora)
        split_df = {
            "": ["jogos", "pontos/jogo", "gols marcados/jogo", "gols sofridos/jogo", "taxa +2.5", "taxa BTTS"],
            "casa": [str(casa_s["jogos"]), str(casa_s["pontos_por_jogo"]), str(casa_s["media_gols_marcados"]),
                     str(casa_s["media_gols_sofridos"]), f"{casa_s['taxa_over25_pct']}%", f"{casa_s['taxa_btts_pct']}%"],
            "fora": [str(fora_s["jogos"]), str(fora_s["pontos_por_jogo"]), str(fora_s["media_gols_marcados"]),
                     str(fora_s["media_gols_sofridos"]), f"{fora_s['taxa_over25_pct']}%", f"{fora_s['taxa_btts_pct']}%"],
        }
        st.dataframe(split_df, hide_index=True, width="stretch")
    return subset


if team2:
    col_a, col_b = st.columns(2)
    subset1 = render_panel(col_a, team1)
    subset2 = render_panel(col_b, team2)
else:
    subset1 = render_panel(st.container(), team1)
    subset2 = None

st.markdown("---")
st.subheader("Tendência de gols ao longo do tempo")

fig = go.Figure()
trend1 = goals_trend(subset1)
if not trend1.empty:
    fig.add_trace(go.Scatter(x=trend1["date"], y=trend1["media_movel_marcados"],
                              mode="lines+markers", name=f"{team1} — marcados (média móvel)"))
    fig.add_trace(go.Scatter(x=trend1["date"], y=trend1["media_movel_sofridos"],
                              mode="lines+markers", name=f"{team1} — sofridos (média móvel)"))
if subset2 is not None:
    trend2 = goals_trend(subset2)
    if not trend2.empty:
        fig.add_trace(go.Scatter(x=trend2["date"], y=trend2["media_movel_marcados"],
                                  mode="lines+markers", name=f"{team2} — marcados (média móvel)"))
        fig.add_trace(go.Scatter(x=trend2["date"], y=trend2["media_movel_sofridos"],
                                  mode="lines+markers", name=f"{team2} — sofridos (média móvel)"))

if fig.data:
    fig.update_layout(xaxis_title="Data", yaxis_title="Gols (média móvel de 5 jogos)", height=450,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, width="stretch")
else:
    st.info("Sem dados suficientes para o gráfico de tendência com esses filtros.")

render_footer()
