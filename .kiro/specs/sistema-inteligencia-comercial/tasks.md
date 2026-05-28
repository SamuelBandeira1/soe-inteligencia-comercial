# Implementation Plan

- [x] 1. Refatorar código existente para estrutura modular



  - Extrair lógica do Ritmo Semanal do dashboard.py principal para módulo separado
  - Criar sistema de filtros compartilhado que pode ser usado por todas as abas
  - Implementar data loader centralizado para carregamento e cache de dados
  - _Requirements: 3.4, 4.4_

- [x] 1.1 Criar estrutura de diretórios e módulos base



  - Criar diretórios app/modules/, app/engines/, app/utils/
  - Implementar arquivos __init__.py para todos os módulos
  - Criar classes base e interfaces para engines de propensão e ação
  - _Requirements: 4.1, 5.1_

- [x] 1.2 Extrair e modularizar sistema de filtros

  - Criar FilterManager class em utils/filters.py
  - Implementar render_sidebar_filters() para renderizar filtros na sidebar
  - Implementar apply_filters() para aplicar filtros consistentemente aos DataFrames
  - Migrar lógica de filtros existente do dashboard.py para o novo sistema
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 1.3 Refatorar módulo de Ritmo Semanal existente



  - Extrair código de ritmo semanal para modules/ritmo_semanal.py
  - Criar função render() que aceita dados filtrados e renderiza a aba completa
  - Manter todas as funcionalidades existentes (gauges, gráficos, cards)
  - Testar que funcionalidade existente não foi quebrada
  - _Requirements: 4.4_

- [x] 2. Implementar engine de cálculo de propensão de compra



  - Criar PropensaoEngine class com algoritmo de scoring baseado em recência, frequência, sazonalidade e volume
  - Implementar cálculo de score de recência (0-30 pontos baseado em dias sem comprar)
  - Implementar cálculo de score de frequência (0-25 pontos baseado em compras por mês)
  - Implementar cálculo de score de sazonalidade (0-25 pontos baseado em padrão mensal do cliente)
  - _Requirements: 1.2, 1.3, 1.4_

- [x] 2.1 Implementar cálculo de score de recência


  - Criar método _calcular_recencia_score() que penaliza clientes sem comprar há muito tempo
  - Implementar lógica: 0-30 dias = 30pts, 31-60 dias = 20pts, 61-90 dias = 10pts, 90+ dias = 0pts
  - Escrever testes unitários para validar cálculo de recência
  - _Requirements: 1.3_

- [x] 2.2 Implementar cálculo de score de frequência e sazonalidade

  - Criar método _calcular_frequencia_score() baseado na média de compras por mês nos últimos 12 meses
  - Criar método _calcular_sazonalidade_score() que analisa meses históricos de maior atividade do cliente
  - Implementar normalização de scores para escala 0-100
  - Escrever testes unitários para validar cálculos
  - _Requirements: 1.4_

- [x] 2.3 Implementar cálculo de score de volume e integração final

  - Criar método _calcular_volume_score() normalizado por linha de produto
  - Implementar método calcular_scores() que combina todos os componentes do score
  - Adicionar geração de motivo_score explicando o score calculado
  - Implementar tratamento para clientes com dados insuficientes
  - _Requirements: 1.2, 1.7_

- [x] 3. Implementar interface de Score de Propensão



  - Criar módulo score_propensao.py com interface Streamlit para exibir scores de clientes
  - Implementar tabela ranqueada de clientes por score de propensão
  - Adicionar filtros por linha de produto e região específicos para propensão
  - Implementar indicadores visuais de score (cores, ícones) para facilitar interpretação
  - _Requirements: 1.1, 1.6, 1.7_

- [x] 3.1 Criar interface básica de Score de Propensão


  - Implementar função render() em modules/score_propensao.py
  - Criar tabela com colunas: cliente, linha, região, score, última compra, motivo
  - Implementar ordenação por score decrescente
  - Adicionar formatação de cores baseada no score (verde/amarelo/vermelho)
  - _Requirements: 1.1_

- [x] 3.2 Implementar filtros específicos para Score de Propensão

  - Integrar FilterManager para filtros de linha de produto e região
  - Implementar recálculo automático de scores quando filtros mudam
  - Adicionar filtro de período para análise histórica
  - Implementar tratamento quando filtros resultam em dataset vazio
  - _Requirements: 1.6, 1.7, 3.3, 3.4_

- [x] 3.3 Adicionar funcionalidades avançadas de Score de Propensão

  - Implementar penalização de score para clientes que compraram na semana atual
  - Adicionar métricas resumo: total de clientes, score médio, distribuição por faixa
  - Implementar exportação de dados de propensão para Excel
  - Adicionar tooltips explicativos para ajudar usuários a interpretar scores
  - _Requirements: 1.5_

