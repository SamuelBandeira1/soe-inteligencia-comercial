# Requirements Document

## Introduction

O Sistema de Inteligência Comercial Semanal é uma aplicação Streamlit que transforma coordenadores comerciais de reativos em proativos. Atualmente, os coordenadores esperam clientes ligarem para fazer pedidos. O sistema fornece inteligência para saber **para quem ligar e quando**, baseado em padrões históricos de compra e análise de propensão.

O sistema possui três módulos principais:
1. **Painel de Ritmo Semanal** (já implementado) - monitora performance vs meta S&OE
2. **Score de Propensão** - identifica clientes com maior probabilidade de comprar
3. **Lista de Ação** - prioriza contatos comerciais por linha de produto

## Requirements

### Requirement 1: Score de Propensão de Compra Semanal

**User Story:** Como coordenador comercial, eu quero ver um score de propensão de compra para cada cliente por linha de produto e UF, para que eu possa priorizar meus contatos comerciais baseado em dados históricos e posição do mês, ou seja, se eu estiver na penúltima semana, e uma linha de produtos estiver muito abaixo, essa inteligencia me forneça quem ligar que provavelmente vai comprar.

#### Acceptance Criteria

1. WHEN o usuário acessa a aba "Score de Propensão" THEN o sistema SHALL exibir uma tabela com clientes ranqueados por score de propensão, tem que ser explícito como é o cálculo do score e oque diz que aquele cliente é bom realmente para comprar
2. WHEN o sistema calcula o score THEN SHALL considerar recência da última compra, frequência histórica, volume médio e sazonalidade, geralmente quem está comprando continua comprando, clientes que ja deixaram de comprar 2 meses já estão com risco de perdermos
3. WHEN um cliente não comprou nos últimos 90 dias THEN o score SHALL ser penalizado proporcionalmente ao tempo sem comprar
4. WHEN um cliente tem padrão sazonal conhecido THEN o score SHALL ser ajustado baseado no mês atual
5. IF o cliente comprou nos últimos 7 dias THEN o score SHALL ser fortemente penalizado (reduzido em 70%) para evitar contatos desnecessários
6. IF o cliente comprou entre 8 e 30 dias atrás THEN o score SHALL ser moderadamente penalizado (reduzido em 20%) pois já está no ciclo de compra do mês, se ele já comprou dentro do mês atual, deixar o maior score para os que não compraram ainda
6. WHEN o usuário filtra por linha de produto THEN o sistema SHALL recalcular scores específicos para aquela linha, e para UF também deve ser possível filtrar
7. WHEN o usuário filtra por região/UF THEN o sistema SHALL mostrar apenas clientes daquela localização

### Requirement 2: Lista de Ação Comercial

**User Story:** Como coordenador comercial, eu quero uma lista priorizada de clientes para contatar por linha de produto, para que eu possa focar meus esforços nos prospects com maior potencial de conversão. Traga para cada cliente o fornecedor que mais o atende, para que eu ja consiga direcionar para meu vendedor entrar em contato.

#### Acceptance Criteria

1. WHEN o usuário acessa a aba "Lista de Ação" THEN o sistema SHALL exibir top 20 clientes ou a tabela completa/selecionável para contatar por linha selecionada
2. WHEN o sistema gera a lista THEN SHALL combinar score de propensão com potencial de volume baseado no histórico, mostrar métricas, gráfico do cliente de evolução histórica de compras, materiais mais comprados, preço médio que o cliente compra, preço médio atual, média móvel, dados estatísticos.
3. WHEN um cliente está na lista THEN o sistema SHALL mostrar: nome, último pedido, volume médio, telefone/contato e motivo da recomendação personalizado para cada cliente
4. WHEN o usuário marca um cliente como "contatado" THEN o sistema SHALL remover da lista atual e registrar a ação num excel exportável.
5. WHEN o sistema detecta cliente com padrão de compra atrasado THEN SHALL priorizar na lista com flag "URGENTE", clientes com mais de 65 dias sem comprar devem ter essa flag.
6. WHEN o usuário exporta a lista THEN o sistema SHALL gerar arquivo Excel com dados completos para uso offline
7. IF não há dados suficientes para um cliente THEN o sistema SHALL indicar "Dados insuficientes" em vez de score incorreto, possibilidade de ajustar o cálculo do score dentro da ferramente escolhendo as métricas de histórico utilizado x recencia x frequencia em caixas de texto e um botão para calcular e trazer as métricas estatísticas do modelo com a tabela.

### Requirement 3: Filtros e Navegação Avançada

**User Story:** Como coordenador comercial, eu quero filtrar dados por múltiplas dimensões simultaneamente, para que eu possa analisar segmentos específicos do meu portfólio. tem que ter um filtro global, e filtros para os níveis que eu quiser ver, família, linha, grupo, fornecedor, cliente, gerencia, empresa.

#### Acceptance Criteria

1. WHEN o usuário aplica filtros THEN todos os módulos (Ritmo, Score, Lista) SHALL refletir a seleção consistentemente
2. WHEN o usuário seleciona múltiplas linhas de produto THEN o sistema SHALL agregar dados mantendo a granularidade necessária
3. WHEN o usuário altera filtro de período THEN o sistema SHALL recalcular scores e listas automaticamente
4. WHEN filtros resultam em dataset vazio THEN o sistema SHALL exibir mensagem clara "Nenhum dado encontrado para os filtros selecionados"
5. WHEN o usuário limpa filtros THEN o sistema SHALL retornar ao estado padrão (todos os dados)

### Requirement 4: Performance e Experiência do Usuário

**User Story:** Como usuário do sistema, eu quero que as análises carreguem rapidamente e a interface seja intuitiva, para que eu possa usar o sistema eficientemente no dia a dia e rapidamente, quero que o sistema tenha interface atrativa, bonita e com os dados a mostra, rótulos bem formatados, indicativos, números visíveis e elegancia.

#### Acceptance Criteria

1. WHEN o usuário carrega qualquer aba THEN o sistema SHALL exibir dados em menos de 4 segundos
2. WHEN dados estão sendo processados THEN o sistema SHALL mostrar indicador de loading com progresso
3. WHEN ocorre erro no carregamento THEN o sistema SHALL exibir mensagem de erro clara e sugestão de ação
4. WHEN o usuário navega entre abas THEN o estado dos filtros SHALL ser preservado
5. WHEN o sistema detecta dados desatualizados THEN SHALL exibir aviso com timestamp da última atualização
6. WHEN o usuário acessa via mobile THEN a interface SHALL ser responsiva e funcional

### Requirement 5: Integração de Dados e Qualidade

**User Story:** Como analista responsável pelo sistema, eu quero garantir que os dados estejam sempre atualizados e consistentes, para que as recomendações sejam confiáveis.

#### Acceptance Criteria

1. WHEN o sistema inicia THEN SHALL validar integridade dos arquivos de dados (vendas, meta, clientes)
2. WHEN dados de cliente estão ausentes THEN o sistema SHALL usar dados agregados sem comprometer a análise
3. WHEN há inconsistências entre vendas e meta THEN o sistema SHALL registrar warnings no log
4. WHEN novos dados são carregados THEN o sistema SHALL invalidar cache automaticamente
5. IF dados críticos estão corrompidos THEN o sistema SHALL falhar graciosamente com mensagem explicativa
6. WHEN o sistema processa dados históricos THEN SHALL manter pelo menos 24 meses de histórico para cálculos de sazonalidade