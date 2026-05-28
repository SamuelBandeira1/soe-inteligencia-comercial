# Requirements Document — S&OE v2 Melhorias

## Introduction

Após revisão técnica do Sistema de Inteligência Comercial S&OE, foram identificados bugs críticos, gargalos de performance, oportunidades de recalibração do score de propensão e limpeza de código legado. Este documento cobre as melhorias necessárias para levar o sistema de "funcional" para "produção robusta".

O sistema atual possui 3 abas: Venda vs Plano S&OP, Venda vs Programa S&OE, e Score de Propensão. A base de dados tem 1.7M linhas, 73k clientes únicos, mediana de inatividade de 665 dias.

## Requirements

### Requirement 1: Correção de Bugs Críticos

**User Story:** Como usuário do dashboard, quero que filtros vazios e cálculos silenciosos sejam tratados de forma consistente, para que o sistema não me engane com dados que parecem certos mas estão errados.

#### Acceptance Criteria

1. WHEN o usuário deseleciona todas as opções de um filtro multiselect THEN o sistema SHALL exibir mensagem clara "Selecione ao menos uma opção" e interromper a renderização — NÃO retornar a base completa silenciosamente
2. WHEN o `PropensaoEngine` é instanciado com `data_referencia` THEN as estatísticas internas (médias, percentis, p90, p75) SHALL ser calculadas relativas a essa data, garantindo consistência temporal para backtests
3. WHEN o sistema carrega dados THEN SHALL usar caminhos relativos via `Path(__file__)`, NÃO caminhos hardcoded com nome de usuário Windows
4. WHEN `groupby.apply` é usado em pandas 3.x THEN SHALL passar `include_groups=False` ou ser refatorado para `groupby([...])[[cols]].agg(...)`
5. WHEN o módulo `ritmo_semanal.py` usa `timedelta` THEN SHALL importá-lo no topo do arquivo, não via `__import__('datetime').timedelta` inline dentro de função

### Requirement 2: Performance com 1.7M Linhas

**User Story:** Como coordenador, quero que cada aba carregue em menos de 3 segundos, para que eu possa navegar entre análises sem perder o ritmo de trabalho.

#### Acceptance Criteria

1. WHEN o sistema converte `dia/mes/ano` em `semana_mes` para registros pós-2026 THEN SHALL usar lookup vetorizado (merge contra tabela de combinações únicas) em vez de `df.apply(axis=1)` que chama Python linha-a-linha
2. WHEN `calcular_scores(linha='CA-50')` é executado na base completa THEN o tempo SHALL ser inferior a 1 segundo
3. WHEN o usuário troca de aba sem mudar filtros THEN nenhum recálculo de engine SHALL ocorrer — verificar via hash do DataFrame no `session_state`
4. WHEN funções de calendário TW existem em múltiplos arquivos THEN SHALL existir em apenas um módulo (`utils/calendar_tw.py`) para evitar divergência silenciosa

### Requirement 3: Recalibração do Score de Propensão

**User Story:** Como coordenador, quero um score que mantenha significado absoluto entre filtros e dias, e tiers dinâmicos (QUENTE/MORNO/FRIO/DORMENTE) que sempre me deem pelo menos uma dezena de prospects acionáveis.

#### Acceptance Criteria

1. WHEN o sistema calcula o score THEN SHALL retornar score absoluto 0–100 SEM normalização min-max global — o mesmo cliente SHALL ter o mesmo score independente do filtro aplicado
2. WHEN o sistema classifica clientes THEN SHALL usar tier dinâmico baseado em percentis P25/P50/P75 da população filtrada:
   - QUENTE: score ≥ P75 E 31 ≤ dias ≤ 100
   - MORNO: score ≥ P50 E dias ≤ 180
   - FRIO: score ≥ P25
   - DORMENTE: demais casos
3. WHEN um cliente tem primeira compra nos últimos 60 dias THEN SHALL ser flagged com badge "NOVO" e não passar pelas regras normais de penalidade de inatividade
4. WHEN uma linha tem menos de 6 meses de histórico THEN SHALL ser flagged com tier "INDEFINIDO" — não comparável com linhas maduras
5. WHEN o sistema calcula score de frequência THEN SHALL usar `min(25, freq × 60)` para dar peso adequado a clientes bimestrais (freq=0.5 → 25 pts, freq=0.25 → 15 pts)
6. WHEN o sistema calcula score de volume THEN SHALL usar transformação logarítmica `min(20, log1p(vol/mediana) × c)` em vez de linear, para evitar que outliers de volume achate os demais
7. WHEN clientes têm >365 dias inativos E ≤3 compras no histórico total THEN SHALL ser excluídos do ranqueamento principal e mostrados em seção separada "Reativação Profunda"
8. WHEN a penalidade de recência é aplicada para clientes que compraram nos últimos 7 dias THEN o multiplicador SHALL ser ×0.60 (não ×0.30) — penalidade menos agressiva para não eliminar clientes que podem ampliar pedido

