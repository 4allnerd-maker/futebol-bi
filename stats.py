"""
Camada de calculos estatisticos: classificacao, forma, streaks, tendencias de
mercado (over/under, BTTS), splits casa/fora. Tudo construido em cima de um
formato "longo" (uma linha por time por partida) derivado de matches.parquet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

POINTS_MAP = {"W": 3, "D": 1, "L": 0}


def build_team_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """Converte o df de partidas (1 linha/jogo) em formato longo (1 linha/time/jogo)."""
    base_cols = ["country", "league_code", "league_name", "tier", "season", "date", "time", "referee"]

    home = pd.DataFrame({
        **{c: matches[c] for c in base_cols},
        "team": matches["home_team"],
        "opponent": matches["away_team"],
        "venue": "casa",
        "goals_for": matches["home_goals"],
        "goals_against": matches["away_goals"],
        "shots_for": matches["home_shots"],
        "shots_against": matches["away_shots"],
        "shots_target_for": matches["home_shots_target"],
        "shots_target_against": matches["away_shots_target"],
        "corners_for": matches["home_corners"],
        "corners_against": matches["away_corners"],
    })
    home["result"] = np.select(
        [matches["result"] == "H", matches["result"] == "D", matches["result"] == "A"],
        ["W", "D", "L"], default=None,
    )

    away = pd.DataFrame({
        **{c: matches[c] for c in base_cols},
        "team": matches["away_team"],
        "opponent": matches["home_team"],
        "venue": "fora",
        "goals_for": matches["away_goals"],
        "goals_against": matches["home_goals"],
        "shots_for": matches["away_shots"],
        "shots_against": matches["home_shots"],
        "shots_target_for": matches["away_shots_target"],
        "shots_target_against": matches["home_shots_target"],
        "corners_for": matches["away_corners"],
        "corners_against": matches["home_corners"],
    })
    away["result"] = np.select(
        [matches["result"] == "A", matches["result"] == "D", matches["result"] == "H"],
        ["W", "D", "L"], default=None,
    )

    long_df = pd.concat([home, away], ignore_index=True)
    long_df = long_df.dropna(subset=["result"])
    long_df["points"] = long_df["result"].map(POINTS_MAP)
    total_goals = long_df["goals_for"] + long_df["goals_against"]
    long_df["over25"] = total_goals > 2.5
    long_df["btts"] = (long_df["goals_for"] > 0) & (long_df["goals_against"] > 0)
    long_df["clean_sheet"] = long_df["goals_against"] == 0
    long_df = long_df.sort_values(["team", "date"]).reset_index(drop=True)
    return long_df


# ---------------------------------------------------------------------------
# Classificacao
# ---------------------------------------------------------------------------

def league_table(team_matches: pd.DataFrame, country: str, league_code: str,
                  season: str, venue: str = "todos") -> pd.DataFrame:
    """Tabela de classificacao. venue: 'todos', 'casa' ou 'fora'."""
    df = team_matches[
        (team_matches["country"] == country)
        & (team_matches["league_code"] == league_code)
        & (team_matches["season"] == season)
    ]
    if venue != "todos":
        df = df[df["venue"] == venue]
    if df.empty:
        return pd.DataFrame(columns=[
            "time", "jogos", "vitorias", "empates", "derrotas",
            "gols_pro", "gols_contra", "saldo", "pontos", "aproveitamento_pct",
        ])

    g = df.groupby("team").agg(
        jogos=("result", "count"),
        vitorias=("result", lambda s: (s == "W").sum()),
        empates=("result", lambda s: (s == "D").sum()),
        derrotas=("result", lambda s: (s == "L").sum()),
        gols_pro=("goals_for", "sum"),
        gols_contra=("goals_against", "sum"),
        pontos=("points", "sum"),
    ).reset_index()
    g["saldo"] = g["gols_pro"] - g["gols_contra"]
    g["aproveitamento_pct"] = (100 * g["pontos"] / (g["jogos"] * 3)).round(1)
    g = g.rename(columns={"team": "time"})
    g = g.sort_values(["pontos", "saldo", "gols_pro"], ascending=False).reset_index(drop=True)
    g.insert(0, "posicao", g.index + 1)
    cols = ["posicao", "time", "jogos", "vitorias", "empates", "derrotas",
            "gols_pro", "gols_contra", "saldo", "pontos", "aproveitamento_pct"]
    return g[cols]


# ---------------------------------------------------------------------------
# Filtro generico usado por forma/streak/tendencias
# ---------------------------------------------------------------------------

def filter_team_matches(
    team_matches: pd.DataFrame,
    team: str,
    venue: str = "todos",
    league_code: str | None = None,
    season: str | None = None,
    last_n: int | None = None,
    date_from=None,
    date_to=None,
    opponent_in: list[str] | None = None,
) -> pd.DataFrame:
    df = team_matches[team_matches["team"] == team]
    if venue != "todos":
        df = df[df["venue"] == venue]
    if league_code:
        df = df[df["league_code"] == league_code]
    if season:
        df = df[df["season"] == season]
    if date_from is not None:
        df = df[df["date"] >= pd.Timestamp(date_from)]
    if date_to is not None:
        df = df[df["date"] <= pd.Timestamp(date_to)]
    if opponent_in:
        df = df[df["opponent"].isin(opponent_in)]
    df = df.sort_values("date")
    if last_n:
        df = df.tail(last_n)
    return df


# ---------------------------------------------------------------------------
# Forma recente
# ---------------------------------------------------------------------------

def recent_form_summary(subset: pd.DataFrame) -> dict:
    """Resumo de forma para um subset ja filtrado (ver filter_team_matches)."""
    if subset.empty:
        return {
            "jogos": 0, "sequencia": "", "pontos_por_jogo": 0.0,
            "media_gols_marcados": 0.0, "media_gols_sofridos": 0.0,
            "taxa_over25_pct": 0.0, "taxa_btts_pct": 0.0, "taxa_clean_sheet_pct": 0.0,
        }
    n = len(subset)
    sequencia = "".join(subset["result"].tolist())
    return {
        "jogos": n,
        "sequencia": sequencia,
        "pontos_por_jogo": round(subset["points"].mean(), 2),
        "media_gols_marcados": round(subset["goals_for"].mean(), 2),
        "media_gols_sofridos": round(subset["goals_against"].mean(), 2),
        "taxa_over25_pct": round(100 * subset["over25"].mean(), 1),
        "taxa_btts_pct": round(100 * subset["btts"].mean(), 1),
        "taxa_clean_sheet_pct": round(100 * subset["clean_sheet"].mean(), 1),
    }


# ---------------------------------------------------------------------------
# Sequencias (streaks) - calculadas sobre o historico completo (ordenado),
# contando a partir do jogo mais recente para tras.
# ---------------------------------------------------------------------------

def _current_streak(flags: pd.Series) -> int:
    """Conta quantas ocorrencias consecutivas de True existem no final da serie."""
    count = 0
    for val in reversed(flags.tolist()):
        if val:
            count += 1
        else:
            break
    return count


def current_streaks(team_matches: pd.DataFrame, team: str, venue: str = "todos") -> dict:
    df = filter_team_matches(team_matches, team, venue=venue)
    if df.empty:
        return {
            "invicto": 0, "vencendo": 0, "sem_perder_ha": 0,
            "sem_sofrer_gol": 0, "sem_marcar": 0, "marcando_ha": 0,
        }
    return {
        "invicto": _current_streak(df["result"] != "L"),
        "vencendo": _current_streak(df["result"] == "W"),
        "sem_vencer_ha": _current_streak(df["result"] != "W"),
        "sem_sofrer_gol": _current_streak(df["clean_sheet"]),
        "sem_marcar": _current_streak(df["goals_for"] == 0),
        "marcando_ha": _current_streak(df["goals_for"] > 0),
    }


# ---------------------------------------------------------------------------
# Tendencia de gols ao longo do tempo (para grafico Plotly)
# ---------------------------------------------------------------------------

def goals_trend(subset: pd.DataFrame, rolling: int = 5) -> pd.DataFrame:
    """Retorna date, goals_for, goals_against e medias moveis, prontos p/ grafico."""
    if subset.empty:
        return pd.DataFrame(columns=["date", "goals_for", "goals_against",
                                      "media_movel_marcados", "media_movel_sofridos"])
    out = subset[["date", "goals_for", "goals_against"]].copy().sort_values("date")
    out["media_movel_marcados"] = out["goals_for"].rolling(rolling, min_periods=1).mean()
    out["media_movel_sofridos"] = out["goals_against"].rolling(rolling, min_periods=1).mean()
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Utilitarios de listagem (para popular filtros na UI)
# ---------------------------------------------------------------------------

def list_leagues(matches: pd.DataFrame) -> pd.DataFrame:
    return (
        matches[["country", "league_code", "league_name", "tier"]]
        .drop_duplicates()
        .sort_values(["country", "league_name"])
        .reset_index(drop=True)
    )


def list_seasons(matches: pd.DataFrame, country: str, league_code: str) -> list[str]:
    sub = matches[(matches["country"] == country) & (matches["league_code"] == league_code)]
    return sorted(sub["season"].dropna().unique().tolist(), reverse=True)


def list_teams(team_matches: pd.DataFrame, country: str | None = None,
                league_code: str | None = None, season: str | None = None) -> list[str]:
    df = team_matches
    if country:
        df = df[df["country"] == country]
    if league_code:
        df = df[df["league_code"] == league_code]
    if season:
        df = df[df["season"] == season]
    return sorted(df["team"].dropna().unique().tolist())
