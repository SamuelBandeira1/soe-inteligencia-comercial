# Implementation Plan — S&OE v2 Melhorias

- [x] 1. Setup e limpeza de legado


- [x] 1.1 Salvar lógica legada e remover arquivos mortos

  - Copiar o conteúdo de `_gerar_acao_sugerida` e `_gerar_motivo_contato` de `acao_engine.py` para comentário no topo de `propensao_engine.py` (referência para task 6.2)
  - Deletar `app/engines/acao_engine.py`
  - Deletar `app/modules/lista_acao.py`
  - Deletar `tests/test_acao_engine.py`
  - Remover linha `from modules import lista_acao` em `dashboard.py`
  - Deletar `data/processed/contatos_realizados.json` se existir
  - Verificar que o dashboard ainda importa sem erros após remoção
  - _Requirements: 5.1, 5.2_

- [x] 1.2 Criar app/config.py com constantes de negócio



  - Criar arquivo com `ROOT`, `DATA_PROCESSED`, `LINHAS_EXCLUIR`, `MAPA_NOME_LINHA`, `FAMILIA_OVERRIDE`
  - Adicionar `PENALIDADES_RECENCIA`, `REATIVACAO_PROFUNDA_DIAS`, `CLIENTE_NOVO_DIAS`, `LINHA_HISTORICO_MIN_MESES`
  - Atualizar `dashboard.py` para importar constantes de `config` em vez de defini-las inline
  - _Requirements: 5.5_

- [-] 1.2b Aplicar LINHAS_EXCLUIR no atualiza_dados.py

  - Importar `LINHAS_EXCLUIR` de `config` no script de atualização
  - Filtrar linhas excluídas antes de salvar `vendas_filtrada.parquet`
  - Remover o filtro duplicado em runtime em `carrega_dados()` se existir
  - _Requirements: 5.5_

- [x] 1.3 Criar app/utils/calendar_tw.py


  - Mover `get_month_tw_ranges` e `day_to_semana_tw` de `dashboard.py` para o novo módulo
  - Implementar `vectorize_semana_tw(years, months, days)` usando lookup table (drop_duplicates + merge)
  - Atualizar imports em `dashboard.py` e `ritmo_semanal.py` para usar `utils.calendar_tw`
  - Remover funções duplicadas de `dashboard.py` e `ritmo_semanal.py`
  - Escrever teste unitário comparando `vectorize_semana_tw` com `day_to_semana_tw` linha-a-linha
  - _Requirements: 2.4, 5.3_

- [x] 1.4 Criar app/utils/visual.py



  - Buscar `def _fmt_ton` em todos os módulos antes de migrar (está em pelo menos 4 arquivos)
  - Mover paleta de cores (`COR_PRIMARIA`, `COR_ACENTO`, etc.) para o novo módulo
  - Mover `cor_ritmo`, `icone_ritmo`, `cor_bg_ritmo`, `seta_tendencia`, `_fmt_ton`
  - Atualizar imports em `dashboard.py`, `ritmo_semanal.py`, `score_propensao.py` — commit por arquivo migrado
  - Verificar que nenhuma função de cor ficou duplicada após migração
  - _Requirements: 5.4_

- [ ] 2. Correções de bugs críticos (P0)
- [ ] 2.1 Corrigir caminho hardcoded em dashboard.py
  - Substituir `OUT = r'C:\Users\samuel.bandeira\...'` por `Path(__file__).resolve().parent.parent / 'data' / 'processed'`
  - Garantir que o mesmo padrão é usado em `atualiza_dados.py` (já usa `Path`, verificar)
  - Testar que o dashboard carrega corretamente após a mudança
  - _Requirements: 1.3_

- [ ] 2.2 Corrigir filtros vazios que retornam base completa silenciosamente
  - Substituir o padrão `empresa_sel = empresa_sel if empresa_sel else todos` por guard com `st.warning` + `st.stop()`
  - Aplicar para `empresa_sel`, `regiao_sel` e `uf_sel`
  - Testar manualmente: deselecionar tudo deve mostrar warning, não dados
  - _Requirements: 1.1_

