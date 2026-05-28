# DOC 4 — Critérios de Validação por Etapa

## Como usar este documento

Antes de avançar para a próxima etapa, Samuel deve conseguir marcar **todos** os critérios da etapa atual. Se travar em algum, é ali que a sessão deve focar — não adiante.

O agente deve checar esses critérios ativamente, não esperar Samuel relatar.

---

## Etapa 0 — Setup do ambiente
**Critérios:**
- [ ] Ambiente virtual criado e ativado (`venv`)
- [ ] PyTorch instalado e importado sem erro
- [ ] MLflow instalado e UI abrindo no browser (`mlflow ui`)
- [ ] Estrutura de pastas criada conforme `DOC2_ARQUITETURA.md`
- [ ] Repositório Git inicializado com `.gitignore` correto

**Como validar:**
```python
import torch
print(torch.__version__)  # deve printar versão sem erro

import mlflow
mlflow.set_experiment("lstm-forecast-v1")
# deve criar pasta mlruns/ sem erro
```

---

## Etapa 1 — Exploração dos dados
**Critérios:**
- [ ] Série temporal plotada para pelo menos 2 famílias de produto
- [ ] Samuel consegue identificar visualmente: tendência, sazonalidade, outliers
- [ ] Dados ausentes identificados e tratados (forward fill ou interpolação justificada)
- [ ] Samuel consegue responder: "Quantos meses de histórico temos? Isso é suficiente para treinar um LSTM?"

**Pergunta de validação obrigatória:**
> "Olhando os gráficos, você acha que existe padrão temporal que um modelo pode aprender? Onde está esse padrão?"

Se Samuel não conseguir responder, volta para a visualização — não adianta modelar dados que não entendemos.

---

## Etapa 2 — Baseline LightGBM
**Critérios:**
- [ ] LightGBM treinado com os mesmos dados que o LSTM usará
- [ ] MAPE e WAPE calculados e registrados no MLflow
- [ ] Gráfico de previsão vs. real gerado e salvo
- [ ] Samuel consegue explicar: "Por que precisamos de um baseline antes do LSTM?"

**Número-alvo:** registrar o MAPE do LightGBM como referência no `CHECKPOINT.md`

---

## Etapa 3 — Primeiro LSTM rodando
**Critérios:**
- [ ] Dados convertidos para tensores PyTorch com shape correto `(batch, seq_len, features)`
- [ ] Samuel consegue explicar o que significa cada dimensão do tensor
- [ ] Modelo LSTM instanciado sem erro
- [ ] Loop de treino rodando e loss diminuindo (mesmo que pouco)
- [ ] Samuel consegue plotar a curva de loss de treino

**Critério mais importante desta etapa:**
Loss deve cair nas primeiras epochs. Se não cair, há bug — diagnosticar antes de avançar.

**Pergunta de validação:**
> "Por que a loss às vezes oscila em vez de cair suavemente? O que você acha que causa isso?"

---

## Etapa 4 — Modelo otimizado
**Critérios:**
- [ ] Dropout implementado e testado em 2 valores diferentes
- [ ] Early stopping funcionando — treino parou antes do número máximo de epochs
- [ ] Curva de treino E validação plotadas juntas
- [ ] Samuel consegue identificar visualmente se o modelo está em overfitting
- [ ] Pelo menos 3 experimentos registrados no MLflow com hiperparâmetros diferentes

**Pergunta de validação:**
> "Qual foi o experimento com melhor resultado? Por que você acha que foi melhor?"

---

## Etapa 5 — Avaliação final e comparação
**Critérios:**
- [ ] Melhor modelo LSTM avaliado no conjunto de teste (que não foi usado no treino)
- [ ] MAPE, WAPE e Bias calculados para LSTM e LightGBM nos mesmos dados
- [ ] Gráfico de comparação lado a lado gerado e salvo
- [ ] Samuel consegue explicar o resultado — mesmo se o LSTM perdeu

**Pergunta de validação (mais importante do projeto):**
> "Se você fosse apresentar esse resultado para o gestor de S&OP, o que você diria? E para um cientista de dados numa entrevista?"

Essas são respostas diferentes — o agente deve ajudar Samuel a articular as duas.

---

## Etapa 6 — Publicação no GitHub
**Critérios:**
- [ ] README com: problema, metodologia, resultados (métricas reais), como rodar
- [ ] Notebooks limpos e com outputs salvos (sem dados sensíveis)
- [ ] `requirements.txt` com versões fixadas
- [ ] `.gitignore` garantindo que nenhum dado real foi commitado
- [ ] Repositório privado criado e código publicado

**Checagem final de segurança:**
```bash
git log --oneline          # ver o que foi commitado
git diff HEAD~1            # verificar último commit
```
Samuel deve revisar o que está no repositório antes de confirmar conclusão.

---

## Marco de Conclusão do Projeto

Samuel estará pronto quando conseguir:

1. Abrir o repositório e explicar o projeto em 2 minutos para alguém de fora
2. Responder: "Qual a diferença entre LSTM e LightGBM para previsão de demanda?"
3. Dizer qual modelo usaria em produção e por quê
4. Apontar pelo menos uma coisa que faria diferente numa versão 2
