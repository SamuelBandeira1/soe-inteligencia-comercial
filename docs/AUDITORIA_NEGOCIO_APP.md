## Auditoria Estratégica — Consultor Estratégico

> Data: 2026-05-30
> Escopo: auditoria das 5 abas da aplicação Streamlit sob perspectiva de P&L, execução comercial e destravamento de carteira.

---

### 1. Avaliação de Cegueira de P&L por Aba

**Tab 1 — Visão Geral: CEGA para P&L**

A aba mostra pace % e gap vs. plano em volume (toneladas ou R$ de receita bruta). Não há qualquer indicação de margem. O problema concreto: um pace de 88% pode representar dois cenários radicalmente diferentes — (a) o gap é concentrado em produtos de alta margem, o que é um problema grave de resultado; (b) o gap é concentrado em produtos commodity de baixa margem, o que pode ser neutro ou até positivo se o mix remanescente for de maior MC. O sistema trata esses dois casos como idênticos. Para um gestor de P&L, são situações opostas.

Informação que falta: MC acumulada realizada vs. MC planejada acumulada, decomposta por família de produto. Sem isso, o "gap" exibido não tem significado financeiro.

**Tab 2 — Plano Comercial: CEGA para P&L, com ilusão de sofisticação**

Esta é a aba mais perigosa do sistema — não por ser simples, mas por parecer analítica enquanto omite as variáveis que importam.

- Alertas de exceção threshold-based sem peso de margem: uma exceção em um cliente T1 de alta MC_ton e uma exceção em um cliente T3 de baixa MC_ton recebem o mesmo destaque visual. Isso induz o time comercial a alocar atenção de forma ineficiente.
- What-if slider de Zona Líquida move volume, não margem: o gestor vê "se eu ativar 200 toneladas adicionais na Zona Líquida, o gap fecha X%". Não vê qual é o impacto em R$ de MC. Se as 200 toneladas disponíveis na Zona Líquida são de produtos abaixo do custo variável ajustado (ex.: produto com sobrecusto de frete), o "fechamento de gap" é uma deterioração de resultado.
- Scatter de oportunidade por propensity × volume: a dimensão volume no eixo Y deveria ser substituída ou complementada por MC_ton. Um cliente com propensity 0.8 e volume potencial de 50 ton de alta MC é mais valioso do que um cliente com propensity 0.9 e 200 ton de commodity.
- Tabela de clientes por propensity score: ordena por quem tem maior probabilidade de comprar, não por quem gera mais margem se comprar. Esses são critérios diferentes e a diferença importa na alocação de tempo do vendedor.

**Tab 3 — Demand Sensing: CEGA para P&L e DESCONECTADA da capacidade física**

O modelo Monte Carlo produz bandas de volume (P10–P90) para 8 semanas. Dois problemas críticos:

Primeiro: P50 de volume não é P50 de margem. Se o mix de produtos vendidos varia ao longo do horizonte de previsão (ex.: maior participação de itens especiais no início do período, menor no final), então a mesma banda de volume pode corresponder a margens radicalmente diferentes dependendo de qual semana é o período de análise. O sistema não faz essa tradução.

Segundo: o modelo é endógeno (histórico de volume próprio) sem sinais exógenos. Em aço e bens pesados, os principais drivers de demanda à frente do ciclo são: (a) carteira de obras de infraestrutura contratadas (dado público via SINAPI e editais), (b) índice de atividade da construção civil (IBGE/FGV), (c) variação de estoque nos distribuidores. Nenhum desses sinais está incorporado. O resultado é um modelo que prevê bem em mercados estáveis e falha precisamente quando a previsão mais importa — em pontos de inflexão de demanda.

**Tab 4 — Dashboard UF: CEGA para P&L e AUSENTE de inteligência de carteira**

O mapa de bolhas por estado mostra vol_ton. Não mostra margem por UF. Não mostra status de backlog por UF. Não mostra ordens bloqueadas por UF.

