# CHECKPOINT — Progresso do Projeto LSTM Forecast

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 25/05/2026
**Etapa atual:** 2 — Baseline LightGBM
**Próxima sessão:** construir o LightGBM baseline com os dados processados

---

## Progresso por Etapa

| Etapa | Status | Data de conclusão | Observações |
|---|---|---|---|
| 0 — Setup ambiente | ✅ Concluído | 25/05/2026 | PyTorch 2.12, MLflow 3.12, LightGBM 4.6 |
| 1 — Exploração dos dados | ✅ Concluído | 25/05/2026 | Ver decisões técnicas abaixo |
| 2 — Baseline LightGBM | ⬜ Não iniciado | — | — |
| 3 — Primeiro LSTM rodando | ⬜ Não iniciado | — | — |
| 4 — Modelo otimizado | ⬜ Não iniciado | — | — |
| 5 — Avaliação e comparação | ⬜ Não iniciado | — | — |
| 6 — Publicação GitHub | ⬜ Não iniciado | — | — |

---

## Resultados Registrados

| Modelo | Família | MAPE | WAPE | Bias | Data |
|---|---|---|---|---|---|
| LightGBM baseline | — | — | — | — | — |
| LSTM v1 | — | — | — | — | — |
| LSTM otimizado | — | — | — | — | — |

---

## Decisões Técnicas Tomadas

- [x] **Granularidade:** nível mensal por linha/empresa/região/UF. Motivo: é o horizonte do S&OP — prever no nível de nota fiscal não tem utilidade operacional.
- [x] **Linhas priorizadas:** CA-50 (principal), Tubo, CA-60, Chapa Plana. Motivo: maior volume e relevância para planejamento de estoque.
- [x] **Dados excluídos:** cliente, material, fornecedor. Motivo: o modelo prevê demanda agregada — dado de cliente some na agregação e cria risco de privacidade no GitHub.
- [x] **Quebra estrutural:** feature binária `expansao_laminador` (0 antes de jul/2024, 1 a partir de jul/2024). Motivo: expansão do laminador dobrou a capacidade de oferta — sem essa feature o modelo tenta aprender dois regimes diferentes como se fossem um.
- [x] **Gap de dados:** 21-31/dez/2025 ausente na base antiga. Decisão: manter dezembro/2025 com volume parcial — impacto mínimo na agregação mensal e o modelo já aprende que dezembro é vale.
- [ ] Janela temporal do LSTM: a definir na Etapa 3
- [ ] Arquitetura final: a definir na Etapa 3
- [ ] Otimizador: a definir na Etapa 3

---

## Dúvidas em Aberto

- Outlier de fev/2022 (~51k ton quando média era ~20k): investigar causa na Etapa 2
- Outlier de set-out/2025: confirmar se é pico legítimo pós-expansão ou evento pontual

---

## Como iniciar a próxima sessão

Cole o conteúdo de `AGENTE_INSTRUCOES.md` no início da conversa com o agente, seguido deste arquivo CHECKPOINT.md atualizado. O agente vai retomar de onde parou.

ATUALIZAÇÃO ABAIXO:

# CHECKPOINT — Progresso do Projeto LSTM Forecast

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 25/05/2026
**Etapa atual:** 3 — Primeiro LSTM rodando
**Próxima sessão:** construir o primeiro LSTM com os dados do CA-50

---

## Progresso por Etapa

| Etapa | Status | Data de conclusão | Observações |
|---|---|---|---|
| 0 — Setup ambiente | ✅ Concluído | 25/05/2026 | PyTorch 2.12, MLflow 3.12, LightGBM 4.6 |
| 1 — Exploração dos dados | ✅ Concluído | 25/05/2026 | Quebra estrutural jul/2024 identificada |
| 2 — Baseline LightGBM | ✅ Concluído | 25/05/2026 | MAPE 25.2%, WAPE 26.1%, Bias -20.2% |
| 3 — Primeiro LSTM rodando | ⬜ Não iniciado | — | — |
| 4 — Modelo otimizado | ⬜ Não iniciado | — | — |
| 5 — Avaliação e comparação | ⬜ Não iniciado | — | — |
| 6 — Publicação GitHub | ⬜ Não iniciado | — | — |

Legenda: ⬜ Não iniciado | 🔄 Em andamento | ✅ Concluído | ⚠️ Travado

---

## Resultados Registrados

