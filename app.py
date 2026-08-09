import streamlit as st

from data_loader import load_matches, load_fixtures, load_meta, refresh_now, render_footer

st.set_page_config(page_title="Futebol BI", page_icon="⚽", layout="wide")

st.title("⚽ Futebol BI")
st.markdown(
    "Ferramenta própria de análise de dados de futebol (dados: "
    "[football-data.co.uk](https://www.football-data.co.uk)) — substituto do Power BI "
    "para acompanhar ligas, classificações e desempenho de times."
)

meta = load_meta()

col1, col2 = st.columns([3, 1])
with col1:
    if meta:
        st.info(f"Última atualização dos dados: **{meta.get('last_update', '?')}**")
    else:
        st.warning("Os dados ainda não foram baixados nesta máquina.")
with col2:
    if st.button("🔄 Atualizar dados agora", width="stretch"):
        with st.spinner("Baixando e processando dados (pode levar 1-2 minutos)..."):
            meta = refresh_now()
        st.success("Dados atualizados!")
        st.rerun()

matches = load_matches()
fixtures = load_fixtures()

if matches.empty:
    st.error(
        "Nenhum dado encontrado ainda. Clique em **Atualizar dados agora** acima, "
        "ou rode `python refresh_data.py` no terminal."
    )
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Partidas na base", f"{len(matches):,}".replace(",", "."))
    m2.metric("Ligas/países cobertos", matches["league_code"].nunique())
    m3.metric("Próximos jogos (calendário)", len(fixtures))
    date_min, date_max = matches["date"].min(), matches["date"].max()
    m4.metric("Período coberto", f"{date_min:%m/%Y} – {date_max:%m/%Y}")

    st.subheader("Cobertura por liga")
    cov = (
        matches.groupby(["country", "league_name", "league_code", "tier"])
        .agg(partidas=("date", "count"), ultima_data=("date", "max"))
        .reset_index()
        .sort_values(["tier", "country"])
        .rename(columns={"country": "país", "league_name": "liga", "league_code": "código", "tier": "tipo"})
    )
    st.dataframe(cov, width="stretch", hide_index=True)

    low_coverage = cov[cov["partidas"] < 50]
    if not low_coverage.empty:
        st.warning(
            "⚠️ Ligas com poucos jogos na base (menos de 50) — os cálculos estatísticos "
            "podem não ser confiáveis ainda: "
            + ", ".join(f"{r['liga']} ({r['país']})" for _, r in low_coverage.iterrows())
        )

    if meta.get("main_leagues_failed") or meta.get("extra_leagues_failed"):
        falhas = (meta.get("main_leagues_failed") or []) + (meta.get("extra_leagues_failed") or [])
        st.warning(f"⚠️ Não foi possível baixar dados para: {', '.join(falhas)} na última atualização.")

    st.markdown("### Páginas disponíveis")
    st.markdown(
        "- **📅 Calendário** — próximos jogos e odds de mercado\n"
        "- **🏆 Tabelas dos Campeonatos** — classificação por liga/temporada\n"
        "- **📊 Desempenho de Times** — forma, sequências, tendências e comparação entre times\n\n"
        "Use o menu à esquerda para navegar."
    )

render_footer()