O problema prático: o estado de SP pode estar com pace acima de 100% porque está sendo abastecido com ordens de margens baixas (spot, frete longo, cliente T3), enquanto o estado de MG está com pace em 70% porque as ordens de alta MC estão travadas em bloqueio de produção. O mapa atual mostra SP como verde e MG como vermelho — a leitura inversa da realidade financeira.

**Tab 5 — Assertividade do Plano: CEGA para o custo financeiro do erro**

Mede MAPE, bias e acurácia de volume. Não mede o impacto financeiro do erro. Um erro de 10% na previsão de um produto de R$ 800/ton de MC é 8× mais grave do que um erro de 10% em um produto de R$ 100/ton de MC. O sistema trata os dois como equivalentes. Isso significa que as melhorias de processo motivadas por essa aba são direcionadas para reduzir erros de volume, não para reduzir erros de margem — que é o que de fato afeta o resultado.

---

### 2. Gap de Tomada de Decisão por Aba e Custo Aproximado

| Aba | Decisão que não pode ser tomada hoje | Custo estimado do gap |
|-----|--------------------------------------|------------------------|
| Tab 1 | Priorizar ações corretivas no gap de maior impacto em margem vs. gap de maior impacto em volume | 3–8% de MC mensal em decisões subótimas de priorização de esforço comercial |
| Tab 2 | Alocar tempo do vendedor por MC esperada vs. por propensity de volume; avaliar impacto real de ativação da Zona Líquida em resultado | Dispersão de esforço comercial em contas de baixo retorno; ativações de Zona Líquida com MC negativa |
| Tab 3 | Traduzir risco de demanda em risco de margem; incorporar sinais de mercado para antecipar inflexões | Reação tardia a quedas de demanda: estoque excessivo de produtos de baixa rotação construído com base em forecast endógeno otimista |
| Tab 4 | Identificar quais estados têm ordens bloqueadas de alta margem e acionar desbloqueio priorizado | Perda de MC por ordens T1/T2 bloqueadas não visíveis no instrumento de gestão territorial |
| Tab 5 | Direcionar melhoria de processo para redução de erro financeiro (não apenas de erro de volume) | Investimento de melhoria de processo direcionado para a dimensão errada; erro de mix não endereçado |

---

### 3. Gap de Destravamento de Carteira

Esta é a lacuna mais grave da aplicação. O conceito de "destravamento de carteira" — identificação, escalada e resolução de ordens bloqueadas — está completamente ausente.

O que está ausente e é padrão em qualquer S&OE funcional em indústria pesada:

**a) Visão de Backlog com Status de Bloqueio**: a aplicação não tem uma visão de carteira em aberto com status operacional de cada ordem (bloqueada / liberada / em produção / aguardando despacho). Sem isso, o gestor comercial não sabe quais ordens estão represando receita neste momento.

**b) Ranking de Ordens por MC_adj**: não existe. O sistema não calcula MC_ton por ordem, não aplica OTIF_weight por cliente, não desconta freight_cost_ton por modal disponível. A sequência de despacho é invisível para o sistema.

**c) Alertas de SLA Breach por Tipo de Bloqueio**: não existe. Ordens bloqueadas não têm owner, não têm SLA, não têm log de escalada. O processo de desbloqueio é integralmente manual e dependente de comunicação informal entre áreas.

**d) Exposição Financeira de Carteira Represada**: não existe um KPI de R$ de MC represada por ordens bloqueadas. Sem esse número, o Diretor Comercial não tem como dimensionar a urgência do problema.

**e) Conexão entre Forecast e Capacidade de Produção**: o Demand Sensing produz uma banda de volume, mas essa banda não é confrontada com a capacidade de laminação disponível no horizonte. A ferramenta pode recomendar ativação comercial de volume que a fábrica não conseguirá produzir — gerando OTIF breach estrutural por excesso de comprometimento comercial.

---

### 4. Restrições Comerciais Inegociáveis para o Arquiteto

As seguintes regras de negócio são não-negociáveis e devem estar embarcadas em qualquer refatoração:

**RC-01**: Todo ranking de cliente, ordem ou oportunidade deve ter MC_ton como dimensão primária. Propensity score, volume potencial e receita bruta são dimensões secundárias. Nenhuma tela deve apresentar uma lista de clientes ou ordens sem a coluna MC_ton visível e ativa como critério de ordenação padrão.

**RC-02**: O OTIF_weight deve ser calculado por cliente com base em dados históricos e deve ser atualizado no mínimo mensalmente. Não pode ser um campo estático ou uma estimativa pontual do KAM. Deve ser uma variável do sistema, não uma opinião do vendedor.

**RC-03**: Toda ativação de Zona Líquida no what-if (Tab 2) deve mostrar o delta de MC total resultante, não apenas o delta de volume. Se o delta de MC for negativo (a ativação piora o resultado por mix ou frete), o sistema deve emitir alerta explícito antes de confirmar a recomendação.

**RC-04**: O Dashboard UF (Tab 4) deve ter uma camada de backlog — quantas ordens estão bloqueadas por estado, qual é a exposição em MC, e qual é o tipo de bloqueio dominante. Essa camada é mais operacionalmente relevante do que o mapa de pace por UF.

**RC-05**: A Tab de Assertividade (Tab 5) deve calcular o erro financeiro ponderado por margem — não apenas o erro de volume. A métrica de referência é: MAPE_MC = soma(|MC_realizada - MC_prevista|) / soma(MC_prevista), por período e por família de produto.

**RC-06**: O sistema deve ter uma tela ou módulo dedicado a Destravamento de Carteira, com as quatro visões descritas na Seção 1.2 Part C deste documento: painel de bloqueios por tipo, sequência recomendada por MC_adj, escalada com log, e exposição financeira total represada.

---

## Auditoria Metodológica — Consultor Metodológico

> Data: 2026-05-30
> Escopo: integridade das definições métricas, pressupostos físicos dos modelos estatísticos, e rastreabilidade de dados nas 5 abas da aplicação Streamlit.

---

### 1. Diagnóstico de Integridade Metodológica

**Tab 1 — Visão Geral**: pace % e gap vs. plano são calculados sobre receita bruta ou volume físico. A métrica não tem definição unívoca documentada — dois analistas podem calcular valores diferentes a partir dos mesmos dados brutos dependendo da granularidade temporal e da base de plano usada (plano original, plano revisado, forecast mais recente). Isso invalida a auditabilidade do indicador.

**Tab 2 — Plano Comercial**: o propensity score não tem definição de variável-alvo documentada. "Propensão a comprar" pode significar probabilidade de qualquer compra no período, probabilidade de compra acima de um volume-mínimo, ou probabilidade de reativação de cliente inativo — são modelos diferentes com features diferentes. O modelo atual não documenta qual das três está sendo calculada. Adicionalmente, o threshold de exceção (alerta) não tem base estatística declarada — não é um quantil da distribuição histórica, não é um desvio-padrão, não tem justificativa metodológica rastreável.

**Tab 3 — Demand Sensing**: o modelo Monte Carlo produz intervalos P10–P90. Os pressupostos do modelo não estão documentados: (a) qual é a distribuição assumida para os resíduos — normal, log-normal, empírica?; (b) as simulações assumem independência temporal entre semanas ou há estrutura de autocorrelação?; (c) qual é o tamanho da janela de calibração e com que frequência o modelo é recalibrado? Sem esses parâmetros documentados, o intervalo P10–P90 não pode ser auditado e o usuário não tem como avaliar se está calibrado. Adicionalmente, o modelo é endógeno — utiliza exclusivamente histórico de volume interno, sem variáveis exógenas. Em mercados com drivers cíclicos externos (construção civil, infraestrutura), modelos endógenos têm viés estrutural em pontos de inflexão.

