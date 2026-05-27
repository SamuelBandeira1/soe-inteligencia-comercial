# Design Document — S&OE v2 Melhorias

## Overview

Esta evolução foca em correções cirúrgicas de bugs, eliminação de gargalos de performance, recalibração do score de propensão com tiers absolutos + dinâmicos, remoção de código legado e melhoria de UX da aba Score. Sem reescrita estrutural — mudanças incrementais e testáveis.

## Architecture

### Mudanças na estrutura de arquivos

```
app/
├── config.py                 # NOVO — constantes de negócio
├── dashboard.py              # Remove constantes, remove import lista_acao, corrige filtros e caminho
├── engines/
│   ├── propensao_engine.py   # Recalibração + correção temporal + tiers
│   └── acao_engine.py        # REMOVER
├── modules/
│   ├── ritmo_semanal.py      # Bug fix import + groupby.apply + usa utils/
│   ├── score_propensao.py    # UI por tier + lookup nomes + acao_sugerida
│   └── lista_acao.py         # REMOVER
└── utils/
    ├── calendar_tw.py        # NOVO — consolidação de get_month_tw_ranges + versão vetorizada
    ├── visual.py             # NOVO — cor_ritmo, paleta, fmt_ton
    └── filters.py            # Mantido (já implementado)

scripts/
└── atualiza_dados.py         # Estender para gerar clientes.parquet e fornecedores.parquet

tests/
├── test_propensao_engine.py  # Atualizar para nova API (data_ref no __init__)
├── test_acao_engine.py       # REMOVER
├── test_integracao.py        # Atualizar
└── test_backtest.py          # NOVO

REMOVER:
  app/engines/acao_engine.py
  app/modules/lista_acao.py
  tests/test_acao_engine.py
  data/processed/contatos_realizados.json (se existir)
```

## Components and Interfaces

### 1. app/config.py (NOVO)

Centraliza todas as constantes de negócio que hoje estão espalhadas em `dashboard.py`.

```python
from pathlib import Path

# Caminhos
ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"

# Linhas de produto
LINHAS_EXCLUIR = {"INOX BARRA", "INOX SUCATA", "INOX TUBO", "SUCATA", "GUSA"}
MAPA_NOME_LINHA = {"BOBINA": "BOBINA SLITTER"}
FAMILIA_OVERRIDE = {"FM": "LONGOS"}

# Score de propensão
SCORE_MAX = {"recencia": 30, "frequencia": 25, "sazonalidade": 15, "tendencia": 10, "volume": 20}

PENALIDADES_RECENCIA = [
    (0,   7,   0.60),   # comprou esta semana — menos agressivo que antes
    (8,   30,  0.85),   # no ciclo do mês
    (31,  100, 1.00),   # janela normal B2B
    (101, 180, 0.65),   # quase desativado
    (181, 9999, 0.30),  # desativado
]

REATIVACAO_PROFUNDA_DIAS = 365
REATIVACAO_PROFUNDA_COMPRAS_MAX = 3
CLIENTE_NOVO_DIAS = 60
LINHA_HISTORICO_MIN_MESES = 6
```

### 2. app/utils/calendar_tw.py (NOVO)

Consolida as funções de calendário TW que hoje estão duplicadas em `dashboard.py` e `ritmo_semanal.py`.

```python
def get_month_tw_ranges(year: int, month: int) -> list[tuple]:
    """Retorna [(semana_mes, dia_inicio, dia_fim), ...] baseado nas Semanas Técnicas."""
    ...

def day_to_semana_tw(year: int, month: int, day: int) -> int | None:
    """Converte dia do mês em semana_mes usando calendário TW."""
    ...

def vectorize_semana_tw(
    years: pd.Series, months: pd.Series, days: pd.Series
) -> pd.Series:
    """
    Versão vetorizada via lookup table.
    Substitui df.apply(axis=1) em carrega_dados() — de ~5s para <100ms.
    """
    unique = pd.DataFrame({"y": years, "m": months, "d": days}).drop_duplicates()
    unique["sem"] = [day_to_semana_tw(y, m, d) for y, m, d in unique.itertuples(index=False)]
    return (
        pd.DataFrame({"y": years, "m": months, "d": days})
        .merge(unique, on=["y", "m", "d"], how="left")["sem"]
        .values
    )
```

### 3. app/utils/visual.py (NOVO)

Consolida funções de cor e formatação que hoje estão duplicadas em 3+ arquivos.

