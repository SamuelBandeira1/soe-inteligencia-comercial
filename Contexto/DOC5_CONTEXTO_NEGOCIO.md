# DOC 5 — Contexto de Negócio: Supply Chain da Aço Cearense

## Para o agente: por que este documento existe

O agente só ensina bem se entende o negócio. Exemplos genéricos de LSTM com dados de temperatura ou ações de bolsa não criam conexão com o problema real. Use este documento para ancorar cada conceito técnico no contexto da Aço Cearense.

---

## O Negócio

**Grupo Aço Cearense** — distribuidora e processadora de aço no Nordeste do Brasil.

**Famílias de produto principais:**
- CA-50, CA-60 (vergalhões de aço para construção civil — maior volume)
- Fio-máquina (processos industriais)
- Chapa Plana, Chapa Grossa
- Tubo, Perfis, Tela, Telha, Lambril, Tarugo, Trelica

**Característica importante:** demanda fortemente ligada ao setor de construção civil, que tem sazonalidade marcada (obras param em dezembro/janeiro, aceleração no segundo semestre). Isso significa que o modelo precisa capturar padrões sazonais — algo que LSTMs fazem bem.

---

## O Processo de S&OP/S&OE

**S&OP (Sales & Operations Planning):**
- Horizonte: 3-18 meses
- Frequência: mensal
- Objetivo: alinhar previsão de demanda com capacidade de compra e estoque

**S&OE (Sales & Operations Execution):**
- Horizonte: semanas
- Frequência: semanal
- Objetivo: ajuste fino do plano mensal com dados de curto prazo

**Onde o modelo LSTM se encaixa:**
O modelo prevê demanda mensal por família de produto para o S&OP. A comparação com LightGBM mostra se redes neurais trazem ganho real de precisão no horizonte de 1-3 meses.

---

## Padrões de Demanda Conhecidos

Use esses padrões como validação qualitativa do modelo:

| Padrão | O que esperar |
|---|---|
| Sazonalidade anual | Picos de março-maio e agosto-outubro; vale em dezembro-janeiro |
| CA-50 vs CA-60 | CA-50 é commoditizado, CA-60 tem demanda mais industrial e estável |
| Impacto de chuvas | Chuvas fortes no Nordeste (fev-abr) desaceleram obras → menos demanda |
| Efeito calendário | Meses com mais dias úteis tendem a ter mais volume |

**Como usar na validação:**
Se o modelo prevê pico em dezembro (quando a demanda historicamente cai), algo está errado — isso é um sanity check qualitativo que o agente deve fazer junto com Samuel.

---

## O que o Modelo LightGBM Atual Faz

Referência para a comparação:

- **Modelo:** `modelo_propensao_v24_enterprise.py` — ensemble XGBoost + RF + LR
- **Foco:** propensão de compra por cliente (B2B)
- **Features:** 35 features em grupos temporais, recência, frequência, volume

**Atenção:** o modelo v24 é de **propensão de compra** (probabilidade de um cliente comprar), não de **forecast de volume**. O LSTM que estamos construindo é um modelo diferente — previsão de volume por família de produto.

Isso significa que a comparação direta não é v24 vs LSTM, mas sim:
- **LightGBM para forecast de série temporal** (baseline a construir) vs. **LSTM**

O agente deve esclarecer essa distinção com Samuel se surgir confusão.

---

## Vocabulário do Negócio que o Agente Deve Conhecer

| Termo | Significado |
|---|---|
| S&OP | Sales & Operations Planning — processo de alinhamento de demanda e supply |
| S&OE | Sales & Operations Execution — versão semanal do S&OP |
| Desvio | Diferença entre realizado e previsto (em volume ou valor) |
| Mix | Composição das vendas por família ou canal |
| Lift | Quantas vezes o modelo é melhor que aleatório (usado no modelo de propensão) |
| MAPE | Mean Absolute Percentage Error — erro médio percentual de forecast |
| Bias | Tendência sistemática de o modelo errar sempre para cima ou para baixo |
| Colaborativo | Processo onde vendedores e planejamento constroem a previsão juntos |
| Consenso | Reunião onde o número final de forecast é acordado entre áreas |

---

## Como usar este contexto nas sessões

**Quando introduzir sliding window:**
> "Você já sabe que o planejamento olha os últimos 3-6 meses para fazer o forecast do próximo. A sliding window é exatamente isso: o modelo aprende vendo 12 meses de histórico para prever o 13º."

**Quando explicar bias:**
> "Bias negativo significa que o modelo subestima sistematicamente. Para S&OP, isso é ruim porque você vai comprar menos aço do que precisa e vai faltar estoque. Bias positivo é comprar demais e travar capital."

**Quando o LSTM errar muito:**
> "No nosso setor, picos de demanda às vezes são causados por grandes obras que aparecem de repente — o modelo não tem como prever isso com séries históricas. Isso é o que chamamos de demanda esporádica, e é uma limitação real de qualquer modelo estatístico."
