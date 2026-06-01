"""
PotencialSemanalEngine — flag de potencial de compra semanal.

Para cada par (cd_cliente, linha), determina se o cliente tem padrão histórico
confirmado de comprar em uma semana específica do mês:

    flag_potencial_semana = (n_meses_comprou / n_meses) >= threshold

Completamente independente de score_propensao (HC1 — nunca mesclar os dois).

Colunas de saída de calcular_flag_potencial():
    cd_cliente, linha, semana_mes,
    flag_potencial_semana (bool),
    n_meses_comprou (int),
    pct_meses (float),
    vol_medio_semana (float),   # vol médio nos meses em que comprou na semana-alvo
    historico_datas (list),     # últimas 3 datas de compra na semana-alvo
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _dia_para_semana(dia: int) -> int:
    """Converte dia do mês para semana simples (1-4), consistente com sazonalidade_semanal.py."""
    if dia <= 7:   return 1
    if dia <= 14:  return 2
    if dia <= 21:  return 3
    return 4


class PotencialSemanalEngine:
    """Calcula flag de potencial de compra por semana do mês."""

    def __init__(self, df_vendas: pd.DataFrame) -> None:
        if "data" not in df_vendas.columns:
            raise ValueError(
                "df_vendas está faltando a coluna obrigatória: 'data'. "
                "Colunas esperadas: data, cd_cliente, linha, vol_ton."
            )
        self._df = df_vendas.copy()
        self._df["data"] = pd.to_datetime(self._df["data"])

        # Deriva semana_mes se ausente — silenciosamente, sem ValueError
        if "semana_mes" not in self._df.columns:
            self._df["semana_mes"] = self._df["data"].dt.day.apply(_dia_para_semana)

    # ── Interface pública ─────────────────────────────────────────────────────

    def calcular_flag_potencial(
        self,
        semana_mes: int,
        n_meses: int = 8,
        threshold: float = 0.75,
    ) -> pd.DataFrame:
        """
        Retorna DataFrame com flag_potencial_semana por (cd_cliente, linha).

        Parameters
        ----------
        semana_mes  : semana-alvo do mês (1-4)
        n_meses     : janela de lookback em meses completos
        threshold   : fração mínima de meses com compra para flag=True (padrão 0.75 = 6/8)
        """
        df = self._df

        if df.empty:
            return pd.DataFrame(columns=[
                "cd_cliente", "linha", "semana_mes",
                "flag_potencial_semana", "n_meses_comprou",
                "pct_meses", "vol_medio_semana", "historico_datas",
            ])

        # ── Janela: últimos n_meses a partir da data máxima ───────────────────
        data_max  = df["data"].max()
        data_corte = data_max - pd.DateOffset(months=n_meses)
        df_janela  = df[df["data"] > data_corte].copy()

        # ── Filtra transações na semana-alvo ──────────────────────────────────
        df_semana = df_janela[df_janela["semana_mes"] == semana_mes].copy()

        # ── n_meses_comprou: meses distintos com pelo menos 1 compra na semana ─
        if not df_semana.empty:
            df_semana["ano_mes"] = df_semana["data"].dt.to_period("M")

            meses_comprou = (
                df_semana.groupby(["cd_cliente", "linha"])["ano_mes"]
                .nunique()
                .reset_index()
                .rename(columns={"ano_mes": "n_meses_comprou"})
            )

            # ── vol_medio_semana: média do vol_ton por mês em que comprou ─────
            vol_por_mes = (
                df_semana.groupby(["cd_cliente", "linha", "ano_mes"])["vol_ton"]
                .sum()
                .groupby(level=["cd_cliente", "linha"])
                .mean()
                .reset_index()
                .rename(columns={"vol_ton": "vol_medio_semana"})
            )

            # ── historico_datas: últimas 3 datas de compra na semana-alvo ─────
            ultimas = (
                df_semana.sort_values("data", ascending=False)
                .groupby(["cd_cliente", "linha"])["data"]
                .apply(lambda s: s.head(3).dt.date.tolist())
                .reset_index()
                .rename(columns={"data": "historico_datas"})
            )

            resultado = (
                meses_comprou
                .merge(vol_por_mes, on=["cd_cliente", "linha"], how="left")
                .merge(ultimas,     on=["cd_cliente", "linha"], how="left")
            )
        else:
            # Nenhuma transação na semana-alvo dentro da janela
            # Ainda precisamos retornar todos os clientes da janela com flag=False
            resultado = pd.DataFrame(columns=[
                "cd_cliente", "linha", "n_meses_comprou",
                "vol_medio_semana", "historico_datas",
            ])

        # ── Base completa de clientes na janela (para incluir os que não compraram) ─
        clientes_janela = (
            df_janela[["cd_cliente", "linha"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )

        resultado = clientes_janela.merge(resultado, on=["cd_cliente", "linha"], how="left")
        resultado["n_meses_comprou"] = resultado["n_meses_comprou"].fillna(0).astype(int)
        resultado["vol_medio_semana"] = resultado["vol_medio_semana"].fillna(0.0)
        resultado["historico_datas"]  = resultado["historico_datas"].apply(
            lambda v: v if isinstance(v, list) else []
        )

        # ── Flag e percentual ─────────────────────────────────────────────────
        resultado["pct_meses"] = resultado["n_meses_comprou"] / n_meses
        resultado["flag_potencial_semana"] = resultado["pct_meses"] >= threshold
        resultado["semana_mes"] = semana_mes

        cols = [
            "cd_cliente", "linha", "semana_mes",
            "flag_potencial_semana", "n_meses_comprou",
            "pct_meses", "vol_medio_semana", "historico_datas",
        ]
        return resultado[cols].reset_index(drop=True)