| Modelo | Família | MAPE | WAPE | Bias | Data |
|---|---|---|---|---|---|
| LightGBM baseline | CA-50 | 25.2% | 26.1% | -20.2% | 25/05/2026 |
| LSTM v1 | — | — | — | — | — |
| LSTM otimizado | — | — | — | — | — |

---

## Decisões Técnicas Tomadas

*(registrar aqui as escolhas feitas e o porquê — serve de histórico e de material de entrevista)*

- [x] **Granularidade:** nível mensal por linha/empresa/região/UF. Motivo: é o horizonte do S&OP — prever no nível de nota fiscal não tem utilidade operacional.
- [x] **Linhas priorizadas:** CA-50 (principal), Tubo, CA-60, Chapa Plana. Motivo: maior volume e relevância para planejamento de estoque.
- [x] **Dados excluídos:** cliente, material, fornecedor. Motivo: o modelo prevê demanda agregada — dado de cliente some na agregação e cria risco de privacidade no GitHub.
- [x] **Quebra estrutural:** feature binária `expansao_laminador` (0 antes de jul/2024, 1 a partir de jul/2024). Motivo: expansão do laminador dobrou a capacidade de oferta — sem essa feature o modelo tenta aprender dois regimes diferentes como se fossem um.
- [x] **Gap de dados:** 21-31/dez/2025 ausente na base antiga. Decisão: manter dezembro/2025 com volume parcial — impacto mínimo na agregação mensal e o modelo já aprende que dezembro é vale.
- [x] **Corte treino/teste:** junho/2025 — 12 meses de teste. Motivo: janela suficiente para avaliar sazonalidade completa sem comprometer o treino.
- [ ] Janela temporal do LSTM: a definir na Etapa 3
- [ ] Arquitetura final: a definir na Etapa 3
- [ ] Otimizador: a definir na Etapa 3

---

## Dúvidas em Aberto

- Outlier de fev/2022 (~51k ton quando média era ~20k): causa não investigada ainda
- Outlier de set-out/2025: pico legítimo pós-expansão confirmado visualmente
- LightGBM com bias -20%: hipótese é lag com memória do regime antigo — LSTM pode capturar melhor

---

## Como iniciar a próxima sessão

Cole o conteúdo de `AGENTE_INSTRUCOES.md` no início da conversa com o agente, seguido deste arquivo CHECKPOINT.md atualizado. O agente vai retomar de onde parou.

ATUALIZAÇÃO ABAIXO:
# CHECKPOINT — Progresso do Projeto LSTM Forecast

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 25/05/2026
**Etapa atual:** 4 — Modelo otimizado
**Próxima sessão:** implementar Early Stopping e Dropout, reduzir overfitting

---

## Progresso por Etapa

| Etapa | Status | Data de conclusão | Observações |
|---|---|---|---|
| 0 — Setup ambiente | ✅ Concluído | 25/05/2026 | PyTorch 2.12, MLflow 3.12, LightGBM 4.6 |
| 1 — Exploração dos dados | ✅ Concluído | 25/05/2026 | Quebra estrutural jul/2024 identificada |
| 2 — Baseline LightGBM | ✅ Concluído | 25/05/2026 | MAPE 25.2%, WAPE 26.1%, Bias -20.2% |
| 3 — Primeiro LSTM rodando | ✅ Concluído | 25/05/2026 | MAPE 27.8%, WAPE 25.4%, Bias -7.6% |
| 4 — Modelo otimizado | ⬜ Não iniciado | — | — |
| 5 — Avaliação e comparação | ⬜ Não iniciado | — | — |
| 6 — Publicação GitHub | ⬜ Não iniciado | — | — |

Legenda: ⬜ Não iniciado | 🔄 Em andamento | ✅ Concluído | ⚠️ Travado

---

## Resultados Registrados

| Modelo | Família | MAPE | WAPE | Bias | Data |
|---|---|---|---|---|---|
| LightGBM baseline | CA-50 | 25.2% | 26.1% | -20.2% | 25/05/2026 |
| LSTM v1 | CA-50 | 27.8% | 25.4% | -7.6% | 25/05/2026 |
| LSTM otimizado | — | — | — | — | — |

---

## Decisões Técnicas Tomadas