- [ ] 2.3 Corrigir import inline de timedelta em ritmo_semanal.py
  - Remover `__import__('datetime').timedelta(...)` da linha ~40
  - Garantir `from datetime import timedelta` no topo do arquivo
  - Verificar que não há outros imports inline no arquivo
  - _Requirements: 1.5_

- [ ] 2.4 Corrigir groupby.apply sem include_groups em ritmo_semanal.py
  - Localizar todos os `groupby(...).apply(lambda g: ...)` no arquivo
  - Refatorar para `groupby([...])[[cols]].agg(...)` onde possível
  - Onde apply for inevitável, adicionar `include_groups=False`
  - _Requirements: 1.4_

- [ ] 3. Performance — vetorização
- [ ] 3.1 Substituir apply(axis=1) em carrega_dados() por vectorize_semana_tw
  - Importar `vectorize_semana_tw` de `utils.calendar_tw`
  - Substituir o bloco `df_v[post_mask].apply(lambda r: day_to_semana_tw(...), axis=1)`
  - Medir tempo antes e depois — confirmar redução de >80% (de ~5s para <100ms)
  - _Requirements: 2.1, 2.2_

- [ ] 3.2 Verificar e reforçar guard de hash em score_propensao.render
  - Confirmar que `_get_engine` (ou equivalente) usa `session_state` com hash do `df_filt`
  - Adicionar teste que simula troca de aba sem mudar filtros e verifica que o engine NÃO é reconstruído (via mock ou contador interno `_build_count`)
  - Se guard não existir, implementar: calcular hash via `pd.util.hash_pandas_object`, armazenar no `session_state`
  - _Requirements: 2.3_

- [ ] 4. Recalibração do score de propensão
- [ ] 4.1 Mover data_referencia para PropensaoEngine.__init__
  - Adicionar parâmetro `data_referencia=None` no `__init__`
  - Salvar como `self.data_ref`
  - Usar `self.data_ref` em todos os cortes temporais em `_preparar_dados` (remover `pd.Timestamp.today()` interno)
  - Remover `data_referencia` de `calcular_scores` (ou emitir `DeprecationWarning` e ignorar)
  - Atualizar todos os testes para passar `data_referencia` no construtor
  - _Requirements: 1.2, 7.1_

- [ ] 4.2 Remover normalização min-max final
  - Localizar e remover o bloco de normalização min-max em `calcular_scores`
  - Score final = score_bruto (já 0–100 pela soma dos componentes + penalidade)
  - Verificar que `test_score_entre_0_e_100` ainda passa
  - Rodar com dados reais e imprimir distribuição (mean, median, max, count por faixa) — não avançar para 4.3 sem validar
  - _Requirements: 3.1_

- [ ] 4.3 Atualizar fórmula de frequência para min(25, freq × 60)
  - Substituir `(freq / freq_ref) × 25` por `(freq * 60.0).clip(0, 25)`
  - Remover dependência de `_freq_p90_linha` (não mais necessário)
  - Atualizar testes de frequência
  - Verificar com dados reais: cliente bimestral (freq=0.5) deve ter ~25 pts
  - Imprimir distribuição após mudança — não avançar para 4.4 sem validar
  - _Requirements: 3.5_

- [ ] 4.4 Atualizar fórmula de volume para logarítmica
  - Calcular `mediana_vol` dos clientes ativos por linha em `_preparar_dados`
  - Substituir fórmula linear por `np.log1p(vol / mediana) × c_vol`
  - Calibrar `c_vol` para que `vol = mediana × 5` dê ~15 pts
  - Atualizar testes de volume
  - _Requirements: 3.6_

- [ ] 4.4b Validação empírica da distribuição após 4.2 + 4.3 + 4.4
  - Rodar engine completa com `data_ref=today` na base real
  - Imprimir: mean, median, max, count(≥70), count(40–69), count(<40) por segmento de inatividade
  - ACEITAÇÃO: pelo menos 5% dos clientes ativos (0–100d) em cada faixa (alto/médio/baixo)
  - Se distribuição quebrar, ajustar `c_vol` ou multiplicador de frequência antes de continuar
  - _Requirements: 3.1, 3.5, 3.6_

