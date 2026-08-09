"""
Pipeline de dados: baixa CSVs da football-data.co.uk, normaliza em um esquema
unico de partidas e salva em Parquet local (data/processed/).

Uso:
    python data_pipeline.py            # roda o pipeline completo
    python -c "from data_pipeline import run_pipeline; run_pipeline()"
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("data_pipeline")

DATA_DIR = Path(__file__).parent / "data" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MATCHES_PATH = DATA_DIR / "matches.parquet"
FIXTURES_PATH = DATA_DIR / "fixtures.parquet"
META_PATH = DATA_DIR / "meta.json"

REQUEST_TIMEOUT = 20

# ---------------------------------------------------------------------------
# Catalogo de ligas
# ---------------------------------------------------------------------------

# codigo -> (pais, nome da liga)
MAIN_LEAGUES: dict[str, tuple[str, str]] = {
    "E0": ("Inglaterra", "Premier League"),
    "E1": ("Inglaterra", "Championship"),
    "E2": ("Inglaterra", "League One"),
    "E3": ("Inglaterra", "League Two"),
    "SC0": ("Escocia", "Premiership"),
    "D1": ("Alemanha", "Bundesliga"),
    "D2": ("Alemanha", "2. Bundesliga"),
    "I1": ("Italia", "Serie A"),
    "I2": ("Italia", "Serie B"),
    "SP1": ("Espanha", "La Liga"),
    "SP2": ("Espanha", "Segunda Division"),
    "F1": ("Franca", "Ligue 1"),
    "F2": ("Franca", "Ligue 2"),
    "N1": ("Holanda", "Eredivisie"),
    "B1": ("Belgica", "First Division A"),
    "P1": ("Portugal", "Primeira Liga"),
    "T1": ("Turquia", "Super Lig"),
    "G1": ("Grecia", "Super League"),
}

# codigo -> (pais, nome da liga)
EXTRA_LEAGUES: dict[str, tuple[str, str]] = {
    "BRA": ("Brasil", "Serie A"),
    "ARG": ("Argentina", "Liga Profesional"),
    "MEX": ("Mexico", "Liga MX"),
    "USA": ("EUA", "MLS"),
}

MAIN_URL_TMPL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
EXTRA_URL_TMPL = "https://www.football-data.co.uk/new/{code}.csv"
FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"


# ---------------------------------------------------------------------------
# Temporadas
# ---------------------------------------------------------------------------

def _season_start_year(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= 7 else today.year - 1


def current_season_code(today: date | None = None) -> str:
    """Ex.: '2526' para a temporada 2025/2026."""
    y = _season_start_year(today)
    return f"{str(y)[2:]}{str(y + 1)[2:]}"


def season_codes(n_previous: int = 2, today: date | None = None) -> list[str]:
    """Temporada atual + N temporadas anteriores, mais recente primeiro."""
    y = _season_start_year(today)
    return [f"{str(y - i)[2:]}{str(y - i + 1)[2:]}" for i in range(n_previous + 1)]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _download_csv(url: str) -> pd.DataFrame | None:
    """Baixa um CSV e retorna DataFrame, ou None se falhar (404, timeout, etc)."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200 or not resp.content.strip():
            log.warning("Sem dados em %s (status %s)", url, resp.status_code)
            return None
        # encoding utf-8-sig: os arquivos vem com BOM
        df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig", on_bad_lines="skip")
        if df.empty:
            return None
        return df
    except requests.RequestException as e:
        log.warning("Falha ao baixar %s: %s", url, e)
        return None
    except pd.errors.ParserError as e:
        log.warning("Falha ao parsear %s: %s", url, e)
        return None


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Retorna a coluna se existir, senao uma serie de NaN do mesmo tamanho."""
    if name in df.columns:
        return df[name]
    return pd.Series([pd.NA] * len(df), index=df.index)


# ---------------------------------------------------------------------------
# Normalizacao -> esquema unico de partidas
# ---------------------------------------------------------------------------

MATCH_COLUMNS = [
    "country", "league_code", "league_name", "tier", "season",
    "date", "time", "home_team", "away_team",
    "home_goals", "away_goals", "result",
    "home_goals_ht", "away_goals_ht", "result_ht",
    "referee",
    "home_shots", "away_shots", "home_shots_target", "away_shots_target",
    "home_corners", "away_corners",
    "home_yellow", "away_yellow", "home_red", "away_red",
    "odds_home", "odds_draw", "odds_away",
    "odds_over25", "odds_under25",
]


def _normalize_main(df: pd.DataFrame, code: str, season: str) -> pd.DataFrame:
    country, league_name = MAIN_LEAGUES[code]
    out = pd.DataFrame({
        "country": country,
        "league_code": code,
        "league_name": league_name,
        "tier": "principal",
        "season": season,
        "date": _parse_dates(_col(df, "Date")),
        "time": _col(df, "Time"),
        "home_team": _col(df, "HomeTeam"),
        "away_team": _col(df, "AwayTeam"),
        "home_goals": pd.to_numeric(_col(df, "FTHG"), errors="coerce"),
        "away_goals": pd.to_numeric(_col(df, "FTAG"), errors="coerce"),
        "result": _col(df, "FTR"),
        "home_goals_ht": pd.to_numeric(_col(df, "HTHG"), errors="coerce"),
        "away_goals_ht": pd.to_numeric(_col(df, "HTAG"), errors="coerce"),
        "result_ht": _col(df, "HTR"),
        "referee": _col(df, "Referee"),
        "home_shots": pd.to_numeric(_col(df, "HS"), errors="coerce"),
        "away_shots": pd.to_numeric(_col(df, "AS"), errors="coerce"),
        "home_shots_target": pd.to_numeric(_col(df, "HST"), errors="coerce"),
        "away_shots_target": pd.to_numeric(_col(df, "AST"), errors="coerce"),
        "home_corners": pd.to_numeric(_col(df, "HC"), errors="coerce"),
        "away_corners": pd.to_numeric(_col(df, "AC"), errors="coerce"),
        "home_yellow": pd.to_numeric(_col(df, "HY"), errors="coerce"),
        "away_yellow": pd.to_numeric(_col(df, "AY"), errors="coerce"),
        "home_red": pd.to_numeric(_col(df, "HR"), errors="coerce"),
        "away_red": pd.to_numeric(_col(df, "AR"), errors="coerce"),
        "odds_home": pd.to_numeric(_col(df, "AvgH"), errors="coerce"),
        "odds_draw": pd.to_numeric(_col(df, "AvgD"), errors="coerce"),
        "odds_away": pd.to_numeric(_col(df, "AvgA"), errors="coerce"),
        "odds_over25": pd.to_numeric(_col(df, "Avg>2.5"), errors="coerce"),
        "odds_under25": pd.to_numeric(_col(df, "Avg<2.5"), errors="coerce"),
    })
    return out[MATCH_COLUMNS]


def _normalize_extra(df: pd.DataFrame, code: str, seasons_keep: set[str]) -> pd.DataFrame:
    country, league_name = EXTRA_LEAGUES[code]
    season_raw = _col(df, "Season").astype(str)
    out = pd.DataFrame({
        "country": country,
        "league_code": code,
        "league_name": league_name,
        "tier": "extra",
        "season": season_raw,
        "date": _parse_dates(_col(df, "Date")),
        "time": _col(df, "Time"),
        "home_team": _col(df, "Home"),
        "away_team": _col(df, "Away"),
        "home_goals": pd.to_numeric(_col(df, "HG"), errors="coerce"),
        "away_goals": pd.to_numeric(_col(df, "AG"), errors="coerce"),
        "result": _col(df, "Res"),
        "home_goals_ht": pd.NA,
        "away_goals_ht": pd.NA,
        "result_ht": pd.NA,
        "referee": pd.NA,
        "home_shots": pd.NA,
        "away_shots": pd.NA,
        "home_shots_target": pd.NA,
        "away_shots_target": pd.NA,
        "home_corners": pd.NA,
        "away_corners": pd.NA,
        "home_yellow": pd.NA,
        "away_yellow": pd.NA,
        "home_red": pd.NA,
        "away_red": pd.NA,
        "odds_home": pd.to_numeric(_col(df, "AvgCH"), errors="coerce"),
        "odds_draw": pd.to_numeric(_col(df, "AvgCD"), errors="coerce"),
        "odds_away": pd.to_numeric(_col(df, "AvgCA"), errors="coerce"),
        "odds_over25": pd.NA,
        "odds_under25": pd.NA,
    })
    out = out[MATCH_COLUMNS]
    if seasons_keep:
        out = out[out["season"].isin(seasons_keep)]
    return out


FIXTURE_COLUMNS = [
    "country", "league_code", "league_name",
    "date", "time", "home_team", "away_team", "referee",
    "odds_home", "odds_draw", "odds_away", "odds_over25", "odds_under25",
]


def _normalize_fixtures(df: pd.DataFrame) -> pd.DataFrame:
    div = _col(df, "Div").astype(str)
    country = div.map(lambda c: MAIN_LEAGUES.get(c, (None, None))[0])
    league_name = div.map(lambda c: MAIN_LEAGUES.get(c, (None, None))[1])
    out = pd.DataFrame({
        "country": country,
        "league_code": div,
        "league_name": league_name,
        "date": _parse_dates(_col(df, "Date")),
        "time": _col(df, "Time"),
        "home_team": _col(df, "HomeTeam"),
        "away_team": _col(df, "AwayTeam"),
        "referee": _col(df, "Referee"),
        "odds_home": pd.to_numeric(_col(df, "AvgH"), errors="coerce"),
        "odds_draw": pd.to_numeric(_col(df, "AvgD"), errors="coerce"),
        "odds_away": pd.to_numeric(_col(df, "AvgA"), errors="coerce"),
        "odds_over25": pd.to_numeric(_col(df, "Avg>2.5"), errors="coerce"),
        "odds_under25": pd.to_numeric(_col(df, "Avg<2.5"), errors="coerce"),
    })
    out = out.dropna(subset=["date", "home_team", "away_team"])
    # so mantem ligas que reconhecemos (mapeadas em MAIN_LEAGUES)
    out = out[out["country"].notna()]
    return out[FIXTURE_COLUMNS]


# ---------------------------------------------------------------------------
# Fetch por categoria
# ---------------------------------------------------------------------------

def fetch_main_leagues(n_previous_seasons: int = 2) -> tuple[pd.DataFrame, dict]:
    frames = []
    status: dict[str, list[str]] = {"ok": [], "falhou": []}
    seasons = season_codes(n_previous_seasons)
    for code in MAIN_LEAGUES:
        got_any = False
        for season in seasons:
            url = MAIN_URL_TMPL.format(season=season, code=code)
            df = _download_csv(url)
            if df is None:
                continue
            frames.append(_normalize_main(df, code, season))
            got_any = True
        if got_any:
            status["ok"].append(code)
        else:
            status["falhou"].append(code)
            log.warning("Nenhuma temporada disponivel para liga %s", code)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=MATCH_COLUMNS)
    return combined, status


def fetch_extra_leagues(n_seasons_keep: int = 3) -> tuple[pd.DataFrame, dict]:
    frames = []
    status: dict[str, list[str]] = {"ok": [], "falhou": []}
    for code in EXTRA_LEAGUES:
        url = EXTRA_URL_TMPL.format(code=code)
        df = _download_csv(url)
        if df is None:
            status["falhou"].append(code)
            continue
        all_seasons = sorted(df["Season"].astype(str).unique())
        keep = set(all_seasons[-n_seasons_keep:])
        frames.append(_normalize_extra(df, code, keep))
        status["ok"].append(code)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=MATCH_COLUMNS)
    return combined, status


def fetch_fixtures() -> pd.DataFrame:
    df = _download_csv(FIXTURES_URL)
    if df is None:
        return pd.DataFrame(columns=FIXTURE_COLUMNS)
    return _normalize_fixtures(df)


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------

def run_pipeline(n_previous_seasons: int = 2, n_extra_seasons_keep: int = 3) -> dict:
    log.info("Baixando ligas principais...")
    main_df, main_status = fetch_main_leagues(n_previous_seasons)
    log.info("Ligas principais: %d ok, %d falharam (%s)",
              len(main_status["ok"]), len(main_status["falhou"]), main_status["falhou"])

    log.info("Baixando ligas extras...")
    extra_df, extra_status = fetch_extra_leagues(n_extra_seasons_keep)
    log.info("Ligas extras: %d ok, %d falharam (%s)",
              len(extra_status["ok"]), len(extra_status["falhou"]), extra_status["falhou"])

    matches = pd.concat([main_df, extra_df], ignore_index=True)
    matches = matches.dropna(subset=["date", "home_team", "away_team"])
    matches = matches.sort_values(["country", "league_code", "date"]).reset_index(drop=True)

    log.info("Baixando fixtures (proximos jogos)...")
    fixtures = fetch_fixtures()

    matches.to_parquet(MATCHES_PATH, index=False)
    fixtures.to_parquet(FIXTURES_PATH, index=False)

    meta = {
        "last_update": datetime.now().isoformat(timespec="seconds"),
        "matches_rows": int(len(matches)),
        "fixtures_rows": int(len(fixtures)),
        "main_leagues_ok": main_status["ok"],
        "main_leagues_failed": main_status["falhou"],
        "extra_leagues_ok": extra_status["ok"],
        "extra_leagues_failed": extra_status["falhou"],
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Pipeline concluido: %d partidas, %d jogos futuros.", len(matches), len(fixtures))
    return meta


if __name__ == "__main__":
    run_pipeline()