- [x] **Granularidade:** nível mensal por linha/empresa/região/UF. Motivo: é o horizonte do S&OP.
- [x] **Linhas priorizadas:** CA-50 (principal), Tubo, CA-60, Chapa Plana.
- [x] **Dados excluídos:** cliente, material, fornecedor.
- [x] **Quebra estrutural:** feature binária `expansao_laminador` (0 antes jul/2024, 1 depois). 
- [x] **Gap de dados:** 21-31/dez/2025 mantido com volume parcial.
- [x] **Corte treino/teste:** junho/2025 — 12 meses de teste.
- [x] **Arquitetura v1:** 2 layers LSTM, hidden_size=64, dropout=0.2, 200 epochs, lr=0.001.
- [x] **Problema identificado:** overfitting após epoch ~35 — loss de validação sobe enquanto treino desce.
- [ ] Janela temporal do LSTM: testada com 12 — avaliar na Etapa 4
- [ ] Early Stopping: a implementar na Etapa 4
- [ ] Otimizador final: Adam lr=0.001 — avaliar variações na Etapa 4

---

## Dúvidas em Aberto

- Outlier de fev/2022: causa não investigada
- Early stopping: parar em torno da epoch 35 — confirmar na Etapa 4
- LSTM v1 com bias -7.6% vs LightGBM -20.2%: hipótese confirmada — LSTM captura melhor a transição de regime

---

## Como iniciar a próxima sessão

Cole o conteúdo de `AGENTE_INSTRUCOES.md` no início da conversa com o agente, seguido deste arquivo CHECKPOINT.md atualizado. O agente vai retomar de onde parou.

ATUALIZAÇÃO ABAIXO:

# CHECKPOINT — Progresso do Projeto LSTM Forecast

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 25/05/2026
**Etapa atual:** 5 — Avaliação final e comparação
**Próxima sessão:** gerar comparação final LSTM vs LightGBM e preparar para publicação

---

## Progresso por Etapa

| Etapa | Status | Data de conclusão | Observações |
|---|---|---|---|
| 0 — Setup ambiente | ✅ Concluído | 25/05/2026 | PyTorch 2.12, MLflow 3.12, LightGBM 4.6 |
| 1 — Exploração dos dados | ✅ Concluído | 25/05/2026 | Quebra estrutural jul/2024 identificada |
| 2 — Baseline LightGBM | ✅ Concluído | 25/05/2026 | MAPE 25.2%, WAPE 26.1%, Bias -20.2% |
| 3 — Primeiro LSTM rodando | ✅ Concluído | 25/05/2026 | MAPE 27.8%, WAPE 25.4%, Bias -7.6% |
| 4 — Modelo otimizado | ✅ Concluído | 25/05/2026 | MAPE 22.6%, WAPE 20.7%, Bias -6.2% |
| 5 — Avaliação e comparação | ⬜ Não iniciado | — | — |
| 6 — Publicação GitHub | ⬜ Não iniciado | — | — |

Legenda: ⬜ Não iniciado | 🔄 Em andamento | ✅ Concluído | ⚠️ Travado

---

## Resultados Registrados

| Modelo | Família | MAPE | WAPE | Bias | Data |
|---|---|---|---|---|---|
| LightGBM baseline | CA-50 | 25.2% | 26.1% | -20.2% | 25/05/2026 |
| LSTM v1 | CA-50 | 27.8% | 25.4% | -7.6% | 25/05/2026 |
| LSTM otimizado | CA-50 | 22.6% | 20.7% | -6.2% | 25/05/2026 |

---

## Decisões Técnicas Tomadas

- [x] **Granularidade:** nível mensal por linha/empresa/região/UF. Motivo: é o horizonte do S&OP.
- [x] **Linhas priorizadas:** CA-50 (principal), Tubo, CA-60, Chapa Plana.
- [x] **Dados excluídos:** cliente, material, fornecedor.
- [x] **Quebra estrutural:** feature binária `expansao_laminador` (0 antes jul/2024, 1 depois).
- [x] **Gap de dados:** 21-31/dez/2025 mantido com volume parcial.
- [x] **Corte treino/teste:** junho/2025 — 12 meses de teste.
- [x] **Arquitetura v1:** 2 layers LSTM, hidden_size=64, dropout=0.2, 200 epochs, lr=0.001.
- [x] **Arquitetura otimizada:** 2 layers LSTM, hidden_size=64, dropout=0.2, Early Stopping patience=20, lr=0.001. Parou na epoch 70.
- [x] **Problema de overfitting resolvido:** Early Stopping + dropout controlaram a generalização.

