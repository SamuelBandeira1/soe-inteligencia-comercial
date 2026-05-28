# Design Document

## Overview

O Sistema de Inteligência Comercial Semanal é uma aplicação Streamlit multi-aba que transforma dados históricos de vendas em insights acionáveis para coordenadores comerciais. O sistema utiliza análise de padrões temporais, cálculo de propensão de compra e priorização inteligente para guiar ações comerciais proativas.

A arquitetura segue o padrão já estabelecido no módulo de Ritmo Semanal, mantendo consistência na estrutura de dados, filtros e experiência do usuário.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                       │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Ritmo Semanal │ Score Propensão │    Lista de Ação        │
│   (implementado)│   (novo módulo) │    (novo módulo)        │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                  Data Processing Layer                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Cálculo Ritmo  │ Engine Propensão│  Gerador Lista Ação     │
│                 │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│ vendas_filtrada │  meta_semanal   │   dados_clientes        │
│   .parquet      │    .parquet     │     .parquet            │
└─────────────────┴─────────────────┴─────────────────────────┘
```

### Component Structure

O sistema mantém a estrutura modular existente e adiciona novos componentes:

```python
app/
├── dashboard.py              # Aplicação principal (existente)
├── modules/
│   ├── __init__.py
│   ├── ritmo_semanal.py     # Módulo existente (refatorado)
│   ├── score_propensao.py   # Novo módulo
│   └── lista_acao.py        # Novo módulo
├── engines/
│   ├── __init__.py
│   ├── propensao_engine.py  # Lógica de cálculo de propensão
│   └── acao_engine.py       # Lógica de geração de lista
└── utils/
    ├── __init__.py
    ├── data_loader.py       # Carregamento de dados (existente)
    ├── filters.py           # Sistema de filtros compartilhado
    └── formatters.py        # Formatação de dados (existente)
```

## Components and Interfaces

### 1. Score Propensão Engine

**Responsabilidade:** Calcular score de propensão de compra para cada cliente por linha de produto.

**Interface:**
```python
class PropensaoEngine:
    def __init__(self, df_vendas: pd.DataFrame, df_clientes: pd.DataFrame = None):
        """Inicializa engine com dados históricos de vendas."""
        
    def calcular_scores(self, 
                       linha: str = None, 
                       regiao: str = None,
                       data_referencia: date = None) -> pd.DataFrame:
        """
        Retorna DataFrame com colunas:
        - cliente_id, cliente_nome, linha, regiao, uf
        - score_propensao (0-100)
        - ultima_compra, dias_sem_comprar
        - volume_medio_mensal, frequencia_compras
        - motivo_score (explicação do score)
        """
        
    def _calcular_recencia_score(self, dias_sem_comprar: int) -> float:
        """Score baseado em recência (0-30 pontos)."""
        
    def _calcular_frequencia_score(self, freq_historica: float) -> float:
        """Score baseado em frequência histórica (0-25 pontos)."""
        
    def _calcular_sazonalidade_score(self, cliente_id: str, mes_atual: int) -> float:
        """Score baseado em padrão sazonal do cliente (0-25 pontos)."""
        
    def _calcular_volume_score(self, volume_medio: float, linha: str) -> float:
        """Score baseado em potencial de volume (0-20 pontos)."""
```

**Algoritmo de Score:**
- **Recência (30%):** Penaliza clientes que não compram há muito tempo
  - 0-30 dias: 30 pontos
  - 31-60 dias: 20 pontos  
  - 61-90 dias: 10 pontos
  - 90+ dias: 0 pontos
- **Frequência (25%):** Premia clientes com compras regulares
  - Baseado na média de compras por mês nos últimos 12 meses
- **Sazonalidade (25%):** Ajusta score baseado no padrão sazonal do cliente
  - Analisa meses históricos de maior atividade do cliente
- **Volume (20%):** Considera potencial de volume baseado no histórico
  - Normalizado por linha de produto

### 2. Lista de Ação Engine

**Responsabilidade:** Gerar lista priorizada de clientes para contato comercial.

**Interface:**
```python
class AcaoEngine:
    def __init__(self, propensao_engine: PropensaoEngine, df_vendas: pd.DataFrame):
        """Inicializa com engine de propensão e dados de vendas."""
        
    def gerar_lista_acao(self, 
                        linha: str,
                        regiao: str = None,
                        limite: int = 20) -> pd.DataFrame:
        """
        Retorna DataFrame com top clientes para contatar:
        - cliente_id, cliente_nome, telefone, email
        - score_propensao, volume_potencial
        - ultima_compra, dias_sem_comprar
        - motivo_contato, prioridade (URGENTE/ALTA/MÉDIA)
        - acao_sugerida
        """
        
    def _calcular_prioridade(self, score: float, dias_sem_comprar: int) -> str:
        """Determina prioridade baseada em score e recência."""
        
    def _gerar_motivo_contato(self, cliente_data: dict) -> str:
        """Gera explicação do motivo para contatar o cliente."""
        
    def marcar_contatado(self, cliente_id: str, data_contato: date, observacoes: str = ""):
        """Registra que cliente foi contatado (para futuras implementações)."""
```

**Lógica de Priorização:**
1. **URGENTE:** Score > 70 E dias_sem_comprar > 45 (cliente regular atrasado)
2. **ALTA:** Score > 60 OU (volume_potencial > média_linha E score > 40)
3. **MÉDIA:** Score entre 30-60
4. **Filtrados:** Score < 30 (baixa probabilidade)

### 3. Sistema de Filtros Compartilhado

**Responsabilidade:** Gerenciar estado de filtros entre todas as abas.

**Interface:**
```python
class FilterManager:
    def __init__(self):
        """Inicializa gerenciador de filtros usando session_state."""
        
    def render_sidebar_filters(self, df_vendas: pd.DataFrame) -> dict:
        """
        Renderiza filtros na sidebar e retorna dict com seleções:
        - empresas: List[str]
        - linhas: List[str] 
        - regioes: List[str]
        - ufs: List[str]
        - periodo_inicio: date
        - periodo_fim: date
        """
        
    def apply_filters(self, df: pd.DataFrame, filters: dict) -> pd.DataFrame:
        """Aplica filtros ao DataFrame."""
        
    def get_current_filters(self) -> dict:
        """Retorna filtros atualmente aplicados."""
