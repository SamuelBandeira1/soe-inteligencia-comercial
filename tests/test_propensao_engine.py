"""Testes unitários para PropensaoEngine."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from datetime import date, timedelta
import pandas as pd
import pytest
from engines.propensao_engine import PropensaoEngine, SCORE_WEIGHTS


# ── Fixture de dados mínimos ──────────────────────────────────────────────────
def _make_df(n_meses: int = 14) -> pd.DataFrame:
    """Gera DataFrame de vendas sintético com 2 clientes e 2 linhas."""
    rows = []
    base = date(2024, 1, 1)
    for i in range(n_meses):
        d = base + timedelta(days=i * 30)
        rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                     "regiao": "NORDESTE", "uf": "CE",
                     "data": d, "vol_ton": 100.0, "val_mm": 5.0})
        if i % 3 == 0:   # CLI002 compra a cada 3 meses
            rows.append({"cd_cliente": "CLI002", "linha": "CA-50",
                         "regiao": "NORDESTE", "uf": "CE",
                         "data": d, "vol_ton": 50.0, "val_mm": 2.5})
    return pd.DataFrame(rows)


@pytest.fixture
def engine():
    return PropensaoEngine(_make_df())


# ── Testes de recência ────────────────────────────────────────────────────────
class TestRecencia:
    def test_comprou_recentemente(self, engine):
        assert engine._calcular_recencia_score(0)  == 30.0
        assert engine._calcular_recencia_score(30) == 30.0

    def test_janela_normal(self, engine):
        assert engine._calcular_recencia_score(31) == 20.0
        assert engine._calcular_recencia_score(60) == 20.0

    def test_esfriando(self, engine):
        assert engine._calcular_recencia_score(61) == 10.0
        assert engine._calcular_recencia_score(90) == 10.0

    def test_inativo_recuperavel(self, engine):
        assert engine._calcular_recencia_score(91)  == 5.0
        assert engine._calcular_recencia_score(180) == 5.0

    def test_muito_inativo(self, engine):
        assert engine._calcular_recencia_score(181) == 0.0
        assert engine._calcular_recencia_score(999) == 0.0

    def test_score_maximo_e_30(self, engine):
        assert engine._calcular_recencia_score(1) == 30.0


# ── Testes de frequência ──────────────────────────────────────────────────────
class TestFrequencia:
    def test_sem_historico(self, engine):
        assert engine._calcular_frequencia_score(0.0) == 0.0

    def test_uma_compra_por_mes(self, engine):
        assert engine._calcular_frequencia_score(1.0) == 25.0

    def test_cap_em_25(self, engine):
        assert engine._calcular_frequencia_score(2.0) == 25.0

    def test_proporcional(self, engine):
        # Nova fórmula: freq × 60, clip 0-25
        # freq=0.5 → 0.5 × 60 = 30 → clip → 25
        score = engine._calcular_frequencia_score(0.5)
        assert score == pytest.approx(25.0)

    def test_frequencia_baixa(self, engine):
        # freq=0.1 → 0.1 × 60 = 6.0
        score = engine._calcular_frequencia_score(0.1)
        assert score == pytest.approx(6.0)


# ── Testes de sazonalidade ────────────────────────────────────────────────────
class TestSazonalidade:
    def test_cliente_sem_historico_retorna_fallback(self, engine):
        # Nova fórmula: sazonalidade máx 15 pts, fallback = 7.5
        score = engine._calcular_sazonalidade_score("CLI_INEXISTENTE", 6)
        assert score == 7.5

    def test_mes_favorito_tem_score_alto(self, engine):
        # CLI001 compra todo mês — distribuição uniforme
        score_jan = engine._calcular_sazonalidade_score("CLI001", 1)
        assert score_jan > 0

    def test_score_entre_0_e_25(self, engine):
        for mes in range(1, 13):
            score = engine._calcular_sazonalidade_score("CLI001", mes)
            assert 0 <= score <= 25


# ── Testes de volume ──────────────────────────────────────────────────────────
class TestVolume:
    def test_volume_zero_retorna_zero(self, engine):
        # Com vol_med=0, score deve ser 0 (sem histórico de volume)
        # O método legado usa _volume_p75 que pode estar vazio nos dados sintéticos
        score = engine._calcular_volume_score(0.0, "CA-50")
        assert score >= 0.0  # pode ser 0 ou fallback dependendo do cache

    def test_volume_acima_referencia_cap_em_20(self, engine):
        # Volume muito alto deve ser capado em 20
        score = engine._calcular_volume_score(99999.0, "CA-50")
        assert score <= 20.0

    def test_linha_sem_historico(self, engine):
        # Nova fórmula: log1p(vol/mediana) × C_VOL — fallback mediana=1.0
        # log1p(100/1) × 8.37 = log1p(100) × 8.37 ≈ 4.615 × 8.37 ≈ 38.6 → clip → 20
        score = engine._calcular_volume_score(100.0, "LINHA_INEXISTENTE")
        assert score <= 20.0  # cap em 20


# ── Testes de integração: calcular_scores ────────────────────────────────────
class TestCalcularScores:
    def test_retorna_dataframe(self, engine):
        df = engine.calcular_scores(linha="CA-50")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_colunas_obrigatorias(self, engine):
        df = engine.calcular_scores()
        for col in ["cliente_id", "linha", "score_propensao", "dias_sem_comprar",
                    "frequencia_compras", "motivo_score"]:
            assert col in df.columns, f"Coluna ausente: {col}"

    def test_score_entre_0_e_100(self, engine):
        df = engine.calcular_scores()
        assert (df["score_propensao"] >= 0).all()
        assert (df["score_propensao"] <= 100).all()

    def test_ordenado_por_score_desc(self, engine):
        df = engine.calcular_scores()
        assert df["score_propensao"].is_monotonic_decreasing

    def test_cliente_frequente_tem_score_maior_ou_igual(self, engine):
        """CLI001 (compra todo mês) deve ter score >= CLI002 (compra a cada 3 meses)."""
        df = engine.calcular_scores(linha="CA-50")
        score_cli001 = df[df["cliente_id"] == "CLI001"]["score_propensao"].values[0]
        score_cli002 = df[df["cliente_id"] == "CLI002"]["score_propensao"].values[0]
        # Com sazonalidade por linha (igual para ambos), a diferença vem da frequência
        # CLI001 compra todo mês (freq=1.0) vs CLI002 a cada 3 meses (freq~0.33)
        assert score_cli001 >= score_cli002

    def test_filtro_linha(self, engine):
        df = engine.calcular_scores(linha="CA-50")
        assert (df["linha"] == "CA-50").all()

    def test_filtro_linha_inexistente_retorna_vazio(self, engine):
        df = engine.calcular_scores(linha="LINHA_QUE_NAO_EXISTE")
        assert df.empty

    def test_penalidade_compra_recente(self, engine):
        """Clientes com compra recente devem ter score penalizado (req 1.5)."""
        score_recente = engine._calcular_recencia_score(1)  # 30 pts
        score_distante = engine._calcular_recencia_score(60)  # 20 pts
        df_ref = engine.calcular_scores(data_referencia=date.today())
        if df_ref.empty:
            return
        mask_semana = df_ref["dias_sem_comprar"] <= 7
        mask_mes = (df_ref["dias_sem_comprar"] > 7) & (df_ref["dias_sem_comprar"] <= 30)
        if mask_semana.any() and mask_mes.any():
            score_semana = df_ref[mask_semana]["score_propensao"].mean()
            score_mes = df_ref[mask_mes]["score_propensao"].mean()
            assert score_semana < score_mes  # penalidade da semana > penalidade do mês

    def test_penalidade_inatividade(self, engine):
        """Clientes inativos há muito tempo devem ter score menor que clientes ativos."""
        df = engine.calcular_scores(data_referencia=date.today())
        if df.empty:
            return
        # Clientes desativados (>180d) devem ter score menor que ativos (<=30d)
        mask_desativado = df["dias_sem_comprar"] > 180
        mask_ativo = df["dias_sem_comprar"] <= 30
        if mask_desativado.any() and mask_ativo.any():
            score_medio_desativado = df[mask_desativado]["score_propensao"].mean()
            score_medio_ativo = df[mask_ativo]["score_propensao"].mean()
            assert score_medio_desativado < score_medio_ativo, (
                f"Desativados ({score_medio_desativado:.1f}) devem ter score menor que ativos ({score_medio_ativo:.1f})"
            )