**Tab 4 — Dashboard UF**: vol_ton por UF não tem definição temporal documentada. Trata-se de volume faturado, volume despachado, volume em carteira confirmada, ou volume em carteira incluindo pedidos bloqueados? A diferença entre essas bases pode ser de 15–30% em períodos de alta de backlog, tornando o mapa geograficamente enganoso.

**Tab 5 — Assertividade do Plano**: MAPE calculado sobre volume físico sem ponderação por margem ou por relevância do SKU. Isso viola o princípio básico de que o custo do erro de previsão não é uniforme — um erro de 10% em um SKU de alta margem é financeiramente incomparável a um erro de 10% em um SKU commodity. A métrica atual não discrimina esses casos, tornando-a inadequada para priorizar esforço de melhoria de processo.

---

### 2. Hard Constraints para o Architect

**HC-01 — Definição Unívoca de MC_ton:** O sistema MUST calcular MC_ton como (Preço_NF - Custo_Variável_Ajustado) / Tonelagem_NF, onde Custo_Variável_Ajustado inclui obrigatoriamente frete_modal, comissão_comercial e desconto_financeiro, e esta fórmula MUST ser documentada e versionada no repositório como única fonte de verdade — nenhuma tela ou modelo pode usar uma definição alternativa de margem sem declarar explicitamente o desvio e obter aprovação do Consultor Metodológico.

**Desvio Aprovado (HC-01-DEV-01):**
- **Situação:** Dados de custo variável por família não disponíveis no pipeline atual.
- **Substituto aprovado:** `receita_ton = val_mm / vol_ton` (Receita por Tonelada, R$/t) como proxy financeiro secundário.
- **Condições:** (1) UI DEVE exibir rótulo "proxy de receita — não representa margem" em toda visualização financeira. (2) `vol_ton` permanece a dimensão primária de planejamento. (3) Desvio revisável quando dados de custo forem integrados ao pipeline.
- **Aprovado por:** Consultor Metodológico, 2026-05-30.
- **Aprovado por:** Usuário (decisão explícita, sessão 2026-05-30).

**HC-02 — Variável-Alvo do Propensity Score Declarada:** O modelo de propensity MUST ter sua variável-alvo definida explicitamente em documentação técnica antes de entrar em produção, especificando o evento modelado (ex.: P(compra ≥ X ton no horizonte H | features F)), o horizonte de previsão H, e o volume-limiar X — e o sistema MUST NOT exibir o score sem essa definição estar acessível ao usuário na própria interface como metadado do modelo.

**HC-03 — Pressupostos do Monte Carlo Documentados e Auditáveis:** O modelo Monte Carlo MUST ter documentação técnica versionada que declare: distribuição de resíduos assumida, estrutura de dependência temporal entre períodos, tamanho da janela de calibração, e frequência de recalibração — e o sistema MUST NOT apresentar intervalos de confiança (P10–P50–P90) sem que esses parâmetros sejam acessíveis ao usuário como metadado do modelo.

**HC-04 — Base Temporal de Dados Definida por Aba:** Cada indicador de volume ou receita exibido no sistema MUST ter sua base de cálculo explicitamente declarada na interface (faturado / despachado / carteira confirmada / carteira total incluindo bloqueados) — e o sistema MUST NOT exibir o mesmo conceito de "volume" com bases diferentes em abas distintas sem sinalização explícita ao usuário.

**HC-05 — MAPE Ponderado por Margem como Métrica Primária:** A Tab de Assertividade MUST calcular e exibir MAPE_MC = Σ(|MC_realizada_t - MC_prevista_t|) / Σ(MC_prevista_t) como métrica primária de qualidade de previsão — e o sistema MUST NOT apresentar MAPE de volume como métrica principal sem exibir em paralelo o MAPE_MC, dado que o custo do erro de previsão é proporcional à margem do produto, não ao volume físico.

**HC-06 — Threshold de Exceção com Base Estatística Rastreável:** Todo alerta de exceção exibido no sistema (Tab 2 e demais) MUST ter seu threshold definido com base em método estatístico documentado (ex.: percentil P95 da distribuição histórica de desvios, ou N desvios-padrão da média móvel de M períodos) — e o sistema MUST NOT usar thresholds fixos ou arbitrários sem que o critério de definição esteja documentado e revisável pelo Consultor Metodológico.