```python
# Paleta
COR_PRIMARIA = "#1B2A4A"
COR_ACENTO   = "#F4822A"
COR_VERDE    = "#28A745"
COR_AMARELO  = "#FFC107"
COR_VERMELHO = "#DC3545"
COR_TEXTO    = "#2C3E50"
COR_GRID     = "#E8ECF0"

def cor_ritmo(pct) -> str: ...
def icone_ritmo(pct) -> str: ...
def cor_bg_ritmo(pct) -> str: ...
def seta_tendencia(var) -> str: ...
def fmt_ton(v) -> str: ...
```

### 4. app/engines/propensao_engine.py (RECALIBRADO)

Mudanças principais:

**a) data_referencia no `__init__`:**
```python
class PropensaoEngine:
    def __init__(self, df_vendas, data_referencia=None):
        self.data_ref = pd.Timestamp(data_referencia) if data_referencia else pd.Timestamp.today()
        self._preparar_dados()  # usa self.data_ref em todos os cortes

    def _preparar_dados(self):
        corte_12m = self.data_ref - pd.DateOffset(months=12)
        corte_100d = self.data_ref - pd.DateOffset(days=100)
        # ... tudo relativo a self.data_ref
```

**b) Score absoluto sem min-max:**
```python
# ANTES (errado):
score_final = (score - s_min) / (s_max - s_min) * 100

# DEPOIS (correto):
score_final = score_bruto  # já 0-100 pela soma dos componentes
```

**c) Fórmula de frequência:**
```python
# ANTES: (freq / freq_ref) × 25  — achata clientes ocasionais
# DEPOIS: min(25, freq × 60)     — bimestral=15pts, mensal=25pts
score_freq = (perfil["frequencia_compras"] * 60.0).clip(0, 25)
```

**d) Fórmula de volume logarítmica:**
```python
import numpy as np
# ANTES: linear — 1 outlier achata os outros 99%
# DEPOIS: log — concentra ganho nos primeiros volumes
mediana_vol = self._vol_mediana_ativos.get(linha or "_all", 1.0)
score_vol = np.log1p(vol / max(mediana_vol, 0.01)) * c_vol  # c_vol calibrado
score_vol = score_vol.clip(0, 20)
```

**e) Componente tendência (novo):**
```python
def _calcular_tendencia(self, perfil: pd.DataFrame) -> pd.Series:
    """vol_3m / (vol_12m / 4) — aceleração recente vs média histórica."""
    # vol_3m: volume nos últimos 3 meses
    # vol_12m: volume nos últimos 12 meses
    # ratio > 1 = acelerando, < 1 = desacelerando
    ratio = (vol_3m / (vol_12m / 4 + 0.001)).clip(0, 3)
    return (ratio / 3 * 10).clip(0, 10)  # 0-10 pts
```

**f) Tier dinâmico:**
```python
def _classificar_tier(self, perfil, p25, p50, p75) -> pd.Series:
    score = perfil["score_propensao"]
    dias  = perfil["dias_sem_comprar"]
    return np.select(
        [
            perfil["flag_novo"],
            perfil["flag_reativacao_profunda"],
            (score >= p75) & (dias >= 31) & (dias <= 100),
            (score >= p50) & (dias <= 180),
            score >= p25,
        ],
        ["NOVO", "REATIVACAO", "QUENTE", "MORNO", "FRIO"],
        default="DORMENTE",
    )
```

**g) Sazonalidade reduzida de 25 para 15 pts** (peso liberado para tendência):
```python
score_saz = perfil["linha"].map(
    lambda l: self._sazonalidade_linha.get(l, {}).get(mes_atual, 7.5)  # fallback = 7.5 (metade de 15)
)
score_saz = score_saz.clip(0, 15)
```

### 5. dashboard.py — correções

**Filtros vazios:**
```python
if not empresa_sel:
    st.warning("Selecione ao menos uma empresa para visualizar os dados.")
    st.stop()
# idem para regiao_sel e uf_sel
```

**Caminho relativo:**
```python
from app.config import DATA_PROCESSED
# ou dentro do arquivo:
OUT = Path(__file__).resolve().parent.parent / "data" / "processed"
```

**Semana TW vetorizada:**
```python
from utils.calendar_tw import vectorize_semana_tw

post_mask = df_v["ano"] >= 2026
if post_mask.any():
    df_v.loc[post_mask, "semana_mes"] = vectorize_semana_tw(
        df_v.loc[post_mask, "ano"],
        df_v.loc[post_mask, "mes"],
        df_v.loc[post_mask, "dia"],
    )
```

