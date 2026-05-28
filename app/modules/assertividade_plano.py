"""
Assertividade do Plano — Aba 5  (v4)

Estrutura da página:
  [1] Header + Banner de status + 4 KPI cards
  [2] Gráfico principal — volume semanal Real vs S&OP vs S&OE
      12 semanas históricas + 8 futuras, separador hoje →
  [3] Tabela agregada compacta — métricas por semana (sem quebra por linha)
  [4] Expander: detalhe por linha de produto (S&OP)
  [5] Expander: detalhe por linha de produto (S&OE)
  [6] Glossário

Constantes:
  N_HIST   = 12   semanas históricas (incluindo a atual)
  N_FUTURO = 8    semanas futuras
  N_CALIB  = 4    semanas para calcular GAP projetado
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import GERENCIA_CONFIG, GERENCIA_DESCONHECIDA
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
    fmt_ton as _fmt_ton,
)

# ── Constantes ────────────────────────────────────────────────────────────────
_FONT    = "Inter, Arial, sans-serif"
_BG      = "rgba(0,0,0,0)"
N_HIST   = 12
N_FUTURO = 8
N_CALIB  = 4

_TH_WMAPE = (10.0, 20.0)
_TH_BIAS  = (5.0,  12.0)
_TH_ADER  = (85.0, 70.0)

_MESES_ABR = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
_MESES_FULL = {
    1: "Janeiro",   2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",      6: "Junho",     7: "Julho",    8: "Agosto",
    9: "Setembro", 10: "Outubro",  11: "Novembro", 12: "Dezembro",
}

_GLOSSARIO: dict[str, str] = {
    "WMAPE": (
        "Weighted Mean Absolute Percentage Error — erro percentual médio "
        "ponderado pelo volume. Verde ≤10% · Amarelo 10–20% · Vermelho >20%."
    ),
    "Bias": (
        "Viés sistemático — se o plano tende a superestimar (+) "
        "ou subestimar (−) o realizado. Verde |bias| ≤5%."
    ),
    "Aderência": (
        "% de semanas em que o erro ficou dentro de ±10% do plano. Meta: ≥85%."
    ),
    "GAP": (
        "Diferença Real − Plano em toneladas. "
        "Positivo = real acima do plano. Negativo = real abaixo."
    ),
    "GAP Projetado": (
        f"Estimativa do desvio futuro = média de (Real − Plano) "
        f"das últimas {N_CALIB} semanas com realizado > 0."
    ),
    "S&OP": (
        "Sales & Operations Planning — plano de médio prazo, "
        "elaborado 30–60 dias antes do mês de execução."
    ),
    "S&OE": (
        "Sales & Operations Execution — programa semanal que "
        "ajusta o S&OP com sinais de curto prazo."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# GERÊNCIA
# ═══════════════════════════════════════════════════════════════════════════════

def _gerencia_efetiva(familia: str, regiao: str) -> str:
    fam = str(familia).upper() if pd.notna(familia) else ""
    reg = str(regiao).upper()  if pd.notna(regiao)  else ""
    for ger, cfg in GERENCIA_CONFIG.items():
        if fam and fam in cfg.get("familias_override", set()):
            return ger
        if reg and reg in cfg.get("regioes", set()):
            return ger
    return GERENCIA_DESCONHECIDA


def _add_gerencia(df: pd.DataFrame) -> pd.DataFrame:
    if "gerencia" in df.columns:
        return df
    df = df.copy()
    if "familia" not in df.columns:
        df["familia"] = ""
    df["gerencia"] = df.apply(
        lambda r: _gerencia_efetiva(r.get("familia", ""), r.get("regiao", "")), axis=1
    )
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS
# ═══════════════════════════════════════════════════════════════════════════════

def _wmape(real: pd.Series, plano: pd.Series) -> float:
    d = real.sum()
    return float((real - plano).abs().sum() / d * 100) if d > 0 else float("nan")


def _bias(real: pd.Series, plano: pd.Series) -> float:
    d = real.sum()
    return float((plano - real).sum() / d * 100) if d > 0 else float("nan")


def _assertividade(
    real: pd.Series,
    plano: pd.Series,
    base: str = "real",
) -> float:
    """
    Assertividade = 1 − MAPE, onde MAPE é calculado sobre a série acumulada.

    base="real"  → MAPE = Σ|Real−Plano| / ΣReal   (Forecast Accuracy clássico)
    base="plano" → MAPE = Σ|Real−Plano| / ΣPlano  (perspectiva do planejador)

    Retorna valor em % (0–100), limitado inferiormente a 0.
    Retorna nan quando a base é zero (evita divisão por zero).
    """
    base_vals = real if base == "real" else plano
    d = base_vals.sum()
    if d == 0:
        return float("nan")
    mape = float((real - plano).abs().sum() / d)
    return float(max(0.0, (1.0 - mape) * 100))


def _assertividade_semana(
    real: float,
    plano: float,
    base: str = "real",
) -> float:
    """Assertividade de uma única semana (escalares)."""
    b = real if base == "real" else plano
    if b == 0:
        return float("nan")
    return float(max(0.0, (1.0 - abs(real - plano) / b) * 100))


def _calc(df: pd.DataFrame, col: str, base: str = "real") -> dict:
    r, p = df["vol_ton"], df[col]
    return {
        "assertividade": _assertividade(r, p, base),
        "bias":          _bias(r, p),
        "gap":           float((r - p).sum()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SEMÁFOROS
# ═══════════════════════════════════════════════════════════════════════════════

def _ca(v: float) -> str:
    """Semáforo de assertividade % (0–100). Verde ≥85 · Amarelo ≥70 · Vermelho <70."""
    if np.isnan(v): return "#94A3B8"
    return COR_VERDE if v >= _TH_ADER[0] else (COR_AMARELO if v >= _TH_ADER[1] else COR_VERMELHO)

def _cg(v: float) -> str:
    if np.isnan(v): return "#94A3B8"
    return COR_VERDE if v >= 0 else COR_VERMELHO


# ═══════════════════════════════════════════════════════════════════════════════
# SPARKLINE SVG
# ═══════════════════════════════════════════════════════════════════════════════

def _sparkline_svg(vals: list, cor: str, w: int = 80, h: int = 24) -> str:
    clean = [
        float(v) for v in vals
        if v is not None and not (isinstance(v, float) and np.isnan(v))
    ]
    if len(clean) < 2:
        return ""
    mn, mx = min(clean), max(clean)
    rng = mx - mn if mx != mn else 1.0
    pts = []
    for i, v in enumerate(clean):
        x = i / (len(clean) - 1) * w
        y = h - (v - mn) / rng * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg width="{w}" height="{h}" style="display:block;overflow:visible">'
        f'<polyline points="{" ".join(pts)}" fill="none" stroke="{cor}" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTES HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _secao(txt: str, sub: str = "") -> None:
    sub_html = (
        f'<div style="font-size:11px;color:#64748B;margin-top:3px;'
        f'font-family:{_FONT};">{sub}</div>'
        if sub else ""
    )
    st.markdown(
        f'<div style="margin:28px 0 14px 0;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:10px;font-weight:700;color:#64748B;'
        f'text-transform:uppercase;letter-spacing:1.5px;'
        f'font-family:{_FONT};white-space:nowrap;">{txt}</span>'
        f'<div style="flex:1;height:1px;background:#E2E8F0;"></div>'
        f'</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _banner_status(assertividade: float, bias: float) -> str:
    if np.isnan(assertividade):
        return ""
    mape = 100 - assertividade
    if mape <= 10 and abs(bias) <= 5:
        cor, icone, label, frase = (
            COR_VERDE, "&#x2713;", "PLANO SAUD&#xC1;VEL",
            f"Assertividade {assertividade:.1f}% &mdash; Bias {bias:+.1f}%",
        )
    elif mape > 20 or abs(bias) > 15:
        cor, icone, label, frase = (
            COR_VERMELHO, "&#x26A0;", "ATEN&#xC7;&#xC3;O CR&#xCD;TICA",
            f"Assertividade {assertividade:.1f}% &mdash; Bias {bias:+.1f}%",
        )
    else:
        cor, icone, label, frase = (
            COR_AMARELO, "&#x7E;", "ATEN&#xC7;&#xC3;O MODERADA",
            f"Assertividade {assertividade:.1f}% &mdash; Bias {bias:+.1f}%",
        )
    return (
        f'<div style="background:{cor}18;border-left:4px solid {cor};border-radius:8px;'
        f'padding:12px 20px;margin-bottom:20px;display:flex;align-items:center;gap:14px;">'
        f'<span style="font-size:22px;color:{cor};font-weight:700;">{icone}</span>'
        f'<div>'
        f'<span style="font-weight:800;color:{cor};font-size:12px;letter-spacing:1px;'
        f'text-transform:uppercase;font-family:{_FONT};">{label}</span>'
        f'<span style="color:#374151;font-size:13.5px;margin-left:12px;'
        f'font-family:{_FONT};">{frase}</span>'
        f'</div></div>'
    )


def _kpi_card(
    label: str, valor: str, cor: str, sub: str,
    spark_vals: list, tooltip: str = "",
) -> str:
    spark = _sparkline_svg(spark_vals, cor)
    tt = f'title="{tooltip}"' if tooltip else ""
    return (
        f'<div {tt} style="background:#FFFFFF;border-radius:12px;padding:16px 18px 12px;'
        f'border:1px solid #E2E8F0;border-left:4px solid {cor};'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.05);position:relative;overflow:hidden;">'
        f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.2px;color:#94A3B8;margin-bottom:6px;font-family:{_FONT};">{label}</div>'
        f'<div style="font-size:26px;font-weight:800;color:{cor};line-height:1.05;'
        f'letter-spacing:-0.8px;font-family:{_FONT};">{valor}</div>'
        f'<div style="margin-top:6px;font-size:11px;color:#94A3B8;font-family:{_FONT};">{sub}</div>'
        f'<div style="position:absolute;bottom:4px;right:8px;opacity:0.45;">{spark}</div>'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HORIZONTE TEMPORAL
# ═══════════════════════════════════════════════════════════════════════════════

def _build_week_sequence(
    df: pd.DataFrame,
    ano_sel: int,
    mes_sel: int,
    semana_atual: int,
) -> list[dict]:
    """N_HIST semanas históricas (inclusive atual) + N_FUTURO futuras."""
    n_sem_mes: dict[tuple[int, int], int] = {}
    for (a, m), grp in df.groupby(["ano", "mes"]):
        n_sem_mes[(int(a), int(m))] = int(grp["semana_mes"].max())

    def _prev(a, m, s):
        if s > 1:
            return a, m, s - 1
        m2 = m - 1 if m > 1 else 12
        a2 = a if m > 1 else a - 1
        return a2, m2, n_sem_mes.get((a2, m2), 4)

    def _next(a, m, s):
        ms = n_sem_mes.get((a, m), 4)
        if s < ms:
            return a, m, s + 1
        m2 = m + 1 if m < 12 else 1
        a2 = a if m < 12 else a + 1
        return a2, m2, 1

    hist: list[dict] = []
    ca, cm, cs = ano_sel, mes_sel, semana_atual
    for _ in range(N_HIST):
        hist.append({"ano": ca, "mes": cm, "semana_mes": cs, "is_future": False})
        ca, cm, cs = _prev(ca, cm, cs)
    hist.reverse()

    fut: list[dict] = []
    fa, fm, fs = ano_sel, mes_sel, semana_atual
    for _ in range(N_FUTURO):
        fa, fm, fs = _next(fa, fm, fs)
        fut.append({"ano": fa, "mes": fm, "semana_mes": fs, "is_future": True})

    return hist + fut


def _week_label(w: dict) -> str:
    return f"{_MESES_ABR[w['mes']]} S{w['semana_mes']}"


def _gap_projetado(
    df: pd.DataFrame,
    col_plano: str,
    semanas: list[dict],
) -> float:
    """Média de (Real − Plano) nas últimas N_CALIB semanas históricas com real > 0."""
    hist = [w for w in semanas if not w["is_future"]]
    deltas: list[float] = []
    for w in hist[-N_CALIB:]:
        sub = df[
            (df["ano"] == w["ano"]) &
            (df["mes"] == w["mes"]) &
            (df["semana_mes"] == w["semana_mes"])
        ]
        if sub.empty or sub["vol_ton"].sum() == 0 or col_plano not in sub.columns:
            continue
        deltas.append(float(sub["vol_ton"].sum() - sub[col_plano].sum()))
    return float(np.mean(deltas)) if deltas else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICO PRINCIPAL — volume semanal Real vs S&OP vs S&OE
# ═══════════════════════════════════════════════════════════════════════════════

def _fig_horizonte(
    df: pd.DataFrame,
    semanas: list[dict],
    tem_sop: bool,
    tem_soe: bool,
    gap_proj_sop: float,
    gap_proj_soe: float,
) -> go.Figure:
    """
    Gráfico de linha: volume semanal agregado (todas as linhas de produto).
    Eixo X = semanas (labels), históricas sólidas, futuras tracejadas.
    Separador visual 'hoje →' entre hist e futuro.
    """
    labels = [_week_label(w) for w in semanas]
    n_hist = sum(1 for w in semanas if not w["is_future"])
    idx_separador = n_hist - 1  # índice da última semana histórica

    def _agregar(col: str) -> list[float | None]:
        vals: list[float | None] = []
        for w in semanas:
            sub = df[
                (df["ano"] == w["ano"]) &
                (df["mes"] == w["mes"]) &
                (df["semana_mes"] == w["semana_mes"])
            ]
            if sub.empty or col not in sub.columns:
                vals.append(None)
            else:
                v = float(sub[col].sum())
                vals.append(v if v > 0 else None)
        return vals

    def _agregar_real() -> list[float | None]:
        vals: list[float | None] = []
        for w in semanas:
            if w["is_future"]:
                vals.append(None)
                continue
            sub = df[
                (df["ano"] == w["ano"]) &
                (df["mes"] == w["mes"]) &
                (df["semana_mes"] == w["semana_mes"])
            ]
            v = float(sub["vol_ton"].sum()) if not sub.empty else 0.0
            vals.append(v if v > 0 else None)
        return vals

    real_vals = _agregar_real()
    sop_vals  = _agregar("meta_sop") if tem_sop else None
    soe_vals  = _agregar("meta_soe") if tem_soe else None

    # GAP projetado para semanas futuras (constante por semana)
    def _proj_vals(base_vals: list[float | None], gap: float) -> list[float | None]:
        """Adiciona a projeção às semanas futuras baseada no plano + gap."""
        out: list[float | None] = []
        for i, (w, v) in enumerate(zip(semanas, base_vals)):
            if w["is_future"] and v is not None:
                out.append(v + gap)
            else:
                out.append(None)
        return out

    fig = go.Figure()

    # ── Fundo cinza nas semanas futuras ───────────────────────────────────────
    if n_hist < len(labels):
        # Add uma shape cobrindo a zona futura
        fig.add_vrect(
            x0=labels[n_hist] if n_hist < len(labels) else labels[-1],
            x1=labels[-1],
            fillcolor="rgba(241,245,249,0.6)",
            line_width=0,
            layer="below",
        )

    # ── Linha Real (histórico) ────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=labels[:n_hist],
        y=real_vals[:n_hist],
        mode="lines+markers",
        name="Real",
        line=dict(color=COR_PRIMARIA, width=3),
        marker=dict(size=8, color=COR_PRIMARIA, line=dict(color="white", width=2)),
        connectgaps=False,
        hovertemplate="<b>%{x}</b><br>Real: <b>%{y:,.0f} t</b><extra></extra>",
    ))

    # ── S&OP histórico + futuro ───────────────────────────────────────────────
    if sop_vals:
        fig.add_trace(go.Scatter(
            x=labels[:n_hist],
            y=sop_vals[:n_hist],
            mode="lines+markers",
            name="S&OP",
            line=dict(color="#94A3B8", width=2, dash="dot"),
            marker=dict(size=6, color="#94A3B8", line=dict(color="white", width=1.5)),
            connectgaps=False,
            hovertemplate="<b>%{x}</b><br>S&OP: <b>%{y:,.0f} t</b><extra></extra>",
        ))
        # Futuro S&OP (tracejado mais leve)
        fig.add_trace(go.Scatter(
            x=labels[n_hist:],
            y=sop_vals[n_hist:],
            mode="lines+markers",
            name="S&OP (proj.)",
            line=dict(color="#CBD5E1", width=1.5, dash="dash"),
            marker=dict(size=5, color="#CBD5E1"),
            connectgaps=False,
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>S&OP proj.: <b>%{y:,.0f} t</b><extra></extra>",
        ))

    # ── S&OE histórico + futuro ───────────────────────────────────────────────
    if soe_vals:
        fig.add_trace(go.Scatter(
            x=labels[:n_hist],
            y=soe_vals[:n_hist],
            mode="lines+markers",
            name="S&OE",
            line=dict(color=COR_ACENTO, width=2, dash="dot"),
            marker=dict(size=6, color=COR_ACENTO, line=dict(color="white", width=1.5)),
            connectgaps=False,
            hovertemplate="<b>%{x}</b><br>S&OE: <b>%{y:,.0f} t</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=labels[n_hist:],
            y=soe_vals[n_hist:],
            mode="lines+markers",
            name="S&OE (proj.)",
            line=dict(color="#FCD34D", width=1.5, dash="dash"),
            marker=dict(size=5, color="#FCD34D"),
            connectgaps=False,
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>S&OE proj.: <b>%{y:,.0f} t</b><extra></extra>",
        ))

    # ── Separador hist / futuro ───────────────────────────────────────────────
    if n_hist < len(labels):
        sep_x = labels[n_hist - 1]
        fig.add_vline(
            x=sep_x,
            line=dict(color="#64748B", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=sep_x, y=1.04, xref="x", yref="paper",
            text="hoje →",
            showarrow=False,
            font=dict(size=10, color="#64748B", family=_FONT),
            bgcolor="white",
            bordercolor="#E2E8F0",
            borderpad=4,
        )

    fig.update_layout(
        height=340,
        margin=dict(t=40, b=60, l=60, r=20),
        paper_bgcolor=_BG,
        plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT, size=11),
        hovermode="x unified",
        xaxis=dict(
            tickfont=dict(size=9, color="#64748B"),
            tickangle=-40,
            gridcolor="#F1F5F9",
            linecolor="#E2E8F0",
            automargin=True,
        ),
        yaxis=dict(
            title=dict(text="Volume (ton)", font=dict(size=11, color="#94A3B8")),
            tickformat=",",
            gridcolor="#F1F5F9",
            tickfont=dict(size=10, color="#94A3B8"),
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.04,
            xanchor="left", x=0,
            font=dict(size=10, family=_FONT),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E2E8F0",
            borderwidth=1,
        ),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# TABELA AGREGADA COMPACTA — métricas por semana (sem quebra por linha)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tabela_agregada(
    df: pd.DataFrame,
    semanas: list[dict],
    tem_sop: bool,
    tem_soe: bool,
    gap_proj_sop: float,
    gap_proj_soe: float,
    base_calc: str = "real",
) -> None:
    """
    Tabela compacta:
    - Colunas: semanas agrupadas por mês (MultiIndex) + Σ por mês
    - Linhas: Real (t) | S&OP (t) | GAP S&OP | Assert% S&OP | S&OE (t) | GAP S&OE | Assert% S&OE
    Semanas futuras: Plano visível, Real = —, GAP projetado em itálico.
    """
    # ── Agrupa semanas por mês ─────────────────────────────────────────────────
    meses_ordem: list[tuple[int, int]] = []
    meses_semanas: dict[tuple[int, int], list[dict]] = {}
    for w in semanas:
        k = (int(w["ano"]), int(w["mes"]))
        if k not in meses_semanas:
            meses_ordem.append(k)
            meses_semanas[k] = []
        meses_semanas[k].append(w)

    # ── Colunas MultiIndex + lookup ───────────────────────────────────────────
    col_tuples: list[tuple[str, str]] = []
    mes_lbl_map: dict[tuple[int, int], str] = {}
    for (a, m) in meses_ordem:
        weeks = meses_semanas[(a, m)]
        has_fut = any(w["is_future"] for w in weeks)
        lbl = f"{_MESES_ABR[m]}/{str(a)[-2:]}{'  →' if has_fut else ''}"
        mes_lbl_map[(a, m)] = lbl
        for w in weeks:
            col_tuples.append((lbl, f"S{w['semana_mes']}" + ("*" if w["is_future"] else "")))
        col_tuples.append((lbl, "Σ"))

    mi_cols = pd.MultiIndex.from_tuples(col_tuples, names=["Mês", "Sem"])

    # ── Linhas ────────────────────────────────────────────────────────────────
    metricas: list[str] = ["Real (t)"]
    if tem_sop:
        metricas += ["S&OP (t)", "GAP S&OP", "Assert% S&OP"]
    if tem_soe:
        metricas += ["S&OE (t)", "GAP S&OE", "Assert% S&OE"]

    # ── Coleta dados por semana ────────────────────────────────────────────────
    # Monta dicts: met -> {col_tuple: str}
    data_cells: dict[str, dict[tuple, str]] = {m: {} for m in metricas}

    for (a, m) in meses_ordem:
        weeks = meses_semanas[(a, m)]
        ml = mes_lbl_map[(a, m)]

        # Acumuladores mensais
        real_m = 0.0
        sop_m  = 0.0
        soe_m  = 0.0
        real_buf: list[float] = []
        sop_buf: list[float]  = []
        soe_buf: list[float]  = []

        for w in weeks:
            sl = f"S{w['semana_mes']}" + ("*" if w["is_future"] else "")
            ck = (ml, sl)

            sub = df[
                (df["ano"] == w["ano"]) &
                (df["mes"] == w["mes"]) &
                (df["semana_mes"] == w["semana_mes"])
            ]

            if w["is_future"]:
                real_w = None
                sop_w  = float(sub["meta_sop"].sum()) if (tem_sop and not sub.empty and "meta_sop" in sub.columns) else None
                soe_w  = float(sub["meta_soe"].sum()) if (tem_soe and not sub.empty and "meta_soe" in sub.columns) else None

                data_cells["Real (t)"][ck] = "—"
                if tem_sop:
                    data_cells["S&OP (t)"][ck]    = f"{int(round(sop_w)):,}" if sop_w else "—"
                    data_cells["GAP S&OP"][ck]    = f"~{int(round(gap_proj_sop)):+,}" if sop_w else "—"
                    data_cells["Assert% S&OP"][ck] = "—"
                if tem_soe:
                    data_cells["S&OE (t)"][ck]    = f"{int(round(soe_w)):,}" if soe_w else "—"
                    data_cells["GAP S&OE"][ck]    = f"~{int(round(gap_proj_soe)):+,}" if soe_w else "—"
                    data_cells["Assert% S&OE"][ck] = "—"

                if sop_w: sop_m += sop_w
                if soe_w: soe_m += soe_w

            else:
                real_w = float(sub["vol_ton"].sum()) if not sub.empty else 0.0
                sop_w  = float(sub["meta_sop"].sum()) if (tem_sop and not sub.empty and "meta_sop" in sub.columns) else 0.0
                soe_w  = float(sub["meta_soe"].sum()) if (tem_soe and not sub.empty and "meta_soe" in sub.columns) else 0.0

                gap_sop_w   = real_w - sop_w  if tem_sop else None
                gap_soe_w   = real_w - soe_w  if tem_soe else None
                assert_sop_w = _assertividade_semana(real_w, sop_w, base_calc) if tem_sop else float("nan")
                assert_soe_w = _assertividade_semana(real_w, soe_w, base_calc) if tem_soe else float("nan")

                data_cells["Real (t)"][ck] = f"{int(round(real_w)):,}" if real_w else "—"
                if tem_sop:
                    data_cells["S&OP (t)"][ck]    = f"{int(round(sop_w)):,}" if sop_w else "—"
                    data_cells["GAP S&OP"][ck]    = f"{int(round(gap_sop_w)):+,}" if (real_w or sop_w) else "—"
                    data_cells["Assert% S&OP"][ck] = f"{assert_sop_w:.1f}%" if not np.isnan(assert_sop_w) else "—"
                if tem_soe:
                    data_cells["S&OE (t)"][ck]    = f"{int(round(soe_w)):,}" if soe_w else "—"
                    data_cells["GAP S&OE"][ck]    = f"{int(round(gap_soe_w)):+,}" if (real_w or soe_w) else "—"
                    data_cells["Assert% S&OE"][ck] = f"{assert_soe_w:.1f}%" if not np.isnan(assert_soe_w) else "—"

                real_m += real_w
                sop_m  += sop_w
                soe_m  += soe_w
                real_buf.append(real_w)
                sop_buf.append(sop_w)
                soe_buf.append(soe_w)

        # Coluna Σ
        sk = (ml, "Σ")
        r_s = pd.Series(real_buf)
        assert_sop_m = _assertividade(r_s, pd.Series(sop_buf), base_calc) if (tem_sop and real_buf) else float("nan")
        assert_soe_m = _assertividade(r_s, pd.Series(soe_buf), base_calc) if (tem_soe and real_buf) else float("nan")

        data_cells["Real (t)"][sk] = f"{int(round(real_m)):,}" if real_m else "—"
        if tem_sop:
            data_cells["S&OP (t)"][sk]    = f"{int(round(sop_m)):,}" if sop_m else "—"
            data_cells["GAP S&OP"][sk]    = f"{int(round(real_m - sop_m)):+,}" if (real_m or sop_m) else "—"
            data_cells["Assert% S&OP"][sk] = f"{assert_sop_m:.1f}%" if not np.isnan(assert_sop_m) else "—"
        if tem_soe:
            data_cells["S&OE (t)"][sk]    = f"{int(round(soe_m)):,}" if soe_m else "—"
            data_cells["GAP S&OE"][sk]    = f"{int(round(real_m - soe_m)):+,}" if (real_m or soe_m) else "—"
            data_cells["Assert% S&OE"][sk] = f"{assert_soe_m:.1f}%" if not np.isnan(assert_soe_m) else "—"

    # ── Constrói DataFrame ─────────────────────────────────────────────────────
    rows = []
    for met in metricas:
        row: dict[tuple, str] = {ct: data_cells[met].get(ct, "—") for ct in col_tuples}
        rows.append(row)

    df_tbl = pd.DataFrame(rows, index=metricas, columns=mi_cols)
    df_tbl.index.name = "Métrica"

    # ── Styling ────────────────────────────────────────────────────────────────
    future_cts = {ct for ct in col_tuples if ct[1].endswith("*")}
    sigma_cts  = {ct for ct in col_tuples if ct[1] == "Σ"}
    _BASE = (
        "font-variant-numeric: tabular-nums; "
        "text-align: right; "
        "font-family: 'Courier New', monospace; "
        "font-size: 12px; "
    )

    def _style_matrix(df_s: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame("", index=df_s.index, columns=df_s.columns)
        for ct in df_s.columns:
            is_fut   = ct in future_cts
            is_sigma = ct in sigma_cts
            for met in df_s.index:
                val = df_s.loc[met, ct]
                css = _BASE
                if val == "—":
                    out.loc[met, ct] = css + "color:#CBD5E1;"
                    continue
                if is_fut:
                    css += "background-color:#F8FAFC;color:#94A3B8;font-style:italic;"
                if is_sigma:
                    css += "font-weight:700;background-color:#F1F5F9;"
                if "GAP" in met:
                    v2 = str(val).replace(",", "").replace("~", "").replace("+", "")
                    try:
                        num = float(v2)
                        c = COR_VERDE if num >= 0 else COR_VERMELHO
                        css += f"color:{c};font-weight:600;"
                    except ValueError:
                        pass
                elif "Assert%" in met:
                    try:
                        num = float(str(val).replace("%", ""))
                        css += f"color:{_ca(num)};font-weight:600;"
                    except ValueError:
                        pass
                out.loc[met, ct] = css
        return out

    styled = df_tbl.style.apply(_style_matrix, axis=None)

    st.dataframe(
        styled,
        use_container_width=True,
        height=56 + len(metricas) * 38,
    )

    st.markdown(
        '<div style="font-size:10px;color:#9AA5B4;margin-top:4px;">'
        '<b>*</b> semana futura &nbsp;·&nbsp; '
        '<b>Σ</b> = acumulado mensal &nbsp;·&nbsp; '
        f'<b>~</b> GAP projetado = média das últimas {N_CALIB} semanas com realizado'
        '</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TABELA DE DETALHE POR LINHA (expansível)
# ═══════════════════════════════════════════════════════════════════════════════

_METRICAS_DETALHE = ["Real (t)", "Plano (t)", "GAP (t)", "Assert%"]


def _render_detalhe_linha(
    df: pd.DataFrame,
    semanas: list[dict],
    col_plano: str,
    gap_proj: float,
    base_calc: str = "real",
    key_suffix: str = "",
) -> None:
    """Tabela MultiIndex (Linha × Métrica) × (Mês → Semana + Σ)."""
    linhas = sorted(df["linha"].unique().tolist())

    meses_ordem: list[tuple[int, int]] = []
    meses_semanas: dict[tuple[int, int], list[dict]] = {}
    for w in semanas:
        k = (int(w["ano"]), int(w["mes"]))
        if k not in meses_semanas:
            meses_ordem.append(k)
            meses_semanas[k] = []
        meses_semanas[k].append(w)

    col_tuples: list[tuple[str, str]] = []
    mes_lbl_map: dict[tuple[int, int], str] = {}
    for (a, m) in meses_ordem:
        ws = meses_semanas[(a, m)]
        lbl = f"{_MESES_ABR[m]}/{str(a)[-2:]}{'  →' if any(w['is_future'] for w in ws) else ''}"
        mes_lbl_map[(a, m)] = lbl
        for w in ws:
            col_tuples.append((lbl, f"S{w['semana_mes']}" + ("*" if w["is_future"] else "")))
        col_tuples.append((lbl, "Σ"))

    mi_cols = pd.MultiIndex.from_tuples(col_tuples, names=["Mês", "Sem"])
    row_tuples = [(lin, met) for lin in linhas for met in _METRICAS_DETALHE]
    mi_rows    = pd.MultiIndex.from_tuples(row_tuples, names=["Linha", "Métrica"])

    cells: dict[tuple, dict[tuple, str]] = {rt: {} for rt in row_tuples}

    for lin in linhas:
        df_lin = df[df["linha"] == lin]
        for (a, m) in meses_ordem:
            ws  = meses_semanas[(a, m)]
            ml  = mes_lbl_map[(a, m)]
            real_m, plano_m = 0.0, 0.0
            r_buf: list[float] = []
            p_buf: list[float] = []

            for w in ws:
                sl = f"S{w['semana_mes']}" + ("*" if w["is_future"] else "")
                ck = (ml, sl)
                sub = df_lin[
                    (df_lin["ano"] == w["ano"]) &
                    (df_lin["mes"] == w["mes"]) &
                    (df_lin["semana_mes"] == w["semana_mes"])
                ]
                if w["is_future"]:
                    plan = float(sub[col_plano].sum()) if (not sub.empty and col_plano in sub.columns) else 0.0
                    cells[(lin, "Real (t)")][ck]  = "—"
                    cells[(lin, "Plano (t)")][ck] = f"{int(round(plan)):,}" if plan else "—"
                    cells[(lin, "GAP (t)")][ck]   = f"~{int(round(gap_proj)):+,}" if plan else "—"
                    cells[(lin, "Assert%")][ck]   = "—"
                    plano_m += plan
                    p_buf.append(plan)
                else:
                    real  = float(sub["vol_ton"].sum()) if not sub.empty else 0.0
                    plan  = float(sub[col_plano].sum()) if (not sub.empty and col_plano in sub.columns) else 0.0
                    gap   = real - plan
                    assrt = _assertividade_semana(real, plan, base_calc)
                    cells[(lin, "Real (t)")][ck]  = f"{int(round(real)):,}" if real else "—"
                    cells[(lin, "Plano (t)")][ck] = f"{int(round(plan)):,}" if plan else "—"
                    cells[(lin, "GAP (t)")][ck]   = f"{int(round(gap)):+,}" if (real or plan) else "—"
                    cells[(lin, "Assert%")][ck]   = f"{assrt:.1f}%" if not np.isnan(assrt) else "—"
                    real_m  += real
                    plano_m += plan
                    r_buf.append(real)
                    p_buf.append(plan)

            sk = (ml, "Σ")
            assrt_m = _assertividade(pd.Series(r_buf), pd.Series(p_buf), base_calc) if r_buf else float("nan")
            cells[(lin, "Real (t)")][sk]  = f"{int(round(real_m)):,}" if real_m else "—"
            cells[(lin, "Plano (t)")][sk] = f"{int(round(plano_m)):,}" if plano_m else "—"
            cells[(lin, "GAP (t)")][sk]   = f"{int(round(real_m - plano_m)):+,}" if (real_m or plano_m) else "—"
            cells[(lin, "Assert%")][sk]   = f"{assrt_m:.1f}%" if not np.isnan(assrt_m) else "—"

    data = [{ct: cells.get(rt, {}).get(ct, "—") for ct in col_tuples} for rt in row_tuples]
    df_tbl = pd.DataFrame(data, index=mi_rows, columns=mi_cols)

    future_cts = {ct for ct in col_tuples if ct[1].endswith("*")}
    sigma_cts  = {ct for ct in col_tuples if ct[1] == "Σ"}
    _BASE = "font-variant-numeric:tabular-nums;text-align:right;font-family:'Courier New',monospace;font-size:12px;"

    def _style(df_s: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame("", index=df_s.index, columns=df_s.columns)
        for ct in df_s.columns:
            is_fut = ct in future_cts
            is_sig = ct in sigma_cts
            for (lin, met) in df_s.index:
                val = df_s.loc[(lin, met), ct]
                css = _BASE
                if val == "—":
                    out.loc[(lin, met), ct] = css + "color:#CBD5E1;"
                    continue
                if is_fut: css += "background-color:#F8FAFC;color:#94A3B8;font-style:italic;"
                if is_sig: css += "font-weight:700;background-color:#F1F5F9;"
                if met == "GAP (t)":
                    try:
                        num = float(str(val).replace(",", "").replace("~", "").replace("+", ""))
                        css += f"color:{COR_VERDE if num >= 0 else COR_VERMELHO};font-weight:600;"
                    except ValueError:
                        pass
                elif met == "Assert%":
                    try:
                        css += f"color:{_ca(float(str(val).replace('%','')))};font-weight:600;"
                    except ValueError:
                        pass
                out.loc[(lin, met), ct] = css
        return out

    n_rows = len(df_tbl)
    st.dataframe(
        df_tbl.style.apply(_style, axis=None),
        use_container_width=True,
        height=min(620, 56 + n_rows * 34),
        key=f"det_{key_suffix}",
    )

    buf = io.BytesIO()
    df_tbl.to_excel(buf, sheet_name=key_suffix[:30])
    buf.seek(0)
    st.download_button(
        "⬇️ Baixar Excel",
        buf,
        f"detalhe_{key_suffix}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{key_suffix}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO
# ═══════════════════════════════════════════════════════════════════════════════

def _tipo_desvio(assertividade: float, bias: float) -> list[dict]:
    """
    Diagnóstico baseado em Assertividade (1−MAPE, 0–100%) e Bias.
    Assertividade ≥ 90% = verde · ≥ 80% = atenção · < 80% = crítico.
    """
    diag: list[dict] = []
    if np.isnan(assertividade) or np.isnan(bias):
        return diag

    mape = 100 - assertividade  # converte para MAPE equivalente

    if mape > 20 and bias > 5:
        diag.append({"sev": "CRITICO",
                     "titulo": "Sobreplanejamento Sistem&#xe1;tico",
                     "descricao": (
                         f"Assertividade <b>{assertividade:.1f}%</b> com Bias <b>{bias:+.1f}%</b> "
                         "— plano acima do realizado de forma consistente."
                     ),
                     "acao": "Revisar uplift nas metas. Ver linhas com maior bias positivo no detalhe."})
    elif mape > 20 and bias < -5:
        diag.append({"sev": "CRITICO",
                     "titulo": "Subplanejamento Sistem&#xe1;tico",
                     "descricao": (
                         f"Assertividade <b>{assertividade:.1f}%</b> com Bias <b>{bias:+.1f}%</b> "
                         "— demanda não capturada no plano."
                     ),
                     "acao": "Revisar sazonalidade e tendência nas premissas do plano."})
    elif mape > 20:
        diag.append({"sev": "CRITICO",
                     "titulo": "Assertividade Cr&iacute;tica",
                     "descricao": (
                         f"Assertividade <b>{assertividade:.1f}%</b> — erro acima de 20% do volume base."
                     ),
                     "acao": "Investigar semanas com maior desvio. Ver detalhe por linha."})
    elif mape > 10:
        diag.append({"sev": "ATENCAO",
                     "titulo": "Assertividade Abaixo da Meta",
                     "descricao": (
                         f"Assertividade <b>{assertividade:.1f}%</b> — erro entre 10% e 20%."
                     ),
                     "acao": "Identificar linhas e semanas com maior desvio."})

    if not diag:
        diag.append({"sev": "OK",
                     "titulo": "Plano Saud&aacute;vel",
                     "descricao": (
                         f"Assertividade <b>{assertividade:.1f}%</b>, Bias <b>{bias:+.1f}%</b>."
                     ),
                     "acao": "Manter processo de revisão semanal."})
    return diag


def _render_recomendacoes(diagnosticos: list[dict]) -> None:
    cores = {
        "CRITICO": (COR_VERMELHO, "#FEF2F2", "#FCA5A5"),
        "ATENCAO": (COR_AMARELO,  "#FFFBEB", "#FDE68A"),
        "OK":      (COR_VERDE,    "#F0FDF4", "#A7F3D0"),
    }
    html = ""
    for item in diagnosticos[:3]:
        ct, cf, cb = cores.get(item.get("sev", "ATENCAO"), cores["ATENCAO"])
        html += (
            f'<div style="background:{cf};border:1px solid {cb};border-left:4px solid {ct};'
            f'border-radius:8px;padding:12px 16px;margin-bottom:10px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">'
            f'<span style="background:{ct};color:white;font-size:9px;font-weight:700;'
            f'padding:2px 8px;border-radius:12px;font-family:{_FONT};">{item.get("sev","")}</span>'
            f'<span style="font-weight:700;color:#111827;font-size:13px;'
            f'font-family:{_FONT};">{item["titulo"]}</span></div>'
            f'<p style="margin:0 0 6px;color:#374151;font-size:12px;line-height:1.5;'
            f'font-family:{_FONT};">{item["descricao"]}</p>'
            f'<div style="background:white;border-radius:5px;padding:7px 12px;'
            f'font-size:11px;color:{ct};font-weight:600;font-family:{_FONT};">'
            f'&#x1F4A1; {item["acao"]}</div></div>'
        )
    if html:
        st.markdown(html, unsafe_allow_html=True)


def _render_glossario() -> None:
    with st.expander("&#x1F4D6; Gloss&#xe1;rio de termos t&#xe9;cnicos", expanded=False):
        cols = st.columns(2)
        items = list(_GLOSSARIO.items())
        mid   = (len(items) + 1) // 2
        for i, (termo, defi) in enumerate(items):
            with cols[0 if i < mid else 1]:
                st.markdown(f"**{termo}**")
                st.caption(defi)


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def render(
    df_f: pd.DataFrame,
    df_v_raw: pd.DataFrame,
    filtros: dict,
    semana_atual: int,
    ano_sel: int,
    mes_sel: int,
    tw_ranges: list | None = None,
) -> None:
    mes_nome = _MESES_FULL.get(mes_sel, str(mes_sel))
    n_sem    = len(tw_ranges) if tw_ranges else 4

    if "gerencia" not in df_f.columns:
        df_f = _add_gerencia(df_f)

    # ── CSS filtros compactos ─────────────────────────────────────────────────
    st.markdown("""
    <style>
    div[data-testid="stMultiSelect"] > div {
        max-height: 38px !important; overflow-y: auto !important;
        overflow-x: hidden !important; scrollbar-width: thin !important;
        scrollbar-color: #CBD5E1 transparent !important;
    }
    div[data-testid="stMultiSelect"] > div::-webkit-scrollbar { width: 4px; }
    div[data-testid="stMultiSelect"] > div::-webkit-scrollbar-thumb {
        background: #CBD5E1; border-radius: 4px;
    }
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        max-width: 140px !important; overflow: hidden !important;
        text-overflow: ellipsis !important; white-space: nowrap !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E3A5F 0%,#0F2440 100%);
                color:white;padding:22px 28px;border-radius:14px;margin-bottom:20px;
                box-shadow:0 4px 20px rgba(30,58,95,0.20);">
      <div style="display:flex;align-items:center;justify-content:space-between;
                  flex-wrap:wrap;gap:8px;">
        <div>
          <h2 style="color:#F1F5F9;margin:0 0 5px 0;font-size:20px;font-weight:800;
                     letter-spacing:-0.3px;font-family:{_FONT};">
            &#x1F4D0; Assertividade do Plano
            <span style="display:inline-block;background:#D97706;color:white;
                         padding:3px 12px;border-radius:20px;font-size:11px;
                         font-weight:700;margin-left:10px;vertical-align:middle;">
              Sem. {semana_atual}/{n_sem}
            </span>
          </h2>
          <p style="color:rgba(255,255,255,0.70);margin:0;font-size:12px;font-family:{_FONT};">
            {mes_nome}/{ano_sel} &nbsp;&middot;&nbsp;
            {N_HIST} semanas hist&oacute;ricas + {N_FUTURO} futuras
            &nbsp;&middot;&nbsp; Real vs S&amp;OP vs S&amp;OE
          </p>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.50);
                    font-family:{_FONT};text-align:right;line-height:1.6;">
          Verde = real &ge; plano<br>Vermelho = real &lt; plano
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Filtros ───────────────────────────────────────────────────────────────
    fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
    ger_disp = sorted(df_f["gerencia"].unique().tolist())
    ger_sel  = fcol1.multiselect(
        f"Gerência ({len(ger_disp)} disponíveis)", ger_disp,
        default=ger_disp, key="assert_ger", placeholder="Todas as gerências",
    )
    lin_disp = sorted(df_f["linha"].unique().tolist())
    lin_sel  = fcol2.multiselect(
        f"Linha ({len(lin_disp)} disponíveis)", lin_disp,
        default=lin_disp, key="assert_lin", placeholder="Todas as linhas",
    )
    base_opcao = fcol3.selectbox(
        "Base do cálculo de Assertividade",
        options=["Base no Real  (1 − |R−P|/R)", "Base no Plano  (1 − |R−P|/P)"],
        index=0,
        key="assert_base",
        help=(
            "Base no Real: mede quanto da demanda real foi capturada.\n"
            "Base no Plano: mede quanto o plano errou em relação à meta definida."
        ),
    )
    base_calc: str = "real" if "Real" in base_opcao else "plano"

    filtro_info = []
    if ger_sel and len(ger_sel) < len(ger_disp):
        filtro_info.append(f"{len(ger_sel)} gerência(s)")
    if lin_sel and len(lin_sel) < len(lin_disp):
        filtro_info.append(f"{len(lin_sel)} linha(s)")
    if filtro_info:
        fcol1.caption(f"Filtros ativos: {' · '.join(filtro_info)}")

    tem_sop = "meta_sop" in df_f.columns and df_f["meta_sop"].sum() > 0
    tem_soe = "meta_soe" in df_f.columns and df_f["meta_soe"].sum() > 0
    if not tem_sop and not tem_soe:
        st.warning("Nenhum plano disponível nos dados.")
        return

    df_fil = df_f.copy()
    if ger_sel: df_fil = df_fil[df_fil["gerencia"].isin(ger_sel)]
    if lin_sel: df_fil = df_fil[df_fil["linha"].isin(lin_sel)]
    if df_fil.empty:
        st.warning("Nenhum dado com os filtros selecionados.")
        return

    # ── Horizonte ─────────────────────────────────────────────────────────────
    semanas      = _build_week_sequence(df_f, ano_sel, mes_sel, semana_atual)
    semanas_hist = [w for w in semanas if not w["is_future"]]

    # Dados históricos para KPIs
    hist_keys = pd.DataFrame([
        {"ano": w["ano"], "mes": w["mes"], "semana_mes": w["semana_mes"]}
        for w in semanas_hist
    ])
    df_hist = df_fil.merge(hist_keys, on=["ano", "mes", "semana_mes"], how="inner")
    if df_hist.empty:
        st.info(f"Sem dados históricos disponíveis para {mes_nome}/{ano_sel}.")
        return

    def _m(col: str) -> dict | None:
        if col not in df_hist.columns or df_hist[col].sum() == 0:
            return None
        return _calc(df_hist, col, base_calc)

    m_sop = _m("meta_sop") if tem_sop else None
    m_soe = _m("meta_soe") if tem_soe else None

    # Gap projetado
    gap_proj_sop = _gap_projetado(df_fil, "meta_sop", semanas) if tem_sop else 0.0
    gap_proj_soe = _gap_projetado(df_fil, "meta_soe", semanas) if tem_soe else 0.0

    # Banner (baseado no plano com mais dados)
    m_ref = m_soe or m_sop
    if m_ref:
        banner = _banner_status(m_ref["assertividade"], m_ref["bias"])
        if banner:
            st.markdown(banner, unsafe_allow_html=True)

    # Sparklines: WMAPE histórico últimos 6 meses
    def _hist_assertividade(col: str) -> list[float | None]:
        """Assertividade acumulada dos últimos 6 meses para sparkline."""
        vals: list[float | None] = []
        a_h, m_h = ano_sel, mes_sel
        for _ in range(6):
            m_h -= 1
            if m_h == 0: m_h, a_h = 12, a_h - 1
            sub = df_f[(df_f["ano"] == a_h) & (df_f["mes"] == m_h)]
            if sub.empty or col not in sub.columns or sub["vol_ton"].sum() == 0:
                vals.append(None); continue
            sems = set(sub.groupby("semana_mes")["vol_ton"].sum().pipe(lambda s: s[s > 0].index))
            s2 = sub[sub["semana_mes"].isin(sems)]
            vals.append(_assertividade(s2["vol_ton"], s2[col], base_calc))
        vals.reverse()
        return vals

    hw_sop = _hist_assertividade("meta_sop") if tem_sop else []
    hw_soe = _hist_assertividade("meta_soe") if tem_soe else []

    # ── [1] KPI Cards ─────────────────────────────────────────────────────────
    _secao(
        f"CALIBRAÇÃO — {N_HIST} SEMANAS HISTÓRICAS ACUMULADAS",
        f"Período: últimas {N_HIST} semanas até {mes_nome}/{ano_sel}",
    )
    kc = st.columns(4, gap="small")

    base_lbl = "base Real" if base_calc == "real" else "base Plano"

    if m_sop and not np.isnan(m_sop["assertividade"]):
        kc[0].markdown(_kpi_card(
            "ASSERTIVIDADE S&OP",
            f"{m_sop['assertividade']:.1f}%",
            _ca(m_sop["assertividade"]),
            f"1 − MAPE · {base_lbl} · GAP {int(round(m_sop['gap'])):+,} t",
            [w for w in hw_sop if w is not None],
            _GLOSSARIO["Aderência"],
        ), unsafe_allow_html=True)
    else:
        kc[0].markdown(_kpi_card("ASSERTIVIDADE S&OP", "—", "#94A3B8", "sem dados S&OP", []), unsafe_allow_html=True)

    if m_soe and not np.isnan(m_soe["assertividade"]):
        kc[1].markdown(_kpi_card(
            "ASSERTIVIDADE S&OE",
            f"{m_soe['assertividade']:.1f}%",
            _ca(m_soe["assertividade"]),
            f"1 − MAPE · {base_lbl} · GAP {int(round(m_soe['gap'])):+,} t",
            [w for w in hw_soe if w is not None],
            _GLOSSARIO["Aderência"],
        ), unsafe_allow_html=True)
    else:
        kc[1].markdown(_kpi_card("ASSERTIVIDADE S&OE", "—", "#94A3B8", "sem dados S&OE", []), unsafe_allow_html=True)

    if m_sop and not np.isnan(m_sop["gap"]):
        kc[2].markdown(_kpi_card(
            "GAP S&OP (t)",
            f"{int(round(m_sop['gap'])):+,} t",
            _cg(m_sop["gap"]),
            "ton a adicionar/subtrair no plano",
            [v for v in hw_sop if v is not None],
            _GLOSSARIO["GAP"],
        ), unsafe_allow_html=True)
    else:
        kc[2].markdown(_kpi_card("GAP S&OP (t)", "—", "#94A3B8", "sem dados S&OP", []), unsafe_allow_html=True)

    if m_soe and not np.isnan(m_soe["gap"]):
        kc[3].markdown(_kpi_card(
            "GAP S&OE (t)",
            f"{int(round(m_soe['gap'])):+,} t",
            _cg(m_soe["gap"]),
            "ton a adicionar/subtrair no programa",
            [v for v in hw_soe if v is not None],
            _GLOSSARIO["GAP"],
        ), unsafe_allow_html=True)
    else:
        kc[3].markdown(_kpi_card("GAP S&OE (t)", "—", "#94A3B8", "sem dados S&OE", []), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    # Diagnóstico abaixo dos cards
    if m_ref:
        diag = _tipo_desvio(m_ref["assertividade"], m_ref["bias"])
        _render_recomendacoes(diag)

    # ── [2] Gráfico principal ─────────────────────────────────────────────────
    _secao(
        "VOLUME SEMANAL — REAL VS PLANOS",
        f"{N_HIST} semanas históricas (linha sólida) + {N_FUTURO} futuras projetadas (tracejado)",
    )
    fig_hz = _fig_horizonte(df_fil, semanas, tem_sop, tem_soe, gap_proj_sop, gap_proj_soe)
    st.plotly_chart(
        fig_hz, use_container_width=True,
        config={"displayModeBar": False},
        key=f"hz_{ano_sel}_{mes_sel}",
    )

    # ── [3] Tabela agregada compacta ──────────────────────────────────────────
    _secao(
        "MÉTRICAS POR SEMANA — VISÃO AGREGADA",
        f"Real, Plano, GAP e Assertividade (1−MAPE, {base_lbl}) · sem quebra por linha",
    )
    _render_tabela_agregada(
        df_fil, semanas, tem_sop, tem_soe, gap_proj_sop, gap_proj_soe, base_calc,
    )

    # ── [4] Detalhe por linha — S&OP ─────────────────────────────────────────
    if tem_sop:
        with st.expander(
            f"&#x1F4CB; Detalhe por linha de produto — S&amp;OP",
            expanded=False,
        ):
            st.caption(
                f"Assertividade = 1−MAPE ({base_lbl}) por semana · "
                f"semanas futuras com GAP projetado (~{int(round(gap_proj_sop)):+,} t/sem)"
            )
            _render_detalhe_linha(
                df_fil, semanas, "meta_sop", gap_proj_sop, base_calc,
                key_suffix=f"sop_{ano_sel}_{mes_sel}",
            )

    # ── [5] Detalhe por linha — S&OE ─────────────────────────────────────────
    if tem_soe:
        with st.expander(
            f"&#x1F4CB; Detalhe por linha de produto — S&amp;OE",
            expanded=False,
        ):
            st.caption(
                f"Assertividade = 1−MAPE ({base_lbl}) por semana · "
                f"semanas futuras com GAP projetado (~{int(round(gap_proj_soe)):+,} t/sem)"
            )
            _render_detalhe_linha(
                df_fil, semanas, "meta_soe", gap_proj_soe, base_calc,
                key_suffix=f"soe_{ano_sel}_{mes_sel}",
            )

    # ── [6] Glossário ─────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    _render_glossario()
