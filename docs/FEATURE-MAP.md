# Feature Map

> Auto-maintained index of every user-facing feature and the code path that implements it. Updated alongside the code — not after the fact.

## Tab 1 — Visão Geral (Sales Pace Overview)

Shows daily and weekly sales pace vs. plan for the selected month, with close-the-gap projection and MoM sparkline cards.

**Flow:**

1. `app/dashboard.py` — sidebar filters (empresa, região, linha, ano/mês) applied; `carrega_dados()` merges vendas + meta parquets; `calcula_pesos()` builds intra-month weight dict
2. `app/utils/data_loader.py` — `load_vendas()` / `load_meta()`: reads `data/processed/vendas_filtrada.parquet` and `meta_semanal.parquet` (local) or downloads from Google Drive if parquets absent
3. `app/dashboard.py` — `render_aba()`: computes pace %, projection, gap; `graf_diario()` draws daily bars with deviations; `graf_semanal()` draws weekly grouped bars with TW labels
4. `app/modules/ritmo_semanal.py` — `render()`: renders weekly rhythm section with gauges and pace cards
5. `app/utils/calendar_tw.py` — `get_month_tw_ranges()` / `vectorize_semana_tw()`: maps calendar days to Technical Week numbers for 2026+ data

---

## Tab 2 — Plano Comercial (Commercial Plan)

Shows a 10-week demand horizon segmented into Frozen / Liquid / Fluid zones, exception alerts, a what-if meta simulator, an opportunity scatter matrix (propensity × volume), and a ranked client contact list.

**Flow:**

1. `app/dashboard.py` — passes filtered `df_f` and `df_v` to module
2. `app/modules/plano_comercial.py` — `render()`: builds 10-week horizon chart with vrect zones; raises exception alerts for lines deviating > threshold; renders what-if slider (Zona Líquida only); renders opportunity matrix scatter
3. `app/engines/propensao_engine.py` — `PropensaoEngine.calcular_scores()`: computes 5-component propensity score per (client, line) from `df_vendas`
4. `app/engines/sazonalidade_semanal.py` — `SemanalPropensaoEngine.score_semana()`: adjusts base score by within-month week seasonality (W=0.40)
5. `app/modules/score_propensao.py` — `render()`: displays ranked client table with tier badges and suggested action column
6. `app/modules/matriz_semanal.py` — `render()`: heat map of Semana × Linha showing % of weekly plan with traffic-light colours

---

## Tab 3 — Demand Sensing (Monte Carlo Forecast)

Diagnoses forecast bias (MAPE, Bias, Hit Rate, CV) on completed weeks, then projects 8 weeks ahead via pace + seasonality with 1 000 Monte Carlo simulations (P10/P25/P50/P75/P90) overlaid with S&OP and S&OE plans.

**Flow:**

1. `app/dashboard.py` — passes filtered `df_f` (semana-level) to module
2. `app/modules/demand_sensing.py` — `render()`: calls `_historico_completo()` to filter completed weeks (vol > 0 AND meta > 0); computes MAPE, Bias, Hit Rate, CV; calls `_monte_carlo()` for probabilistic projection; renders diagnostic charts and fan chart

---

## Tab 4 — Dashboard UF (State-Level Performance)

Renders an offline bubble map of Brazil sized by sales volume per state, highlights top risks and top performers, and shows a detailed UF table with pace % and gap.

**Flow:**

1. `app/dashboard.py` — passes filtered `df_f` to module
2. `app/modules/dashboard_uf.py` — `render()`: aggregates vol_ton and meta_soe by UF; maps UF to lat/lon via embedded `_UF_COORDS` dict (no external GeoJSON); builds Plotly Scattergeo bubble map; computes risk/opportunity cards; renders detail table

---

## Tab 5 — Assertividade do Plano (Forecast Accuracy)

Compares 12 historical + 8 future weeks of Real vs. S&OP vs. S&OE, shows MAPE/Bias summary KPIs, a weekly metrics table, and per-line detail expanders.

**Flow:**

1. `app/dashboard.py` — passes filtered `df_f` to module
2. `app/modules/assertividade_plano.py` — `render()`: builds combined historical+future chart with today separator; computes Bias and MAPE over last `N_CALIB=4` weeks; renders aggregated weekly table; renders per-line S&OP and S&OE expanders with download buttons

---

## Authentication Gate

Blocks unauthenticated access before any dashboard content is shown.

**Flow:**

1. `app/dashboard.py` — calls `require_auth()` immediately after imports
2. `app/utils/auth.py` — `require_auth()`: checks `st.session_state`; if not authenticated, renders login form and calls `st.stop()`; validates credentials against bcrypt hashes in `st.secrets["users"]`; brute-force lockout after 5 failures (5-minute cooldown)

---

## Data Pipeline (ETL — runs locally, not in app)

Transforms raw source files into parquets consumed by the dashboard.

**Flow:**

1. `ATUALIZAR_E_RODAR.bat` — orchestrates: increment sales → ETL → launch dashboard
2. `scripts/incrementa_vendas_diario.py` — merges monthly sales CSV into master raw file
3. `scripts/atualiza_dados.py` — reads `data/raw/base_vendas_soe.csv` + `base_previsao.xlsx`; normalises company/gerência/region names using constants from `app/config.py`; writes four files to `data/processed/`
4. `app/utils/data_loader.py` — at runtime, `load_vendas()` / `load_meta()` read the parquets (or download from Google Drive if absent locally)
