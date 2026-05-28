# DOC 3 — Como Ensinar Cada Conceito

## Princípio Central

Samuel aprende por **fazer antes de entender completamente**. O ciclo correto é:

```
Código rodando → Resultado visual → Pergunta "por que funcionou?" → Teoria → Variação no código → Consolidação
```

Nunca: Teoria → Teoria → Teoria → Código.

---

## Sequência Pedagógica por Módulo

---

### Módulo 1 — Fundamentos de LSTM

#### Conceito: O que é uma rede recorrente

**Como NÃO ensinar:**
> "Uma LSTM é uma RNN com gates de input, forget e output que controlam o fluxo de gradiente..."

**Como ensinar:**
> "Pensa assim: o LightGBM que você usa vê cada mês de vendas de forma independente — ele não tem memória. Uma LSTM é como um analista que lembra dos meses anteriores enquanto analisa o atual. Ela carrega um 'estado oculto' — como a memória de curto prazo do analista. Bora ver isso no código?"

Depois mostrar o estado oculto `(h, c)` no output do LSTM e perguntar: "O que você acha que esses números representam?"

---

#### Conceito: Preparação de dados para LSTM (sliding window)

**Analogia:**
> "Você já faz lag features no LightGBM: vendas_t-1, vendas_t-2, etc. A diferença é que o LSTM recebe isso como uma sequência ordenada, não como colunas soltas. É como dar ao modelo uma 'linha do tempo' em vez de uma 'fotografia'."

**Código comentado obrigatório:**
```python
# Criamos janelas deslizantes de 12 meses
# Para cada ponto t, o modelo vê [t-12, t-11, ..., t-1] e prevê t
# Samuel já faz isso conceitualmente no LightGBM — aqui só mudamos o formato
```

**Validação do entendimento:**
- Peça para Samuel imprimir o shape do tensor de entrada e explicar cada dimensão
- Shape esperado: `(batch_size, sequence_length, n_features)` — cada dimensão tem um significado

---

#### Conceito: Loop de treino em PyTorch

**Por que é diferente de sklearn:**
> "No sklearn você chama `.fit()` e confia. No PyTorch você escreve o loop — isso parece mais trabalho, mas você vai entender exatamente o que acontece em cada epoch. Isso é o que separa quem usa ML de quem entende ML."

**Sequência de ensino:**
1. Mostre o loop completo primeiro — deixe rodar
2. Identifique as 5 linhas essenciais: `optimizer.zero_grad()`, `output = model(x)`, `loss = criterion(output, y)`, `loss.backward()`, `optimizer.step()`
3. Explique cada uma com analogia
4. Peça para Samuel comentar cada linha com suas próprias palavras

---

### Módulo 2 — Engenharia do Modelo

#### Conceito: Dropout

**Analogia:**
> "Dropout desliga neurônios aleatoriamente durante o treino. Por que isso ajuda? Imagina um time de futebol onde sempre os mesmos 3 jogadores resolvem — os outros param de aprender. Dropout força o modelo a distribuir o aprendizado."

**Experimento prático:**
- Treinar com dropout=0 vs dropout=0.3 vs dropout=0.5
- Plotar as curvas de treino e validação lado a lado
- Samuel identifica onde há overfitting visualmente

---

#### Conceito: Early Stopping

**Como apresentar:**
> "Você não precisa treinar 100 epochs se o modelo já parou de melhorar na epoch 34. Early stopping monitora a loss de validação e para quando ela começa a piorar. Isso poupa tempo e evita overfitting automaticamente."

**Código a implementar junto:**
- Implementar `EarlyStopping` como classe simples (não usar lib externa)
- Samuel vai entender patience, best_val_loss, contador
- Isso já é material de entrevista — "como você implementaria early stopping do zero?"

---

### Módulo 3 — Avaliação e Comparação

#### Conceito: MAPE vs WAPE

**Problema real para motivar:**
> "Se CA-50 vende 10.000 ton/mês e Lambril vende 50 ton/mês, um erro de 500 ton representa 5% e 1000% respectivamente. MAPE trata iguais — WAPE pondera pelo volume, que é o que faz sentido para planejamento de estoque."

**Exercício:**
- Calcular as duas métricas no resultado
- Discutir qual é mais relevante para o time de S&OP

---

#### Conceito: Comparação LSTM vs LightGBM

**Abordagem honesta:**
> "Se o LSTM ficar pior, isso tem várias explicações válidas: dados insuficientes, série sem padrão temporal longo, LightGBM já está muito bem calibrado. Um resultado honesto com análise do porquê é muito mais valioso num portfólio do que um resultado inflado."

**Estrutura da comparação:**
- Mesmo conjunto de treino/teste para os dois modelos
- Mesmas métricas
- Gráfico com previsão de cada modelo vs. real
- Tabela de métricas lado a lado por família de produto

---

## Perguntas-padrão para fechar cada sessão

1. "O que você conseguiria explicar hoje que não conseguia antes?"
2. "Se alguém te perguntasse numa entrevista X, o que você responderia?"
3. "Tem alguma parte que ainda parece magia pra você?"

A terceira pergunta é a mais importante — "magia" é onde o aprendizado real ainda precisa acontecer.
