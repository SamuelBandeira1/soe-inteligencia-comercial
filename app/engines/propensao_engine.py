"""
Engine de cálculo de score de propensão de compra.

Score composto por 5 componentes (todos vetorizados — sem apply/loop):
  - Recência     (30 pts): dias desde a última compra
  - Frequência   (25 pts): compras/mês nos últimos 12m × 60, clip 0-25
  - Sazonalidade (15 pts): padrão mensal da LINHA — normalizado para peso 15
  - Volume       (20 pts): log1p(vol/mediana) × C_VOL=8.37, clip 0-20
  - Tendência    (10 pts): ratio vol_3m/vol_12m_trimestral × 5, clip 0-10

Total teórico: 100 pts. Score exibido = score bruto absoluto (sem min-max).

**Por que sem min-max?**
  A normalização min-max força o cliente de maior score a sempre ter 100.
  Isso cria a falsa impressão de "100% de chance de comprar". O score absoluto
  é mais honesto: um cliente com 72 pts tem histórico forte, mas não é certeza.

Penalidades (CF2 — calibrado para evitar colapso da distribuição):
  ≤ 7 dias    → ×0.75  (acabou de comprar — prioridade baixa de ligação)
  8–30 dias   → ×0.92  (no ciclo do mês — leve redução)
  31–100 dias → ×1.00  (janela normal de recompra B2B)
  101–180 dias→ ×0.70  (esfriando)
  > 180 dias  → ×0.30  (inativo)

Tier de recência (exibição visual):
  QUENTE   : 0–30 dias
  MORNO    : 31–100 dias
  FRIO     : 101–180 dias
  DORMENTE : > 180 dias

Fornecedor principal: cd_fornecedor que mais vendeu ao cliente (vol) nos
últimos 12 meses — exibido na Lista de Ação conforme Req 2.2.

═══════════════════════════════════════════════════════════════════════════════
SNAPSHOT — lógica legada de acao_engine.py (removido na task 1.1)
Referência para task 6.2 (migrar _gerar_acao_sugerida para este engine).
═══════════════════════════════════════════════════════════════════════════════

def _gerar_motivo_contato(cliente_data: dict) -> str:
    dias  = cliente_data.get("dias_sem_comprar", 0)
    score = cliente_data.get("score_propensao", 0)
    freq  = cliente_data.get("frequencia_compras", 0)
    vol   = cliente_data.get("volume_medio_mensal", 0)
    linha = cliente_data.get("linha", "")
    partes = []
    if dias >= 45 and freq >= 0.5:
        partes.append(f"cliente regular sem comprar há {dias} dias")
    elif dias >= 30:
        partes.append(f"{dias} dias sem pedido")
    elif dias <= 7:
        partes.append("comprou recentemente — oportunidade de ampliar volume")
    if score >= 70:
        partes.append("alta propensão de recompra")
    if vol > 0:
        vol_fmt = f"{int(round(vol)):,}".replace(",", ".")
        partes.append(f"volume médio {vol_fmt} ton/mês em {linha}")
    return " · ".join(partes) if partes else "perfil favorável para contato"

def _gerar_acao_sugerida(cliente_data: dict) -> str:
    dias  = cliente_data.get("dias_sem_comprar", 0)
    score = cliente_data.get("score_propensao", 0)
    freq  = cliente_data.get("frequencia_compras", 0)
    if dias >= 45 and freq >= 0.5:
        return "📞 Ligar — cliente regular atrasado"
    if score >= 70 and dias <= 30:
        return "💬 Oferecer volume adicional"
    if score >= 60:
        return "📞 Ligar — alta propensão"
    if dias >= 60:
        return "📧 E-mail de reativação"
    return "📞 Contato de relacionamento"

PRIORIDADE_LEGADO = {
    "URGENTE": "score >= 70 AND dias >= 45",
    "ALTA":    "score >= 60",
    "MÉDIA":   "score >= 30",
}
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

# ── Parâmetros calibrados (simulação 2026-05-26, 251.717 pares, c_vol=8.37) ──
C_VOL   = 8.37   # log1p(vol/mediana) × C_VOL → ~15 pts para vol = mediana × 5
PEN_7D  = 0.75   # penalidade ≤7d  (CF2 — não colapsa distribuição ativo 0-30d)
PEN_30D = 0.92   # penalidade 8-30d
PEN_ESF = 0.70   # penalidade esfriando 101-180d
PEN_INA = 0.30   # penalidade inativo >180d

SCORE_WEIGHTS = {
    "recencia":     0.30,
    "frequencia":   0.25,
    "sazonalidade": 0.15,
    "volume":       0.20,
    "tendencia":    0.10,
}

PRIORIDADE_THRESHOLDS = {
    "urgente": {"score_min": 70, "dias_min": 45},
    "alta":    {"score_min": 60},
    "media":   {"score_min": 30},
}


@dataclass
class ClientePropensao:
    cliente_id: str
    cliente_nome: str
    linha: str
    regiao: str
    uf: str
    score_propensao: float
    ultima_compra: Optional[date]
    dias_sem_comprar: int
    volume_medio_mensal: float
    frequencia_compras: float
    motivo_score: str
    tier: str = "DORMENTE"
    fornecedor_principal: str = ""
    telefone: str = ""
    email: str = ""


class PropensaoEngine:
    """Calcula scores de prioridade de contato — totalmente vetorizado, sem apply/loop."""

    def __init__(
        self,
        df_vendas: pd.DataFrame,
        df_clientes: pd.DataFrame | None = None,
        data_referencia: date | None = None,
    ):
        self.df_vendas   = df_vendas.copy()
        self.df_clientes = df_clientes.copy() if df_clientes is not None else pd.DataFrame()
        # data_referencia no __init__ permite backtest (Task 4.1):
        #   engine = PropensaoEngine(df, data_referencia=date(2025, 12, 31))
        # Se None, cada chamada de calcular_scores() usa date.today() como default.
        self._data_ref_default: pd.Timestamp | None = (
            pd.Timestamp(data_referencia) if data_referencia else None
        )
        self._last_scores: pd.DataFrame | None = None
        self._validar_colunas()
        self._preparar_dados()

    # ── Interface pública ─────────────────────────────────────────────────────

    def calcular_scores(
        self,
        linha: str | None = None,
        regiao: str | None = None,
        data_referencia: date | None = None,
    ) -> pd.DataFrame:
        # Prioridade: argumento explícito > data_ref do __init__ > hoje
        ref = (
            pd.Timestamp(data_referencia) if data_referencia
            else self._data_ref_default or pd.Timestamp.today()
        )
        mes_atual = ref.month

        # Filtra ANTES de qualquer agregação — reduz drasticamente o volume
        df = self.df_vendas
        if linha:
            df = df[df["linha"] == linha]
        if regiao:
            df = df[df["regiao"] == regiao]
        if df.empty:
            return pd.DataFrame()

        # ── Perfil base: última compra + região/UF ────────────────────────────
        ultima = (
            df.groupby(["cd_cliente", "linha"])
            .agg(
                ultima_compra=("data", "max"),
                regiao=("regiao", "last"),
                uf=("uf", "last"),
            )
            .reset_index()
        )
        ultima["dias_sem_comprar"] = (
            ref - pd.to_datetime(ultima["ultima_compra"])
        ).dt.days.clip(lower=0).astype(int)

        # ── Janelas temporais ─────────────────────────────────────────────────
        df = df.copy()
        df["data"] = pd.to_datetime(df["data"])

        corte_12m = ref - pd.DateOffset(months=12)
        corte_3m  = ref - pd.DateOffset(months=3)

        df_12m = df[df["data"] >= corte_12m]
        df_3m  = df[df["data"] >= corte_3m]

        # ── Frequência e volume nos últimos 12m ───────────────────────────────
        if not df_12m.empty:
            df_12m = df_12m.copy()
            df_12m["ano_mes"] = df_12m["data"].dt.to_period("M")
            freq = (
                df_12m.groupby(["cd_cliente", "linha"])["ano_mes"]
                .nunique()
                .div(12.0)
                .reset_index()
                .rename(columns={"ano_mes": "frequencia_compras"})
            )
            vol_med = (
                df_12m.groupby(["cd_cliente", "linha", "ano_mes"])["vol_ton"]
                .sum()
                .groupby(level=["cd_cliente", "linha"])
                .mean()
                .reset_index()
                .rename(columns={"vol_ton": "volume_medio_mensal"})
            )
            # Volume total 12m (para cálculo de tendência)
            vol_12m_total = (
                df_12m.groupby(["cd_cliente", "linha"])["vol_ton"]
                .sum()
                .reset_index()
                .rename(columns={"vol_ton": "vol_12m"})
            )
        else:
            freq         = pd.DataFrame(columns=["cd_cliente", "linha", "frequencia_compras"])
            vol_med      = pd.DataFrame(columns=["cd_cliente", "linha", "volume_medio_mensal"])
            vol_12m_total = pd.DataFrame(columns=["cd_cliente", "linha", "vol_12m"])

        # ── Volume últimos 3m (para tendência) ───────────────────────────────
        if not df_3m.empty:
            vol_3m_total = (
                df_3m.groupby(["cd_cliente", "linha"])["vol_ton"]
                .sum()
                .reset_index()
                .rename(columns={"vol_ton": "vol_3m"})
            )
        else:
            vol_3m_total = pd.DataFrame(columns=["cd_cliente", "linha", "vol_3m"])

        # ── Fornecedor principal: cd_fornecedor com maior volume nos últimos 12m ─
        fornecedor_principal = pd.DataFrame(
            columns=["cd_cliente", "linha", "fornecedor_principal"]
        )
        if "cd_fornecedor" in df_12m.columns and not df_12m.empty:
            forn = (
                df_12m.groupby(["cd_cliente", "linha", "cd_fornecedor"])["vol_ton"]
                .sum()
                .reset_index()
            )
            idx_max = forn.groupby(["cd_cliente", "linha"])["vol_ton"].idxmax()
            fornecedor_principal = (
                forn.loc[idx_max, ["cd_cliente", "linha", "cd_fornecedor"]]
                .rename(columns={"cd_fornecedor": "fornecedor_principal"})
            )

        # ── Junta tudo ────────────────────────────────────────────────────────
        perfil = (
            ultima
            .merge(freq,              on=["cd_cliente", "linha"], how="left")
            .merge(vol_med,           on=["cd_cliente", "linha"], how="left")
            .merge(vol_12m_total,     on=["cd_cliente", "linha"], how="left")
            .merge(vol_3m_total,      on=["cd_cliente", "linha"], how="left")
            .merge(fornecedor_principal, on=["cd_cliente", "linha"], how="left")
        )
        perfil["frequencia_compras"]   = perfil["frequencia_compras"].fillna(0.0)
        perfil["volume_medio_mensal"]  = perfil["volume_medio_mensal"].fillna(0.0)
        perfil["vol_12m"]              = perfil["vol_12m"].fillna(0.0)
        perfil["vol_3m"]               = perfil["vol_3m"].fillna(0.0)
        perfil["fornecedor_principal"] = perfil.get("fornecedor_principal",
                                                     pd.Series("", index=perfil.index)).fillna("")

        # ── Score de recência (vetorizado com np.select) ──────────────────────
        dias = perfil["dias_sem_comprar"]
        perfil["score_recencia"] = np.select(
            [dias <= 30, dias <= 60, dias <= 90, dias <= 180],
            [30.0,       20.0,       10.0,        5.0],
            default=0.0,
        )

        # ── Score de frequência: min(25, freq × 60) ───────────────────────────
        # freq = meses_com_compra / 12 → ex: compra todo mês = 1.0 → 25 pts
        # Calibrado: freq × 60 escala bem para base B2B (2-5 compras/ano = 10-25 pts)
        perfil["score_frequencia"] = (perfil["frequencia_compras"] * 60.0).clip(0, 25)

        # ── Score de sazonalidade por LINHA (peso 15, fallback 7.5) ──────────
        perfil["score_sazonalidade"] = perfil["linha"].map(
            lambda l: self._sazonalidade_linha.get(l, {}).get(mes_atual, 7.5)
        )

        # ── Score de volume: log1p(ratio) × C_VOL, clip 0-20 ─────────────────
        # Log evita que um único gigante domine — vol = mediana → ~5.8 pts
        # vol = mediana × 5 → ~15 pts (critério de calibração)
        vol_ref = self._vol_median_linha.get(linha or "_all", 1.0)
        ratio   = (perfil["volume_medio_mensal"] / max(vol_ref, 0.01)).clip(lower=0)
        perfil["score_volume"] = np.minimum(np.log1p(ratio.astype(float)) * C_VOL, 20.0)

        # ── Score de tendência: ratio vol_3m / (vol_12m/4) × 5, clip 0-10 ────
        # Mede se o cliente está acelerando o ritmo de compra
        # Ratio > 1 = comprando mais que a média trimestral → tendência positiva
        vol_12m_q = (perfil["vol_12m"] / 4.0).clip(lower=0.001)
        ratio_tend = (perfil["vol_3m"] / vol_12m_q).clip(lower=0)
        perfil["score_tendencia"] = (ratio_tend * 5.0).clip(0, 10)
        # Zera tendência para clientes sem histórico 12m
        perfil.loc[perfil["vol_12m"] == 0, "score_tendencia"] = 0.0

        # ── Score bruto: soma direta (sem min-max — valor absoluto) ──────────
        # rec: 0-30 | freq: 0-25 | saz: 0-15 | vol: 0-20 | tend: 0-10 → max 100
        perfil["score_bruto"] = (
            perfil["score_recencia"]
            + perfil["score_frequencia"]
            + perfil["score_sazonalidade"]
            + perfil["score_volume"]
            + perfil["score_tendencia"]
        ).clip(0, 100)

        # ── Penalidade por recência (vetorizado) — CF2 calibrado ─────────────
        # ≤ 7 dias    → ×0.75  (acabou de comprar — prioridade baixa de ligação)
        # 8–30 dias   → ×0.92  (no ciclo do mês — leve redução)
        # 31–100 dias → ×1.00  (janela normal de recompra B2B — sem penalidade)
        # 101–180 dias→ ×0.70  (esfriando)
        # > 180 dias  → ×0.30  (inativo)
        _dias = dias.to_numpy(dtype=np.float64)
        _sb   = perfil["score_bruto"].to_numpy(dtype=np.float64)
        perfil["score_propensao"] = pd.Series(
            np.select(
                [_dias <= 7, _dias <= 30, _dias <= 100, _dias <= 180],
                [_sb * PEN_7D, _sb * PEN_30D, _sb, _sb * PEN_ESF],
                default=_sb * PEN_INA,
            ),
            index=perfil.index,
            dtype=np.float64,
        ).clip(0, 100).round(1)

        # ── Tier de recência (QUENTE / MORNO / FRIO / DORMENTE) ──────────────
        perfil["tier"] = np.select(
            [dias <= 30, dias <= 100, dias <= 180],
            ["QUENTE",   "MORNO",    "FRIO"],
            default="DORMENTE",
        )

        # ── P1-F2: flag_sazon_insuficiente (<104 semanas distintas de histórico) ─
        # Threshold HC3: 104 semanas = 2 anos de dados semanais.
        # DISTINTO de flag_indefinido (<3 meses por linha): este gate é por cliente×linha.
        # Quando True: score_sazonalidade = NaN e score_bruto é recalculado sem o componente.
        # Lookup vetorizado: cd_cliente ainda não foi renomeado para cliente_id aqui
        semanas_hist = self._semanas_historico_cliente
        _key_saz = perfil["cd_cliente"].astype(str) + "||" + perfil["linha"].astype(str)
        _saz_map  = {f"{k[0]}||{k[1]}": v for k, v in semanas_hist.items()}
        perfil["flag_sazon_insuficiente"] = _key_saz.map(_saz_map).fillna(0) < 104
        mask_insuf = perfil["flag_sazon_insuficiente"]
        # Salva o valor de sazonalidade que foi usado (pode ser fallback 7.5 ou calculado)
        # e zera esse componente no score_bruto quando insuficiente.
        saz_usada = perfil["score_sazonalidade"].copy()
        perfil.loc[mask_insuf, "score_sazonalidade"] = np.nan
        # Recalcula score_bruto: subtrai a sazonalidade que estava embutida
        perfil.loc[mask_insuf, "score_bruto"] = (
            perfil.loc[mask_insuf, "score_bruto"] - saz_usada[mask_insuf]
        ).clip(0, 100)
        # Recalcula score_propensao para os afetados (aplica mesma penalidade de recência)
        _dias_insuf = dias[mask_insuf].to_numpy(dtype=np.float64)
        _sb_insuf   = perfil.loc[mask_insuf, "score_bruto"].to_numpy(dtype=np.float64)
        perfil.loc[mask_insuf, "score_propensao"] = pd.Series(
            np.select(
                [_dias_insuf <= 7, _dias_insuf <= 30, _dias_insuf <= 100, _dias_insuf <= 180],
                [_sb_insuf * PEN_7D, _sb_insuf * PEN_30D, _sb_insuf, _sb_insuf * PEN_ESF],
                default=_sb_insuf * PEN_INA,
            ),
            index=perfil.index[mask_insuf],
            dtype=np.float64,
        ).clip(0, 100).round(1)

        # ── Flag NOVO: cliente que não tinha histórico na linha antes de 90d ──
        # "Novo" = nunca apareceu nesta linha antes dos últimos 90 dias
        corte_90d   = ref - pd.DateOffset(days=90)
        df_antes_90 = df[df["data"] < corte_90d]
        if not df_antes_90.empty and "cd_cliente" in df_antes_90.columns:
            clientes_com_hist = set(
                zip(df_antes_90["cd_cliente"].astype(str),
                    df_antes_90["linha"].astype(str))
            )
            par_atual = list(zip(
                perfil["cd_cliente"].astype(str),
                perfil["linha"].astype(str),
            ))
            perfil["flag_novo"] = [p not in clientes_com_hist for p in par_atual]
        else:
            perfil["flag_novo"] = True

        # ── Flag INDEFINIDO: linha com histórico < 3 meses de dados ──────────
        # Score de linhas com histórico curto é estatisticamente não confiável
        meses_hist_linha = self._meses_historico_linha
        perfil["flag_indefinido"] = perfil["linha"].map(
            lambda l: meses_hist_linha.get(l, 0) < 3
        )

        # ── Rank dentro da população retornada ────────────────────────────────
        # Calculado DEPOIS da penalidade — rank = posição no ranking final
        # Será recalculado após ordenação no output

        # ── Motivo (vetorizado via categorias) ────────────────────────────────
        perfil["motivo_score"] = self._gerar_motivos_vetorizado(perfil)

        # ── Saída ─────────────────────────────────────────────────────────────
        # ── Lookup de nome e telefone do cliente ─────────────────────────────
        # Pega o valor mais recente por cd_cliente na base bruta
        df_raw = self.df_vendas
        clientes_perfil = set(perfil["cd_cliente"].astype(str))

        if "nome_cliente" in df_raw.columns:
            lookup_nome = (
                df_raw[df_raw["cd_cliente"].astype(str).isin(clientes_perfil)]
                .sort_values("data")
                .groupby("cd_cliente")["nome_cliente"]
                .last()
            )
            perfil["_nome"] = perfil["cd_cliente"].astype(str).map(lookup_nome)
        else:
            perfil["_nome"] = None

        if "telefone_cliente" in df_raw.columns:
            lookup_tel = (
                df_raw[df_raw["cd_cliente"].astype(str).isin(clientes_perfil)]
                .sort_values("data")
                .groupby("cd_cliente")["telefone_cliente"]
                .last()
            )
            perfil["telefone"] = perfil["cd_cliente"].astype(str).map(lookup_tel).fillna("")
        else:
            perfil["telefone"] = ""

        if "vendedor" in df_raw.columns:
            lookup_vend = (
                df_raw[df_raw["cd_cliente"].astype(str).isin(clientes_perfil)]
                .sort_values("data")
                .groupby("cd_cliente")["vendedor"]
                .last()
            )
            perfil["vendedor"] = perfil["cd_cliente"].astype(str).map(lookup_vend).fillna("")
        else:
            perfil["vendedor"] = ""

        if "gerencia" in df_raw.columns:
            lookup_ger = (
                df_raw[df_raw["cd_cliente"].astype(str).isin(clientes_perfil)]
                .sort_values("data")
                .groupby("cd_cliente")["gerencia"]
                .last()
            )
            perfil["gerencia"] = perfil["cd_cliente"].astype(str).map(lookup_ger).fillna("")
        else:
            perfil["gerencia"] = ""

        perfil = perfil.rename(columns={"cd_cliente": "cliente_id"})
        perfil["cliente_nome"] = perfil["_nome"].fillna(perfil["cliente_id"])
        perfil = perfil.drop(columns=["_nome"])

        if "email" not in perfil.columns:
            perfil["email"] = ""

        cols = [
            "cliente_id", "cliente_nome", "linha", "regiao", "uf",
            "score_propensao", "score_bruto", "tier",
            "flag_novo", "flag_indefinido", "flag_sazon_insuficiente",
            "ultima_compra", "dias_sem_comprar",
            "volume_medio_mensal", "frequencia_compras",
            "score_recencia", "score_frequencia", "score_sazonalidade",
            "score_volume", "score_tendencia",
            "motivo_score", "fornecedor_principal",
            "telefone", "email", "vendedor", "gerencia",
        ]
        out = (
            perfil[[c for c in cols if c in perfil.columns]]
            .sort_values("score_propensao", ascending=False)
            .reset_index(drop=True)
        )
        self._last_scores = out
        return out

    # ── P1-F3: decomposição de score para um único cliente×linha ─────────────

    def get_decomposition(self, cliente_id: str, linha: str) -> dict | None:
        """
        Retorna dict com os 5 componentes de score + flags para o cliente×linha.
        Lookup no último DataFrame calculado por calcular_scores().
        Retorna None se calcular_scores() ainda não foi chamado ou cliente não encontrado.
        """
        if self._last_scores is None or self._last_scores.empty:
            return None
        mask = (
            (self._last_scores["cliente_id"].astype(str) == str(cliente_id)) &
            (self._last_scores["linha"].astype(str) == str(linha))
        )
        rows = self._last_scores[mask]
        if rows.empty:
            return None
        r = rows.iloc[0]
        componentes = [
            "score_recencia", "score_frequencia", "score_sazonalidade",
            "score_volume", "score_tendencia",
        ]
        flags = ["flag_novo", "flag_indefinido", "flag_sazon_insuficiente"]
        result: dict = {
            "cliente_id": str(cliente_id),
            "linha": str(linha),
            "score_propensao": float(r.get("score_propensao", 0)),
            "score_bruto": float(r.get("score_bruto", 0)),
        }
        for c in componentes:
            v = r.get(c)
            result[c] = None if pd.isna(v) else float(v)
        for f in flags:
            if f in r.index:
                result[f] = bool(r[f])
        return result

    # ── Componentes individuais (mantidos para testes unitários) ─────────────

    def _calcular_recencia_score(self, dias_sem_comprar: int) -> float:
        if dias_sem_comprar <= 30:  return 30.0
        if dias_sem_comprar <= 60:  return 20.0
        if dias_sem_comprar <= 90:  return 10.0
        if dias_sem_comprar <= 180: return 5.0
        return 0.0

    def _calcular_frequencia_score(self, freq_historica: float) -> float:
        return float(min(max(freq_historica * 60.0, 0.0), 25.0))

    def _calcular_sazonalidade_score(self, cliente_id: str, mes_atual: int) -> float:
        return 7.5

    def _calcular_volume_score(self, volume_medio: float, linha: str) -> float:
        if linha not in self._vol_median_linha:
            return 5.0
        med = self._vol_median_linha[linha]
        if med <= 0 or volume_medio <= 0:
            return 0.0
        ratio = volume_medio / med
        return float(min(np.log1p(ratio) * C_VOL, 20.0))

    # ── Preparação de dados ───────────────────────────────────────────────────

    def _preparar_dados(self) -> None:
        df = self.df_vendas.copy()
        df["data"] = pd.to_datetime(df["data"])
        df["mes"]  = df["data"].dt.month
        df["ano"]  = df["data"].dt.year

        # semana_mes para o mapeamento de histórico semanal (P1-F2)
        if "semana_mes" not in df.columns:
            df["semana_mes"] = df["data"].dt.day.apply(
                lambda d: 1 if d <= 7 else 2 if d <= 14 else 3 if d <= 21 else 4
            )

        # Sazonalidade por LINHA: {linha: {mes: score_0_15}}
        # Peso 15 (era 25) — calibrado para não inflar scores de itens sazonais
        vol_linha_mes = (
            df.groupby(["linha", "mes"])["vol_ton"].sum().reset_index()
        )
        totais_linha  = vol_linha_mes.groupby("linha")["vol_ton"].transform("sum")
        vol_linha_mes["peso"]      = (vol_linha_mes["vol_ton"] / totais_linha).fillna(0)
        # Peso 15 máx (era 25) · fallback 7.5 (era 12.5)
        vol_linha_mes["score_saz"] = (vol_linha_mes["peso"] * 45.0).clip(0, 15)

        self._sazonalidade_linha: dict[str, dict[int, float]] = {}
        for linha, grp in vol_linha_mes.groupby("linha"):
            self._sazonalidade_linha[linha] = dict(zip(grp["mes"], grp["score_saz"]))

        ref_prep  = self._data_ref_default or pd.Timestamp.today()
        corte_12m = ref_prep - pd.DateOffset(months=12)

        if "cd_cliente" in df.columns:
            df_12m = df[df["data"] >= corte_12m].copy()
            df_12m["ano_mes"] = df_12m["data"].dt.to_period("M")

            # Volume mediano mensal por linha (mediana é mais robusta que média p/ outliers)
            vol_todos = (
                df_12m.groupby(["cd_cliente", "linha", "ano_mes"])["vol_ton"]
                .sum()
                .groupby(level=["cd_cliente", "linha"])
                .mean()
                .reset_index()
                .rename(columns={"vol_ton": "vol_med"})
            )
            self._vol_median_linha: dict[str, float] = (
                vol_todos.groupby("linha")["vol_med"].median().to_dict()
            )
            self._vol_median_linha["_all"] = float(
                vol_todos["vol_med"].median() if not vol_todos.empty else 1.0
            )

            # Frequência média por linha (mantida p/ referência interna)
            freq_todos = (
                df_12m.groupby(["cd_cliente", "linha"])["ano_mes"]
                .nunique()
                .div(12.0)
                .reset_index()
                .rename(columns={"ano_mes": "freq"})
            )
            self._freq_mean_linha: dict[str, float] = (
                freq_todos.groupby("linha")["freq"].mean().to_dict()
            )
            self._freq_mean_linha["_all"] = float(
                freq_todos["freq"].mean() if not freq_todos.empty else 0.25
            )

            # Histórico disponível por linha: quantos meses distintos existem
            # Usado pelo flag INDEFINIDO — linhas com < 3 meses têm score não confiável
            self._meses_historico_linha: dict[str, int] = (
                df.groupby("linha")["data"]
                .apply(lambda s: s.dt.to_period("M").nunique())
                .to_dict()
            )

            # Aliases retrocompatíveis
            self._vol_p75_ativos  = self._vol_median_linha.copy()
            self._volume_p75      = self._vol_median_linha.copy()
            self._freq_p90_linha  = self._freq_mean_linha.copy()

            # P1-F2: semanas distintas (ano_mes, semana_mes) por (cd_cliente, linha)
            # Usa histórico completo (não windowed) — mede profundidade total de dados.
            # Limitação conhecida: para backtest (data_referencia passada), o count
            # inclui dados após a data de referência, inflando levemente o total.
            # Aceitável para produção; Task 4.1 (backtest) pode windowed aqui se necessário.
            df_sem = df.copy()
            df_sem["ano_mes_sem_key"] = (
                df_sem["data"].dt.to_period("M").astype(str)
                + "_" + df_sem["semana_mes"].astype(str)
            )
            sem_hist = (
                df_sem.groupby(["cd_cliente", "linha"])["ano_mes_sem_key"]
                .nunique()
                .reset_index()
                .rename(columns={"ano_mes_sem_key": "n_semanas"})
            )
            self._semanas_historico_cliente: dict[tuple[str, str], int] = {
                (str(r["cd_cliente"]), str(r["linha"])): int(r["n_semanas"])
                for _, r in sem_hist.iterrows()
            }

        else:
            self._freq_mean_linha             = {"_all": 0.25}
            self._freq_p90_linha              = {"_all": 0.25}
            self._vol_median_linha            = {"_all": 1.0}
            self._vol_p75_ativos              = {"_all": 1.0}
            self._volume_p75                  = {}
            self._meses_historico_linha       = {}
            self._semanas_historico_cliente   = {}

    def _gerar_motivos_vetorizado(self, perfil: pd.DataFrame) -> pd.Series:
        """Gera coluna de motivos sem apply — usa np.select por categoria."""
        dias  = perfil["dias_sem_comprar"]
        freq  = perfil["frequencia_compras"]
        vol   = perfil["score_volume"]

        rec_txt = np.select(
            [dias <= 7, dias <= 30, dias <= 60, dias <= 90, dias <= 180],
            ["comprou esta semana", "comprou este mês",
             "60d sem comprar", "90d sem comprar", "inativo"],
            default="muito inativo",
        )
        rec_txt = np.where(
            (dias > 30) & (dias <= 180),
            dias.astype(str) + "d sem comprar",
            rec_txt,
        )

        freq_txt = np.select(
            [freq >= 0.8, freq >= 0.4, freq > 0],
            ["alta frequência", "frequência regular", "baixa frequência"],
            default="sem histórico recente",
        )

        vol_txt = np.where(vol >= 15, " · alto volume", "")

        return pd.Series(
            [f"{r} · {f}{v}" for r, f, v in zip(rec_txt, freq_txt, vol_txt)],
            index=perfil.index,
        )

    def _validar_colunas(self) -> None:
        faltando = {"linha", "data", "vol_ton"} - set(self.df_vendas.columns)
        if faltando:
            raise ValueError(f"df_vendas está faltando colunas: {faltando}")
