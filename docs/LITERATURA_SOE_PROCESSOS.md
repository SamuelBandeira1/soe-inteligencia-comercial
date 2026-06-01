
## Section 1.2 — Gestão de Carteira e Backlog: Priorização por Margem de Contribuição e OTIF

> Contribuição: Consultor Estratégico

---

### Part A — Critérios de Priorização: A Fórmula MC_adj

A priorização de backlog em indústrias de aço e bens pesados não pode ser feita por receita por tonelada. Receita por tonelada é uma métrica de faturamento, não de resultado. Uma ordem de 500 toneladas de laminado especial pode ter receita/ton menor do que uma ordem de aço commodity, mas margem de contribuição três vezes superior após dedução dos custos variáveis de produção. Priorizar pela métrica errada é equivalente a esvaziar o caixa enquanto parecer ocupado.

**A métrica correta é a Margem de Contribuição por Tonelada (MC_ton):** receita líquida por tonelada menos custos variáveis diretos (matéria-prima, energia, consumíveis de laminação, embalagem). Não inclui rateio de fixos — esses não mudam com a decisão de despacho.

A priorização final utiliza a fórmula ajustada:

```
MC_adj = (MC_ton × OTIF_weight) - freight_cost_ton - setup_cost_amortized
```

**MC_ton**: margem de contribuição unitária em R$/ton, calculada por SKU (bitola, especificação, acabamento). Deve ser extraída do ERP por nota fiscal histórica — não estimada por família de produto, pois a variação intra-família pode ser superior a 40%.

**OTIF_weight**: multiplicador que reflete o custo de não-entrega no prazo para aquele cliente. Definido por tier:

| Tier | Perfil do Cliente | OTIF_weight | Consequência de OTIF breach |
|------|-------------------|-------------|------------------------------|
| T1 | Contas estratégicas com cláusula contratual de SLA | 1.30–1.50 | Multa contratual (0,5–2% do valor da NF por dia) + risco de perda de quota de fornecimento |
| T2 | Contas-chave sem cláusula formal mas com histórico de represália comercial | 1.10–1.25 | Perda estimada de 15–30% do volume futuro daquele cliente |
| T3 | Spot / transacional, sem histórico de recompra relevante | 1.00 | Desconto de renegociação ou cancelamento sem consequência sistêmica |

O OTIF_weight não é estimativa subjetiva — deve ser calculado com base em (a) histórico de penalidades pagas por cliente nos últimos 12 meses e (b) análise de churn: clientes que reduziram volume após episódios de OTIF breach.

**freight_cost_ton**: custo de frete por tonelada para aquela ordem específica. Não usar custo médio de frete por região — a variação por tipo de veículo, peso da carga, distância e sazonalidade de disponibilidade de carreteiro torna a média inutilizável. Para cada ordem em backlog, o sistema deve calcular o custo de frete com base no modal disponível e na janela de entrega exigida.

**setup_cost_amortized**: custo de setup de laminação amortizado por tonelada da ordem, quando aquela ordem exige troca de bitola, cilindros ou ajuste de forno. Em aciaria integrada, um changeover pode custar entre R$ 80 mil e R$ 350 mil em tempo parado, refugo de ajuste e desgaste antecipado de ferramental. Para ordens que podem ser agrupadas em sequência de laminação compatível, o setup_cost_amortized é zero. Para ordens isoladas que exigem changeover exclusivo, o custo deve ser dividido pelo volume da ordem.

**Regra de ouro operacional**: quando o ranking por MC_adj divergir do ranking por receita bruta em mais de 3 posições para uma mesma semana de despacho, a divergência deve ser apresentada explicitamente ao Gerente Comercial e ao PCP antes da confirmação da sequência. Esse momento de decisão é onde se ganha ou se perde margem real.

---

### Part B — Taxonomia de Ordens Bloqueadas e Protocolo de Desbloqueio

Ordem bloqueada é ordem que existe no sistema, tem demanda confirmada do cliente, mas não flui para faturamento. Cada dia de ordem bloqueada é um dia de capital imobilizado sem receita. Em empresas com ciclo de caixa apertado, backlog bloqueado é equivalente funcional a inadimplência.

#### Tipo 1 — Bloqueio de Crédito

**Definição**: o cliente ultrapassou o limite de crédito aprovado ou está com títulos vencidos acima do threshold de tolerância da política de crédito.

**Escalation owner**: Gerente de Crédito e Cobrança, com co-responsabilidade do Gerente de Conta (KAM).

**SLA de resolução**: 24 horas para clientes T1 e T2. 48 horas para T3.

**Consequência de SLA miss**: para T1, cada dia de atraso gera risco de acionamento de cláusula de OTIF; para T2, risco de o cliente acionar alternativa de mercado; para T3, liberar a capacidade para ordens T1/T2 desbloqueadas.

**Protocolo**: o sistema deve exibir valor em aberto do cliente, percentual de utilização do limite e histórico de pagamentos dos últimos 6 meses diretamente na tela de escalada.

#### Tipo 2 — Bloqueio de Frete

**Definição**: não há transportadora disponível para a janela de entrega contratada, ou o custo de frete disponível excede o threshold de viabilidade da ordem (MC_adj < zero após freight_cost_ton real).

