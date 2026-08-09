"""
Script standalone para atualizar os dados sem abrir o Streamlit.
Pensado para ser agendado (Agendador de Tarefas do Windows, cron, GitHub Actions).

Uso:
    venv\\Scripts\\python.exe refresh_data.py
"""
import sys

from data_pipeline import run_pipeline

if __name__ == "__main__":
    try:
        meta = run_pipeline()
    except Exception as e:
        print(f"ERRO: falha ao atualizar os dados: {e}", file=sys.stderr)
        sys.exit(1)

    falhas = (meta.get("main_leagues_failed") or []) + (meta.get("extra_leagues_failed") or [])
    print(f"OK: {meta['matches_rows']} partidas, {meta['fixtures_rows']} jogos futuros.")
    if falhas:
        print(f"AVISO: falha ao baixar: {', '.join(falhas)}")
    sys.exit(0)
