# Session — Assertividade v4: Fórmula Contínua + Variáveis Exógenas

## Status

done

## Last Active

2026-05-28

## Resumo

Refatoração da fórmula de assertividade de binária (aderência ±10%) para contínua (1−MAPE).
Adição de toggle de base (Real vs Plano). Redesign completo da estrutura da página (v4).
Registro de dívida técnica e roadmap de variáveis exógenas (solicitado por Humberto).

## Log

- `2026-05-28` **[user]** Questionou se fórmula aderência = 1 − MAPE fazia sentido → confirmado e refinado
- `2026-05-28` **[maestro]** Substituiu `_aderencia()` (binário ±10%) por `_assertividade()` (1−MAPE contínuo)
  - `_assertividade(real, plano, base)` → Σ|R−P| / Σbase, retorna % 0–100
  - `_assertividade_semana(r, p, base)` → versão escalar para célula de tabela
  - Acumulação ponderada (Σ erros absolutos / Σ base), não média simples das semanas
- `2026-05-28` **[user]** Pediu toggle para escolher base de cálculo (Real ou Plano)
  - Implementado como `st.selectbox("Base do cálculo de Assertividade", ...)` nos filtros
  - `base_calc: str = "real" | "plano"` propagado para `_calc()`, `_assertividade()`, `_hist_assertividade()`
- `2026-05-28` **[maestro]** Redesign estrutural da página (v4):
  - [1] Header + Banner + 4 KPI cards (Assertividade S&OP, S&OE, GAP S&OP, GAP S&OE)
  - [2] Gráfico linha principal: 12 hist + 8 futuras, separador "hoje →", vrect fundo futuro
  - [3] Tabela agregada compacta (sem quebra por linha)
  - [4/5] Expanders: detalhe por linha de produto (S&OP / S&OE)
  - [6] Glossário
- `2026-05-28` **[runtime]** KeyError: 'wmape' na linha 1129 — `_calc()` atualizado mas call sites não
  - Fix: `_banner_status(m_ref["assertividade"], m_ref["bias"])`
  - Fix: assinatura `_banner_status(assertividade, bias)` + usa mape=100−assertividade internamente
  - Fix: `_hist_wmape` → `_hist_assertividade`, sparklines passam valores diretos (sem inversão 100-w)
- `2026-05-28` **[user/Humberto]** Solicitou roadmap de variáveis exógenas (salvo em long-term como PRIORIDADE ALTA)
- `2026-05-28` **[maestro]** Varredura final do código — dívida técnica identificada (ver Discovered Issues no long-term)
- `2026-05-29` **[user]** Identificou bug crítico: cálculo de assertividade sobre dados já agregados causava cancelamento de erros opostos entre linhas/gerências na mesma semana
- `2026-05-29` **[maestro]** Correção granular em `assertividade_plano.py`:
  - Adicionou constante `_GRP_PLANO = ["ano", "mes", "semana_mes", "linha", "gerencia"]`
  - Adicionou helper `_agrupar_nivel_plano(df, *cols)` — agrupa ao menor nível de planejamento antes de qualquer cálculo de erro
  - `_calc()`: chama `_agrupar_nivel_plano()` antes de extrair `r, p` para `_assertividade()`
  - `_render_tabela_agregada()`: por semana e coluna Σ usam acumuladores de DFs granulares (`grp_sop`, `grp_soe`) → `pd.concat` → `_assertividade()`
  - `_render_detalhe_linha()`: mesmo padrão — `grp_buf` acumula DFs granulares, Σ faz concat
  - `_hist_assertividade()`: chama `_agrupar_nivel_plano()` antes de `_assertividade()`
  - `_assertividade_semana()` tornou-se dead code (não é mais chamada)

## Dívida Técnica Identificada (não corrigida nesta sessão)

1. `_wmape()` (linha 116) — dead code, nunca chamada após refactor
2. `_TH_WMAPE = (10.0, 20.0)` (linha 40) — constante órfã, não utilizada
3. `_GLOSSARIO["WMAPE"]` e `_GLOSSARIO["Aderência"]` — nomenclatura antiga; KPI cards usam tooltip `_GLOSSARIO["Aderência"]` mas o card agora é "Assertividade"
4. Comentário linha 1134: `# Sparklines: WMAPE histórico` → deveria ser `Assertividade histórica`
5. `_assertividade_semana()` — virou dead code após correção granular (2026-05-29)
6. **Página não foi testada em execução** após a correção granular — encerrada antes de confirmar

## Constantes Atuais (assertividade_plano.py v4)

```python
N_HIST   = 12   # semanas históricas
N_FUTURO = 8    # semanas futuras
N_CALIB  = 4    # semanas para GAP projetado
```

## Próximos Passos Sugeridos

1. **[URGENTE]** Rodar `ATUALIZAR_E_RODAR.bat` para confirmar que a aba carrega sem erros após correção granular
2. **[LIMPEZA]** Remover dead code: `_wmape()`, `_assertividade_semana()`, `_TH_WMAPE`, atualizar `_GLOSSARIO`, corrigir comentário linha 1134
3. **[ROADMAP - ALTA PRIORIDADE]** Variáveis exógenas no Demand Sensing (ver long-term)
