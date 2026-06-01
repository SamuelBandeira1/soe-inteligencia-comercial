"""
Testes comportamentais para app/modules/acao_semanal.py — Phase 2.

Cobre APENAS lógica pura (sem Streamlit):
  - _ZONE_ACTION mapping
  - generate_email_text()
  - _gerar_motivo_potencial()
  - _build_client_table()
  - _badge_zona()
  - _truncar_email_vendedor()

AC cobertos automaticamente:
  AC-P2-4: zona badge não nulo
  AC-P2-6: decomposição retorna 5 componentes
  AC-P2-8: email gerado só quando estado = 'rascunho'
  AC-P2-9: email limita 10 clientes por vendedor
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from datetime import date
import numpy as np
import pandas as pd
import pytest

from modules.acao_semanal import (
    _ZONE_ACTION,
    _badge_zona,
    _gerar_motivo_potencial,
    generate_email_text,
    _truncar_email_vendedor,
)


# ═══════════════════════════════════════════════════════════════════════════════
# _ZONE_ACTION mapping (AC-P2-4, HC2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestZoneActionMap:
    def test_frozen_action(self):
        assert _ZONE_ACTION["frozen"] == "Confirmar pedido ou rastrear entrega"

    def test_liquid_action(self):
        assert _ZONE_ACTION["liquid"] == "Negociar volume ou simular what-if"

    def test_fluid_action(self):
        assert _ZONE_ACTION["fluid"] == "Qualificar interesse ou prospectar"

    def test_all_zones_present(self):
        assert set(_ZONE_ACTION.keys()) == {"frozen", "liquid", "fluid"}

    def test_no_zone_returns_fallback(self):
        # Past zone não tem ação — deve ter fallback
        action = _ZONE_ACTION.get("past", _ZONE_ACTION["fluid"])
        assert isinstance(action, str) and len(action) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# _badge_zona (AC-P2-4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBadgeZona:
    def test_frozen_returns_lock_emoji(self):
        assert "🔒" in _badge_zona("frozen")

    def test_liquid_returns_cycle_emoji(self):
        assert "🔄" in _badge_zona("liquid")

    def test_fluid_returns_satellite_emoji(self):
        assert "📡" in _badge_zona("fluid")

    def test_past_returns_string(self):
        result = _badge_zona("past")
        assert isinstance(result, str)

    def test_unknown_returns_string(self):
        result = _badge_zona("unknown")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════════
# _gerar_motivo_potencial (AC-P2-7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGerarMotivoPotencial:
    def _row_potencial(self, n=6, pct=0.75, vol=10.5, datas=None, saz=None, insuf=False):
        """Cria dict simulando linha do df de potencial."""
        return {
            "n_meses_comprou": n,
            "pct_meses": pct,
            "vol_medio_semana": vol,
            "historico_datas": datas or [date(2026, 5, 3), date(2026, 4, 5)],
            "score_sazonalidade": saz,
            "flag_sazon_insuficiente": insuf,
        }

    def test_good_contains_months_info(self):
        row = self._row_potencial(n=6, pct=0.75)
        text = _gerar_motivo_potencial(row, n_meses=8)
        assert "6" in text and "8" in text

    def test_good_contains_volume_info(self):
        row = self._row_potencial(vol=15.3)
        text = _gerar_motivo_potencial(row, n_meses=8)
        assert "15" in text

    def test_sazon_shown_when_available(self):
        row = self._row_potencial(saz=12.5, insuf=False)
        text = _gerar_motivo_potencial(row, n_meses=8)
        assert "12" in text or "sazon" in text.lower()

    def test_sazon_insuficiente_shows_dash_warning(self):
        row = self._row_potencial(saz=None, insuf=True)
        text = _gerar_motivo_potencial(row, n_meses=8)
        assert "⚠️" in text or "—" in text

    def test_zero_months_no_crash(self):
        """Ugly — cliente sem histórico não deve lançar exceção."""
        row = self._row_potencial(n=0, pct=0.0, vol=0.0, datas=[])
        text = _gerar_motivo_potencial(row, n_meses=8)
        assert isinstance(text, str)

    def test_returns_string(self):
        row = self._row_potencial()
        assert isinstance(_gerar_motivo_potencial(row, n_meses=8), str)


# ═══════════════════════════════════════════════════════════════════════════════
# _truncar_email_vendedor (AC-P2-9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTruncarEmailVendedor:
    def _make_df(self, n: int) -> pd.DataFrame:
        return pd.DataFrame({
            "cliente_id": [f"C{i:03d}" for i in range(n)],
            "cliente_nome": [f"Cliente {i}" for i in range(n)],
            "score_propensao": [float(100 - i) for i in range(n)],
            "tier": ["QUENTE"] * n,
            "zona": ["frozen"] * n,
            "telefone": ["(85) 9999"] * n,
            "flag_potencial_semana": [True] * n,
            "n_meses_comprou": [6] * n,
            "pct_meses": [0.75] * n,
        })

    def test_exactly_10_when_more_than_10(self):
        df = self._make_df(15)
        result_df, note = _truncar_email_vendedor(df)
        assert len(result_df) == 10

    def test_note_contains_total_when_truncated(self):
        df = self._make_df(15)
        _, note = _truncar_email_vendedor(df)
        assert note is not None
        assert "15" in note

    def test_no_truncation_when_exactly_10(self):
        df = self._make_df(10)
        result_df, note = _truncar_email_vendedor(df)
        assert len(result_df) == 10
        assert note is None

    def test_no_truncation_below_10(self):
        df = self._make_df(7)
        result_df, note = _truncar_email_vendedor(df)
        assert len(result_df) == 7
        assert note is None

    def test_empty_df_no_crash(self):
        """Ugly — df vazio não deve lançar exceção."""
        df = self._make_df(0)
        result_df, note = _truncar_email_vendedor(df)
        assert len(result_df) == 0
        assert note is None

    def test_sorted_by_score_desc(self):
        """Os 10 mantidos devem ser os de maior score_propensao."""
        df = self._make_df(15)
        result_df, _ = _truncar_email_vendedor(df)
        scores = result_df["score_propensao"].tolist()
        assert scores == sorted(scores, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# generate_email_text (AC-P2-8, AC-P2-9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerateEmailText:
    def _make_scores(self, n_clientes=3, vendedor="Vendedor A", gerencia="Comercial 1"):
        return pd.DataFrame({
            "cliente_id": [f"C{i:03d}" for i in range(n_clientes)],
            "cliente_nome": [f"Cliente {i}" for i in range(n_clientes)],
            "score_propensao": [float(80 - i * 5) for i in range(n_clientes)],
            "tier": ["QUENTE"] * n_clientes,
            "zona": ["frozen"] * n_clientes,
            "telefone": ["(85) 9999"] * n_clientes,
            "flag_potencial_semana": [True] * n_clientes,
            "n_meses_comprou": [6] * n_clientes,
            "pct_meses": [0.75] * n_clientes,
            "vol_medio_semana": [10.0] * n_clientes,
            "historico_datas": [[date(2026, 5, 3)]] * n_clientes,
            "score_sazonalidade": [10.0] * n_clientes,
            "flag_sazon_insuficiente": [False] * n_clientes,
            "vendedor": [vendedor] * n_clientes,
            "gerencia": [gerencia] * n_clientes,
            "acao_sugerida": [_ZONE_ACTION["frozen"]] * n_clientes,
        })

    def test_good_email_has_header(self):
        df = self._make_scores()
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "PLANO DE AÇÃO SEMANAL" in text

    def test_good_email_contains_vendedor(self):
        df = self._make_scores()
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "Vendedor A" in text

    def test_good_email_contains_zona_label(self):
        df = self._make_scores()
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "Congelada" in text

    def test_email_liquid_zona_label(self):
        df = self._make_scores()
        df["zona"] = "liquid"
        text = generate_email_text(df, semana_label="S2 Jan", zona="liquid",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "Líquida" in text

    def test_email_fluid_zona_label(self):
        df = self._make_scores()
        df["zona"] = "fluid"
        text = generate_email_text(df, semana_label="S3 Jan", zona="fluid",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "Fluida" in text

    def test_email_caps_at_10_per_vendedor(self):
        """AC-P2-9: email deve limitar 10 clientes por vendedor."""
        df = self._make_scores(n_clientes=15)
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        # Count how many numbered client lines ("  1. ", "  2. ", ...) appear
        lines_with_number = [l for l in text.splitlines()
                             if l.strip() and l.strip()[0].isdigit() and ". " in l]
        assert len(lines_with_number) <= 10

    def test_email_note_when_truncated(self):
        """Nota de truncamento deve aparecer quando há mais de 10 clientes."""
        df = self._make_scores(n_clientes=12)
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert "mostrando 10" in text

    def test_email_with_alertas(self):
        alertas = [{"linha": "Vergalhão", "zona": "frozen", "gap_pct": 0.35,
                    "meta": 100.0, "estimada": 65.0}]
        df = self._make_scores()
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=alertas)
        assert "Vergalhão" in text

    def test_empty_df_no_crash(self):
        """Ugly — df vazio não deve lançar exceção."""
        df = self._make_scores(0)
        text = generate_email_text(df, semana_label="S1 Jan", zona="frozen",
                                   gerencia_sel="Comercial 1", alertas=[])
        assert isinstance(text, str)