- [ ] 4.5 Reduzir peso de sazonalidade de 25 para 15 pts e adicionar componente tendência
  - Ajustar `score_saz` para clip em 15 (fallback = 7.5)
  - Implementar `_calcular_tendencia` vetorizado (sem `.apply` linha-a-linha):
    - Pré-computar `vol_3m` e `vol_12m` por cliente via groupby em `_preparar_dados`
    - `ratio = vol_3m / (vol_12m / 4)` — 1.0 = mantém ritmo
    - `score = np.clip(ratio * 5, 0, 10)` — ratio≥2.0 → 10pts, ratio=1.0 → 5pts, ratio=0 → 0pts
  - Adicionar `score_tendencia` ao score final
  - Verificar que soma máxima ainda é 100 (30+25+15+10+20=100)
  - _Requirements: 6.5_

- [ ] 4.6 Implementar tier dinâmico com ordem de precedência correta
  - Calcular p25, p50, p75 de `score_propensao` por população retornada
  - Implementar `_classificar_tier` com ordem de precedência obrigatória:
    1. Linha < 6m histórico → INDEFINIDO (sobrescreve tudo)
    2. Primeira compra ≤ 60d → NOVO
    3. dias ≥ 365 E compras_total ≤ 3 → REATIVACAO
    4. score ≥ p75 E 31 ≤ dias ≤ 100 → QUENTE
    5. score ≥ p50 E dias ≤ 180 → MORNO
    6. score ≥ p25 → FRIO
    7. demais → DORMENTE
  - Adicionar coluna `tier` à saída de `calcular_scores`
  - Escrever testes: população com scores conhecidos deve gerar tiers corretos
  - _Requirements: 3.2, 3.3, 3.4, 3.7_

- [ ] 4.7 Implementar flags NOVO e REATIVACAO_PROFUNDA
  - Calcular `primeira_compra` (data mínima) por cliente em `_preparar_dados`
  - `flag_novo = (self.data_ref - primeira_compra).days <= 60`
  - `flag_reativacao_profunda = (dias >= 365) & (compras_total <= 3)`
  - Clientes NOVO não recebem penalidade de inatividade
  - Adicionar colunas ao output de `calcular_scores`
  - _Requirements: 3.3, 3.7_

- [ ] 4.8 Ajustar penalidade de recência para ×0.60 nos primeiros 7 dias
  - Alterar multiplicador de `0.30` para `0.60` para `dias <= 7`
  - Atualizar teste `test_penalidade_compra_recente`
  - _Requirements: 3.8_

- [ ] 4.9 Flag INDEFINIDO para linhas com pouco histórico
  - Calcular `meses_distintos` por linha em `_preparar_dados`
  - Se linha tiver < 6 meses de histórico, tier = "INDEFINIDO" (via `_classificar_tier`)
  - Não calcular sazonalidade para essas linhas (usar fallback 7.5)
  - _Requirements: 3.4_

- [ ] 5. Lookup de nomes de clientes e fornecedores
- [ ] 5.1 Estender atualiza_dados.py para gerar clientes.parquet
  - Extrair `cd_cliente` únicos do DataFrame unificado
  - Gerar `nome_cliente` como placeholder ("Cliente XXXXX") até ter fonte real — documentar como TODO
  - Salvar `clientes.parquet` com colunas: `cd_cliente, nome_cliente, telefone, email`
  - _Requirements: 4.1_

- [ ] 5.2 Carregar clientes.parquet em carrega_dados()
  - Adicionar leitura de `clientes.parquet` com try/except
  - Se arquivo ausente: `st.warning` + retornar DataFrame vazio
  - Retornar `df_clientes` junto com `df` e `df_v`
  - _Requirements: 4.2, 4.3_

- [ ] 5.3 Aplicar lookup de nomes em score_propensao.render
  - Fazer merge de `df_scores` com `df_clientes` (left join em `cd_cliente`)
  - Usar `nome_cliente` quando disponível, fallback para `cd_cliente`
  - Exibir `nome_cliente` na tabela/cards em vez do código
  - _Requirements: 4.4_