**HC-07 — OTIF_weight como Variável do Sistema, não Opinião do Vendedor:** O OTIF_weight por cliente MUST ser calculado automaticamente a partir de dados históricos de cumprimento de prazo e quantidade, atualizado com frequência mínima mensal, e armazenado como variável do sistema com log de versão — o sistema MUST NOT aceitar OTIF_weight como entrada manual do usuário comercial sem revisão e aprovação do responsável pelo processo de dados.

**HC-08 — Delta de MC em Toda Simulação What-if:** Qualquer funcionalidade de simulação ou what-if (incluindo slider de Zona Líquida na Tab 2) MUST calcular e exibir o delta de Margem de Contribuição total resultante do cenário simulado — e o sistema MUST NOT confirmar ou recomendar uma ação de ativação comercial sem que o delta de MC seja apresentado antes da confirmação, com alerta explícito se o delta for negativo.

**HC-09 — Sinais Exógenos com Correlação Documentada:** Qualquer variável exógena incorporada ao modelo de Demand Sensing MUST ter sua correlação histórica com a demanda interna documentada (coeficiente, janela de defasagem, período de calibração) antes da inclusão — e o sistema MUST NOT incorporar uma variável exógena como feature preditiva sem evidência quantitativa de correlação superior a |0,35| no horizonte de previsão relevante.

**HC-10 — Rastreabilidade de Versão de Plano:** O sistema MUST manter rastreabilidade da versão do plano usada como denominador em qualquer cálculo de gap ou pace (plano original, revisão R1, revisão R2, forecast mais recente) — e o sistema MUST NOT calcular gap vs. plano sem que a versão do plano esteja identificada na interface, pois a troca silenciosa de base de plano invalida a comparabilidade histórica de séries de pace.

---

### 3. Tabela de Cobertura de Constraints

| Constraint | Aplica-se a | Fase |
|---|---|---|
| HC-01 — Definição Unívoca de MC_ton | Tab 1, Tab 2, Tab 4, ETL, modelo de propensity, ranking de ordens | Fase 1 — Fundação de Dados |
| HC-02 — Variável-Alvo do Propensity Declarada | Tab 2, modelo de propensity score | Fase 1 — Fundação de Dados |
| HC-03 — Pressupostos do Monte Carlo Documentados | Tab 3, módulo de Demand Sensing | Fase 2 — Modelos Probabilísticos |
| HC-04 — Base Temporal de Dados por Aba | Tab 1, Tab 2, Tab 4, ETL de carteira | Fase 1 — Fundação de Dados |
| HC-05 — MAPE Ponderado por Margem | Tab 5, módulo de Assertividade | Fase 3 — Métricas de Qualidade |
| HC-06 — Threshold de Exceção com Base Estatística | Tab 2, sistema de alertas | Fase 2 — Modelos Probabilísticos |
| HC-07 — OTIF_weight como Variável do Sistema | Tab 2, ranking de ordens, módulo de Destravamento | Fase 1 — Fundação de Dados |
| HC-08 — Delta de MC em Toda Simulação What-if | Tab 2, toda funcionalidade de simulação | Fase 2 — Modelos Probabilísticos |
| HC-09 — Sinais Exógenos com Correlação Documentada | Tab 3, módulo de Demand Sensing | Fase 2 — Modelos Probabilísticos |
| HC-10 — Rastreabilidade de Versão de Plano | Tab 1, Tab 5, ETL de plano | Fase 1 — Fundação de Dados |

---

### 5. Trade-offs a Surfacear para o Usuário (Conflitos com o Consultor Metodológico)

Os conflitos abaixo são previsíveis entre a agenda de processo e a agenda comercial. Devem ser apresentados ao usuário para decisão explícita — não resolvidos unilateralmente pelo Arquiteto:

**Trade-off 1 — Granularidade de MC_ton vs. Disponibilidade de Dados**
A agenda comercial exige MC_ton por SKU extraída do ERP por NF histórica. A agenda metodológica pode recomendar uma abordagem mais gradual (MC por família de produto primeiro, SKU depois). O risco da abordagem gradual: MC por família é média que esconde a variação intra-família — exatamente onde estão as decisões de priorização. Posição do Consultor Estratégico: implementar MC_ton por SKU desde o início, mesmo que requeira integração ERP mais complexa. Fazer pela metade invalida a lógica de priorização.

**Trade-off 2 — Velocidade de Escalada vs. Governança de Processo**
A agenda comercial exige escalada em 4–24 horas dependendo do tipo de bloqueio. A agenda metodológica pode recomendar fluxos de aprovação com mais camadas (comitê semanal de crédito, reunião de S&OE como fórum de desbloqueio). O risco da governança pesada: ordens T1 bloqueadas por crédito não podem esperar um comitê semanal — a multa contratual começa a correr antes do próximo comitê. Posição do Consultor Estratégico: fluxos de escalada devem ter SLA definidos por tier, com by-pass de comitê para ordens T1 com exposição acima de threshold financeiro definido pelo Diretor Comercial.

**Trade-off 3 — Recomendação de Sequência de Despacho vs. Autonomia do PCP**
A agenda comercial exige que o sistema produza uma sequência recomendada de despacho por MC_adj. Isso pode conflitar com a autonomia do PCP, que otimiza sequência por critério de produção (setup mínimo, aproveitamento de forno, sequência de bitola). Posição do Consultor Estratégico: o sistema deve mostrar ambas as sequências lado a lado — a sequência ótima por MC_adj e a sequência ótima por custo de produção — e calcular o delta financeiro entre as duas. A decisão final é do PCP com ciência do custo de oportunidade comercial. O que não é aceitável é o PCP decidir sem ver esse delta.

**Trade-off 4 — Incorporação de Sinais Exógenos no Forecast vs. Complexidade de Manutenção**
A agenda comercial exige sinais exógenos no modelo de Demand Sensing (carteira de obras, indicadores de construção, estoque de distribuidores). A agenda metodológica pode recomendar manter o modelo endógeno por simplicidade de manutenção e auditabilidade. O risco do modelo endógeno: é o modelo que mais falha precisamente quando a previsão mais importa — em inflexões de demanda. O custo de uma inflexão não prevista em aço é alto: estoque excessivo construído próximo ao pico ou falta de capacidade comprometida próximo ao vale. Posição do Consultor Estratégico: pelo menos um sinal exógeno de alta correlação (ex.: IPCA-construção ou índice de licitações de obras) deve ser incorporado no horizonte de 4 a 8 semanas, mesmo que isso aumente a complexidade do modelo. A simplicidade de manutenção não é um argumento válido para manter um modelo com viés estrutural.

---

### 6. Avaliação de Impacto Estratégico

| Dimensão | Score | Justificativa |
|----------|-------|---------------|
| P&L Visibility | BAIXO | Nenhuma aba opera com MC como métrica primária |
| Destravamento de Carteira | AUSENTE | Funcionalidade completamente inexistente na aplicação atual |
| Qualidade de Decisão Comercial | MÉDIO | Plano Comercial tem estrutura correta mas variáveis erradas |
| Demand Sensing | MÉDIO-BAIXO | Modelo técnico válido mas sem tradução financeira e sem sinais exógenos |
| Governança de Execução | BAIXO | Sem SLA, sem log de escalada, sem responsabilização por bloqueio |

**Veredicto**: a aplicação atual é um sistema de reporte de volume com estética analítica. Ela informa mas não decide. Para se tornar um instrumento de S&OE operacional, precisa de duas mudanças estruturais: (1) MC_ton como coluna vertebral de todos os rankings e alertas, e (2) um módulo de Destravamento de Carteira com as funcionalidades descritas na Seção 1.2 Part C deste documento.

---
