# Long-Term Memory — S&OE Inteligência Comercial

---

## Preferences

- Usuário prefere push manual e explícito: nunca subir código sem ele dizer "faz o push" ou equivalente
- Usuário prefere bat files 100% ASCII (sem unicode box chars como ╔══) para evitar erros de encoding no CMD
- Fonte de dados mudou: antes Databricks (bloqueado), agora Power BI. Dados chegam via CSV mensal `vendas_soe_mes_YYYY-MM.csv` em `data/raw/`. Contagem de linhas menor que Databricks (consolidado/deduplicado no Power BI) é comportamento esperado.
- Usuário prefere dados no Google Drive + leitura via st.secrets[gdrive], nunca parquets em repositório público
- Usuário prefere respostas diretas sem recapitular o que foi feito — vai direto ao ponto
- Usuário prefere que o Maestro orquestre agentes especializados em paralelo quando as zonas de edição não se sobrepõem
- Usuário exige que o Maestro siga o fluxo completo de agentes: boot sequence → session memory → Contextualizer (se sem .context.md) → Architect → Reviewer adversarial → Coder → Reviewer de código. Não pular etapas mesmo para tarefas aparentemente simples.
- Usuário usa o apelido "Maestro" para se referir ao agente principal
- Usuário valoriza dashboards com storytelling: Situação → Diagnóstico → Causa → Ação → Detalhe

## Feedback

- Multiselect com tags empilhadas empurra conteúdo para baixo — preferência por scroll interno ou contador "X selecionados"
- Tabela com decimais flutuantes (4 casas) causa confusão — obrigatório inteiro ou 1 casa decimal fixa alinhada à direita
- Monte Carlo retroativo é valioso: usuário quer ver realizado vs faixa de confiança das últimas 12 semanas
- KPIs devem comparar S&OP vs S&OE lado a lado, não apenas um plano de referência
- Rótulos de eixo cortados são inaceitáveis — margens dinâmicas obrigatórias

## Learned Rules

- NUNCA versionar: data/raw/, data/processed/, .streamlit/secrets.toml, credentials_gdrive.json, token_gdrive.json
- Parquets contêm dados de clientes — NUNCA subir para HF Spaces ou GitHub
- Dados chegam ao HF Spaces via Google Drive (st.secrets[gdrive]) — o Space lê do Drive, não do repo
- FAZER_PUSH.bat sobe apenas código: git push origin (GitHub) + git push hf main --force (HF Spaces)
- add_vline() do Plotly falha em eixos categóricos — usar add_shape() + add_annotation() separados
- _semanas_futuras() deve iterar meses sucessivos até completar N semanas, não parar no próximo mês
- Cálculo de calibração deve ignorar semanas com vol_ton == 0 (semana futura) no divisor
- Int64 do pandas causa TypeError no openpyxl — converter com astype(object).where(notna()) antes de to_excel
- Agentes paralelos só são seguros quando as zonas de edição (funções alvo) não se sobrepõem no mesmo arquivo
- Quando um agente cai sem handoff limpo (ex: erro de socket), SEMPRE verificar o estado real dos arquivos antes de prosseguir — pode ter deixado o trabalho num estado intermediário quebrado. Não confiar só na ausência de notificação.

## ⚠️ PRIORIDADE ALTA — Roadmap (solicitado por Humberto, gerente)

### Variáveis Exógenas no Demand Sensing
**Problema:** O modelo atual é endógeno — aprende padrões históricos de volume, mas não captura
sinais de mercado que explicam por que um cliente que *pode* comprar *não* compra no período.
Exemplos de fatores exógenos relevantes:
- Especulação de redução de preço do aço → cliente adia compra esperando queda
- Cenário macro (câmbio, juros, SELIC) → comprador congela capex
- Estoque alto no cliente → churn temporário sem sinal nos dados históricos
- Crise setorial (construção civil, agro) → demanda sistematicamente abaixo do plano

**O que implementar:**
1. Estrutura de input para variáveis exógenas (CSV/planilha ou widget no dashboard)
2. Incorporação no Monte Carlo: ajuste dos parâmetros de distribuição por cenário
3. Sugestão de variáveis-proxy disponíveis publicamente (IPCA, PMC IBGE, preço do minério, câmbio BRL/USD)
4. Modo "e se": simular impacto de um choque exógeno na faixa de confiança

**Referência técnica:** SARIMAX, Prophet com regressores externos, ou XGBoost com features de séries temporais — a escolha depende da frequência dos dados e do volume de histórico disponível.

---

## Discovered Issues