- [x] 4. Implementar engine de geração de Lista de Ação



  - Criar AcaoEngine class que combina scores de propensão com potencial de volume
  - Implementar lógica de priorização (URGENTE/ALTA/MÉDIA) baseada em score e recência
  - Implementar geração de motivos de contato personalizados para cada cliente
  - Criar sistema de ações sugeridas baseado no perfil do cliente
  - _Requirements: 2.2, 2.4, 2.5_

- [x] 4.1 Implementar lógica de priorização de clientes


  - Criar método _calcular_prioridade() com regras: URGENTE (score>70 E dias>45), ALTA (score>60 OU volume alto), MÉDIA (score 30-60)
  - Implementar cálculo de volume_potencial baseado no histórico do cliente
  - Criar método _gerar_motivo_contato() que explica por que contatar o cliente
  - Escrever testes unitários para validar lógica de priorização
  - _Requirements: 2.5_

- [x] 4.2 Implementar geração de lista de ação completa

  - Criar método gerar_lista_acao() que retorna top 20 clientes priorizados
  - Implementar filtro por linha de produto específica
  - Adicionar dados de contato (telefone, email) quando disponíveis
  - Implementar tratamento para casos sem dados suficientes
  - _Requirements: 2.1, 2.2, 2.3, 2.7_

- [x] 4.3 Implementar funcionalidade de marcação de contatos

  - Criar método marcar_contatado() para registrar ações comerciais
  - Implementar persistência de dados de contatos realizados
  - Adicionar lógica para remover clientes contatados da lista atual
  - Preparar estrutura para futuras funcionalidades de CRM
  - _Requirements: 2.4_

- [x] 5. Implementar interface de Lista de Ação



  - Criar módulo lista_acao.py com interface Streamlit para exibir lista priorizada
  - Implementar seletor de linha de produto para gerar lista específica
  - Adicionar funcionalidade de exportação da lista para Excel
  - Implementar interface para marcar clientes como contatados
  - _Requirements: 2.1, 2.3, 2.4, 2.6_

- [x] 5.1 Criar interface básica de Lista de Ação


  - Implementar função render() em modules/lista_acao.py
  - Criar seletor de linha de produto na parte superior da aba
  - Implementar tabela com top 20 clientes: nome, score, prioridade, último pedido, motivo
  - Adicionar indicadores visuais de prioridade (badges coloridos)
  - _Requirements: 2.1, 2.3_

- [x] 5.2 Implementar funcionalidades de ação e exportação

  - Adicionar botões "Marcar como Contatado" para cada cliente na lista
  - Implementar exportação da lista para Excel com dados completos
  - Adicionar campos de observações para registrar resultado do contato
  - Implementar atualização automática da lista após marcar contatos
  - _Requirements: 2.4, 2.6_

- [x] 5.3 Adicionar métricas e insights da Lista de Ação

  - Implementar cards com métricas: total de prospects, distribuição por prioridade
  - Adicionar gráfico de potencial de volume por prioridade
  - Implementar alertas para clientes com padrão "URGENTE"
  - Adicionar histórico de contatos realizados (preparação para futuras versões)
  - _Requirements: 2.5_

- [x] 6. Integrar módulos e implementar navegação final



  - Integrar todos os módulos no dashboard.py principal com sistema de abas
  - Implementar consistência de filtros entre todas as abas
  - Adicionar sistema de cache para otimizar performance
  - Implementar tratamento de erros e validação de dados em toda a aplicação
  - _Requirements: 3.1, 4.1, 4.2, 4.3, 5.2_

- [x] 6.1 Integrar sistema de abas e navegação


  - Modificar dashboard.py para usar estrutura de 3 abas: Ritmo, Score, Lista
  - Implementar preservação de estado de filtros ao navegar entre abas
  - Integrar FilterManager para aplicar filtros consistentemente
  - Testar navegação completa entre todas as funcionalidades
  - _Requirements: 3.1, 4.4_

- [x] 6.2 Implementar sistema de cache e otimização de performance


  - Adicionar @st.cache_data para cálculos de propensão (TTL 1 hora)
  - Implementar cache para lista de ação (TTL 30 minutos)
  - Otimizar carregamento de dados para garantir < 3 segundos por aba
  - Adicionar indicadores de loading durante processamento
  - _Requirements: 4.1, 4.2_

- [x] 6.3 Implementar tratamento de erros e validação final


  - Adicionar validação de integridade de dados na inicialização
  - Implementar tratamento graceful para dados ausentes ou corrompidos
  - Adicionar mensagens de erro claras e sugestões de ação
  - Implementar logs de warning para inconsistências de dados
  - _Requirements: 4.3, 5.1, 5.3, 5.4, 5.5, 5.6_

- [x] 7. Testes finais e documentação





  - Escrever testes unitários para todos os engines (PropensaoEngine, AcaoEngine)
  - Implementar testes de integração para fluxo completo de dados
  - Criar testes de performance para garantir requisitos de velocidade
  - Documentar APIs e criar guia de uso para coordenadores comerciais
  - _Requirements: 4.1, 4.2, 4.3_