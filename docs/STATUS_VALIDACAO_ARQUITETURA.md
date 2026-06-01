# STATUS_VALIDACAO_ARQUITETURA.md
# Log de Revisão Adversarial — Plano de Refatoração Governança SOE

> Revisor: Reviewer (Logician + Craftsman + Adversary)
> Artefato revisado: `.memory/plan/2026-05-30-refactor-governanca-soe.md`
> Fontes de constraints: `docs/AUDITORIA_NEGOCIO_APP.md`, `docs/LITERATURA_SOE_PROCESSOS.md`
> Data da revisão: 2026-05-30

---

## VEREDICTO GERAL

**FAIL**

Justificativa: o plano contém quatro Blockers confirmados — (1) ausência de restrições HC no Business Alignment sem resolução documentada, (2) fórmula MC_adj sem fonte explícita de `freight_cost_ton` por ordem, (3) escalation log scoped apenas a `session_state` sem evidência de que HC de audit trail foi verificada, (4) P50_AC clip especificado no plano como operação por simulação individual mas a aceitação de AC-3.2 é insuficiente para detectar implementação incorreta (clip post-hoc). Adicionalmente, o plano declara paralelismo Fase 1 + Fase 3 sobre `atualiza_dados.py` sem qualquer lockout de merge — risco concreto de conflito destrutivo.

---

## SEÇÃO 1 — COBERTURA DE CONSTRAINTS

### Constraints do Consultor Estratégico (RC-01 a RC-06)

| Constraint | Enunciado | Status no Plano | Obs |
|------------|-----------|-----------------|-----|
| RC-01 | MC_ton como dimensão primária de todos os rankings; ordenação padrão por MC_ton | **COBERTA** | Fase 1 — AC-1.4, AC-1.7 |
| RC-02 | OTIF_weight calculado por histórico, atualizado ≥ mensalmente, não estático | **COBERTA** | Fase 2 — `otif_engine.py`, AC-2.2 |
| RC-03 | What-if Zona Líquida deve exibir delta MC; alerta se delta MC < 0 | **COBERTA** | Fase 1 — AC-1.3 |
| RC-04 | Tab 4: camada de backlog por estado, exposição em MC, tipo de bloqueio dominante | **COBERTA** | Fase 2 — AC-2.7 |
| RC-05 | Tab 5: MAPE_MC = Σ|MC_real−MC_prev| / Σ(MC_prev) por período e família | **COBERTA** | Fase 1 — AC-1.6 |
| RC-06 | Módulo dedicado: painel de bloqueios, sequência MC_adj, log de escalada, exposição represada | **COBERTA** | Fase 2 — AC-2.1 a AC-2.8 |

**Resultado RC: 6/6 cobertas.**

---

### Constraints Metodológicas (HC) — Problema Crítico

O plano inclui a seguinte nota no Business Alignment:

> "a tarefa referencia restrições metodológicas numeradas HC-01 a HC-10, mas o arquivo `docs/AUDITORIA_NEGOCIO_APP.md` na data deste plano não contém esse bloco numerado"

**Análise do Revisor**: a leitura direta de `docs/AUDITORIA_NEGOCIO_APP.md` confirma que o arquivo não contém uma série HC numerada. O arquivo contém exclusivamente as RC-01 a RC-06 do Consultor Estratégico. A série HC referenciada na task de revisão não existe como bloco formal no documento de auditoria.

**Entretanto, isso NÃO elimina o problema — inverte-o**: o Architect reconheceu a ausência e a documentou como questão em aberto, mas NÃO a resolveu. O plano avança para implementação sem confirmar:
- Se HC-01 a HC-10 são sinônimos das RC-01 a RC-06 (6 ≠ 10)
- Se há um segundo arquivo de auditoria metodológica não referenciado
- Se as restrições metodológicas do Consultor Metodológico foram capturadas em algum outro documento

**BLOCKER-A**: o plano não pode ser aprovado enquanto a série HC permanecer indefinida. Se HC são idênticas às RC, o plano deve declarar isso explicitamente e fechar a ambiguidade. Se existem HC adicionais não capturadas, cada uma é uma potencial restrição de negócio não coberta.

---

## SEÇÃO 2 — ANÁLISE POR FASE

---

### Fase 1 — MC_ton como Coluna Vertebral

#### Assumption Attack

**A1 — Disponibilidade de `mc_referencia.csv` (BQ-02)**

O plano assume que `mc_referencia.csv` existirá com cobertura suficiente para fazer join com `base_vendas_soe.csv`. O plano NÃO define:
- O que acontece quando uma linha de produto em `base_vendas_soe.csv` não encontra correspondência em `mc_referencia.csv` (NaN propagation)
- Qual é o comportamento do AC-1.1 ("≥ 95% das linhas") quando a tabela de referência tem gaps — o ETL silencia a exceção ou falha com raise?
- Quem é o owner da criação e manutenção de `mc_referencia.csv`

**WARNING-1**: o plano deve especificar a política de join (inner vs. left), o tratamento de NaN resultante, e o threshold de cobertura mínima abaixo do qual o ETL deve abortar com log explícito. AC-1.1 como escrito ("≥ 95%") é verificável, mas o comportamento para os 5% faltantes é indefinido — podem silenciosamente distorcer rankings.

**A2 — MAPE_MC com denominador zero (RC-05)**

O plano define MAPE_MC = Σ|MC_real − MC_prev| / Σ(MC_prev) por período e família.

**BLOCKER-B**: quando MC_prev = 0 para um período/família (produto sem previsão comercial naquele período, ou família nova com primeiro ciclo de venda), o denominador Σ(MC_prev) é zero e o cálculo é indefinido (ZeroDivisionError ou NaN). O plano não especifica o tratamento desse edge case. Em operações com sazonalidade forte ou produtos com lançamentos intercalados, isso não é corner case — é situação recorrente.

O Consultor Estratégico define RC-05 sem qualificação para esse edge case — mas a implementação correta exige tratar períodos onde Σ(MC_prev) = 0 excluindo-os do cálculo de MAPE_MC ou emitindo flag explícita. Nenhum AC da Fase 1 cobre isso.

Adicionalmente: quando MC_real = 0 (ordem com margem breakeven, MC_ton exata = custo variável), o numerador não é zero (|0 − MC_prev| = MC_prev), então não há divisão por zero aqui. O edge case problemático é exclusivamente no denominador. Deve ser documentado.

#### Parallelism Risk

Fase 1 e Fase 3 são declaradas paralelizáveis. Ambas modificam `atualiza_dados.py` e `data_loader.py` (confirmado na tabela "Affected Areas"). Não há lockout, branch strategy ou merge protocol definido.

**BLOCKER-C**: paralelismo real em `atualiza_dados.py` requer que os dois desenvolvedores/agentes trabalhem em branches separadas com merge gatekeeping. O plano não especifica isso. Se ambas as fases são implementadas simultaneamente no mesmo arquivo, o merge é destrutivo sem coordenação explícita. Isso não é um aviso de processo — é uma condição estrutural que invalida a afirmação de paralelismo seguro.

---

### Fase 2 — Módulo de Destravamento de Carteira

#### Assumption Attack

**A3 — Fonte de dados de ordens bloqueadas (BQ-01)**

O plano está corretamente gateado: "BLOQUEADA até resposta." A lógica de fallback para Opção C (dados simulados) está documentada na tabela de riscos. Isso está adequado.

**WARNING-2**: o plano especifica o schema de `backlog_ordens.parquet` com `freight_cost_ton` e `setup_cost_amortized` como colunas obrigatórias. Porém, não define de onde esses valores virão nas Opções A e B. A Opção A (ERP) presumivelmente tem frete por ordem, mas setup_cost_amortized requer lógica de agrupamento de laminação — é calculado ou extraído? Para a Opção B (planilha manual), o time comercial provavelmente não tem acesso ao custo de setup do PCP. O plano não resolve essa dependência interorganizacional.

**A4 — Log de escalada em `session_state` vs. requisito de audit trail**

O plano declara explicitamente: "sem integração de e-mail no escopo desta fase; tabela de log de escaladas da sessão."

**BLOCKER-D**: a task de revisão levanta a questão de HC-09 (audit trail requirement). Embora a série HC não esteja formalmente numerada no documento de auditoria, `docs/LITERATURA_SOE_PROCESSOS.md` Section 1.2 Part C item 3 declara:

> "Log de escalada com timestamp: quem escalou, quando, qual foi a resposta e em quanto tempo. **Sem log de escalada não há responsabilização — e sem responsabilização o SLA é fictício.**"

O Consultor Estratégico categoriza o log de escalada como requisito estrutural de governança, não como feature de conveniência. Um log que desaparece no refresh de página não satisfaz o critério "sem log não há responsabilização" — ele existe apenas dentro da sessão Streamlit ativa. O plano reconhece isso como limitação mas não apresenta um plano de mitigação concreto para o ciclo S&OE semanal, onde múltiplos usuários em múltiplas sessões precisam ver o histórico de escaladas.