- `_semanas_futuras()` original só cobria mês atual + próximo mês — corrigido para loop multi-mês
- Tabela detalhada exportava Int64 para Excel sem conversão, causando TypeError no openpyxl
- **[RESOLVIDO 2026-05-30]** Dívida técnica em `assertividade_plano.py`: dead code já estava limpo. Página testada com dados reais: S&OP 46.3% | S&OE 42.3% mai/2026.
- `tests/test_integracao.py` linha 19: `from utils.filters import apply_filters` — arquivo `app/utils/filters.py` não existe. Tests vão falhar com ImportError.
- `scripts/sync_vault.py`: path hardcoded `D:/brain_organizer/...` — não portável.
- `src/` contém 4 arquivos Python completamente vazios (features.py, modelo.py, ritmo.py, exporta_lista.py): dead code (`_wmape`, `_TH_WMAPE`, `_assertividade_semana`), glossário antigo — tudo já estava limpo no arquivo. Página testada com dados reais: S&OP 46.3% | S&OE 42.3% mai/2026. Todos os call sites de `_agrupar_nivel_plano` verificados.
- **[corrigido — sessão 2026-05-29]** Cálculo de assertividade estava sendo feito sobre dados já agregados (total semanal), causando cancelamento de erros opostos. Corrigido: `|erro|` agora calculado no nível semana × linha × gerência via `_agrupar_nivel_plano()` em todos os pontos de cálculo.

## Learned Rules (continuação)

- Assertividade = 1 − MAPE (contínuo, 0–100%), **não** binário ±10%
- Acumulação de assertividade deve ser ponderada por volume: Σ|R−P| / Σbase — não média simples das semanas
- `_calc()` retorna `{assertividade, bias, gap}` — não mais `wmape`, `aderencia`
- KPI tooltip deve apontar para chave correta no `_GLOSSARIO` (bug pendente: ainda aponta para "Aderência")
- Após refatorar uma função que retorna dict, varrer **todos** os call sites antes de fechar PR
- **`|erro|` deve ser calculado no menor nível de planejamento (semana × linha × gerência), depois somado** — nunca sobre dados já agregados. Agregar antes de calcular `|R−P|` causa cancelamento de erros opostos (ex: linha A +100t e B −100t → total 0 → erro 0, mascarando 200t de desvio real)
- `_GRP_PLANO = ["ano", "mes", "semana_mes", "linha", "gerencia"]` é a chave canônica de agrupamento para cálculo de assertividade em `assertividade_plano.py`
- `_agrupar_nivel_plano(df, *cols)` é o helper que garante granularidade correta antes de `_assertividade()`
- **HC-02/HC-T4 (parecer Metodológico 2026-05-30): NÃO unificar o "bias" do Demand Sensing com o Bias canônico.** São objetos estatísticos distintos: (a) Bias EXIBIDO = razão-de-somas `Σ(P−R)/Σbase×100`, sinal P−R (positivo=plano acima do real), HC-02, em todas as abas; (b) termo que centra o ruído do Monte Carlo = média-de-razões `mean((R−P)/P)`, sinal R−P, NÃO pode chamar-se "bias" (usar `mc_drift`/`erro_rel_medio`), NÃO pode ler `metricas['bias']`. Reunificar reintroduz bug de forecast. Só a grandeza HC-02 usa o rótulo público "Bias" na UI.
- Corrigir o Bias exibido em `demand_sensing.py` INVERTE o sinal atual (hoje R−P) → reauditar narrativas (`:261-286`, `:381-388`, `:697-747`, `:789-800`) no mesmo PR, senão over/underforecasting trocam de lado na tela.

## Project Notes

- Stack: Streamlit + Plotly + pandas, hospedado em HF Spaces, dados no Google Drive
- 5 abas: Visão Geral, Plano Comercial, Demand Sensing, Dashboard UF, Assertividade do Plano
- Monte Carlo: N_SIM=1000, SEED=42, N_PACE=8, N_FUTURO=8, N_HIST=16
- Monte Carlo retroativo: últimas 12 semanas históricas, para cada semana usa só dados ANTERIORES a ela
- Semana técnica (TW): calculada por calendar_tw.py, label formato "TW10B Mar/2026"
- Atualização de dados: ATUALIZAR_E_RODAR.bat → incrementa_vendas_diario.py → atualiza_dados.py → dashboard
- Deploy de código: FAZER_PUSH.bat → GitHub (origin) + HF Spaces (hf remote, force push)
- Deploy de dados: usuário sobe parquets manualmente para Google Drive via SUBIR_DADOS_GDRIVE.bat
- Assertividade do Plano v4: 12 hist + 8 futuras, toggle base Real/Plano, gráfico principal sempre visível, tabela agregada + expanders por linha
- Gerências definidas em config.py via GERENCIA_CONFIG com familias_override e regioes
- Personas disponíveis: maestro, architect, coder, reviewer, contextualizer (em .agents/personas/)
- Skills disponíveis: analise-desvios-vendas, pptx, docx, xlsx, pdf, xlsx, verify, run, code-review, security-review, init (em .addy-skills/ e sistema)