### Requirement 4: Lookup de Nomes de Clientes e Fornecedores

**User Story:** Como coordenador, quero ver o NOME do cliente na tabela de propensão, não apenas o código, para que eu possa agir imediatamente sem precisar consultar outro sistema.

#### Acceptance Criteria

1. WHEN o script `atualiza_dados.py` é executado THEN SHALL gerar `clientes.parquet` com colunas `cd_cliente, nome_cliente, telefone, email` a partir dos dados disponíveis
2. WHEN o sistema carrega dados THEN SHALL fazer left join com `clientes.parquet` para enriquecer o DataFrame de vendas
3. IF `clientes.parquet` não existir THEN o sistema SHALL exibir warning e usar `cd_cliente` como fallback, sem quebrar a aplicação
4. WHEN a tabela de Score de Propensão é exibida THEN SHALL mostrar `nome_cliente` em vez de `cd_cliente` quando disponível

### Requirement 5: Limpeza de Código Legado e Organização

**User Story:** Como mantenedor do código, quero que o repositório contenha apenas o que está em produção, para que novos desenvolvedores não percam tempo entendendo código morto.

#### Acceptance Criteria

1. WHEN o repositório é auditado THEN os arquivos `app/engines/acao_engine.py`, `app/modules/lista_acao.py` e `tests/test_acao_engine.py` SHALL ser removidos
2. WHEN o `dashboard.py` é carregado THEN SHALL importar apenas módulos efetivamente utilizados — remover `from modules import lista_acao`
3. WHEN funções utilitárias de calendário TW são definidas THEN SHALL existir em apenas um arquivo `utils/calendar_tw.py`, importado por `dashboard.py` e `ritmo_semanal.py`
4. WHEN funções de cor e formatação visual são definidas (cor_ritmo, icone_ritmo, _fmt_ton, paleta) THEN SHALL existir em apenas um arquivo `utils/visual.py`
5. WHEN constantes de negócio são definidas (LINHAS_EXCLUIR, FAMILIA_OVERRIDE, MAPA_NOME_LINHA) THEN SHALL estar em `app/config.py`, não espalhadas em `dashboard.py`

### Requirement 6: UX da Aba Score de Propensão

**User Story:** Como coordenador, quero entender em 1 segundo qual cliente priorizar e por quê, sem precisar interpretar tabelas longas de 100 linhas.

#### Acceptance Criteria

1. WHEN a aba Score é renderizada THEN SHALL mostrar 4 seções visuais (QUENTE/MORNO/FRIO/DORMENTE) com cards por cliente em vez de tabela monolítica
2. WHEN um cliente aparece no Score THEN SHALL incluir `acao_sugerida` (ex: "Ligar agora — cliente regular atrasado 52 dias")
3. WHEN os ícones das abas são definidos THEN a aba S&OE SHALL usar ícone diferente da aba Score (📊 para S&OE, 🎯 para Score)
4. WHEN o usuário acessa a aba Score pela primeira vez na sessão THEN o expander "Como o score é calculado?" SHALL aparecer expandido (controlado por `session_state`)
5. WHEN a tabela/cards de Score são exibidos THEN SHALL incluir coluna `tendencia` (volume últimos 3m vs média 12m) com seta ↑↓→

### Requirement 7: Validação e Backtest do Score

**User Story:** Como cientista de dados responsável pelo sistema, quero conseguir validar o score com dados históricos para confirmar que ele realmente prediz compras.

#### Acceptance Criteria

1. WHEN `PropensaoEngine(df, data_referencia=X)` é instanciado THEN o resultado SHALL ser idêntico ao que seria gerado se rodado na data X — sem leakage temporal (nenhuma estatística interna usa dados após X)
2. WHEN um script de backtest é executado com `data_ref = M-1` THEN SHALL comparar top 20 do score contra clientes que efetivamente compraram em M e calcular precision@20
3. WHEN o sistema tem mais de 18 meses de histórico THEN o script de backtest SHALL conseguir rodar para os últimos 6 meses e gerar tabela de precision@20 por mês
