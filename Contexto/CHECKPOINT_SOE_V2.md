# CHECKPOINT — Sistema de Inteligência Comercial S&OE

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 27/05/2026
**Projeto:** Sistema de Inteligência Comercial Semanal — S&OE
**Etapa atual:** Ambiente recriado após quarentena de antivírus. v2 pronta para implementação.

---

## Sessão 27/05/2026 — Recomposição pós-quarentena

### O que foi perdido pelo antivírus
- `venv/` — apontava para Python 3.14 em caminho de outro PC (`samuel.bandeira`)
- `data/raw/` — todos os CSVs de vendas e previsão (6 arquivos)
- `data/processed/` — todos os parquets gerados (4 arquivos)
- `requirements.txt` — não existia

### O que foi recomposto nesta sessão
- ✅ `venv/` recriado com Python 3.10.6 (instalado em `C:\Users\samue\AppData\Local\Programs\Python\Python310\`)
- ✅ `requirements.txt` gerado a partir do venv (streamlit 1.57, pandas 2.3.3, numpy 2.2.6, plotly 6.7, scikit-learn 1.7, pyarrow 24)
- ✅ `data/raw/` criado com `LEIA-ME.txt` documentando os arquivos esperados
- ✅ Todos os imports críticos do dashboard testados e funcionando
- ✅ Código-fonte 100% intacto — nenhum módulo de lógica foi perdido

### Dados — pendente
Os CSVs originais estão sendo recuperados. Quando chegarem (possivelmente com escopo ligeiramente diferente), rodar `ATUALIZAR_E_RODAR.bat` para regenerar os parquets.

### Integração das novas bases (27/05/2026 — tarde)

Bases recebidas com estrutura nova (sistema único, 2024-2026):
- `data/raw/base_vendas_soe.csv`   — 1,402,300 linhas, Jan/2024–Mai/2026
- `data/raw/base_previsao.xlsx`    — 222,957 linhas, semanas TW 2026

Mudanças estruturais tratadas:
- CSV unificado (ACC+ACI+SIN) — ETL simplificado de 4 arquivos para 1
- `regiao` agora derivada de `uf` via UF_PARA_REGIAO (config.py)
- Gerências normalizadas: `Comercial I/II` → `Comercial 1/2`
- `nome_cliente` e `vendedor` adicionados ao schema (desbloqueia lookup de nomes)
- `valor_venda_mil` mapeado para `val_mm`, + `valor_liquido`, `valor_imposto` preservados
- `COMERCIAL 3` (previsão) mapeado para `Comercial 2`; `PORTO` filtrado
- Acento em colunas do Excel (`gerência`) tratado via normalização ASCII

Parquets gerados e validados:
- `vendas_filtrada.parquet` — 1,399,898 linhas × 21 colunas (32.6 MB)
- `meta_semanal.parquet`    — 115,445 linhas × 16 colunas (1.5 MB)
- meta_soe: 736k ton | meta_sop: 1,134k ton

Alerta identificado no relatório de qualidade:
- Mai/2025 com apenas 29,827 ton (29% da média) — base começa incompleta nesse mês

### Próximos passos
1. ✅ Pipeline rodando com novas bases
2. Implementar v2 (spec em `.kiro/specs/soe-v2-melhorias/tasks.md`)
3. Validar dashboard na prática (rodar SÓ_RODAR_DASHBOARD.bat e navegar nas abas)

---

---

## O que foi construído (v1 — CONCLUÍDO)

### Dashboard Streamlit — 3 abas funcionais

| Aba | Status | Descrição |
|---|---|---|
| Venda vs Plano S&OP | ✅ Funcionando | Ritmo semanal vs meta mensal com pesos históricos por linha |
| Venda vs Programa S&OE | ✅ Funcionando | Mesma lógica para metas semanais de execução (Jan–Jul/2026) |
| Score de Propensão | ✅ Funcionando | Ranqueamento de clientes B2B por probabilidade de compra |

### Arquitetura atual

```
app/
├── dashboard.py              # ~1.600 linhas — aplicação principal
├── engines/
│   ├── propensao_engine.py   # Score vetorizado, ~2.6s total com 1.7M linhas
│   └── acao_engine.py        # LEGADO — a remover na v2
├── modules/
│   ├── ritmo_semanal.py      # Abas S&OP e S&OE
│   ├── score_propensao.py    # Aba Score de Propensão
│   └── lista_acao.py         # LEGADO — a remover na v2
└── utils/
    └── filters.py            # Filtros compartilhados (implementado, não usado ainda)
scripts/
└── atualiza_dados.py         # Atualização incremental dos parquets
tests/
├── test_propensao_engine.py  # 26 testes — todos passando
├── test_acao_engine.py       # LEGADO — a remover na v2
└── test_integracao.py        # Testes com dados reais
```

### Dados

- `vendas_filtrada.parquet` — 1.7M linhas, 2019–2026
- `meta_semanal.parquet` — metas S&OP e S&OE por semana
- 73k clientes únicos, 20 linhas de produto
- Mediana de inatividade: **665 dias** (base B2B com cauda longa)
- Clientes ativos CA-50 (0–100d): ~3.700

### Score de Propensão — fórmula atual (v1)

```
score = rec + freq + saz + vol  (soma direta, 0–100 pts)

rec  = 0–30 pts  (≤30d=30, ≤60d=20, ≤90d=10, ≤180d=5, >180d=0)
freq = 0–25 pts  (normalizado pelo p90 dos ativos da linha)
saz  = 0–25 pts  (sazonalidade por LINHA, não por cliente)
vol  = 0–20 pts  (normalizado pelo p75 dos ativos da linha)

Penalidade de inatividade:
  ≤7d   → ×0.30  | 8–30d → ×0.80  | 31–100d → ×1.00
  101–180d → ×0.60 | >180d → ×0.15
```

**Distribuição real (CA-50):**
- Ativo (0–30d): média 40, max 65
- Regular (31–100d): média 38, max 71
- Esfriando (101–180d): média 20, max 34
- Inativo (181–365d): média 4, max 8
- Desativado (365d+): média 1, max 1

### Performance atual

| Operação | Tempo |
|---|---|
| `PropensaoEngine._preparar_dados` | ~1.8s |
| `calcular_scores(linha='CA-50')` | ~0.8s |
| `calcular_scores()` (todas as linhas) | ~4.5s |

---

## Bugs identificados na revisão (a corrigir na v2)

| ID | Severidade | Descrição | Arquivo |
|---|---|---|---|
| B1 | 🔴 Crítico | Filtro vazio retorna base completa silenciosamente | dashboard.py:1614 |
| B2 | 🔴 Crítico | `apply(axis=1)` em 1.7M linhas para semana TW | dashboard.py:262 |
| B3 | 🔴 Crítico | `_preparar_dados` usa `today()`, `calcular_scores` aceita `data_referencia` — inconsistência temporal | propensao_engine.py |
| B4 | 🔴 Crítico | Caminho hardcoded com nome de usuário Windows | dashboard.py:61 |
| B5 | 🟡 Médio | `__import__('datetime').timedelta` inline em função | ritmo_semanal.py:40 |
| B6 | 🟡 Médio | `groupby.apply` sem `include_groups=False` (pandas 3.x) | ritmo_semanal.py |
| B7 | 🟡 Médio | Import de `lista_acao` não usado | dashboard.py:16 |
| B8 | 🟡 Médio | `get_month_tw_ranges` duplicada em 2 arquivos | dashboard.py + ritmo_semanal.py |
| B9 | 🟡 Médio | `utils/filters.py` implementado mas não usado | filters.py |

---

## Próximos passos — v2 (spec criada)

A spec completa está em `.kiro/specs/soe-v2-melhorias/`.

### Prioridade P0 (~4h) — bugs que enganam o usuário hoje
1. Corrigir filtros vazios (B1)
2. Vetorizar semana TW (B2)
3. Corrigir inconsistência temporal no engine (B3)
4. Corrigir caminho hardcoded (B4)

### Prioridade P1 (~6h) — melhorias de valor
5. Recalibração do score: tiers dinâmicos (QUENTE/MORNO/FRIO/DORMENTE), sem min-max, flag NOVO
6. Lookup de nomes de clientes
7. Remoção de código legado (acao_engine, lista_acao)
8. Consolidação de utilitários (calendar_tw.py, visual.py, config.py)

### Prioridade P2 (~8h) — evolução
9. UI por tier (cards em vez de tabela)
10. Componente tendência no score
11. Script de backtest para validar calibração

---

## Como retomar

1. Abra o Kiro e carregue este arquivo como contexto
2. Abra `.kiro/specs/soe-v2-melhorias/tasks.md`
3. Comece pela task 1.1 (remoção de legado) — é a mais segura e libera espaço mental
4. Depois task 2.1 (caminho hardcoded) — 10 minutos, alto impacto
5. Depois task 2.2 (filtros vazios) — 30 minutos, corrige bug crítico

---

## Decisões técnicas registradas

- [x] Sazonalidade por linha (não por cliente) — 73k clientes levava 15s, 20 linhas é instantâneo
- [x] Score absoluto (soma direta 0–100) — sem normalização min-max que quebra comparação entre filtros
- [x] Lista de Ação removida do dashboard — Score com filtros é suficiente
- [x] Calendário TW (ISO) para 2026+, bins fixos para histórico pré-2026
- [x] Penalidade de inatividade: ×0.60 para >180d (não ×0.10 — muito agressivo)
- [ ] Tiers dinâmicos (QUENTE/MORNO/FRIO/DORMENTE) — a implementar na v2
- [ ] Componente tendência (vol_3m vs média 12m) — a implementar na v2
- [ ] Lookup de nomes de clientes — a implementar na v2