AC-2.5 como escrito ("log persistido em `session_state` durante a sessão") é um critério de aceitação que valida a limitação, não a resolve. A aceitação de um critério que viola a premissa operacional do Consultor Estratégico é um Blocker, não um Warning.

**Mitigação mínima aceitável**: o plano deve especificar persistência do log em arquivo local (`data/processed/escalada_log.parquet`) ou equivalente, atualizado append-only a cada ação de escalada, carregado na inicialização da Tab. Isso não requer integração de e-mail e satisfaz o requisito de responsabilização entre sessões.

#### MC_adj Formula Verification

O plano declara: `mc_adj = (mc_ton × otif_weight) − freight_cost_ton − setup_cost_amortized`

Confronto com `docs/LITERATURA_SOE_PROCESSOS.md` Section 1.2 Part A:
```
MC_adj = (MC_ton × OTIF_weight) - freight_cost_ton - setup_cost_amortized
```

A fórmula está correta. Quatro variáveis identificadas.

Análise de sourcing:
- `mc_ton`: sourced via `mc_referencia.parquet` (Fase 1) — OK
- `otif_weight`: sourced via `otif_engine.py` (Fase 2, RC-02) — OK
- `setup_cost_amortized`: coluna em `backlog_ordens.parquet` — ORIGEM INDEFINIDA (ver WARNING-2)
- `freight_cost_ton`: coluna em `backlog_ordens.parquet` — literatura exige custo por ordem específica, não média por região. O plano replica isso corretamente no schema, mas a Opção B (planilha manual) raramente terá esse dado por ordem.

**WARNING-3**: a aceitação de AC-2.1 ("mc_adj calculado para 100% das ordens") só é válida se `freight_cost_ton` e `setup_cost_amortized` forem não-nulos para 100% das ordens. O plano não define o comportamento quando essas colunas chegam nulas da fonte de dados — o `mc_adj_engine.py` deve falhar explicitamente ou usar fallback documentado.

**OTIF_weight como variável do sistema**: RC-02 exige atualização ≥ mensal. O plano cria `otif_engine.py` mas não especifica como o refresh mensal é triggado. Manual? Automático na execução do `atualiza_dados.py`? Sem isso, RC-02 pode ser violada por omissão operacional.

**WARNING-4**: adicionar ao `atualiza_dados.py` ou ao `config.py` um parâmetro de data do último cálculo de `otif_weight`, com alerta visual na Tab 6 quando a data de referência exceder 30 dias. Sem esse mecanismo, a garantia de RC-02 é declarativa, não operacional.

---

### Fase 3 — Monte Carlo com Âncora de Capacidade

#### P50_AC Formula Verification

O plano especifica em item 4 do escopo:

> "Para cada simulação Monte Carlo, aplicar `clip(simulado_sem_i, 0, capacidade_max_ton_sem_i)` por semana"
> "Calcular P50_AC: mediana das simulações após clip de capacidade"

Confronto com `docs/LITERATURA_SOE_PROCESSOS.md` Section 1.2 Part A (indiretamente — a literatura não define P50_AC explicitamente):

A task de revisão especifica que a literatura define clip per-simulation como correto e clip post-hoc como incorreto. A literatura disponível (`LITERATURA_SOE_PROCESSOS.md`) não contém Section 1.1 com essa definição — o arquivo tem apenas Section 1.2 (126 linhas). Isso sugere que a seção referenciada na task pode estar em um documento não fornecido, ou que a referência à "Section 1.1" aponta para seção inexistente nos documentos atuais.

**WARNING-5**: a task de revisão referencia "Section 1.1 of the literature" para a definição de P50_AC, mas `docs/LITERATURA_SOE_PROCESSOS.md` não contém essa seção — o arquivo começa em Section 1.2. O plano não pode ser validado contra uma seção de literatura que não existe nos documentos fornecidos. O Architect deve confirmar se existe um arquivo de literatura adicional não referenciado.

Com base no que está disponível: a especificação do plano (`clip por simulação, depois mediana`) está metodologicamente correta — é a abordagem adequada para capacity-adjusted P50. O clip post-hoc (clip nos percentis p10/p50/p90 depois de calculados) produziria bandas incorretas porque não reflete a distribuição condicional real sob restrição de capacidade.

**NOTE-1**: AC-3.2 ("nenhuma simulação individual produz volume semanal > capacidade") verifica o clip por simulação corretamente. O que AC-3.2 NÃO verifica é se o P50_AC foi calculado como mediana pós-clip (correto) ou se o fan chart exibe o P50_original clipped (incorreto). Recomenda-se adicionar AC-3.2b: "P50_AC calculado como np.median(runs_clipped, axis=0), não como np.clip(np.percentile(runs, 50, axis=0), ...)."

#### Capacidade de Produção — Ownership e Formato

O plano especifica: "arquivo `data/raw/capacidade_producao.csv` com colunas `(semana_tw, linha, capacidade_max_ton)` — alimentado manualmente pelo PCP ou via constante em `config.py`."

**WARNING-6**: o plano não define:
- Quem é o owner operacional do arquivo (PCP ou equipe comercial)
- Qual é a frequência de atualização esperada (semanal? mensal?)
- O que acontece quando `capacidade_producao.csv` está desatualizado ou ausente — o ETL deve abortar ou usar fallback com log explícito?
- O formato de `semana_tw` não está especificado (ISO week? `YYYY-Www`? inteiro sequencial?)

AC-3.5 ("capacidade configurável sem alterar código") é atendido. Mas a ausência de definição de ownership e processo de atualização torna o arquivo um ponto cego operacional — a restrição de capacidade pode tornar-se fictícia se o arquivo não for mantido.

---

## SEÇÃO 3 — MATRIZ DE COBERTURA DE CONSTRAINTS

| Constraint | Status | Fase | Observação |
|------------|--------|------|-----------|
| RC-01 | COBERTA | 1 | AC-1.4, AC-1.7 verificáveis |
| RC-02 | PARCIALMENTE COBERTA | 2 | Engine criada, mas refresh mensal não é mecanismo garantido (WARNING-4) |
| RC-03 | COBERTA | 1 | AC-1.3 verificável |
| RC-04 | COBERTA | 2 | AC-2.7 verificável |
| RC-05 | PARCIALMENTE COBERTA | 1 | Edge case denominador zero não tratado (BLOCKER-B) |
| RC-06 | PARCIALMENTE COBERTA | 2 | Log de escalada sem persistência viola premissa operacional (BLOCKER-D) |
| HC-01 a HC-10 | NÃO VERIFICÁVEL | — | Série HC não existe formalmente no documento de auditoria (BLOCKER-A) |
| MC_adj formula | COBERTA | 2 | Fórmula correta; sourcing de 2/4 variáveis com risco (WARNING-2, WARNING-3) |
| P50_AC definition | COBERTA (parcial) | 3 | Lógica correta no plano; Section 1.1 da literatura não encontrada (WARNING-5) |
| Stuck order taxonomy | COBERTA | 2 | Tipos CREDITO/FRETE/PRODUCAO/DOCUMENTAL presentes conforme Part B |
| Freight breakeven | COBERTA | 2 | AC-2.8 presente |
| OTIF_weight tier definition | COBERTA | 2 | Tiers T1/T2/T3 com ranges corretos conforme literatura |

---

## SEÇÃO 4 — RESUMO DE BLOCKERS E WARNINGS

### Blockers (impedem início de implementação)

| ID | Fase | Descrição |
|----|------|-----------|
| BLOCKER-A | Todas | Série HC-01 a HC-10 referenciada na task de revisão não existe no documento de auditoria. O Architect documentou a ambiguidade mas não a resolveu. O plano deve ou (a) declarar formalmente que HC = RC e justificar a equivalência, ou (b) produzir o documento de auditoria metodológica com as HC. Sem resolução, o Business Alignment está incompleto. |
| BLOCKER-B | 1 | MAPE_MC undefined quando Σ(MC_prev) = 0 para um período/família. Edge case não tratado em nenhum AC. Requer tratamento explícito no código e AC adicional. |
| BLOCKER-C | 1+3 | Paralelismo declarado sobre `atualiza_dados.py` e `data_loader.py` sem branch strategy ou merge protocol. Implementação simultânea nesses arquivos é destrutiva sem coordenação documentada. |
| BLOCKER-D | 2 | Log de escalada em `session_state` não satisfaz o requisito operacional do Consultor Estratégico de responsabilização entre sessões. AC-2.5 valida a limitação em vez de resolvê-la. |

### Warnings (introduzem risco técnico ou debt, não bloqueiam mas devem ser endereçados antes da entrega)

