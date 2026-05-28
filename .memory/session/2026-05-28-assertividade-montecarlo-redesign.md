# Session — Assertividade + Monte Carlo Redesign

## Status

done

## Last Active

2026-05-28

## Current Task

Redesign completo da página de Assertividade + implementação do Monte Carlo retroativo no Demand Sensing.

## Log

- `2026-05-28 09:00` **[user]** Solicitou Monte Carlo retroativo: ver realizado vs faixa de confiança das últimas 8 semanas
- `2026-05-28 09:05` **[maestro]** Implementou _monte_carlo_retroativo() em demand_sensing.py — para cada semana histórica usa só dados anteriores a ela
- `2026-05-28 09:10` **[maestro]** Estendeu _render_monte_carlo() com parâmetros semanas_hist/mc_hist/realizados_hist; adicionou faixa cinza histórica + linha realizado + separador "hoje →"
- `2026-05-28 09:20` **[maestro]** Corrigido TypeError: add_vline() falha em eixos categóricos → substituído por add_shape() + add_annotation()
- `2026-05-28 09:25` **[user]** Solicitou 12 semanas históricas (era 8) e 8 semanas futuras (N_FUTURO já era 8)
- `2026-05-28 09:30` **[maestro]** n_hist=12, _semanas_futuras() reescrita para iterar meses sucessivos até completar N semanas
- `2026-05-28 10:00` **[user]** Acionou redesign completo da página de Assertividade com 3 frentes: UI/CSS, dados, refatoração
- `2026-05-28 10:05` **[maestro]** Disparou Agente 1 (CSS/UX) e Agente 2 (Data) em paralelo; Agente 3 (Refactor) em sequência
- `2026-05-28 10:10` **[agente-css]** Corrigiu overflow Pareto (tickangle=-45, margem dinâmica), Desvio por Linha (margem esquerda proporcional), CSS multiselect com scroll interno
- `2026-05-28 10:15` **[agente-data]** Refatorou _render_tabela(): calibração ignora semanas zeradas, Int64, alinhamento monospace, export Excel corrigido
- `2026-05-28 10:20` **[agente-refactor]** Reestruturou KPI cards em st.columns(4, gap="small"): Assertividade S&OP % | Assertividade S&OE % | GAP S&OP (t) | GAP S&OE (t)
- `2026-05-28 10:25` **[maestro]** _secao() padronizada com linha divisória flex + subtítulo descritivo; captions redundantes removidos
- `2026-05-28 10:30` **[user]** Solicitou checkpoint e prompt de onboarding para próximo chat
- `2026-05-28 10:35` **[maestro]** Criou .memory/long-term.md, session file e ONBOARDING_PROXIMO_CHAT.md
