"""
Simulação offline da recalibração do score (tasks 4.2 -> 4.9 da v2).

Roda as fórmulas propostas SEM tocar o engine real, em sequência incremental,
para validar a distribuição antes do Kiro implementar.

Cenários simulados:
  C0 — Baseline (engine atual: min-max + freq/media + vol/mediana)
  C1 — Task 4.2: remover min-max final (score absoluto puro)
  C2 — Task 4.3: freq = min(25, freq × 60), sem normalizar por p90
  C3 — Task 4.4: vol = clip(log1p(vol/mediana) × c_vol, 0, 20)
  C4 — Task 4.5: saz peso 15 (era 25) + tendência 0-10
  C5 — Task 4.8: penalidade ≤7d de ×0.30 -> ×0.60
  CF — Final v2 (todas mudanças aplicadas)

Critério de aceitação (task 4.4b): ≥5% dos clientes ativos (0-100d) em cada
faixa (alto ≥70 / médio 40-69 / baixo <40).

Output: docs/CALIBRACAO_RECOMENDADA.md  +  CSV com distribuições.

Como rodar:
    python scripts/simulacao_calibracao/simular.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "app"))

from engines.propensao_engine import PropensaoEngine  # baseline

DATA_PATH   = ROOT / "data" / "processed" / "vendas_filtrada.parquet"
OUT_REPORT  = ROOT / "docs" / "CALIBRACAO_RECOMENDADA.md"
OUT_CSV     = ROOT / "docs" / "calibracao_distribuicoes.csv"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Preparação de dados — replica _preparar_dados do engine mas em pandas puro
# ═══════════════════════════════════════════════════════════════════════════════

def carrega_vendas() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df["data"] = pd.to_datetime(df["data"])
    for col in ["empresa", "linha", "regiao", "uf"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    return df


def constroi_perfil(df: pd.DataFrame, ref: pd.Timestamp) -> pd.DataFrame:
    """Constrói perfil base por (cliente, linha) com colunas necessárias para o score.

    Retorna DataFrame com:
      cd_cliente, linha, regiao, uf, ultima_compra, dias_sem_comprar,
      frequencia_compras (compras/mês nos últimos 12m),
      volume_medio_mensal (média mensal nos últimos 12m),
      compras_total (qtd total de pedidos no histórico),
      primeira_compra,
      vol_3m  (volume últimos 3 meses),
      vol_12m (volume últimos 12 meses),
      meses_linha_historico (qtd meses distintos da LINHA no histórico)
    """
    corte_12m = ref - pd.DateOffset(months=12)
    corte_3m  = ref - pd.DateOffset(months=3)

    df = df[df["data"] <= ref].copy()
    df["ano_mes"] = df["data"].dt.to_period("M")

    # Última compra, primeira compra, regiao/uf
    base = (
        df.groupby(["cd_cliente", "linha"])
        .agg(
            ultima_compra=("data", "max"),
            primeira_compra=("data", "min"),
            regiao=("regiao", "last"),
            uf=("uf", "last"),
            compras_total=("data", "count"),
        )
        .reset_index()
    )
    base["dias_sem_comprar"] = (ref - base["ultima_compra"]).dt.days.clip(lower=0).astype(int)

    # Frequência (meses distintos / 12) nos últimos 12m
    df_12m = df[df["data"] >= corte_12m].copy()
    if not df_12m.empty:
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
        vol_12m = (
            df_12m.groupby(["cd_cliente", "linha"])["vol_ton"]
            .sum().reset_index().rename(columns={"vol_ton": "vol_12m"})
        )
    else:
        freq    = pd.DataFrame(columns=["cd_cliente", "linha", "frequencia_compras"])
        vol_med = pd.DataFrame(columns=["cd_cliente", "linha", "volume_medio_mensal"])
        vol_12m = pd.DataFrame(columns=["cd_cliente", "linha", "vol_12m"])

    # Volume últimos 3m
    df_3m = df[df["data"] >= corte_3m]
    vol_3m = (
        df_3m.groupby(["cd_cliente", "linha"])["vol_ton"]
        .sum().reset_index().rename(columns={"vol_ton": "vol_3m"})
    )

    perfil = (
        base
        .merge(freq,    on=["cd_cliente", "linha"], how="left")
        .merge(vol_med, on=["cd_cliente", "linha"], how="left")
        .merge(vol_3m,  on=["cd_cliente", "linha"], how="left")
        .merge(vol_12m, on=["cd_cliente", "linha"], how="left")
    )
    for c in ["frequencia_compras", "volume_medio_mensal", "vol_3m", "vol_12m"]:
        perfil[c] = perfil[c].fillna(0.0)

    # Histórico da linha (meses distintos em toda base)
    hist_linha = df.groupby("linha")["ano_mes"].nunique().to_dict()
    perfil["meses_linha_historico"] = perfil["linha"].map(hist_linha).fillna(0).astype(int)

    return perfil


def calcula_referencias(df: pd.DataFrame, ref: pd.Timestamp) -> dict:
    """Calcula referências usadas pelos componentes:
       - freq_mean_linha (média da freq por linha — usado no baseline v1.5)
       - freq_p90_linha (engine atual usa)
       - vol_mediana_linha
       - sazonalidade_linha[(linha, mes)] -> score 0-25 (peso histórico × 75)
    """
    corte_12m = ref - pd.DateOffset(months=12)
    df = df[df["data"] <= ref].copy()
    df["mes"] = df["data"].dt.month
    df["ano_mes"] = df["data"].dt.to_period("M")
    df_12m = df[df["data"] >= corte_12m].copy()

    # Frequência por linha (média e p90)
    if not df_12m.empty:
        freq_cli = (
            df_12m.groupby(["cd_cliente", "linha"])["ano_mes"].nunique().div(12.0)
            .reset_index().rename(columns={"ano_mes": "freq"})
        )
        freq_mean = freq_cli.groupby("linha")["freq"].mean().to_dict()
        freq_p90  = freq_cli.groupby("linha")["freq"].quantile(0.9).to_dict()
        vol_cli = (
            df_12m.groupby(["cd_cliente", "linha", "ano_mes"])["vol_ton"].sum()
            .groupby(level=["cd_cliente", "linha"]).mean()
            .reset_index().rename(columns={"vol_ton": "vol_med"})
        )
        vol_mediana = vol_cli.groupby("linha")["vol_med"].median().to_dict()
        vol_p75     = vol_cli.groupby("linha")["vol_med"].quantile(0.75).to_dict()
    else:
        freq_mean = freq_p90 = {}
        vol_mediana = vol_p75 = {}

    # Sazonalidade por linha
    vol_linha_mes = df.groupby(["linha", "mes"])["vol_ton"].sum().reset_index()
    totais = vol_linha_mes.groupby("linha")["vol_ton"].transform("sum")
    vol_linha_mes["peso"] = (vol_linha_mes["vol_ton"] / totais).fillna(0)
    vol_linha_mes["score_saz_25"] = (vol_linha_mes["peso"] * 75.0).clip(0, 25)
    vol_linha_mes["score_saz_15"] = (vol_linha_mes["peso"] * 75.0).clip(0, 15)
    saz_25 = {(r.linha, r.mes): r.score_saz_25 for r in vol_linha_mes.itertuples()}
    saz_15 = {(r.linha, r.mes): r.score_saz_15 for r in vol_linha_mes.itertuples()}

    return {
        "freq_mean":   freq_mean,
        "freq_p90":    freq_p90,
        "vol_mediana": vol_mediana,
        "vol_p75":     vol_p75,
        "saz_25":      saz_25,
        "saz_15":      saz_15,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Componentes do score — cada cenário escolhe quais usar
# ═══════════════════════════════════════════════════════════════════════════════

def score_recencia(dias: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [dias <= 30, dias <= 60, dias <= 90, dias <= 180],
            [30.0,       20.0,       10.0,        5.0],
            default=0.0,
        ),
        index=dias.index,
    )


def score_freq_v1(perfil: pd.DataFrame, refs: dict) -> pd.Series:
    """Engine atual: freq / mean_linha × 25 (clip 0-25)."""
    ref = perfil["linha"].map(refs["freq_mean"]).fillna(0.25).clip(lower=0.01)
    return (perfil["frequencia_compras"] / ref * 25.0).clip(0, 25)


def score_freq_v2(perfil: pd.DataFrame) -> pd.Series:
    """Task 4.3: min(25, freq × 60). Não normaliza por linha."""
    return (perfil["frequencia_compras"] * 60.0).clip(0, 25)


def score_sazonalidade(perfil: pd.DataFrame, ref: pd.Timestamp,
                        saz_dict: dict, fallback: float) -> pd.Series:
    mes = ref.month
    return perfil["linha"].map(lambda l: saz_dict.get((l, mes), fallback))


def score_vol_v1(perfil: pd.DataFrame, refs: dict) -> pd.Series:
    """Engine atual: vol / mediana_linha × 20 (clip 0-20)."""
    med = perfil["linha"].map(refs["vol_mediana"]).fillna(1.0).clip(lower=0.01)
    return (perfil["volume_medio_mensal"] / med * 20.0).clip(0, 20)


def score_vol_v2(perfil: pd.DataFrame, refs: dict, c_vol: float) -> pd.Series:
    """Task 4.4: log1p(vol/mediana) × c_vol, clip 0-20."""
    med = perfil["linha"].map(refs["vol_mediana"]).fillna(1.0).clip(lower=0.01)
    ratio = (perfil["volume_medio_mensal"] / med).clip(lower=0)
    return np.minimum(np.log1p(ratio) * c_vol, 20.0)


def score_tendencia(perfil: pd.DataFrame) -> pd.Series:
    """Task 4.5: ratio = vol_3m / (vol_12m/4). Score = clip(ratio × 5, 0, 10)."""
    denom = (perfil["vol_12m"] / 4.0).clip(lower=0.01)
    ratio = (perfil["vol_3m"] / denom).clip(lower=0)
    return (ratio * 5.0).clip(0, 10)


def aplica_penalidade(score: pd.Series, dias: pd.Series,
                       p_7d: float = 0.60, p_30d: float = 0.80,
                       p_180d: float = 0.70, p_inativo: float = 0.30) -> pd.Series:
    """Penalidade multiplicativa por recência (parametrizada).

    Defaults reproduzem cenário CF da v2.
    """
    return pd.Series(
        np.select(
            [dias <= 7, dias <= 30, dias <= 100, dias <= 180],
            [score * p_7d, score * p_30d, score, score * p_180d],
            default=score * p_inativo,
        ),
        index=score.index,
    ).clip(0, 100)


def minmax_normaliza(score: pd.Series) -> pd.Series:
    smin, smax = score.min(), score.max()
    if smax > smin:
        return ((score - smin) / (smax - smin) * 100).clip(0, 100).round(1)
    return pd.Series(50.0, index=score.index)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Cenários
# ═══════════════════════════════════════════════════════════════════════════════

def cenario_C0_baseline(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp) -> pd.Series:
    """Engine atual: min-max final."""
    s_rec = score_recencia(perfil["dias_sem_comprar"])
    s_frq = score_freq_v1(perfil, refs)
    s_saz = score_sazonalidade(perfil, ref, refs["saz_25"], fallback=12.5)
    s_vol = score_vol_v1(perfil, refs)
    bruto = (s_rec + s_frq + s_saz + s_vol).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"], p_7d=0.30)
    return minmax_normaliza(bruto)


def cenario_C1_sem_minmax(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp) -> pd.Series:
    """C0 sem normalização min-max final."""
    s_rec = score_recencia(perfil["dias_sem_comprar"])
    s_frq = score_freq_v1(perfil, refs)
    s_saz = score_sazonalidade(perfil, ref, refs["saz_25"], fallback=12.5)
    s_vol = score_vol_v1(perfil, refs)
    bruto = (s_rec + s_frq + s_saz + s_vol).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"], p_7d=0.30)
    return bruto.round(1)


def cenario_C2_freq_v2(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp) -> pd.Series:
    """C1 + freq nova fórmula."""
    s_rec = score_recencia(perfil["dias_sem_comprar"])
    s_frq = score_freq_v2(perfil)
    s_saz = score_sazonalidade(perfil, ref, refs["saz_25"], fallback=12.5)
    s_vol = score_vol_v1(perfil, refs)
    bruto = (s_rec + s_frq + s_saz + s_vol).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"], p_7d=0.30)
    return bruto.round(1)


def cenario_C3_vol_log(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp,
                        c_vol: float) -> pd.Series:
    """C2 + volume logarítmico."""
    s_rec = score_recencia(perfil["dias_sem_comprar"])
    s_frq = score_freq_v2(perfil)
    s_saz = score_sazonalidade(perfil, ref, refs["saz_25"], fallback=12.5)
    s_vol = score_vol_v2(perfil, refs, c_vol)
    bruto = (s_rec + s_frq + s_saz + s_vol).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"], p_7d=0.30)
    return bruto.round(1)


def cenario_C4_saz_tend(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp,
                         c_vol: float) -> pd.Series:
    """C3 + saz peso 15 + tendência 10."""
    s_rec  = score_recencia(perfil["dias_sem_comprar"])
    s_frq  = score_freq_v2(perfil)
    s_saz  = score_sazonalidade(perfil, ref, refs["saz_15"], fallback=7.5)
    s_vol  = score_vol_v2(perfil, refs, c_vol)
    s_tend = score_tendencia(perfil)
    bruto = (s_rec + s_frq + s_saz + s_vol + s_tend).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"], p_7d=0.30)
    return bruto.round(1)


def cenario_CF_final(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp,
                      c_vol: float) -> pd.Series:
    """Final v2 proposto pelas tasks: pen 7d=0.60, 30d=0.80."""
    s_rec  = score_recencia(perfil["dias_sem_comprar"])
    s_frq  = score_freq_v2(perfil)
    s_saz  = score_sazonalidade(perfil, ref, refs["saz_15"], fallback=7.5)
    s_vol  = score_vol_v2(perfil, refs, c_vol)
    s_tend = score_tendencia(perfil)
    bruto = (s_rec + s_frq + s_saz + s_vol + s_tend).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"],
                              p_7d=0.60, p_30d=0.80, p_180d=0.70, p_inativo=0.30)
    return bruto.round(1)


def cenario_CF2_pen_suavizada(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp,
                               c_vol: float) -> pd.Series:
    """CF2 — penalidades suavizadas para passar no critério 4.4b.
    Diagnose: cliente top no bruto chega a 92 pts, mas pen ×0.60 (≤7d) joga p/ 55.
    Suavizando: ≤7d=0.75, 8-30d=0.92 — preserva sinal de 'comprou recente' sem zerar.
    """
    s_rec  = score_recencia(perfil["dias_sem_comprar"])
    s_frq  = score_freq_v2(perfil)
    s_saz  = score_sazonalidade(perfil, ref, refs["saz_15"], fallback=7.5)
    s_vol  = score_vol_v2(perfil, refs, c_vol)
    s_tend = score_tendencia(perfil)
    bruto = (s_rec + s_frq + s_saz + s_vol + s_tend).clip(0, 100)
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"],
                              p_7d=0.75, p_30d=0.92, p_180d=0.70, p_inativo=0.30)
    return bruto.round(1)


def cenario_CF3_score_objetivo(perfil: pd.DataFrame, refs: dict, ref: pd.Timestamp,
                                c_vol: float) -> pd.Series:
    """CF3 — score 'objetivo' SEM penalidade de compra recente.
    Filosofia: penalidade serve para ordenar contato, não para reduzir o valor do
    cliente. Clientes inativos antigos AINDA são penalizados, mas clientes
    recentes mantêm o score real (o que indica 'cliente bom').
    """
    s_rec  = score_recencia(perfil["dias_sem_comprar"])
    s_frq  = score_freq_v2(perfil)
    s_saz  = score_sazonalidade(perfil, ref, refs["saz_15"], fallback=7.5)
    s_vol  = score_vol_v2(perfil, refs, c_vol)
    s_tend = score_tendencia(perfil)
    bruto = (s_rec + s_frq + s_saz + s_vol + s_tend).clip(0, 100)
    # Sem penalidade para dias <= 100 — score reflete propensão real do cliente
    bruto = aplica_penalidade(bruto, perfil["dias_sem_comprar"],
                              p_7d=1.00, p_30d=1.00, p_180d=0.70, p_inativo=0.30)
    return bruto.round(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Métricas / relatório
# ═══════════════════════════════════════════════════════════════════════════════

def stats(scores: pd.Series, perfil: pd.DataFrame) -> dict:
    """Estatísticas globais e por segmento de inatividade."""
    s = scores.dropna()
    out = {
        "n": len(s),
        "mean": round(s.mean(), 2),
        "median": round(s.median(), 2),
        "max": round(s.max(), 2),
        "p25": round(s.quantile(0.25), 2),
        "p75": round(s.quantile(0.75), 2),
        "alto_pct":  round((s >= 70).mean() * 100, 2),
        "medio_pct": round(((s >= 40) & (s < 70)).mean() * 100, 2),
        "baixo_pct": round((s < 40).mean() * 100, 2),
    }
    # Por segmento de inatividade
    seg_def = [
        ("ativo_0_30",   (perfil["dias_sem_comprar"] >= 0)   & (perfil["dias_sem_comprar"] <= 30)),
        ("ativo_31_100", (perfil["dias_sem_comprar"] >= 31)  & (perfil["dias_sem_comprar"] <= 100)),
        ("esfriando_101_180", (perfil["dias_sem_comprar"] >= 101) & (perfil["dias_sem_comprar"] <= 180)),
        ("inativo_181_365",   (perfil["dias_sem_comprar"] >= 181) & (perfil["dias_sem_comprar"] <= 365)),
        ("dormente_366+", (perfil["dias_sem_comprar"] >= 366)),
    ]
    for label, mask in seg_def:
        s_seg = scores[mask].dropna()
        if len(s_seg) == 0:
            out[f"{label}_n"]    = 0
            out[f"{label}_mean"] = None
            out[f"{label}_alto_pct"] = None
            continue
        out[f"{label}_n"]    = len(s_seg)
        out[f"{label}_mean"] = round(s_seg.mean(), 2)
        out[f"{label}_alto_pct"]  = round((s_seg >= 70).mean() * 100, 2)
        out[f"{label}_medio_pct"] = round(((s_seg >= 40) & (s_seg < 70)).mean() * 100, 2)
        out[f"{label}_baixo_pct"] = round((s_seg < 40).mean() * 100, 2)
    return out


def faixa_para_str(stat: dict, segmento: str) -> str:
    n = stat.get(f"{segmento}_n", 0)
    if n == 0:
        return "—"
    a = stat[f"{segmento}_alto_pct"]
    m = stat[f"{segmento}_medio_pct"]
    b = stat[f"{segmento}_baixo_pct"]
    return f"{a:.1f}% / {m:.1f}% / {b:.1f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Calibração do c_vol
# ═══════════════════════════════════════════════════════════════════════════════

def calibra_c_vol(perfil: pd.DataFrame, refs: dict) -> float:
    """Calibra c_vol para que vol = mediana × 5 dê ~15 pts.

    score = c_vol × log1p(ratio) = c_vol × log1p(5) ≈ c_vol × 1.7918
    Se queremos score = 15 quando ratio = 5: c_vol = 15 / log1p(5) ≈ 8.37
    """
    target = 15.0
    ratio  = 5.0
    return round(target / np.log1p(ratio), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Pipeline principal
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("\n=== Simulação offline da recalibração v2 ===\n")

    print("[1/4] Carregando dados...")
    df = carrega_vendas()
    print(f"  - {len(df):,} linhas, período {df['data'].min().date()} -> {df['data'].max().date()}")

    ref = pd.Timestamp.today().normalize()
    print(f"  - Data de referência: {ref.date()}")

    print("[2/4] Construindo perfil base (~30s)...")
    perfil = constroi_perfil(df, ref)
    refs   = calcula_referencias(df, ref)
    print(f"  - {len(perfil):,} pares (cliente × linha)")
    print(f"  - {perfil['cd_cliente'].nunique():,} clientes únicos")
    print(f"  - {perfil['linha'].nunique()} linhas")

    c_vol = calibra_c_vol(perfil, refs)
    print(f"  - c_vol calibrado: {c_vol}")

    print("[3/4] Rodando cenários...")
    cenarios = {
        "C0_baseline":      cenario_C0_baseline(perfil, refs, ref),
        "C1_sem_minmax":    cenario_C1_sem_minmax(perfil, refs, ref),
        "C2_freq_v2":       cenario_C2_freq_v2(perfil, refs, ref),
        "C3_vol_log":       cenario_C3_vol_log(perfil, refs, ref, c_vol),
        "C4_saz15_tend":    cenario_C4_saz_tend(perfil, refs, ref, c_vol),
        "CF_v2_kiro":       cenario_CF_final(perfil, refs, ref, c_vol),
        "CF2_pen_suave":    cenario_CF2_pen_suavizada(perfil, refs, ref, c_vol),
        "CF3_sem_pen_ativos": cenario_CF3_score_objetivo(perfil, refs, ref, c_vol),
    }

    print("[4/4] Computando estatísticas e gerando relatório...")
    todas_stats = {nome: stats(s, perfil) for nome, s in cenarios.items()}

    # CSV — tabela completa
    df_stats = pd.DataFrame(todas_stats).T
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_stats.to_csv(OUT_CSV, index_label="cenario")
    print(f"  - CSV salvo: {OUT_CSV.relative_to(ROOT)}")

    # Markdown
    gerar_relatorio(todas_stats, perfil, refs, c_vol, ref)
    print(f"  - Markdown salvo: {OUT_REPORT.relative_to(ROOT)}")

    # Critério de aceitação (task 4.4b)
    print("\n=== Critério de aceitação (task 4.4b) ===")
    print("  >= 5% dos clientes ativos (0-100d) em cada faixa (alto/medio/baixo)\n")
    for nome in ["CF_v2_kiro", "CF2_pen_suave", "CF3_sem_pen_ativos"]:
        final = todas_stats[nome]
        print(f"Cenario {nome}:")
        for seg in ["ativo_0_30", "ativo_31_100"]:
            a = final.get(f"{seg}_alto_pct")  or 0
            m = final.get(f"{seg}_medio_pct") or 0
            b = final.get(f"{seg}_baixo_pct") or 0
            ok = (a >= 5 and m >= 5 and b >= 5)
            flag = "OK" if ok else "FALHA"
            print(f"  [{flag}] {seg}: alto={a:.1f}% medio={m:.1f}% baixo={b:.1f}%")
        print()


def gerar_relatorio(stats_all: dict, perfil: pd.DataFrame,
                     refs: dict, c_vol: float, ref: pd.Timestamp) -> None:
    cenario_descs = {
        "C0_baseline":          "Engine atual (min-max + freq/mean + vol/mediana)",
        "C1_sem_minmax":        "Task 4.2: remover min-max final (score absoluto)",
        "C2_freq_v2":           "Task 4.3: freq = min(25, freq × 60)",
        "C3_vol_log":           f"Task 4.4: vol = log1p(vol/mediana) × {c_vol}, clip 0-20",
        "C4_saz15_tend":        "Task 4.5: saz peso 15 + tendência 0-10",
        "CF_v2_kiro":           "v2 conforme tasks: pen 7d=0.60, 30d=0.80",
        "CF2_pen_suave":        "AJUSTE: pen 7d=0.75, 30d=0.92 (recomendado)",
        "CF3_sem_pen_ativos":   "ALTERNATIVA: sem penalidade até 100d",
    }

    lines = []
    lines.append("# Calibração Recomendada — Score de Propensão v2\n")
    lines.append(f"**Data de referência da simulação:** {ref.date()}  ")
    lines.append(f"**Base:** {len(perfil):,} pares (cliente × linha) · {perfil['cd_cliente'].nunique():,} clientes  ")
    lines.append(f"**c_vol calibrado:** {c_vol} (para vol = mediana × 5 -> ~15 pts)\n")
    lines.append("Esta simulação roda as fórmulas das tasks 4.x **antes** da implementação. ")
    lines.append("O objetivo é validar se a distribuição final do score atende ao critério de ")
    lines.append("aceitação da task 4.4b (≥5% dos clientes ativos em cada faixa).\n")

    # Tabela 1 — distribuição global
    lines.append("## 1. Distribuição global por cenário\n")
    lines.append("| Cenário | n | mean | median | max | p25 | p75 | Alto ≥70 | Médio 40-69 | Baixo <40 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for nome, s in stats_all.items():
        lines.append(
            f"| `{nome}` | {s['n']:,} | {s['mean']} | {s['median']} | {s['max']} | "
            f"{s['p25']} | {s['p75']} | "
            f"{s['alto_pct']}% | {s['medio_pct']}% | {s['baixo_pct']}% |"
        )
    lines.append("")
    lines.append("**Descrições:**")
    for k, v in cenario_descs.items():
        lines.append(f"- `{k}` — {v}")
    lines.append("")

    # Tabela 2 — distribuição por segmento de inatividade
    lines.append("## 2. Distribuição por segmento de inatividade (Alto% / Médio% / Baixo%)\n")
    segs = ["ativo_0_30", "ativo_31_100", "esfriando_101_180",
            "inativo_181_365", "dormente_366+"]
    lines.append("| Cenário | Ativo 0-30d | Ativo 31-100d | Esfriando 101-180d | Inativo 181-365d | Dormente >365d |")
    lines.append("|---|---|---|---|---|---|")
    for nome in stats_all:
        cells = [f"`{nome}`"]
        for seg in segs:
            cells.append(faixa_para_str(stats_all[nome], seg))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # Critério de aceitação
    lines.append("## 3. Critério de aceitação (task 4.4b)\n")
    lines.append("**Regra:** após a recalibração, ≥5% dos clientes ativos (0-100d) devem cair ")
    lines.append("em cada uma das faixas alto/médio/baixo. Isso garante que a distribuição ")
    lines.append("não colapse novamente no extremo (problema de 94% baixo da v1).\n")

    final = stats_all["CF_v2_kiro"]
    lines.append("**Resultado para o cenário final `CF_v2_kiro`:**\n")
    lines.append("| Segmento | n | Alto ≥70 | Médio 40-69 | Baixo <40 | Status |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for seg, label in [("ativo_0_30", "Ativo 0-30d"), ("ativo_31_100", "Ativo 31-100d")]:
        n = final.get(f"{seg}_n", 0)
        a = final.get(f"{seg}_alto_pct")  or 0
        m = final.get(f"{seg}_medio_pct") or 0
        b = final.get(f"{seg}_baixo_pct") or 0
        ok = (a >= 5 and m >= 5 and b >= 5)
        flag = "✅ OK" if ok else "❌ FALHA"
        lines.append(f"| {label} | {n:,} | {a}% | {m}% | {b}% | {flag} |")
    lines.append("")

    # Recomendações ao Kiro
    lines.append("## 4. Recomendações para o Kiro\n")
    lines.append("Ao executar as tasks 4.2 -> 4.9, usar os seguintes parâmetros já calibrados:\n")
    lines.append("```python")
    lines.append("# Task 4.3 — fórmula de frequência")
    lines.append("score_freq = (frequencia_compras * 60.0).clip(0, 25)")
    lines.append("")
    lines.append("# Task 4.4 — fórmula de volume (logarítmica)")
    lines.append(f"C_VOL = {c_vol}  # calibrado p/ vol = mediana × 5 -> ~15 pts")
    lines.append("ratio = (volume_medio / mediana_linha).clip(lower=0)")
    lines.append("score_vol = np.minimum(np.log1p(ratio) * C_VOL, 20.0)")
    lines.append("")
    lines.append("# Task 4.5 — sazonalidade peso 15 e tendência peso 10")
    lines.append("score_saz_max = 15  # era 25")
    lines.append("score_saz_fallback = 7.5  # era 12.5")
    lines.append("ratio_tend = (vol_3m / (vol_12m / 4)).clip(lower=0)")
    lines.append("score_tend = (ratio_tend * 5.0).clip(0, 10)")
    lines.append("")
    lines.append("# Task 4.8 — penalidade ≤7d")
    lines.append("PEN_7D = 0.60  # era 0.30")
    lines.append("```\n")

    lines.append("## 5. Análise comparativa\n")
    lines.append(_comparativo_textual(stats_all))
    lines.append("")

    # Próximos passos
    lines.append("## 6. Próximos passos\n")
    lines.append("1. Kiro executa tasks 4.2 -> 4.9 usando os parâmetros calibrados acima.")
    lines.append("2. Após implementar, rodar este script novamente para confirmar paridade ")
    lines.append("   entre simulação e implementação real.")
    lines.append("3. Task 4.4b vira apenas uma confirmação (já foi validado aqui).\n")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def _comparativo_textual(stats_all: dict) -> str:
    """Gera análise comparativa entre os cenários."""
    baseline = stats_all["C0_baseline"]
    final    = stats_all["CF_v2_kiro"]

    txt = []
    txt.append("**Baseline (engine atual) vs Final v2:**\n")
    txt.append(f"- Score médio: {baseline['mean']} -> {final['mean']} "
               f"({'+' if final['mean']>baseline['mean'] else ''}{final['mean']-baseline['mean']:.1f})")
    txt.append(f"- Score máximo: {baseline['max']} -> {final['max']}")
    txt.append(f"- % alto (≥70): {baseline['alto_pct']}% -> {final['alto_pct']}%")
    txt.append(f"- % médio (40-69): {baseline['medio_pct']}% -> {final['medio_pct']}%")
    txt.append(f"- % baixo (<40): {baseline['baixo_pct']}% -> {final['baixo_pct']}%")
    txt.append("")
    txt.append("**Efeito de cada mudança incremental:**\n")
    ordem = ["C0_baseline", "C1_sem_minmax", "C2_freq_v2",
             "C3_vol_log", "C4_saz15_tend", "CF_v2_kiro"]
    for i in range(1, len(ordem)):
        ant, cur = stats_all[ordem[i-1]], stats_all[ordem[i]]
        delta_mean = cur["mean"] - ant["mean"]
        delta_alto = cur["alto_pct"] - ant["alto_pct"]
        txt.append(
            f"- `{ordem[i-1]}` -> `{ordem[i]}`: "
            f"mean Δ={delta_mean:+.1f}, alto% Δ={delta_alto:+.1f}pp"
        )
    return "\n".join(txt)


if __name__ == "__main__":
    main()