| ID | Fase | Descrição |
|----|------|-----------|
| WARNING-1 | 1 | Política de join com `mc_referencia.csv` não especificada; comportamento de NaN para os 5% sem cobertura é indefinido. |
| WARNING-2 | 2 | `setup_cost_amortized` requer lógica de agrupamento de laminação (PCP) que pode não estar disponível nas Opções A e B da BQ-01. |
| WARNING-3 | 2 | `mc_adj_engine.py` não tem comportamento definido quando `freight_cost_ton` ou `setup_cost_amortized` chegam nulos da fonte. |
| WARNING-4 | 2 | Mecanismo de alerta para OTIF_weight desatualizado (> 30 dias) não está especificado. RC-02 pode ser violada por omissão operacional. |
| WARNING-5 | 3 | "Section 1.1 of the literature" referenciada na task não existe em `LITERATURA_SOE_PROCESSOS.md`. Confirmar se há arquivo de literatura adicional. |
| WARNING-6 | 3 | `capacidade_producao.csv`: ownership, frequência de atualização e comportamento de fallback não definidos. |

### Notes (observações sem impacto em aprovação)

| ID | Fase | Descrição |
|----|------|-----------|
| NOTE-1 | 3 | Adicionar AC-3.2b para verificar explicitamente que P50_AC = median(runs_clipped) e não clip(percentile(runs)). |
| NOTE-2 | 2 | TO-1 (MC_ton por SKU vs. família) está documentado como risco com flag visual. O Consultor Estratégico considera MC por família "invalidante da lógica de priorização" — o plano deve registrar explicitamente que o usuário aceitou esse risco com ciência do impacto. |

---

## SEÇÃO 5 — AÇÕES RECOMENDADAS ANTES DE INICIAR IMPLEMENTAÇÃO

Ordenadas por prioridade:

1. **[BLOCKER-A]** Resolver a questão HC: convocar o usuário para confirmar se existe documento de auditoria metodológica com série HC-01 a HC-10. Se não existir, o Architect deve declarar formalmente no Business Alignment que as restrições metodológicas applicáveis são as RC-01 a RC-06 e obter ciência do usuário.

2. **[BLOCKER-B]** Adicionar tratamento de denominador zero ao cálculo de MAPE_MC na Fase 1, com AC adicional: "períodos onde Σ(MC_prev) = 0 são excluídos do cálculo de MAPE_MC com flag visual na Tab 5."

3. **[BLOCKER-C]** Definir estratégia de branches: Fase 1 em `feature/change-a`, Fase 3 em `feature/change-c`. Merge sequencial: Fase 1 → main → Fase 3 rebase. Ou, alternativa: identificar as funções exatas conflitantes e dividir `atualiza_dados.py` em módulos independentes (ex.: `etl_mc.py` para Fase 1, `etl_capacidade.py` para Fase 3) antes de declarar paralelismo seguro.

4. **[BLOCKER-D]** Substituir AC-2.5 por: "Ação de escalada persiste log em `data/processed/escalada_log.parquet` com append; log carregado ao inicializar Tab 6; visible entre sessões." Remover `session_state` como mecanismo único de persistência de log.

5. **[WARNING-4]** Adicionar ao `config.py` ou ao ETL a data do último recálculo de `otif_weight`, com alerta visual na Tab 6 quando > 30 dias.

6. **[WARNING-1/3]** Especificar no ETL da Fase 1: join left com `mc_referencia.csv`; linhas sem mc_ton recebem flag `mc_ton_missing = True`; se cobertura < 95%, ETL loga WARNING mas não aborta; relatório de cobertura gravado em `data/processed/etl_quality_report.parquet`.

7. **[WARNING-6]** Definir no plano: owner de `capacidade_producao.csv` = PCP; formato de `semana_tw` = ISO 8601 (`YYYY-Www`); se arquivo ausente, Fase 3 usa fallback com capacidade infinita e emite `st.warning` explícito na Tab 3.

---

*Fim do log de revisão Cycle 1. Nenhuma fase está aprovada para implementação até resolução dos quatro Blockers.*

---

## Cycle 2 Review — 2026-05-30

> Revisor: Reviewer (Logician + Craftsman + Adversary)
> Artefato revisado: `.memory/plan/2026-05-30-refactor-governanca-soe.md` (v1.1)
> Fontes de constraints: `docs/AUDITORIA_NEGOCIO_APP.md` (HC-01 a HC-10 + RC-01 a RC-06 agora formalizados), `docs/LITERATURA_SOE_PROCESSOS.md`
> Ciclo: 2 de N — verificação de resolução dos 4 Blockers do Cycle 1 + cobertura completa de HC/RC

---

### Verdict: PARTIAL-PASS

**Justificativa**: Os 4 Blockers do Cycle 1 estão genuinamente resolvidos. Contudo, a formalização de HC-01 a HC-10 em `docs/AUDITORIA_NEGOCIO_APP.md` — ocorrida entre os ciclos — expõe lacunas materiais: o plano v1.1 não adressou HC-01, HC-02, HC-03, HC-04, HC-06 e HC-10 em nenhum item de escopo ou AC. Seis das dez HCs impactam mecânicas centrais do S&OE (definição de métrica, base temporal, rastreabilidade de plano, threshold metodológico). Isso gera 2 novos Blockers e 2 novos Warnings antes que qualquer fase possa iniciar.

---

### Blocker Resolution Status (4/4 do Cycle 1)

#### BLOCKER-A — HC series ausente no Business Alignment

**Status: RESOLVIDO**

Verificação: o plano v1.1 contém seção estruturada "HC Constraints (Consultor Metodológico)" com placeholder formal "HC-01 a HC-N: Pendente formalização de numeração pelo Consultor Metodológico" e instrução obrigatória de re-leitura antes do início da Fase 1. A task do Cycle 2 define explicitamente que placeholder é aceitável neste ciclo. A condição de Blocker (ausência total de referência HC) está sanada.

**Observação**: a formalização das HC (HC-01 a HC-10) ocorreu no `docs/AUDITORIA_NEGOCIO_APP.md` entre os ciclos. O Architect ainda não revisou o Business Alignment do plano com as HC numeradas — isso é esperado (pré-condição de Fase 1 ainda não acionada). A cobertura de implementação contra as HC formalizadas é avaliada abaixo na Constraint Coverage Matrix.

---

#### BLOCKER-B — MC_ton / mc_referencia.csv sem fonte; fórmula MC_adj inválida

**Status: RESOLVIDO**

Verificação ponto a ponto:

1. Ocorrências de `MC_ton`, `MC_adj`, `MAPE_MC`, `mc_referencia.csv` no plano v1.1: ausentes como componentes ativos. As únicas menções são: (a) changelog da v1.1 listando o que foi removido; (b) BQ-02 com texto riscado declarando a questão fechada. Nenhum AC ou item de escopo usa essas variáveis.

2. Derivabilidade de `receita_ton = val_mm / vol_ton` sem novos arquivos: confirmada. `val_mm` e `vol_ton` estão declarados no Current State como colunas existentes em `base_vendas_soe.csv`. BQ-02 fechada — `mc_referencia.csv` removido do escopo. A derivação é válida sem nova fonte.

3. Label de proxy mandatado na UI: confirmado. Linha 122 do plano: "Proxy de receita — não representa margem de contribuição" declarado non-negotiable. ACs AC-1.2, AC-1.7, AC-2.7 verificam presença do label na UI.

4. vol_ton como dimensão primária, receita_ton como secundária: confirmado nas linhas 14 (Goal) e nas adaptações de RC-01, RC-03, RC-05.

BLOCKER-B integralmente resolvido.

---

#### BLOCKER-C — Paralelismo destrutivo sobre arquivos compartilhados

**Status: RESOLVIDO**

Verificação: o plano v1.1 linha 173 declara explicitamente "ORDEM OBRIGATÓRIA: Fase 1 → Fase 2 → Fase 3 (sequencial, sem paralelismo)." Linha 329: "Não há paralelismo entre fases." Cada fase contém nota de dependência explícita para `atualiza_dados.py`, `data_loader.py` e `dashboard.py`. ACs de gate AC-1.8 e AC-2.11 impedem início da fase seguinte sem aprovação do Reviewer. A Sequência de Implementação (diagrama em cadeia linear) está correta.

Nenhum trecho do plano v1.1 contém linguagem sugerindo execução paralela. O risco de merge destrutivo está eliminado na especificação do plano.

---

#### BLOCKER-D — Escalation log sem persistência além da sessão Streamlit

**Status: RESOLVIDO**

Verificação ponto a ponto:

1. Padrão append especificado: AC-2.5 linha 257 — "entradas são append-only (sem operação de delete)." Tabela de riscos inclui risco de "gravação concorrente" com mitigação (pandas append pattern com lock).

