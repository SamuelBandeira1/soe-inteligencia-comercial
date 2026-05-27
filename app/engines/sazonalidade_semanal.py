"""
SemanalPropensaoEngine — Score de propensão ajustado por sazonalidade intra-mês.

Algoritmo (within-month purchase seasonality — padrão B2B industrial):
─────────────────────────────────────────────────────────────────────
Para cada par (cd_cliente, linha), calcula a distribuição histórica
de compras por semana do mês (semana_mes ∈ {1, 2, 3, 4}):

    pct_semana[cliente, linha, k] =
        count(transações na semana k) / count(total transações)

Score semanal combinado:
    score_semanal = score_propensao × (1 + W × pct_semana[k])

    W = 0.40 → cliente que compra 100% na semana k recebe +40% no score base.
    Efeito prático: a semana preferida do cliente sobe no ranking sem "sequestrar"
    scores de clientes com alto propensão mas padrão mais distribuído.

Ação sugerida gerada automaticamente baseada em:
    - Dias sem comprar
    - Semana do mês como padrão (pct_semana ≥ 0.40 = "semana preferida")
    - Score semanal

Uso:
    engine = SemanalPropensaoEngine(df_vendas)
    df_scores_base = PropensaoEngine(df_vendas).calcular_scores()
    df_semana = engine.score_semana(df_scores_base, semana=2)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Peso do componente sazonal semanal sobre o score base
W_SEMANA: float = 0.40

# Mínimo de transações históricas para considerar o padrão confiável
MIN_TRANSACOES_PADRAO: int = 3


class SemanalPropensaoEngine:
    """
    Enriquece scores de propensão com padrão de compra intra-mês.

    Parameters
    ----------
    df_vendas : DataFrame de vendas com colunas:
        cd_cliente, linha, semana_mes (1-4), data, vol_ton, familia, regiao, uf
    """

    def __init__(self, df_vendas: pd.DataFrame) -> None:
        self._df = df_vendas.copy()
        self._df["data"] = pd.to_datetime(self._df["data"])
        self._padrao: pd.DataFrame = self._calcular_padrao_semanal()

    # ── Interface pública ─────────────────────────────────────────────────────

    def score_semana(
        self,
        df_scores: pd.DataFrame,
        semana: int,
    ) -> pd.DataFrame:
        """
        Retorna df_scores enriquecido com score_semanal, pct_semana e acao_semanal,
        ordenado por score_semanal decrescente.

        Parameters
        ----------
        df_scores : saída de PropensaoEngine.calcular_scores()
        semana    : semana do mês selecionada (1–4)
        """
        if df_scores.empty:
            return df_scores

        col = f"pct_sem_{semana}"

        # Semanas além do máximo calculado (ex: semana 5 em mês TW)
        # recebem pct_semana = 0 — sem boost, mas o score base ainda funciona
        if col not in self._padrao.columns:
            df = df_scores.copy()
            df["pct_semana"] = 0.0
            df["score_semanal"] = df["score_propensao"].round(1)
            df["padrao_semana_forte"] = False
            df["acao_semanal"] = df.apply(lambda r: _acao_semana(r, semana), axis=1)
            return df.sort_values("score_semanal", ascending=False).reset_index(drop=True)

        padrao_sem = self._padrao[["cd_cliente", "linha", col]].rename(
            columns={col: "pct_semana"}
        )

        df = df_scores.merge(padrao_sem, on=["cd_cliente", "linha"], how="left")
        df["pct_semana"] = df["pct_semana"].fillna(0.0)

        # Score combinado
        df["score_semanal"] = (
            df["score_propensao"] * (1.0 + W_SEMANA * df["pct_semana"])
        ).round(1)

        # Flag de padrão confirmado (≥ 3 transações e pct ≥ 35%)
        df["padrao_semana_forte"] = df["pct_semana"] >= 0.35

        # Ação sugerida orientada à semana
        df["acao_semanal"] = df.apply(
            lambda r: _acao_semana(r, semana), axis=1
        )

        return df.sort_values("score_semanal", ascending=False).reset_index(drop=True)

    def get_padrao(self, cd_cliente: str, linha: str) -> dict[int, float]:
        """Retorna dict {1: pct, ..., N: pct} para o cliente×linha."""
        row = self._padrao[
            (self._padrao["cd_cliente"] == cd_cliente) &
            (self._padrao["linha"] == linha)
        ]
        if row.empty:
            return {s: 0.0 for s in range(1, 6)}
        r = row.iloc[0]
        max_s = max(
            int(c.replace("pct_sem_", ""))
            for c in self._padrao.columns if c.startswith("pct_sem_")
        )
        return {k: float(r.get(f"pct_sem_{k}", 0.0)) for k in range(1, max_s + 1)}

    # ── Cálculo interno ───────────────────────────────────────────────────────

    def _calcular_padrao_semanal(self) -> pd.DataFrame:
        """
        Para cada (cd_cliente, linha): conta transações por semana_mes,
        calcula percentuais e filtra pares com histórico insuficiente.
        """
        df = self._df.copy()

        # Garante coluna semana_mes (caso use dados brutos sem semana pré-calculada)
        if "semana_mes" not in df.columns:
            df["semana_mes"] = df["data"].dt.day.apply(_dia_para_semana)

        # Conta transações únicas por (cliente, linha, semana)
        # Uma "transação" = um dia com venda > 0 (evita pesar pelo volume)
        agg = (
            df[df["vol_ton"] > 0]
            .groupby(["cd_cliente", "linha", "semana_mes"])
            .size()
            .reset_index(name="n_trans")
        )

        # Descobre quantas semanas distintas existem nos dados (calendário TW pode ter 5)
        max_sem = int(agg["semana_mes"].max()) if not agg.empty else 4
        max_sem = max(max_sem, 4)  # mínimo 4

        # Pivot: linhas = cliente×linha, colunas = semana 1..max_sem
        pivot = agg.pivot_table(
            index=["cd_cliente", "linha"],
            columns="semana_mes",
            values="n_trans",
            fill_value=0,
        ).reset_index()

        # Garante todas as colunas de semana presentes
        for s in range(1, max_sem + 1):
            if s not in pivot.columns:
                pivot[s] = 0

        # Renomeia colunas numéricas para n1, n2, ...
        rename_map = {s: f"n{s}" for s in range(1, max_sem + 1)}
        pivot = pivot.rename(columns=rename_map)

        n_cols = [f"n{s}" for s in range(1, max_sem + 1)]
        pivot["total"] = pivot[n_cols].sum(axis=1)

        # Zera pares com histórico insuficiente
        pivot.loc[pivot["total"] < MIN_TRANSACOES_PADRAO, n_cols] = 0
        pivot.loc[pivot["total"] < MIN_TRANSACOES_PADRAO, "total"] = 1  # evita /0

        pct_cols = []
        for s in range(1, max_sem + 1):
            col_n = f"n{s}"
            col_p = f"pct_sem_{s}"
            pivot[col_p] = (pivot[col_n] / pivot["total"]).round(3)
            pct_cols.append(col_p)

        return pivot[["cd_cliente", "linha"] + pct_cols + ["total"]]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _dia_para_semana(dia: int) -> int:
    """Converte dia do mês para semana simples (1-4)."""
    if dia <= 7:   return 1
    if dia <= 14:  return 2
    if dia <= 21:  return 3
    return 4


def _acao_semana(row: pd.Series, semana: int) -> str:
    """Gera ação comercial sugerida para a semana selecionada."""
    dias    = int(row.get("dias_sem_comprar", 999))
    score_s = float(row.get("score_semanal", 0))
    pct_sem = float(row.get("pct_semana", 0))
    freq    = float(row.get("frequencia_compras", 0))

    semana_label = {1: "1ª", 2: "2ª", 3: "3ª", 4: "4ª"}.get(semana, f"{semana}ª")

    if pct_sem >= 0.50:
        prefixo = f"📅 Padrão confirmado: compra preferencial na {semana_label} semana"
        if dias <= 7:
            return f"💬 {prefixo}. Acabou de comprar — ofereça volume adicional."
        if dias >= 60:
            return f"⚠️ {prefixo}, mas está {dias}d sem comprar. Prioridade alta de contato."
        return f"📞 {prefixo}. Ligue esta semana."

    if score_s >= 60 and dias >= 31:
        return f"📞 Alta propensão ({score_s:.0f} pts) — ligar nesta semana."

    if dias >= 90 and freq >= 0.5:
        return f"🔄 Cliente regular parado há {dias}d. Ação de reativação urgente."

    if score_s >= 40:
        return f"📋 Score médio ({score_s:.0f} pts) — contato de relacionamento."

    return "📧 Score baixo — e-mail ou mensagem de relacionamento."
