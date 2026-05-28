# DOC 2 — Arquitetura Técnica do Projeto

## Visão Geral

O projeto constrói um modelo LSTM para previsão de demanda mensal por família de produto, usando dados históricos de vendas da Aço Cearense. O resultado é comparado diretamente com o modelo LightGBM já em produção.

---

## Stack Técnica

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Deep Learning | **PyTorch** | Mais usado em mercado/pesquisa, mais didático que Keras para aprender o que acontece por baixo |
| Tracking de experimentos | **MLflow** | Padrão de mercado, gratuito, roda local |
| Manipulação de dados | **pandas + numpy** | Já domina |
| Visualização | **matplotlib + seaborn** | Gráficos de série temporal e comparação |
| Ambiente | **venv + requirements.txt** | Simples, reproduzível, sem overhead de Docker ainda |
| Versionamento | **Git + GitHub** | Já configurado |

**Por que PyTorch e não Keras/TensorFlow?**
Keras é mais simples de começar, mas esconde demais. Com PyTorch, Samuel vai entender o loop de treino, o que é um tensor, como o gradiente flui. Isso torna o aprendizado mais sólido e é o que o mercado de pesquisa e empresas tech usam.

---

## Estrutura de Pastas do Repositório

```
lstm-forecast-demanda/
│
├── data/
│   ├── raw/                  # dados originais — NÃO versionar se sensível
│   ├── processed/            # dados após preprocessing
│   └── .gitkeep
│
├── notebooks/
│   ├── 01_exploracao.ipynb   # EDA da série temporal
│   ├── 02_baseline.ipynb     # LightGBM baseline para comparação
│   ├── 03_lstm_v1.ipynb      # Primeiro modelo LSTM
│   └── 04_comparacao.ipynb   # Resultados finais lado a lado
│
├── src/
│   ├── data_prep.py          # pipeline de preparação de dados
│   ├── model.py              # arquitetura LSTM em PyTorch
│   ├── train.py              # loop de treino
│   ├── evaluate.py           # métricas e visualizações
│   └── config.py             # hiperparâmetros centralizados
│
├── mlruns/                   # experimentos MLflow (não versionar)
├── outputs/                  # gráficos e resultados exportados
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Arquitetura do Modelo LSTM

### Versão 1 (Módulo 1) — Many-to-One simples
```
Input: janela de 12 meses de histórico
       [vendas_t-12, ..., vendas_t-1] + features sazonais

LSTM Layer 1: hidden_size=64, dropout=0.2
LSTM Layer 2: hidden_size=32, dropout=0.2
Linear Layer: output_size=1 (próximo mês)
```

### Versão 2 (Módulo 2) — Encoder-Decoder multi-step
```
Encoder: lê janela histórica de 12 meses
Decoder: gera previsão para os próximos 3 meses
         (mais útil para S&OP que só prevê 1 mês)
```

**Por que começar simples?**
Many-to-one é mais fácil de debugar. Se o modelo não aprende nada aqui, há problema nos dados ou na preparação — identificar isso antes de complicar a arquitetura poupa horas.

---

## Dados de Entrada

**Séries a modelar (por ordem de prioridade):**
1. CA-50 (maior volume, mais histórico)
2. CA-60
3. Fio-máquina
4. Consolidado geral

**Features de entrada:**
- Vendas (volume) dos últimos N meses — lag features
- Mês do ano (sazonalidade) — sin/cos encoding
- Indicadores de tendência: variação mês a mês
- Flag de mês especial (janeiro, julho, dezembro — padrões conhecidos no setor)

**O que NÃO entra nos dados do GitHub:**
- Valores de venda reais com nome de clientes
- Qualquer coluna identificável de cliente/vendedor
- O que entra: séries agregadas por família de produto (sem dado pessoal)

---

## Métricas de Avaliação

| Métrica | O que mede | Por que usar |
|---|---|---|
| **MAPE** | Erro percentual médio | Comparável entre famílias com volumes diferentes |
| **WAPE** | MAPE ponderado por volume | Mais justo para itens de alto volume |
| **Bias** | Tendência de super/subestimar | Importante para planejamento de estoque |
| **MAE** | Erro absoluto médio | Fácil de comunicar para gestores |

**Benchmark a bater:** resultado do LightGBM atual nos mesmos dados de teste.

---

## .gitignore essencial

```
data/raw/
data/processed/
mlruns/
*.pkl
*.pt          # modelos treinados (pesados)
__pycache__/
.env
venv/
*.ipynb_checkpoints
outputs/      # opcional: gráficos gerados localmente
```