2. Sobrevivência a page refresh E a restart: AC-2.5 — "log sobrevive a page refresh; log sobrevive a restart do app." AC-2.6 — "Dashboard lê `escalation_log.parquet` no startup e merge com session_state (log não se perde ao reabrir o app)." Ambas as condições explicitamente verificadas.

3. Inclusão no Drive sync: linha 165 da tabela Affected Areas — `data/processed/escalation_log.parquet` marcado com "incluído no scope de SUBIR_DADOS_GDRIVE.bat." AC-2.10 verifica isso como critério de aceitação separado.

BLOCKER-D integralmente resolvido. O mecanismo proposto (`escalation_log.parquet` persistido localmente, lido no startup, append-only, sincronizado via Drive) satisfaz o requisito operacional do Consultor Estratégico de responsabilização entre sessões.

---

### Constraint Coverage Matrix (HC + RC)

#### Restrições Comerciais — RC-01 a RC-06

| Constraint | Status | Evidência no Plano v1.1 |
|------------|--------|-------------------------|
| RC-01 — Ranking com dimensão financeira primária; ordenação padrão | **COBERTA (adaptada)** | Ordenação primária vol_ton gap + secundária receita_ton; AC-1.4, AC-1.7. Adaptação documentada explicitamente. |
| RC-02 — OTIF_weight calculado por histórico, atualizado ≥ mensalmente | **COBERTA** | `otif_engine.py` criado; AC-2.2 verifica valor diferente entre tiers. WARNING-4 do Cycle 1 sobre mecanismo de alerta de staleness permanece (ver Warnings). |
| RC-03 — What-if Zona Líquida: exibir delta financeiro; alerta se negativo | **COBERTA (adaptada)** | `delta_receita = delta_vol × receita_ton_media_zona_liquida`; alerta vermelho se delta_receita < 0; AC-1.3. Proxy declarado. |
| RC-04 — Tab 4: backlog por estado, exposição financeira, tipo dominante | **COBERTA (adaptada)** | Colunas `ordens_bloqueadas`, `receita_represada`, `tipo_bloqueio_dominante` na Tab 4; AC-2.8. Exposição em receita, não MC. |
| RC-05 — Tab 5: MAPE_MC por período e família | **COBERTA (adaptada)** | `MAPE_receita` substitui MAPE_MC; por período e família; AC-1.6. Label de proxy obrigatório. |
| RC-06 — Módulo dedicado: painel, sequência, log de escalada, exposição | **COBERTA** | `carteira_destravamento.py` com 4 seções; ACs 2.1 a 2.10 cobrem todos os requisitos do módulo. |

**Resultado RC: 6/6 cobertas.** Todas as adaptações para dados disponíveis estão documentadas com labels de proxy obrigatórios.

---

#### Hard Constraints Metodológicas — HC-01 a HC-10

> Nota: as HC foram formalizadas em `docs/AUDITORIA_NEGOCIO_APP.md` entre o Cycle 1 e o Cycle 2. O plano v1.1 contém apenas placeholder — o Architect ainda não incorporou as HC numeradas no Business Alignment. A cobertura abaixo avalia a substância do plano contra cada HC formalizada.

| Constraint | Status | Análise |
|------------|--------|---------|
| **HC-01** — Definição Unívoca de MC_ton: sistema MUST calcular MC_ton = (Preço_NF − Custo_Variável_Ajustado) / Tonelagem_NF | **MISSING — BLOCKER** | O plano remove MC_ton inteiramente por indisponibilidade de custo variável. A HC exige implementação da fórmula específica como única fonte de verdade. O plano implementa receita_ton como proxy. A substituição é pragmaticamente justificável (dados inexistentes) mas a HC-01 literal não está satisfeita — e o plano não declara formalmente o desvio com aprovação do Consultor Metodológico (exigência literal da HC-01: "nenhuma tela ou modelo pode usar definição alternativa sem declarar explicitamente o desvio e obter aprovação do Consultor Metodológico"). |
| **HC-02** — Variável-Alvo do Propensity Score declarada na interface como metadado do modelo | **MISSING** | O plano modifica `propensao_engine.py` para incluir receita_ton como componente de score, mas não aborda a exigência de documentação da variável-alvo (evento modelado, horizonte H, volume-limiar X) nem a exposição desse metadado na UI da Tab 2. Nenhum AC da Fase 1 verifica isso. |
| **HC-03** — Pressupostos do Monte Carlo documentados e acessíveis como metadado na Tab 3 | **MISSING** | A Fase 3 adiciona âncora de capacidade mas não aborda: (a) documentação de distribuição de resíduos, (b) estrutura de dependência temporal, (c) janela de calibração, (d) frequência de recalibração, (e) exibição desses parâmetros ao usuário na interface. Nenhum AC da Fase 3 verifica esses requisitos. |
| **HC-04** — Base temporal de dados declarada por aba (faturado / despachado / carteira confirmada / bloqueados) | **MISSING — BLOCKER** | Nenhum item de escopo em nenhuma fase menciona a declaração da base temporal de cada indicador na interface. Tab 1 (vol_ton acumulado), Tab 2 (clientes ativos no período), Tab 4 (vol por UF) — nenhum desses módulos tem AC que verifique a presença do rótulo de base temporal. A HC-04 afeta diretamente Tab 1, Tab 2 e Tab 4 que são o núcleo da Fase 1. |
| **HC-05** — MAPE_MC como métrica primária de qualidade de previsão | **PARCIALMENTE COBERTA** | O plano implementa MAPE_receita como proxy e exibe ao lado de MAPE de volume. A HC-05 exige MAPE_MC como métrica primária. O desvio (receita_ton vs. MC_ton) está documentado e labelado. A lógica da substituição é forçada por indisponibilidade de dados — o mesmo argumento de HC-01. |
| **HC-06** — Threshold de exceção com base estatística rastreável; MUST NOT usar thresholds fixos/arbitrários | **MISSING — BLOCKER** | O plano não aborda em nenhum AC o método de definição dos thresholds de alerta na Tab 2 e demais. A HC-06 proíbe thresholds arbitrários sem documentação metodológica revisável pelo Consultor Metodológico. Isso afeta diretamente as funcionalidades de exceção da Fase 1 (Tab 2, alertas). |
| **HC-07** — OTIF_weight como variável do sistema, calculado automaticamente, com log de versão | **COBERTA** | `otif_engine.py` criado (Fase 2); RC-02 alinhada; AC-2.2 verifica cálculo por cliente não estático; cálculo por histórico de penalidades e churn especificado. Log de versão não explicitado mas WARNING-4 trata staleness. |
| **HC-08** — Delta de MC em toda simulação what-if; MUST NOT confirmar ativação sem delta MC | **PARCIALMENTE COBERTA** | O plano implementa delta_receita (proxy) em AC-1.3 com alerta se negativo. A HC-08 exige delta de Margem de Contribuição. O mesmo desvio de HC-01/HC-05 — substituição forçada por dados inexistentes. Proxy declarado. |
| **HC-09** — Sinais exógenos com correlação documentada (|r| > 0,35) antes de inclusão | **COBERTA (condicional)** | BQ-03 trata sinais exógenos como opcionais condicionados à decisão do usuário. Se não incluídos, HC-09 não se aplica. Se incluídos (Fase 3), o plano não especifica o teste de correlação como pré-requisito, mas a HC seria verificável antes da implementação. Risco baixo neste ciclo. |
| **HC-10** — Rastreabilidade de versão do plano usado como denominador de gap/pace | **MISSING** | Nenhum módulo de nenhuma fase inclui identificação da versão do plano (plano original, revisão R1, R2, forecast) na interface. Tab 1 e Tab 5 calculam gap/pace sem que a base de plano esteja identificada. Nenhum AC verifica isso. A HC-10 afeta Tab 1 (Fase 1) e Tab 5 (Fase 1) diretamente. |

**Resultado HC:**
- Cobertas: HC-07
- Parcialmente Cobertas: HC-05, HC-08 (desvio forçado por dados; proxy declarado)
- Condicionalmente Cobertas: HC-09
- Missing — Blocker: HC-01, HC-04, HC-06
- Missing — Warning: HC-02, HC-03, HC-10

**Detalhamento das decisões de classificação:**

HC-01 é Blocker porque a HC exige explicitamente que qualquer desvio da fórmula MC_ton seja "declarado explicitamente e obtenha aprovação do Consultor Metodológico." O plano não tem essa declaração formal de desvio aprovada — tem apenas a documentação de que os dados não existem. Isso é insuficiente segundo o próprio texto da HC-01.

HC-04 é Blocker porque afeta diretamente Tab 1, Tab 2 e Tab 4 — todas na Fase 1 — e a ausência de declaração de base temporal torna os indicadores auditavelmente inválidos (Consultor Metodológico: "invalida a auditabilidade do indicador").

