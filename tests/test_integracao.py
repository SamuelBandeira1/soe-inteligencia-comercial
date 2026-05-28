"""
Testes de integração — fluxo completo com dados reais.

Valida o pipeline: dados → PropensaoEngine → saída.
Requer os arquivos parquet em data/processed/.

AcaoEngine foi removido na v2 (task 1.1) — testes correspondentes deletados.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pandas as pd
import pytest

from engines.propensao_engine import PropensaoEngine
from utils.filters import apply_filters

# ── Caminho dos dados reais ───────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
VENDAS_PATH = os.path.join(DATA_DIR, "vendas_filtrada.parquet")


def _dados_disponiveis() -> bool:
    return os.path.exists(VENDAS_PATH)


@pytest.fixture(scope="module")
def df_vendas():
    if not _dados_disponiveis():
        pytest.skip("Arquivo vendas_filtrada.parquet não encontrado")
    df = pd.read_parquet(VENDAS_PATH)
    df["data"] = pd.to_datetime(df["data"])
    for col in ["empresa", "linha", "regiao", "uf"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    return df


@pytest.fixture(scope="module")
def prop_engine(df_vendas):
    return PropensaoEngine(df_vendas)


# ── Testes de integridade dos dados ──────────────────────────────────────────
class TestIntegridadeDados:
    def test_colunas_minimas_presentes(self, df_vendas):
        for col in ["data", "linha", "vol_ton", "empresa", "regiao", "uf"]:
            assert col in df_vendas.columns, f"Coluna ausente: {col}"

    def test_sem_vol_ton_negativo(self, df_vendas):
        assert (df_vendas["vol_ton"] >= 0).all(), "Existem volumes negativos"

    def test_datas_validas(self, df_vendas):
        assert df_vendas["data"].notna().all(), "Existem datas nulas"
        assert df_vendas["data"].min() > pd.Timestamp("2018-01-01")

    def test_linhas_conhecidas_presentes(self, df_vendas):
        linhas = df_vendas["linha"].unique()
        assert len(linhas) > 0, "Nenhuma linha de produto encontrada"

    def test_historico_minimo_24_meses(self, df_vendas):
        """Req 5.6: manter pelo menos 24 meses de histórico."""
        meses = df_vendas["data"].dt.to_period("M").nunique()
        assert meses >= 24, f"Histórico insuficiente: {meses} meses (mínimo 24)"


# ── Testes de fluxo completo ──────────────────────────────────────────────────
class TestFluxoCompleto:
    def test_scores_calculados_para_ca50(self, prop_engine):
        df = prop_engine.calcular_scores(linha="CA-50")
        assert not df.empty, "Nenhum score calculado para CA-50"
        assert (df["score_propensao"].between(0, 100)).all()

    def test_scores_ordenados_desc(self, prop_engine):
        df = prop_engine.calcular_scores(linha="CA-50")
        assert df["score_propensao"].is_monotonic_decreasing

    def test_filtro_regiao_funciona(self, prop_engine, df_vendas):
        regioes = df_vendas["regiao"].dropna().unique()
        if len(regioes) == 0:
            pytest.skip("Sem regiões disponíveis")
        regiao = regioes[0]
        df = prop_engine.calcular_scores(regiao=regiao)
        if not df.empty:
            assert (df["regiao"] == regiao).all()

    def test_todas_linhas_geram_scores(self, prop_engine, df_vendas):
        """Todas as linhas com histórico devem gerar pelo menos 1 score."""
        linhas = df_vendas["linha"].dropna().unique()[:5]  # testa as 5 primeiras
        for linha in linhas:
            df = prop_engine.calcular_scores(linha=linha)
            assert not df.empty, f"Nenhum score para linha: {linha}"


# ── Testes de consistência de filtros ────────────────────────────────────────
class TestFiltros:
    def test_apply_filters_empresa(self, df_vendas):
        empresas = df_vendas["empresa"].dropna().unique()[:1].tolist()
        filtros = {"empresas": empresas, "linhas": [], "regioes": [], "ufs": []}
        df_filt = apply_filters(df_vendas, filtros)
        assert (df_filt["empresa"].isin(empresas)).all()

    def test_apply_filters_vazio_retorna_tudo(self, df_vendas):
        filtros = {"empresas": [], "linhas": [], "regioes": [], "ufs": []}
        df_filt = apply_filters(df_vendas, filtros)
        assert len(df_filt) == len(df_vendas)

    def test_apply_filters_uf(self, df_vendas):
        ufs = df_vendas["uf"].dropna().unique()[:2].tolist()
        filtros = {"empresas": [], "linhas": [], "regioes": [], "ufs": ufs}
        df_filt = apply_filters(df_vendas, filtros)
        assert (df_filt["uf"].isin(ufs)).all()

    def test_filtro_inexistente_retorna_vazio(self, df_vendas):
        filtros = {"empresas": ["EMPRESA_INEXISTENTE"], "linhas": [], "regioes": [], "ufs": []}
        df_filt = apply_filters(df_vendas, filtros)
        assert df_filt.empty


# ── Testes de performance ─────────────────────────────────────────────────────
class TestPerformance:
    def test_calcular_scores_menos_de_3_segundos(self, prop_engine):
        """Req 4.1: scores devem ser calculados em < 3 segundos."""
        inicio = time.time()
        prop_engine.calcular_scores(linha="CA-50")
        elapsed = time.time() - inicio
        assert elapsed < 3.0, f"Cálculo de scores demorou {elapsed:.1f}s (limite: 3s)"

    def test_scores_dataset_completo_menos_de_10_segundos(self, prop_engine):
        """Testa performance com dataset completo (sem filtro de linha)."""
        inicio = time.time()
        prop_engine.calcular_scores()
        elapsed = time.time() - inicio
        assert elapsed < 10.0, f"Scores completos demoraram {elapsed:.1f}s (limite: 10s)"
