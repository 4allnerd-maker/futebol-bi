# Futebol BI

Ferramenta própria de análise de dados de futebol para apostas esportivas — substituto do
Power BI. Baixa dados de futebol de ligas da Europa e das Américas (fonte:
[football-data.co.uk](https://www.football-data.co.uk), gratuita, sem cadastro), calcula
estatísticas e tendências, e apresenta tudo em um app Streamlit com tabelas, filtros e
gráficos interativos.

## Estrutura do projeto

```
futebol-bi/
  data_pipeline.py      # baixa e normaliza os CSVs em Parquet (data/processed/)
  stats.py               # camada de cálculos: classificação, forma, streaks, tendências
  data_loader.py          # cache do Streamlit + funções de atualização
  refresh_data.py          # script standalone para agendar a atualização dos dados
  app.py                    # página inicial do Streamlit
  pages/
    1_📅_Calendario.py       # próximos jogos e odds de mercado
    2_🏆_Tabelas.py            # classificação por liga/temporada
    3_📊_Desempenho_Times.py    # forma, sequências, tendências, comparação entre times
  data/processed/               # matches.parquet, fixtures.parquet, meta.json (gerados)
  requirements.txt
```

## Instalação

Requer Python 3.11+. No PowerShell, a partir da pasta `futebol-bi`:

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## Como rodar

Primeiro baixe os dados (demora ~1-2 minutos na primeira vez):

```powershell
venv\Scripts\python.exe refresh_data.py
```

Depois suba o app:

```powershell
venv\Scripts\streamlit.exe run app.py
```

Abra `http://localhost:8501` no navegador. Você também pode clicar em **"Atualizar dados
agora"** na página inicial a qualquer momento, em vez de rodar `refresh_data.py` manualmente.

## Páginas

- **📅 Calendário** — próximos jogos (ligas europeias principais), com filtro por liga,
  intervalo de datas e time, mostrando as odds médias de mercado.
- **🏆 Tabelas dos Campeonatos** — seletor de país/liga/temporada, classificação completa
  (geral, casa ou fora), com destaque aproximado de zona de acesso e de rebaixamento.
- **📊 Desempenho de Times** — o coração da ferramenta: forma recente, sequências (streaks),
  tendência de gols marcados/sofridos, taxas de over/under 2.5 e ambas marcam, splits
  casa/fora, e filtros de segmentação (liga, temporada, mandante/visitante, últimos N jogos,
  intervalo de datas, adversários da metade de cima/baixo da tabela). Permite comparar dois
  times lado a lado.

## Cobertura de dados

- **Ligas principais** (chutes, escanteios, cartões, odds completas): Inglaterra (4
  divisões), Escócia, Alemanha (2), Itália (2), Espanha (2), França (2), Holanda, Bélgica,
  Portugal, Turquia, Grécia.
- **Ligas extras** (só resultado e odds, sem chutes/escanteios): Brasil, Argentina, México,
  EUA.
- **Calendário de próximos jogos**: só cobre as ligas europeias principais (o
  `fixtures.csv` da fonte não inclui as ligas extras).
- A página inicial mostra um aviso automático se alguma liga estiver com poucos jogos na
  base (< 50) ou se o último download falhou para alguma liga — isso costuma acontecer logo
  no início de uma temporada nova, antes de a liga em questão ter dados suficientes na fonte.

## Atualização automática dos dados

Os dados carregados no app ficam em cache por 6 horas (`CACHE_TTL_SECONDS` em
`data_loader.py`). Para manter os dados sempre frescos mesmo sem abrir o app, agende
`refresh_data.py` para rodar sozinho.

### Windows (Agendador de Tarefas)

1. Abra o **Agendador de Tarefas** (Task Scheduler) do Windows.
2. **Criar Tarefa Básica** → nome "FutebolBI_AtualizarDados".
3. Gatilho: diariamente, no horário que preferir (ex.: 06:00, antes de você abrir o app).
4. Ação: **Iniciar um programa**.
   - Programa/script: caminho completo para `venv\Scripts\python.exe` dentro da pasta do
     projeto (ex.: `C:\Users\...\futebol-bi\venv\Scripts\python.exe`).
   - Argumentos: `refresh_data.py`
   - Iniciar em: caminho completo da pasta `futebol-bi` (importante — é onde o script
     procura `data/processed/`).
5. Salve. Você pode testar clicando com o botão direito na tarefa → **Executar**.

### Linux/Mac (cron)

```
0 6 * * * cd /caminho/para/futebol-bi && venv/bin/python refresh_data.py >> refresh.log 2>&1
```

## Hospedado (Streamlit Community Cloud)

Este repositório já vem com tudo pronto para deploy gratuito:

- `data/processed/*.parquet` fica versionado no repo (não está no `.gitignore`), então o
  deploy já sobe com dados.
- `.github/workflows/refresh_data.yml` roda `refresh_data.py` todo dia às 06:00 UTC (e pode
  ser disparado manualmente pela aba **Actions** do GitHub), commitando os Parquet
  atualizados de volta no repositório. O Streamlit Cloud detecta o push e recarrega os dados
  automaticamente — ninguém precisa abrir o app nem rodar nada localmente.

Passos para publicar (feito uma única vez):

1. Em [share.streamlit.io](https://share.streamlit.io), faça login com a conta GitHub.
2. **New app** → selecione este repositório → arquivo principal `app.py` → **Deploy**.
3. Pronto — o app fica em uma URL pública tipo `https://SEU-APP.streamlit.app`, sempre
   atualizado pelo GitHub Actions.

## Aviso

⚠️ Esta ferramenta serve apenas para análise estatística de dados históricos. Não é garantia
de resultado nem recomendação de aposta. Jogue com responsabilidade.