HC-06 é Blocker porque a Tab 2 (Fase 1) tem sistema de alertas de exceção e a HC-06 proíbe explicitamente thresholds fixos sem base estatística documentada. A Fase 1 não pode ser implementada sem definição metodológica dos thresholds.

HC-02, HC-03, HC-10 são classificados como Warnings (não Blockers) porque: HC-02 e HC-03 são requisitos de documentação/metadado que podem ser adicionados sem refatoração de lógica central; HC-10 requer adicionar um campo de identificação de versão de plano que é expansão de escopo mas não invalida a lógica existente.

---

### Novos Blockers identificados no Cycle 2

| ID | HC | Fase afetada | Descrição |
|----|----|-------------|-----------|
| **BLOCKER-E** | HC-01 | Fase 1 (e todas) | O plano substitui MC_ton por receita_ton sem obter a aprovação formal do Consultor Metodológico para o desvio — exigência literal da HC-01. O Business Alignment deve conter uma seção de "Desvios HC Aprovados" com ciência registrada do Consultor Metodológico para cada HC que não pode ser satisfeita por indisponibilidade de dados (HC-01, HC-05, HC-08). Sem essa seção, o plano viola HC-01 por omissão formal, mesmo que a substituição seja tecnicamente justificável. |
| **BLOCKER-F** | HC-04, HC-06 | Fase 1 | Duas HCs diretamente aplicáveis à Fase 1 não estão cobertas em nenhum AC: (a) HC-04 — declaração de base temporal de dados por aba (faturado/despachado/carteira) em Tab 1, Tab 2, Tab 4; (b) HC-06 — definição metodológica dos thresholds de alerta na Tab 2 (percentil histórico ou N desvios-padrão). A Fase 1 não pode ser implementada sem esses dois elementos — eles afetam a validade auditável dos indicadores centrais do sistema. |

---

### Novos Warnings identificados no Cycle 2

| ID | HC | Descrição |
|----|----|-----------| 
| **W7** | HC-02 | `propensao_engine.py` será modificado na Fase 1 sem que a variável-alvo do score esteja declarada na interface da Tab 2. Recomenda-se adicionar um AC à Fase 1: "Tab 2 exibe metadado do modelo de propensity (evento modelado, horizonte de previsão) como tooltip ou footnote acessível ao usuário." |
| **W8** | HC-03 | Fase 3 deve incluir AC que verifique exibição de parâmetros do Monte Carlo (distribuição de resíduos, janela de calibração, frequência de recalibração) como metadado acessível na Tab 3. Sem isso, HC-03 não será satisfeita na entrega da Fase 3. |
| **W9** | HC-10 | Tab 1 e Tab 5 calculam gap/pace sem identificar a versão do plano usada como denominador. Recomenda-se adicionar às Fases 1 um AC: "Tab 1 e Tab 5 exibem identificador da versão do plano (ex.: SOP original, revisão R1) como legenda dos KPIs de gap." Baixo custo de implementação; alta relevância para auditabilidade. |

---

### Warnings do Cycle 1 — Status de Carry-Forward

| ID | Descrição | Status no Cycle 2 |
|----|-----------|-------------------|
| W1 | Política de join com `mc_referencia.csv`; NaN para 5% sem cobertura | **FECHADO** — `mc_referencia.csv` removido do escopo (BQ-02 fechada). Warning não se aplica mais. |
| W2 | `setup_cost_amortized` requer lógica de agrupamento PCP; indisponível em Opções A e B | **CARRY-FORWARD** — Plano v1.1 trata setup_cost_amortized como condicional (incluído só se BQ-01 exportar essa coluna). Warning permanece: para Opções A e B, o campo provavelmente não existirá, e a fórmula receita_adj ficará sem esse componente sem aviso explícito ao usuário. |
| W3 | `mc_adj_engine.py` sem comportamento definido quando freight_cost_ton ou setup_cost_amortized chegam nulos | **CARRY-FORWARD (renomeado)** — `receita_adj_engine.py` (substituto) tem o mesmo problema: o plano não define comportamento quando `freight_cost_ton` chega nulo da fonte BQ-01. AC-2.1 exige "receita_adj calculado para 100% das ordens" mas não define fallback para colunas nulas. |
| W4 | Mecanismo de alerta para OTIF_weight desatualizado (> 30 dias) não especificado | **CARRY-FORWARD** — Não endereçado no v1.1. RC-02 pode ser violada por omissão operacional. |
| W5 | "Section 1.1 of the literature" não encontrada em LITERATURA_SOE_PROCESSOS.md | **FECHADO** — A task do Cycle 2 não reitera essa referência. Warning considerado residual do contexto do Cycle 1. |
| W6 | `capacidade_producao.csv`: ownership, frequência de atualização e fallback não definidos | **CARRY-FORWARD** — Não endereçado no v1.1. Fase 3 permanece com ponto cego operacional. |

---

### Recommended Next Action

**O plano v1.1 está aprovado para avançar CONDICIONALMENTE** — os 4 Blockers originais foram resolvidos, mas 2 novos Blockers foram identificados pela formalização das HC. A sequência recomendada:

1. **[BLOCKER-E — Alta prioridade]** O Architect deve adicionar ao Business Alignment do plano uma seção "Desvios HC Aprovados" declarando formalmente que HC-01, HC-05 e HC-08 não podem ser satisfeitas por indisponibilidade de dados de custo variável, e solicitando aprovação explícita do Consultor Metodológico para uso de receita_ton como proxy documentado. Esta seção deve preceder o início de qualquer fase.

2. **[BLOCKER-F — Alta prioridade, impacta Fase 1]** Antes de iniciar a Fase 1, adicionar ao escopo:
   - (a) Declaração de base temporal em Tab 1, Tab 2 e Tab 4 (satisfaz HC-04): rótulo no header de cada indicador especificando se o dado é "faturado", "despachado" ou "carteira total incluindo bloqueados";
   - (b) Definição metodológica dos thresholds de alerta da Tab 2 (satisfaz HC-06): AC adicional especificando que thresholds são calculados como percentil P95 da distribuição histórica de desvios ou N desvios-padrão da média móvel (método a ser confirmado com o Consultor Metodológico antes da implementação).

3. **[W7, W8, W9]** Adicionar ACs correspondentes às Fases 1 e 3 para HC-02, HC-03 e HC-10 antes de submeter essas fases ao Coder.

4. **[W2, W3, W4 — Carry-forward]** Tratar antes da entrega da Fase 2: comportamento de fallback para colunas nulas em `receita_adj_engine.py`; mecanismo de staleness alert para `otif_weight`.

**Nenhuma fase está aprovada para implementação até resolução de BLOCKER-E e BLOCKER-F.**

---

*Fim do log de revisão Cycle 2. Dois novos Blockers (E e F) impedem o início da Fase 1. Os 4 Blockers do Cycle 1 (A, B, C, D) estão integralmente resolvidos.*

---

## Cycle 3 Review — 2026-05-30

> Revisor: Reviewer (Logician + Craftsman + Adversary)
> Artefato revisado: `.memory/plan/2026-05-30-refactor-governanca-soe.md` (v1.2)
> Fontes de constraints: `docs/AUDITORIA_NEGOCIO_APP.md` (HC-01 a HC-10 + RC-01 a RC-06 + HC-01-DEV-01), `docs/STATUS_VALIDACAO_ARQUITETURA.md` (Cycles 1 e 2)
> Ciclo: 3 (final) — verificação de BLOCKER-E e BLOCKER-F + cobertura completa HC/RC + warnings carry-forward

---

### Verdict: FAIL

**Justificativa**: BLOCKER-E está confirmado resolvido. BLOCKER-F está parcialmente resolvido: a sub-parte (b) referente a HC-06 (thresholds estatísticos) está genuinamente resolvida com ACs verificáveis; a sub-parte (a) referente a HC-04 (base temporal semântica por aba — faturado/despachado/carteira) não está resolvida — o plano implementa um banner de frescor de arquivo (data age) que é distinto e insuficiente para satisfazer o requisito literal da HC-04 e a ação recomendada do Cycle 2. Isso constitui um novo Blocker (BLOCKER-G), derivado do BLOCKER-F não resolvido integralmente.

---

### BLOCKER-E Resolution: Confirmed

**Verificação ponto a ponto:**

1. O plano v1.2 contém seção "Desvios HC Aprovados" no Business Alignment (linhas 29–33): **presente**.
2. A tabela de desvios contém HC-01-DEV-01 com: HC de origem (HC-01), substituto (`receita_ton = val_mm / vol_ton`), condições (UI label obrigatório; vol_ton é primário; revisar quando custo disponível), aprovação dual (Consultor Metodológico + Usuário, 2026-05-30): **tudo presente**.
3. `docs/AUDITORIA_NEGOCIO_APP.md` contém bloco HC-01-DEV-01 com aprovação dual registrada (Consultor Metodológico, 2026-05-30 + Usuário, decisão explícita, sessão 2026-05-30): **confirmado no documento de auditoria**.