- [ ] 5.4 Estender atualiza_dados.py para gerar fornecedores.parquet
  - Extrair `cd_fornecedor` únicos do DataFrame unificado
  - Gerar `nome_fornecedor` placeholder ("Forn. XXXXX")
  - Salvar `fornecedores.parquet` com colunas: `cd_fornecedor, nome_fornecedor`
  - _Requirements: 4.1_

- [ ] 5.5 Aplicar lookup de fornecedor em score_propensao.render
  - Merge `df_scores` com `df_fornecedores` em `cd_fornecedor` (left join)
  - Exibir `nome_fornecedor` com código entre parênteses se ambíguo
  - Fallback para `cd_fornecedor` se lookup ausente
  - _Requirements: 4.3_

- [ ] 6. UX da aba Score de Propensão
- [ ] 6.1 Substituir tabela monolítica por seções de tier
  - Criar função `_render_tier_section(df_tier, tier, cor, icone)` que exibe cards
  - Renderizar 4 colunas (QUENTE/MORNO/FRIO/DORMENTE) com top 5 por tier
  - Adicionar botão "Ver todos" que expande lista completa do tier
  - Seção separada para NOVO e REATIVACAO
  - _Requirements: 6.1_

- [ ] 6.2 Adicionar acao_sugerida nos cards
  - Usar a lógica copiada de `acao_engine.py` na task 1.1 como referência
  - Implementar `_gerar_acao_sugerida` em `propensao_engine.py` baseado em tier + dias + frequencia
  - Exibir em cada card de cliente
  - _Requirements: 6.2_

- [ ] 6.3 Corrigir ícones duplicados nas abas
  - Mudar ícone da aba S&OE de "🎯" para "📊"
  - Manter "🎯" apenas para Score de Propensão
  - _Requirements: 6.3_

- [ ] 6.4 Expander de explicação aberto na primeira sessão
  - Usar `st.session_state` com chave `score_explicacao_vista`
  - Se chave não existe: `expanded=True` + setar flag
  - Nas sessões seguintes: `expanded=False`
  - _Requirements: 6.4_

- [ ] 6.5 Adicionar coluna tendência nos cards/tabela
  - Usar `score_tendencia` calculado na task 4.5
  - Exibir seta ↑↓→ em cada cliente: ↑ se ratio > 1.2, ↓ se ratio < 0.8, → caso contrário
  - _Requirements: 6.5_

- [ ] 7. Validação e backtest
- [ ] 7.1 Criar tests/test_backtest.py com teste de consistência temporal
  - Criar DataFrame sintético com vendas de 2024-01 a 2025-12
  - Instanciar `PropensaoEngine(df, data_referencia=date(2025, 6, 1))`
  - Chamar `calcular_scores()` e validar comportamento (não atributos internos):
    - Nenhum cliente com `ultima_compra > 2025-06-01` aparece no resultado
    - `dias_sem_comprar` é relativo a 2025-06-01, não a `today()`
    - Frequência considera apenas vendas entre 2024-06-01 e 2025-06-01
  - _Requirements: 7.1_

- [ ] 7.2 Criar scripts/backtest_propensao.py
  - Aceitar `data_ref` como argumento (default: mês anterior)
  - Instanciar engine com `data_ref = M-1`
  - Comparar top 20 do score contra clientes que compraram em M
  - Calcular e imprimir precision@20 por linha de produto
  - _Requirements: 7.2_

- [ ] 7.3 Criar tests/test_smoke.py com teste de renderização real
  - Usar `streamlit.testing.v1.AppTest` se disponível na versão instalada
  - Se não disponível: importar cada função `render()` e chamar com mocks de `st.*`
  - Verificar que cada aba renderiza sem exception
  - Verificar que mudança de filtro não quebra
  - Verificar que tabela de score tem ao menos 1 linha com dados sintéticos
  - _Requirements: 5._ (housekeeping)