**Escalation owner**: Gerente de Logística/Transporte, com alerta ao Gerente Comercial quando a causa é inviabilidade econômica.

**SLA de resolução**: 4 horas para identificação de alternativa logística. 8 horas para decisão comercial quando não há alternativa dentro do threshold.

**Consequência de SLA miss**: quando o frete spot necessário para cumprir o prazo elimina a margem da ordem, a decisão correta pode ser renegociar o prazo com o cliente. Essa decisão não pode ser tomada pela logística — é uma decisão comercial.

**Protocolo**: o sistema deve calcular automaticamente o breakeven de frete para cada ordem bloqueada — qual é o máximo de freight_cost_ton que mantém MC_adj > 0 — e apresentar isso ao Gerente de Logística antes da busca por alternativas.

#### Tipo 3 — Bloqueio de Produção

**Definição**: não há slot de laminação, montagem ou processamento disponível dentro da janela de entrega comprometida com o cliente.

**Escalation owner**: PCP (Planejamento e Controle da Produção), com escalada ao Diretor Industrial quando o bloqueio afeta ordens T1.

**SLA de resolução**: 48 horas para replanejamento de sequência. 72 horas para decisão de comunicação ao cliente quando não há solução operacional.

**Consequência de SLA miss**: para T1, passadas 72 horas sem resolução, o Diretor Comercial deve assumir a comunicação com o cliente — não delegar ao KAM. A narrativa de um atraso gerenciado proativamente preserva o relacionamento; a descoberta tardia pelo cliente aciona penalidade retroativa.

**Protocolo**: o sistema deve mostrar o custo de oportunidade do bloqueio — qual é a MC total represada pela produção bloqueada, não apenas o volume. Isso força o PCP a ponderar reprogramação por critério financeiro, não apenas por FIFO.

#### Tipo 4 — Bloqueio Documental

**Definição**: a ordem está produzida e disponível para despacho, mas não pode ser faturada por ausência de: Nota Fiscal, certificado de qualidade (laudo de ensaio), autorização de inspeção do cliente, ou licença de transporte para cargas especiais.

**Escalation owner**: Analista de Faturamento / Qualidade / Logística Especial, dependendo do documento faltante.

**SLA de resolução**: NF — 2 horas. Certificado de qualidade — 4 horas. Inspeção de terceiros — agendamento com no mínimo 5 dias úteis de antecedência do despacho planejado.

**Consequência de SLA miss**: produto acabado em estoque gera custo de carregamento e não gera receita. Em períodos de alta demanda, um produto acabado parado por bloqueio documental pode representar a perda de um slot de produção futuro.

---

### Part C — Requisitos de Dashboard para Inteligência de Backlog

O que um dashboard de gestão de backlog **deve mostrar** para gerar decisão executiva:

**1. Painel de Ordens Bloqueadas por Tipo (visão em tempo real)**
- Contagem de ordens bloqueadas: total e por tipo (crédito / frete / produção / documental)
- Volume bloqueado em toneladas por tipo
- **Exposição financeira por tipo**: MC_adj × volume × dias em bloqueio — essa métrica responde quanto estamos deixando de faturar por causa de cada bloqueio específico
- Aging do bloqueio com semáforo vermelho para ordens que já ultrapassaram o SLA de resolução definido

**2. Sequência Recomendada de Despacho**
- Ranking das próximas ordens a despachar, ordenado por MC_adj — não por data de entrada, não por tamanho do pedido
- Para cada ordem: cliente, tier OTIF, data de comprometimento, janela de entrega restante, MC_adj calculado, tipo de bloqueio se houver, owner da resolução
- Alerta visual quando a sequência sugerida por MC_adj conflita com a sequência atual do PCP

**3. Escalada com Um Clique**
- Para cada ordem bloqueada: ação de escalada que gera automaticamente uma notificação para o owner correto, com contexto pré-preenchido (cliente, valor, MC exposta, SLA restante)
- Log de escalada com timestamp: quem escalou, quando, qual foi a resposta e em quanto tempo
- Sem log de escalada não há responsabilização — e sem responsabilização o SLA é fictício

**4. Exposição Total de Carteira Represada**
- KPI de topo: R$ de MC total represada por ordens bloqueadas (soma de todos os tipos)
- Comparação com a semana anterior e com a meta de carteira fluída definida pelo Diretor Comercial
- Decomposição por causa raiz: qual tipo de bloqueio representa a maior exposição financeira nesta semana

**O que um dashboard visualmente atraente mas inútil para decisão mostra:**
- Mapa com bolhas coloridas por estado sem cruzamento com status de bloqueio
- Distribuição de volume por região sem margem (nenhuma decisão operacional emerge disso)
- KPI de "pace %" sem desagregação por margem — um pace de 95% composto inteiramente de ordens T3 de baixa margem é um desastre silencioso
- Tabela de clientes ordenada por propensity score sem indicação de tier OTIF ou MC_ton

A distinção não é estética. É operacional. O dashboard inútil é um relatório de situação. O dashboard correto é um instrumento de decisão. A diferença entre os dois é medida em R$ de MC faturada por semana.

---