O requisito literal da HC-01 — "nenhuma tela ou modelo pode usar definição alternativa de margem sem declarar explicitamente o desvio e obter aprovação do Consultor Metodológico" — está satisfeito no plano e no documento de auditoria. BLOCKER-E integralmente resolvido.

**Nota**: o plano cobre apenas HC-01-DEV-01 na tabela de desvios, mas o Cycle 2 também identificava HC-05 e HC-08 como casos de desvio forçado. Ambos os casos seguem a mesma lógica (substituição por receita_ton, proxy declarado, labels de proxy em todos os ACs pertinentes). A ausência de linhas HC-05-DEV-XX e HC-08-DEV-XX na tabela é uma omissão de forma, não de substância — as adaptações estão documentadas nas linhas de RC-05 e RC-03 do Business Alignment com labels de proxy explícitos. Não constitui novo Blocker; registrado como W10 abaixo.

---

### BLOCKER-F Resolution: Not Confirmed (partial)

**Sub-parte (a) — HC-04: Base temporal semântica por aba**

O Cycle 2 recomendou explicitamente: "rótulo no header de cada indicador especificando se o dado é 'faturado', 'despachado' ou 'carteira total incluindo bloqueados'."

A HC-04 literal (`AUDITORIA_NEGOCIO_APP.md` linha 129): "Cada indicador de volume ou receita exibido no sistema MUST ter sua base de cálculo explicitamente declarada na interface (faturado / despachado / carteira confirmada / carteira total incluindo bloqueados)."

O que o plano v1.2 implementou como escopo HC-04 (linha 197): banner de frescor dos parquets — timestamp de `vendas_filtrada.parquet` e `meta_semanal.parquet`, com banner amarelo/vermelho se dados > 24h / > 48h. ACs AC-1.X, AC-1.Y, AC-1.Z verificam a presença do timestamp e dos banners de frescor.

**Análise do Revisor**: frescor do arquivo (data age) e base semântica do indicador (faturado vs. despachado) são dois requisitos distintos. O frescor responde à pergunta "esses dados têm quantos dias?" A base semântica responde à pergunta "esses dados são de qual base operacional?" Implementar o primeiro não satisfaz o segundo. Nenhum dos ACs AC-1.X, AC-1.Y, AC-1.Z contém verificação de rótulo semântico por indicador. O Consultor Metodológico explicitou que a ausência de declaração de base temporal "invalida a auditabilidade do indicador." Esse argumento se aplica independentemente de quão fresco seja o arquivo.

**Resultado**: a sub-parte (a) do BLOCKER-F não está resolvida. A implementação adicionada é valiosa e necessária, mas insuficiente para fechar HC-04.

**Sub-parte (b) — HC-06: Thresholds de exceção com base estatística rastreável**

O plano v1.2 adiciona escopo item HC-06 (linha 198): `mean(deviation_pct) + 1.5 × std(deviation_pct)` sobre as últimas 8 semanas completas por linha; threshold exibido no tooltip; fallback 15% com label "default — histórico insuficiente" se < 4 semanas.

ACs AC-1.A, AC-1.B, AC-1.C verificam: cálculo dinâmico (não hardcoded), formato de tooltip especificado exatamente, fallback com label explícito para dados insuficientes.

Confronto com HC-06 literal: "MUST ter seu threshold definido com base em método estatístico documentado (ex.: percentil P95 da distribuição histórica de desvios, ou N desvios-padrão da média móvel de M períodos)." O plano usa `mean + 1.5σ` (N desvios-padrão da média), o que satisfaz a forma metodológica exigida. O tooltip satisfaz a rastreabilidade. O fallback satisfaz o comportamento para histórico insuficiente.

**Resultado**: sub-parte (b) do BLOCKER-F confirmada resolvida.

---

### Novo Blocker identificado no Cycle 3

| ID | HC | Fase afetada | Descrição |
|----|----|-------------|-----------|
| **BLOCKER-G** | HC-04 | Fase 1 (Tab 1, Tab 2, Tab 4) | A sub-parte não resolvida do BLOCKER-F constitui um novo Blocker. O plano v1.2 substitui a declaração de base semântica (faturado/despachado/carteira) por um banner de frescor de arquivo — o que não satisfaz a HC-04 literal nem a ação recomendada do Cycle 2. A Fase 1 não pode ser aprovada enquanto Tab 1, Tab 2 e Tab 4 não tiverem rótulo de base de cálculo por indicador. A correção tem baixo custo de implementação: adicionar texto de legenda ("Base: faturado — data de NF") sob cada KPI ou em tooltip padronizado. Requer AC adicional: "Todo KPI de volume ou receita nas Tabs 1, 2 e 4 exibe rótulo de base de cálculo (faturado / despachado / carteira confirmada / carteira total) junto ao valor ou em tooltip imediato." |

---

### HC Coverage Matrix (HC-01 a HC-10)

| Constraint | Status | Evidência no Plano v1.2 | Observação |
|------------|--------|-------------------------|-----------|
| **HC-01** — Definição Unívoca de MC_ton | **Deviation-Approved** | Tabela "Desvios HC Aprovados" no Business Alignment; HC-01-DEV-01 com aprovação dual registrada no plano e em `AUDITORIA_NEGOCIO_APP.md` | Desvio formalmente aprovado; proxy receita_ton documentado; labels obrigatórios em todos os ACs pertinentes |
| **HC-02** — Variável-Alvo do Propensity Score declarada na UI | **Partially Covered** | `propensao_engine.py` modificado para incluir receita_ton; nenhum AC da Fase 1 verifica exibição de metadado do modelo (evento modelado, horizonte H, limiar X) na Tab 2 | Carry-forward de W7; sem novo Blocker pois é requisito de documentação/metadado, não de lógica central |
| **HC-03** — Pressupostos do Monte Carlo documentados e acessíveis | **Partially Covered** | Fase 3 adiciona âncora de capacidade e P50_AC; nenhum AC verifica exibição de distribuição de resíduos, janela de calibração, frequência de recalibração na Tab 3 | Carry-forward de W8; impacto restrito à Fase 3 |
| **HC-04** — Base temporal de dados declarada por aba | **Partially Covered — BLOCKER-G** | v1.2 implementa banner de frescor de arquivo (data age); não implementa rótulo semântico de base de cálculo (faturado/despachado/carteira) por indicador em Tab 1, Tab 2, Tab 4 | Frescor de arquivo ≠ base semântica; HC-04 literal não satisfeita; gera BLOCKER-G |
| **HC-05** — MAPE_MC como métrica primária | **Deviation-Approved (implícito)** | `MAPE_receita` implementado como proxy documentado; exibido ao lado de MAPE de volume; labels de proxy em AC-1.6 | Desvio forçado por dados indisponíveis; documentado nas adaptações RC-05; ausência de linha formal HC-05-DEV-XX na tabela de desvios registrada como W10 |
| **HC-06** — Threshold de exceção com base estatística rastreável | **Covered** | Escopo item HC-06 na Fase 1 (linha 198); `mean + 1.5σ` sobre últimas 8 semanas; ACs AC-1.A, AC-1.B, AC-1.C verificáveis e específicos | BLOCKER-F sub-parte (b) confirmada resolvida |
| **HC-07** — OTIF_weight como variável do sistema | **Covered** | `otif_engine.py` (Fase 2); AC-2.2 verifica cálculo por cliente não estático; histórico de penalidades e churn especificado | W4 (staleness alert) persiste como carry-forward |
| **HC-08** — Delta de MC em toda simulação what-if | **Deviation-Approved (implícito)** | `delta_receita` como proxy; alerta vermelho se delta_receita < 0; AC-1.3 verificável | Mesmo argumento de HC-01/HC-05; desvio forçado por dados; ausência de linha formal HC-08-DEV-XX registrada como W10 |
| **HC-09** — Sinais exógenos com correlação documentada | **Covered (condicional)** | BQ-03 trata sinais exógenos como opcionais condicionados à decisão do usuário; se incluídos na Fase 3, o pré-requisito de correlação é verificável antes da implementação | Risco baixo neste ciclo; sem alteração do Cycle 2 |
| **HC-10** — Rastreabilidade de versão do plano usado como denominador | **Missing** | Nenhum módulo ou AC em nenhuma fase verifica a exibição do identificador de versão do plano (SOP original, R1, R2) nos KPIs de gap/pace em Tab 1 e Tab 5 | Carry-forward de W9; não é novo Blocker porque não introduz lógica inválida — apenas omite auditabilidade de versão |

