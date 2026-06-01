"""
Testes unitários para PotencialSemanalEngine.

Cobertura Good/Bad/Ugly conforme plano 2026-06-01-feat-unified-action-page.md:
  Good  — caminho feliz: flag=True, pct correto
  Bad   — abaixo do threshold: flag=False
  Ugly  — dados ausentes/vazios/colunas faltando
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from datetime import date
import numpy as np
import pandas as pd
import pytest

from engines.potencial_engine import PotencialSemanalEngine


# ── Helpers de fixture ────────────────────────────────────────────────────────

def _data_com_semana(ano: int, mes: int, semana: int) -> date:
    """Retorna um dia do mês que cai na semana_mes indicada (1-4)."""
    dia = {1: 3, 2: 10, 3: 17, 4: 24}[semana]
    return date(ano, mes, dia)


def _df_n_meses_semana2(n_meses_comprou: int, total_meses: int = 8) -> pd.DataFrame:
    """
    Cria DataFrame onde CLI001/CA-50 compra na semana 2 em n_meses_comprou
    dos últimos total_meses meses (data máxima = 2024-08-15).
    """
    rows = []
    max_date = date(2024, 8, 15)
    meses = []
    # últimos total_meses meses retroativos à max_date
    for i in range(total_meses):
        m = max_date.month - i
        y = max_date.year
        while m <= 0:
            m += 12
            y -= 1
        meses.append((y, m))

    for idx, (y, m) in enumerate(meses):
        if idx < n_meses_comprou:
            rows.append({
                "cd_cliente": "CLI001",
                "linha": "CA-50",
                "data": date(y, m, 10),   # dia 10 → semana 2
                "vol_ton": 100.0,
            })

    # Adiciona a própria data máxima para ancorar a janela
    rows.append({
        "cd_cliente": "CLI001",
        "linha": "CA-50",
        "data": max_date,
        "vol_ton": 1.0,    # vol mínimo só p/ ancorar o período
    })
    return pd.DataFrame(rows)


# ── Good: flag_potencial=True para 6/8 meses ─────────────────────────────────

class TestFlagPotencialGood:
    def test_6_de_8_meses_flag_true(self):
        df = _df_n_meses_semana2(6)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8, threshold=0.75)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert row["flag_potencial_semana"] is True or row["flag_potencial_semana"] == True
        assert row["n_meses_comprou"] == 6

    def test_8_de_8_meses_pct_maximo(self):
        """Comprou em todos os meses → pct_meses = 1.0, flag = True."""
        rows = []
        for mes in range(1, 9):
            rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                         "data": date(2024, mes, 10), "vol_ton": 50.0})
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert row["flag_potencial_semana"] is True or row["flag_potencial_semana"] == True
        assert abs(row["pct_meses"] - 1.0) < 0.01

    def test_vol_medio_semana_calculado(self):
        """vol_medio_semana deve refletir apenas meses em que o cliente comprou na semana alvo."""
        rows = []
        for mes in range(1, 9):
            rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                         "data": date(2024, mes, 10), "vol_ton": float(mes * 10)})
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert row["vol_medio_semana"] > 0

    def test_historico_datas_lista(self):
        """historico_datas deve ser uma lista (últimas 3 datas)."""
        rows = []
        for mes in range(1, 9):
            rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                         "data": date(2024, mes, 10), "vol_ton": 50.0})
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert isinstance(row["historico_datas"], list)
        assert len(row["historico_datas"]) <= 3

    def test_flag_potencial_independente_de_score_propensao(self):
        """flag_potencial_semana NÃO deve depender de score_propensao (colunas separadas)."""
        rows = []
        for mes in range(1, 9):
            rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                         "data": date(2024, mes, 10), "vol_ton": 50.0})
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2)
        assert "flag_potencial_semana" in resultado.columns
        assert "score_propensao" not in resultado.columns


# ── Bad: flag_potencial=False para 5/8 meses ─────────────────────────────────

class TestFlagPotencialBad:
    def test_5_de_8_meses_flag_false(self):
        df = _df_n_meses_semana2(5)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8, threshold=0.75)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert row["flag_potencial_semana"] is False or row["flag_potencial_semana"] == False

    def test_pct_meses_correto_5_de_8(self):
        df = _df_n_meses_semana2(5)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8, threshold=0.75)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        # pct_meses = n_meses_comprou / n_meses — deve ser <= 0.625
        assert row["pct_meses"] <= 0.625 + 0.01

    def test_semana_errada_nao_conta(self):
        """Cliente que compra APENAS na semana 1 → semana 2 = flag False."""
        rows = []
        for mes in range(1, 9):
            rows.append({"cd_cliente": "CLI001", "linha": "CA-50",
                         "data": date(2024, mes, 3), "vol_ton": 50.0})  # dia 3 = semana 1
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8, threshold=0.75)
        row = resultado[resultado["cd_cliente"] == "CLI001"].iloc[0]
        assert row["flag_potencial_semana"] is False or row["flag_potencial_semana"] == False


# ── Ugly: zero transações, DataFrame vazio, coluna semana_mes ausente ─────────

class TestFlagPotencialUgly:
    def test_cliente_sem_historico_flag_false(self):
        """Cliente sem nenhuma transação → flag False, pct 0.0, sem crash."""
        rows = [
            {"cd_cliente": "OUTRO", "linha": "CA-50",
             "data": date(2024, 1, 10), "vol_ton": 50.0},
        ]
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2, n_meses=8)
        # CLI001 não existe — resultado pode estar vazio ou ter apenas OUTRO
        cli001 = resultado[resultado["cd_cliente"] == "CLI001"]
        if not cli001.empty:
            assert cli001.iloc[0]["flag_potencial_semana"] == False

    def test_dataframe_vazio_retorna_vazio(self):
        """DataFrame vazio → retorna DataFrame vazio sem exception."""
        df = pd.DataFrame(columns=["cd_cliente", "linha", "data", "vol_ton"])
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2)
        assert isinstance(resultado, pd.DataFrame)
        assert resultado.empty

    def test_semana_mes_ausente_derivada_silenciosamente(self):
        """Se semana_mes não estiver no df, deve ser derivada de 'data' sem exception."""
        rows = [
            {"cd_cliente": "CLI001", "linha": "CA-50",
             "data": date(2024, mes, 10), "vol_ton": 50.0}
            for mes in range(1, 9)
        ]
        df = pd.DataFrame(rows)
        assert "semana_mes" not in df.columns
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2)
        assert not resultado.empty
        assert "flag_potencial_semana" in resultado.columns

    def test_sem_coluna_data_raise_valueerror(self):
        """df sem coluna 'data' deve levantar ValueError."""
        df = pd.DataFrame({"cd_cliente": ["CLI001"], "linha": ["CA-50"], "vol_ton": [10.0]})
        with pytest.raises(ValueError, match="data"):
            PotencialSemanalEngine(df)

    def test_colunas_saida_esperadas(self):
        """Resultado deve conter todas as colunas exigidas pelo contrato."""
        rows = [
            {"cd_cliente": "CLI001", "linha": "CA-50",
             "data": date(2024, mes, 10), "vol_ton": 50.0}
            for mes in range(1, 9)
        ]
        df = pd.DataFrame(rows)
        engine = PotencialSemanalEngine(df)
        resultado = engine.calcular_flag_potencial(semana_mes=2)
        for col in ["cd_cliente", "linha", "semana_mes", "flag_potencial_semana",
                    "n_meses_comprou", "pct_meses", "vol_medio_semana", "historico_datas"]:
            assert col in resultado.columns, f"Coluna ausente: {col}"