---

## Dúvidas em Aberto

- Outlier de fev/2022: causa não investigada
- Por que não fixar epochs em 50: Early Stopping é adaptativo — o ponto ótimo muda com cada experimento

---

## Como iniciar a próxima sessão

Cole o conteúdo de `AGENTE_INSTRUCOES.md` no início da conversa com o agente, seguido deste arquivo CHECKPOINT.md atualizado. O agente vai retomar de onde parou.


Atualização abaixo:

# CHECKPOINT — Progresso do Projeto LSTM Forecast

> Atualizar este arquivo ao final de cada sessão de trabalho.

---

## Status Atual

**Última sessão:** 25/05/2026
**Etapa atual:** PROJETO CONCLUÍDO
**Próximo projeto:** Sistema de Inteligência Comercial Semanal — S&OE

---

## Progresso por Etapa

| Etapa | Status | Data de conclusão | Observações |
|---|---|---|---|
| 0 — Setup ambiente | ✅ Concluído | 25/05/2026 | PyTorch 2.12, MLflow 3.12, LightGBM 4.6 |
| 1 — Exploração dos dados | ✅ Concluído | 25/05/2026 | Quebra estrutural jul/2024 identificada |
| 2 — Baseline LightGBM | ✅ Concluído | 25/05/2026 | MAPE 25.2%, WAPE 26.1%, Bias -20.2% |
| 3 — Primeiro LSTM rodando | ✅ Concluído | 25/05/2026 | MAPE 27.8%, WAPE 25.4%, Bias -7.6% |
| 4 — Modelo otimizado | ✅ Concluído | 25/05/2026 | MAPE 22.6%, WAPE 20.7%, Bias -6.2% |
| 5 — Avaliação e comparação | ✅ Concluído | 25/05/2026 | Comparação final gerada, GIFs criados |
| 6 — Publicação GitHub | ✅ Concluído | 25/05/2026 | Repositório privado publicado |

---

## Resultados Registrados

| Modelo | Família | MAPE | WAPE | Bias | Data |
|---|---|---|---|---|---|
| LightGBM baseline | CA-50 | 25.2% | 26.1% | -20.2% | 25/05/2026 |
| LSTM v1 | CA-50 | 27.8% | 25.4% | -7.6% | 25/05/2026 |
| LSTM otimizado | CA-50 | 22.6% | 20.7% | -6.2% | 25/05/2026 |

---

## Decisões Técnicas Tomadas

- [x] Granularidade: mensal por linha/empresa/região/UF
- [x] Linhas priorizadas: CA-50 (principal), Tubo, CA-60, Chapa Plana
- [x] Dados excluídos: cliente, material, fornecedor
- [x] Quebra estrutural: feature binária `expansao_laminador` (0 antes jul/2024, 1 depois)
- [x] Gap dez/2025: mantido com volume parcial
- [x] Corte treino/teste: junho/2025 — 12 meses de teste
- [x] Arquitetura final: 2 layers LSTM, hidden_size=64, dropout=0.2, Early Stopping patience=20
- [x] Repositório: github.com/SamuelBandeira1/lstm-forecast-demanda (privado)

---

## Aprendizados Principais

- LSTM captura melhor transição de regime que LightGBM — bias caiu de -20% para -6%
- Série semanal tem ruído alto demais para LSTM com dados disponíveis
- Problema real não é forecast de volume — é inteligência comercial semanal
- Padrão intra-mês confirmado nos dados: semana 4 vende 49% mais que semana 1
- Meta linear do S&OE é inadequada — não considera padrão histórico intra-mês

---

## Próximo Projeto — Sistema de Inteligência Comercial Semanal

**Problema:** coordenadores são reativos — esperam cliente ligar. Precisam saber para quem ligar e quando.

**Três módulos planejados:**
1. Painel de ritmo semanal vs plano S&OE com padrão histórico ponderado
2. Score de propensão de compra semanal por cliente
3. Lista de ação: top clientes para ligar por linha de produto

**Dados disponíveis:**
- Histórico de pedidos por cliente com data, hora, linha, volume
- Meta semanal por linha e região (S&OP e S&OE)
- Hierarquia completa de produto: família, linha, grupo, tipo, espessura

**Repositório novo:** a criar no próximo chat