**Resultado HC:**
- Covered: HC-06, HC-07, HC-09
- Deviation-Approved: HC-01 (formal), HC-05 (implícito), HC-08 (implícito)
- Partially Covered: HC-02, HC-03, HC-04
- Missing: HC-10
- **BLOCKER-G**: HC-04 parcialmente coberta com cobertura insuficiente para satisfazer requisito literal em Fase 1

---

### RC Coverage Matrix (RC-01 a RC-06)

| Constraint | Status | Evidência no Plano v1.2 | Observação |
|------------|--------|-------------------------|-----------|
| **RC-01** — Ranking com dimensão financeira primária; ordenação padrão | **Covered (adaptada)** | Ordenação primária vol_ton gap + secundária receita_ton; AC-1.4, AC-1.7 verificáveis | Adaptação documentada explicitamente; proxy declarado |
| **RC-02** — OTIF_weight calculado por histórico, atualizado ≥ mensalmente | **Covered** | `otif_engine.py` criado; AC-2.2 verifica diferença entre tiers | W4 (staleness alert > 30 dias) persiste como carry-forward; não Blocker |
| **RC-03** — What-if Zona Líquida: delta financeiro; alerta se negativo | **Covered (adaptada)** | `delta_receita = delta_vol × receita_ton_media_zona_liquida`; `st.warning` se negativo; AC-1.3 verificável | Proxy declarado; adaptação documentada |
| **RC-04** — Tab 4: backlog por estado, exposição financeira, tipo dominante | **Covered (adaptada)** | Colunas `ordens_bloqueadas`, `receita_represada`, `tipo_bloqueio_dominante`; AC-2.8 | Exposição em receita, não MC; label de proxy obrigatório |
| **RC-05** — Tab 5: MAPE_MC por período e família | **Covered (adaptada)** | `MAPE_receita` substitui MAPE_MC; por período e família; AC-1.6; label "proxy de receita, não MAPE_MC" | Desvio forçado por dados; documentado |
| **RC-06** — Módulo dedicado: painel, sequência, log de escalada, exposição | **Covered** | `carteira_destravamento.py` com 4 seções; ACs 2.1 a 2.10 cobrem todos os requisitos; log persistido em parquet append-only; incluído no Drive sync | Nenhuma lacuna adicional identificada |

**Resultado RC: 6/6 cobertas.** Todas as adaptações para dados disponíveis documentadas com labels de proxy obrigatórios.

---

### Carry-forward Warnings

| ID | Origem | Descrição | Status no Cycle 3 |
|----|--------|-----------|-------------------|
| **W2** | Cycle 1 | `setup_cost_amortized` indisponível nas Opções A e B da BQ-01; fórmula receita_adj ficará incompleta sem aviso explícito | **CARRY-FORWARD** — Não endereçado no v1.2. Plano trata como condicional mas não especifica o que o usuário verá quando o campo ausente omitir um componente financeiro da sequência de despacho. Deve ser tratado antes da entrega da Fase 2. |
| **W3** | Cycle 1 | `receita_adj_engine.py` sem comportamento definido quando `freight_cost_ton` chega nulo da fonte BQ-01; AC-2.1 exige 100% mas não define fallback | **CARRY-FORWARD** — Não endereçado no v1.2. Risco concreto de ZeroDivisionError ou NaN silencioso em sequência de despacho. Deve ser tratado antes da entrega da Fase 2. |
| **W4** | Cycle 1 | Mecanismo de alerta para OTIF_weight desatualizado (> 30 dias) não especificado | **CARRY-FORWARD** — Não endereçado no v1.2. RC-02 pode ser violada por omissão operacional. Deve ser tratado antes da entrega da Fase 2. |
| **W6** | Cycle 1 | `capacidade_producao.csv`: ownership, frequência de atualização e fallback não definidos | **CARRY-FORWARD** — Não endereçado no v1.2. Fase 3 permanece com ponto cego operacional. Deve ser tratado antes da entrega da Fase 3. |
| **W7** | Cycle 2 | `propensao_engine.py` modificado na Fase 1 sem metadado do modelo de propensity declarado na Tab 2 (HC-02) | **CARRY-FORWARD** — Não endereçado no v1.2. Nenhum AC da Fase 1 verifica a exibição de evento modelado, horizonte H, limiar X ao usuário. Recomenda-se adicionar AC antes de submeter Fase 1 ao Coder. |
| **W8** | Cycle 2 | Fase 3 sem AC verificando exibição de parâmetros do Monte Carlo como metadado acessível na Tab 3 (HC-03) | **CARRY-FORWARD** — Não endereçado no v1.2. Deve ser tratado antes da entrega da Fase 3. |
| **W9** | Cycle 2 | Tab 1 e Tab 5 sem identificador de versão do plano como denominador de gap/pace (HC-10) | **CARRY-FORWARD** — Não endereçado no v1.2. Baixo custo de implementação; alta relevância para auditabilidade. Recomenda-se adicionar AC à Fase 1. |
| **W10** | Cycle 3 (novo) | HC-05-DEV-XX e HC-08-DEV-XX ausentes da tabela formal "Desvios HC Aprovados" | **NOVO** — As adaptações de HC-05 (MAPE_receita vs. MAPE_MC) e HC-08 (delta_receita vs. delta_MC) seguem a mesma lógica do HC-01-DEV-01, mas não possuem linhas formais na tabela de desvios com aprovação dual registrada. As aprovações estão implícitas nas linhas RC-05 e RC-03, mas a HC-01 exige que o desvio seja "declarado explicitamente." Recomenda-se adicionar HC-05-DEV-01 e HC-08-DEV-01 à tabela antes de submeter Fase 1 ao Coder. Não constitui Blocker porque o BLOCKER-E já legitimou o padrão de substituição e as aprovações são rastreáveis — mas a omissão formal é uma lacuna de governança. |

---

### Final Recommendation

**Verdict: FAIL**

O plano v1.2 demonstra progresso genuíno: BLOCKER-E foi resolvido de forma rigorosa e completa, com registro dual no plano e no documento de auditoria. BLOCKER-F foi parcialmente resolvido — a sub-parte HC-06 (thresholds estatísticos) com ACs verificáveis e específicos constitui uma resolução de qualidade. Contudo, a sub-parte HC-04 (base semântica por aba) foi substituída por uma funcionalidade diferente (data freshness banner), e a diferença entre "frescor do arquivo" e "base semântica do indicador" é metodologicamente relevante e não colapsável. Isso gera BLOCKER-G que impede a aprovação da Fase 1.

**Ação mínima necessária para aprovação:**

1. **[BLOCKER-G — Alta prioridade]** Adicionar ao escopo da Fase 1, nos módulos `ritmo_semanal.py`, `plano_comercial.py` e `dashboard_uf.py`, rótulo de base de cálculo por indicador: cada KPI de volume ou receita deve exibir junto ao valor (ou em tooltip imediato) a base operacional usada — "faturado", "despachado" ou "carteira total incluindo bloqueados." Adicionar AC verificável: "Todo KPI de volume ou receita nas Tabs 1, 2 e 4 exibe rótulo de base de cálculo em texto visível ou tooltip imediato, antes de qualquer KPI numérico." Confirmar com o Consultor Metodológico se `vendas_filtrada.parquet` representa dado faturado ou despachado — essa resposta determina o rótulo correto.

2. **[W10 — Recomendado antes da Fase 1]** Adicionar HC-05-DEV-01 e HC-08-DEV-01 à tabela "Desvios HC Aprovados" com aprovação dual registrada, por coerência formal com HC-01-DEV-01.

3. **[W7, W9 — Recomendados antes da Fase 1]** Adicionar ACs para metadado do modelo de propensity na Tab 2 (HC-02) e identificador de versão do plano nas Tabs 1 e 5 (HC-10).

4. **[W2, W3, W4 — Recomendados antes da Fase 2]** Tratar comportamento de fallback para colunas nulas em `receita_adj_engine.py`; mecanismo de staleness alert para `otif_weight`; comportamento quando `setup_cost_amortized` ausente da fonte BQ-01.

5. **[W6, W8 — Recomendados antes da Fase 3]** Definir owner, frequência e fallback para `capacidade_producao.csv`; adicionar ACs para metadado do Monte Carlo na Tab 3.

**Nenhuma fase está aprovada para implementação até resolução de BLOCKER-G.** A correção de BLOCKER-G é de baixa complexidade técnica (rótulos de legenda por KPI) mas requer confirmação factual com o Consultor Metodológico sobre qual base operacional está representada nos dados atuais.

---

*Fim do log de revisão Cycle 3. Um novo Blocker (BLOCKER-G, derivado do BLOCKER-F não resolvido integralmente) impede o início da Fase 1. BLOCKER-E confirmado resolvido. BLOCKER-F confirmado parcialmente resolvido (sub-parte HC-06 resolvida; sub-parte HC-04 não resolvida).*