### 6. score_propensao.py — UI por tier

```python
def render(df_vendas, filtros):
    ...
    df_scores = engine.calcular_scores(linha=linha_param, regiao=regiao_param)

    # Seção NOVO (destaque especial)
    df_novo = df_scores[df_scores["tier"] == "NOVO"]
    if not df_novo.empty:
        st.markdown("### 🆕 Clientes Novos (1ª compra ≤ 60 dias)")
        _render_tier_cards(df_novo, "#7B1FA2")

    # 4 colunas de tier
    tier_config = {
        "QUENTE":   ("#B71C1C", "🔥"),
        "MORNO":    ("#E65100", "🌡️"),
        "FRIO":     ("#1565C0", "❄️"),
        "DORMENTE": ("#757575", "💤"),
    }
    cols = st.columns(4)
    for col, (tier, (cor, icone)) in zip(cols, tier_config.items()):
        df_tier = df_scores[df_scores["tier"] == tier]
        with col:
            _render_tier_section(df_tier, tier, cor, icone)

    # Reativação Profunda (colapsado)
    df_reat = df_scores[df_scores["tier"] == "REATIVACAO"]
    if not df_reat.empty:
        with st.expander(f"💤 Reativação Profunda ({len(df_reat)} clientes)"):
            _render_tier_cards(df_reat, "#757575")
```

### 7. scripts/atualiza_dados.py — lookup de nomes

```python
def gerar_clientes_parquet(df_unif: pd.DataFrame) -> None:
    """Gera clientes.parquet com nomes (placeholder até ter fonte real)."""
    clientes = df_unif[["cd_cliente"]].drop_duplicates()
    clientes["nome_cliente"] = "Cliente " + clientes["cd_cliente"].astype(str)
    clientes["telefone"] = ""
    clientes["email"] = ""
    clientes.to_parquet(OUT / "clientes.parquet", index=False)
    log(f"clientes.parquet: {len(clientes):,} registros")
```

## Data Models

### Saída de `calcular_scores()` — colunas adicionadas

| Coluna | Tipo | Descrição |
|---|---|---|
| `tier` | str | QUENTE / MORNO / FRIO / DORMENTE / NOVO / REATIVACAO / INDEFINIDO |
| `flag_novo` | bool | Primeira compra ≤ 60 dias |
| `flag_reativacao_profunda` | bool | >365d inativo E ≤3 compras total |
| `acao_sugerida` | str | Texto de ação para o coordenador |
| `tendencia` | float | vol_3m / (vol_12m/4) — ratio de aceleração |
| `score_tendencia` | float | 0–10 pts |
| `nome_cliente` | str | Nome do cliente (se lookup disponível) |

## Error Handling

- `clientes.parquet` ausente → warning + fallback para `cd_cliente`
- `data_referencia` inválida → `ValueError("data_referencia precisa ser date ou Timestamp")`
- Linha com < 6 meses de histórico → tier "INDEFINIDO", sazonalidade usa fallback
- Base vazia após filtros → `st.warning("Nenhum dado encontrado")` + `return` em todos os módulos
- `cd_cliente` com tipo inesperado → assert no `_validar_colunas`

## Testing Strategy

### Testes unitários atualizados
- `test_propensao_engine.py`: atualizar para passar `data_referencia` no `__init__`
- Novos testes: `test_tier_dinamico`, `test_flag_novo`, `test_flag_reativacao`
- Testes de fórmula: frequência com `freq × 60`, volume logarítmico

### Teste de backtest (novo)
```python
# tests/test_backtest.py
def test_sem_leakage_temporal():
    """Engine com data_ref=2025-06-01 não usa dados após essa data."""
    eng = PropensaoEngine(df, data_referencia=date(2025, 6, 1))
    assert eng.data_ref == pd.Timestamp("2025-06-01")
    # Verifica que corte_12m = 2024-06-01
    assert eng._corte_12m == pd.Timestamp("2024-06-01")
```

### Teste de performance
```python
def test_vectorize_semana_tw_performance():
    """vectorize_semana_tw deve ser >10x mais rápido que apply."""
    # Gera 200k linhas de 2026
    ...
    assert tempo_vetorizado < tempo_apply / 10
```

### Smoke test
```python
# tests/test_smoke.py
def test_todas_abas_renderizam():
    """Cada módulo de aba deve importar e chamar render() sem exception."""
    from modules import ritmo_semanal, score_propensao
    # Verifica que não há ImportError nem AttributeError
```