```

## Data Models

### 1. Modelo de Dados de Propensão

```python
@dataclass
class ClientePropensao:
    cliente_id: str
    cliente_nome: str
    linha: str
    regiao: str
    uf: str
    score_propensao: float  # 0-100
    ultima_compra: date
    dias_sem_comprar: int
    volume_medio_mensal: float
    frequencia_compras: float  # compras por mês
    motivo_score: str
    telefone: str = None
    email: str = None
```

### 2. Modelo de Lista de Ação

```python
@dataclass
class ItemListaAcao:
    cliente_id: str
    cliente_nome: str
    linha: str
    score_propensao: float
    volume_potencial: float
    ultima_compra: date
    dias_sem_comprar: int
    prioridade: str  # URGENTE/ALTA/MÉDIA
    motivo_contato: str
    acao_sugerida: str
    telefone: str = None
    email: str = None
    contatado: bool = False
    data_ultimo_contato: date = None
```

### 3. Estrutura de Dados Existente (mantida)

Os dados já carregados continuam com a mesma estrutura:
- `df_vendas`: vendas históricas com dimensões empresa/linha/região/UF/data
- `df_meta`: metas semanais S&OP e S&OE
- Cálculos de peso semanal e projeções mantidos

## Error Handling

### 1. Tratamento de Dados Ausentes

```python
def handle_missing_data(df: pd.DataFrame, required_columns: List[str]) -> pd.DataFrame:
    """
    Trata dados ausentes com estratégias específicas:
    - Clientes sem telefone: marca como "Contato não disponível"
    - Vendas sem cliente_id: agrupa como "Cliente não identificado"
    - Datas inválidas: remove registros com log de warning
    """
```

### 2. Validação de Integridade

```python
def validate_data_integrity(df_vendas: pd.DataFrame, df_meta: pd.DataFrame) -> List[str]:
    """
    Valida integridade dos dados e retorna lista de warnings:
    - Vendas sem meta correspondente
    - Períodos com gaps nos dados
    - Clientes com padrões anômalos (volume muito alto/baixo)
    """
```

### 3. Fallbacks Graceful

- **Sem dados de cliente:** Sistema funciona com dados agregados
- **Período insuficiente:** Aviso de "Dados limitados" com score reduzido
- **Erro de cálculo:** Score padrão de 50 com motivo "Erro no cálculo"

## Testing Strategy

### 1. Testes Unitários

```python
# test_propensao_engine.py
def test_calcular_recencia_score():
    """Testa cálculo de score de recência."""
    
def test_calcular_frequencia_score():
    """Testa cálculo de score de frequência."""
    
def test_score_integration():
    """Testa integração completa do cálculo de score."""

# test_acao_engine.py  
def test_gerar_lista_acao():
    """Testa geração de lista de ação."""
    
def test_prioridade_calculation():
    """Testa cálculo de prioridades."""
```

### 2. Testes de Integração

```python
def test_filter_consistency():
    """Testa se filtros são aplicados consistentemente em todas as abas."""
    
def test_data_flow():
    """Testa fluxo completo: dados → propensão → lista de ação."""
```

### 3. Testes de Performance

```python
def test_score_calculation_performance():
    """Garante que cálculo de scores termina em < 3 segundos."""
    
def test_large_dataset_handling():
    """Testa comportamento com datasets grandes (>100k registros)."""
```

## Implementation Notes

### 1. Refatoração Necessária

O código atual em `dashboard.py` (1549 linhas) precisa ser refatorado:

1. **Extrair módulo de Ritmo Semanal** para `modules/ritmo_semanal.py`
2. **Criar sistema de filtros compartilhado** em `utils/filters.py`
3. **Modularizar carregamento de dados** em `utils/data_loader.py`

### 2. Estrutura de Abas

```python
# Estrutura principal das abas
tab1, tab2, tab3 = st.tabs(["📊 Ritmo Semanal", "🎯 Score Propensão", "📋 Lista de Ação"])

with tab1:
    ritmo_semanal.render(df_filtered, filters)
    
with tab2:
    score_propensao.render(df_filtered, filters)
    
with tab3:
    lista_acao.render(df_filtered, filters)
```

### 3. Cache Strategy

```python
@st.cache_data(ttl=3600)  # Cache por 1 hora
def calcular_scores_propensao(df_vendas_hash: str, filters: dict):
    """Cache de scores de propensão."""
    
@st.cache_data(ttl=1800)  # Cache por 30 minutos  
def gerar_lista_acao_cache(scores_hash: str, linha: str):
    """Cache de lista de ação."""
```

### 4. Configurações

```python
# config.py
SCORE_WEIGHTS = {
    'recencia': 0.30,
    'frequencia': 0.25, 
    'sazonalidade': 0.25,
    'volume': 0.20
}

PRIORIDADE_THRESHOLDS = {
    'urgente': {'score_min': 70, 'dias_min': 45},
    'alta': {'score_min': 60, 'volume_percentil': 75},
    'media': {'score_min': 30}
}

CACHE_TTL = {
    'scores': 3600,  # 1 hora
    'lista_acao': 1800,  # 30 minutos
    'dados_base': 7200  # 2 horas
}
```