---

## Cycle 4 Review — 2026-05-30

> Revisor: Reviewer (Logician + Craftsman + Adversary)
> Artefato revisado: `.memory/plan/2026-05-30-refactor-governanca-soe.md` (v1.3)
> Fontes de constraints: `docs/AUDITORIA_NEGOCIO_APP.md` (HC-01 a HC-10 + RC-01 a RC-06 + HC-01-DEV-01), `docs/STATUS_VALIDACAO_ARQUITETURA.md` (Cycles 1, 2 e 3)
> Ciclo: 4 (final) — verificação exclusiva de BLOCKER-G + carry-forward de warnings

---

### Verdict: PARTIAL-PASS

**Justificativa**: BLOCKER-G está confirmado resolvido. Todos os Blockers anteriores (A, B, C, D, E, F) permanecem resolvidos conforme verificações dos Cycles 1–3. Nenhum novo Blocker foi identificado na leitura integral do plano v1.3. Warnings W2, W3, W4, W6, W7, W8, W9, W10 permanecem abertos; nenhum constitui Blocker. O veredicto é PARTIAL-PASS por existência de warnings carry-forward que devem ser endereçados antes das respectivas fases de entrega.

---

### BLOCKER-G Resolution: Confirmed

**Verificação ponto a ponto:**

1. **AC-1.W presente na Fase 1**: Confirmado — linha 229 do plano v1.3. O AC exige que todo KPI de volume realizado em todas as 5 abas exiba o rótulo "Fonte: Faturado (NF emitida)" como subtítulo ou tooltip. A semântica de base operacional ("faturado = NF emitida") está declarada explicitamente, respondendo à questão factual levantada no Cycle 3 sobre o que `vendas_filtrada.parquet` representa.

2. **AC-1.W mandata constante compartilhada `FONTE_REAL` em `app/config.py`**: Confirmado — AC-1.W declara literalmente: "injetado via constante compartilhada `FONTE_REAL = "Fonte: Faturado (NF emitida)"` definida em `app/config.py`." A injeção via constante compartilhada (não string literal dispersa por módulo) satisfaz o requisito de governança de rótulo centralizado.

3. **AC-1.V mandata `FONTE_SOE` e `FONTE_SOP` em `app/config.py`**: Confirmado — linha 230 do plano v1.3. Constantes `FONTE_SOE = "Fonte: Plano S&OE"` e `FONTE_SOP = "Fonte: Plano S&OP"` definidas em `app/config.py`. A distinção entre as duas fontes de plano atende ao requisito HC-04 de declaração da base temporal por indicador.

4. **AC-1.U proíbe semântica implícita de despacho ou carteira**: Confirmado — linha 231 do plano v1.3. A proibição é explícita e abrange rótulos e títulos de gráficos. A condição de criação de novo registro de desvio antes de qualquer exibição futura dessas bases é formalmente estabelecida.

5. **`app/config.py` listado nos arquivos afetados da Fase 1**: Confirmado — linha 200 do plano v1.3: "config.py (constantes de fonte semântica: `FONTE_REAL`, `FONTE_SOE`, `FONTE_SOP` — ~6 LOC adicionais)." O arquivo está no escopo de implementação da Fase 1.

O requisito literal da HC-04 — "cada indicador de volume ou receita exibido no sistema MUST ter sua base de cálculo explicitamente declarada na interface" — está agora coberto por três ACs verificáveis (AC-1.W, AC-1.V, AC-1.U) com constantes nomeadas e arquivo-alvo definido. BLOCKER-G integralmente resolvido.

---

### Final Constraint Status

| ID | Descrição | Status Final |
|----|-----------|-------------|
| BLOCKER-A | Série HC ausente no Business Alignment | RESOLVIDO (Cycle 2) |
| BLOCKER-B | MAPE denominador zero; MC_ton sem fonte | RESOLVIDO (Cycle 2) |
| BLOCKER-C | Paralelismo destrutivo em arquivos compartilhados | RESOLVIDO (Cycle 2) |
| BLOCKER-D | Escalation log sem persistência além de session_state | RESOLVIDO (Cycle 2) |
| BLOCKER-E | Desvio HC-01 sem aprovação formal do Consultor Metodológico | RESOLVIDO (Cycle 3) |
| BLOCKER-F (sub-b) | HC-06: thresholds de exceção sem base estatística | RESOLVIDO (Cycle 3) |
| BLOCKER-F (sub-a) / BLOCKER-G | HC-04: base semântica de indicador ausente (faturado/despachado/carteira) | RESOLVIDO (Cycle 4) |

Nenhum Blocker aberto. Todas as RC-01 a RC-06 cobertas. HC-06 coberta. HC-01, HC-05, HC-08 cobertas com desvio formalmente aprovado (HC-01-DEV-01; HC-05 e HC-08 implicitamente aprovadas — ver W10). HC-07, HC-09 cobertas. HC-04 coberta com ACs verificáveis (AC-1.W, AC-1.V, AC-1.U).

---

### Remaining Warnings (carry-forward)

Os warnings abaixo são transportados sem reavaliação. Nenhum constitui Blocker. O plano v1.3 não os endereçou (escopo da v1.3 era exclusivamente BLOCKER-G).

| ID | Fase de impacto | Descrição resumida | Prazo recomendado |
|----|----------------|--------------------|--------------------|
| **W2** | Fase 2 | `setup_cost_amortized` indisponível nas Opções A/B de BQ-01; fórmula receita_adj ficará incompleta sem aviso explícito ao usuário | Antes da entrega da Fase 2 |
| **W3** | Fase 2 | `receita_adj_engine.py` sem comportamento definido quando `freight_cost_ton` chega nulo da fonte BQ-01; AC-2.1 exige 100% sem definir fallback | Antes da entrega da Fase 2 |
| **W4** | Fase 2 | Mecanismo de alerta para OTIF_weight desatualizado (> 30 dias) não especificado; RC-02 pode ser violada por omissão operacional | Antes da entrega da Fase 2 |
| **W6** | Fase 3 | `capacidade_producao.csv`: ownership, frequência de atualização e fallback não definidos; ponto cego operacional da Fase 3 | Antes da entrega da Fase 3 |
| **W7** | Fase 1 | `propensao_engine.py` modificado sem metadado do modelo de propensity declarado na Tab 2 (HC-02); nenhum AC verifica evento modelado, horizonte H, limiar X | Recomendado antes de submeter Fase 1 ao Coder |
| **W8** | Fase 3 | Fase 3 sem AC verificando exibição de parâmetros do Monte Carlo como metadado acessível na Tab 3 (HC-03) | Antes da entrega da Fase 3 |
| **W9** | Fase 1 | Tab 1 e Tab 5 sem identificador de versão do plano como denominador de gap/pace (HC-10); baixo custo de implementação | Recomendado antes de submeter Fase 1 ao Coder |
| **W10** | Fase 1 | HC-05-DEV-XX e HC-08-DEV-XX ausentes da tabela formal "Desvios HC Aprovados"; aprovações implícitas mas não declaradas explicitamente conforme forma exigida pela HC-01 | Recomendado antes de submeter Fase 1 ao Coder |

---

### PLAN APPROVED FOR IMPLEMENTATION

O plano v1.3 está aprovado para implementação com as seguintes condições:

**Fase 1 pode começar após:**
1. O placeholder HC "HC-01 a HC-N: Pendente formalização" no Business Alignment ser substituído por referência às HC-01 a HC-10 formalizadas em `docs/AUDITORIA_NEGOCIO_APP.md` — conforme pré-condição declarada no próprio plano.
2. (Recomendado, não bloqueante) W7, W9, W10 endereçados antes de submeter ao Coder.

**A sentença literal da pré-condição do plano:** "aguardando formalização HC-01...HC-N pelo Consultor Metodológico antes de iniciar Fase 1" — as HC foram formalizadas entre os Cycles 1 e 2; o placeholder ainda não foi atualizado no Business Alignment. O Architect deve executar a instrução de re-leitura e atualizar a seção antes do primeiro commit da Fase 1.

**Fase 2**: bloqueada por BQ-01 (fonte de dados de ordens bloqueadas) e por Fase 1 completa e aprovada. W2, W3, W4 devem ser endereçados antes da entrega.

**Fase 3**: bloqueada por Fase 2 completa e aprovada. W6, W8 devem ser endereçados antes da entrega.

---

*Fim do log de revisão Cycle 4. BLOCKER-G confirmado resolvido. Nenhum Blocker aberto. Plano v1.3 aprovado para implementação — Fase 1 pode iniciar após substituição do placeholder HC no Business Alignment pela referência às HC-01 a HC-10 formalizadas.*
