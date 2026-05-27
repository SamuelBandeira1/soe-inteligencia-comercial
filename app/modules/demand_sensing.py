"""
Módulo Demand Sensing — diagnóstico de viés e projeção probabilística de demanda.

Responde:
  1. Estamos subestimando ou superestimando o plano semanal?
     → MAPE, Bias, Hit Rate, CV calculados sobre semanas COMPLETAS (vol > 0)

  2. Quanto vamos vender nas próximas semanas?
     → Forecast via pace recente + sazonalidade
     → Monte Carlo (1 000 simulações) mostrando P10/P25/P50/P75/P90
     → Plano S&OP e Programa S&OE sobrepostos para comparação

Filtro de semanas válidas: apenas semanas com vol_ton > 0 AND meta > 0
(exclui semanas futuras que têm meta mas ainda não têm realizado)
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.calendar_tw import get_month_tw_ranges, tw_label as _tw_label
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_TEXTO, COR_GRID, fmt_ton as _fmt_ton,
)

MESES = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',
         7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}
MESES_FULL = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
              7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'}

N_HIST       = 16    # semanas históricas para métricas
N_PACE       = 8     # semanas para cálculo de pace
N_FUTURO     = 8     # semanas à frente
N_SIM        = 1000  # simulações Monte Carlo
SEED         = 42    # reprodutibilidade
HIT_THRESH   = 0.10  # ±10% = "acertou"


# _tw_label importado de utils.calendar_tw (tw_label) — sem duplicação

# ══════════════════════════════════════════════════════════════════════
# 1. CÁLCULOS
# ══════════════════════════════════════════════════════════════════════

def _semana_key(ano: int, mes: int, sem: int) -> int:
    return ano * 10000 + mes * 100 + sem


def _historico_completo(df_f: pd.DataFrame, col_meta: str, n: int = N_HIST) -> pd.DataFrame:
    """
    Agrega semanas e filtra apenas as COMPLETAS (vol > 0 e meta > 0).
    Isso exclui semanas futuras que têm meta mas ainda não têm realizado.
    """
    agg = (
        df_f.groupby(['ano', 'mes', 'semana_mes'])[['vol_ton', col_meta]]
        .sum()
        .reset_index()
        .rename(columns={col_meta: 'meta'})
    )

    # Só semanas com realizado E com plano
    agg = agg[(agg['vol_ton'] > 0) & (agg['meta'] > 0)].copy()
    agg['semana_key'] = agg.apply(
        lambda r: _semana_key(int(r['ano']), int(r['mes']), int(r['semana_mes'])), axis=1
    )
    agg = agg.sort_values('semana_key').tail(n).reset_index(drop=True)
    agg['erro']  = (agg['vol_ton'] - agg['meta']) / agg['meta']
    agg['label'] = agg.apply(
        lambda r: _tw_label(int(r['ano']), int(r['mes']), int(r['semana_mes'])),
        axis=1,
    )
    return agg


def _calcular_metricas(df_hist: pd.DataFrame) -> dict:
    if df_hist.empty:
        return {}
    erros = df_hist['erro']
    mape      = float((erros.abs()).mean() * 100)
    bias      = float(erros.mean() * 100)
    hit_rate  = float((erros.abs() <= HIT_THRESH).mean() * 100)
    cv        = float(erros.std(ddof=1) * 100) if len(erros) > 1 else 0.0
    mae       = float((df_hist['vol_ton'] - df_hist['meta']).abs().mean())
    return dict(mape=mape, bias=bias, hit_rate=hit_rate, cv=cv, mae=mae, n=len(df_hist))


def _pace_e_std(df_f: pd.DataFrame, semana_excl: tuple | None, n: int = N_PACE) -> tuple[float, float]:
    agg = df_f.groupby(['ano', 'mes', 'semana_mes'])['vol_ton'].sum().reset_index()
    agg = agg[agg['vol_ton'] > 0]
    if semana_excl:
        a, m, s = semana_excl
        agg = agg[~((agg['ano']==a)&(agg['mes']==m)&(agg['semana_mes']==s))]
    agg['semana_key'] = agg.apply(
        lambda r: _semana_key(int(r['ano']), int(r['mes']), int(r['semana_mes'])), axis=1
    )
    vals = agg.sort_values('semana_key').tail(n)['vol_ton']
    if vals.empty:
        return 0.0, 0.0
    return float(vals.mean()), float(vals.std(ddof=1) if len(vals) > 1 else 0.0)


def _peso_global(pesos: dict, semana: int, n_semanas: int) -> float:
    vals = [pesos[l].get(semana, 1/n_semanas) for l in pesos if semana in pesos.get(l,{})]
    return float(np.mean(vals)) if vals else 1/n_semanas


def _semanas_futuras(ano: int, mes: int, sem_atual: int, n_sem_mes: int, n: int = N_FUTURO):
    result = []
    for s in range(sem_atual + 1, n_sem_mes + 1):
        tw = get_month_tw_ranges(ano, mes)
        if s <= len(tw):
            _, di, df_ = tw[s-1]
            result.append((ano, mes, s, di, df_))
    prox_mes = mes + 1 if mes < 12 else 1
    prox_ano = ano if mes < 12 else ano + 1
    for sem_m, di, df_ in get_month_tw_ranges(prox_ano, prox_mes):
        result.append((prox_ano, prox_mes, sem_m, di, df_))
        if len(result) >= n:
            break
    return result[:n]


def _monte_carlo(
    pace: float,
    std: float,
    bias_frac: float,
    pesos: dict,
    semanas: list,
    n_sim: int = N_SIM,
) -> dict:
    rng = np.random.default_rng(SEED)
    n_weeks = len(semanas)
    sims = np.zeros((n_sim, n_weeks))
    for i, (ano, mes, sem, _, _) in enumerate(semanas):
        tw = get_month_tw_ranges(ano, mes)
        n_sem = len(tw)
        peso_rel = _peso_global(pesos, sem, n_sem) / (1/n_sem)
        base = pace * peso_rel
        # Cada simulação: ruído multiplicativo centrado no bias histórico
        noise = rng.normal(loc=bias_frac, scale=std/pace if pace > 0 else 0.10, size=n_sim)
        sims[:, i] = np.maximum(0, base * (1 + noise))
    return {
        'p10': np.percentile(sims, 10, axis=0),
        'p25': np.percentile(sims, 25, axis=0),
        'p50': np.percentile(sims, 50, axis=0),
        'p75': np.percentile(sims, 75, axis=0),
        'p90': np.percentile(sims, 90, axis=0),
    }


def _meta_semana(df_f: pd.DataFrame, col: str, ano: int, mes: int, sem: int) -> float:
    v = df_f[(df_f['ano']==ano)&(df_f['mes']==mes)&(df_f['semana_mes']==sem)][col].sum()
    return float(v)


# ══════════════════════════════════════════════════════════════════════
# 2. VISUAIS
# ══════════════════════════════════════════════════════════════════════

def _render_hero(m: dict, col_meta: str) -> None:
    bias = m.get('bias', 0)
    mape = m.get('mape', 0)
    n    = m.get('n', 0)
    if n == 0:
        return

    cv = m.get('cv', 0)

    if abs(bias) < 5:
        cor, emoji, titulo = COR_VERDE, "✅", "PLANO CALIBRADO"
        desc = (f"Nas últimas {n} semanas completas, o realizado ficou em média "
                f"<b>{bias:+.1f}%</b> do plano — dentro da margem de tolerância de ±5%.")
        acao = "Nenhum ajuste estrutural necessário. Continue monitorando o padrão."

    elif bias > 0:
        intensidade = "🚨" if bias > 15 else "⚠️"
        cor = COR_VERMELHO if bias > 15 else COR_AMARELO
        emoji, titulo = intensidade, f"UNDERFORECASTING — Demanda sistematicamente acima do plano em {bias:.1f}%"
        desc = (f"Nas últimas {n} semanas, as vendas foram em média <b>+{bias:.1f}%</b> "
                f"acima do plano. A capacidade de entrega pode estar sendo subestimada.")
        limite_inf = bias - cv * 0.5
        limite_sup = bias + cv * 0.5
        acao = (f"<b>Alerta de Underforecasting:</b> O plano está sistematicamente abaixo "
                f"da demanda real. Com base no bias observado ({bias:+.1f}%) e na volatilidade "
                f"histórica (σ={cv:.1f}%), a <b>faixa de revisão sugerida</b> para o próximo "
                f"ciclo S&OE é de <b>[+{limite_inf:.0f}%, +{limite_sup:.0f}%]</b>. "
                f"Avalie com o time comercial antes de ajustar o plano.")

    else:
        intensidade = "🚨" if abs(bias) > 15 else "⚠️"
        cor = COR_VERMELHO if abs(bias) > 15 else COR_AMARELO
        emoji, titulo = intensidade, f"OVERFORECASTING — Plano sistematicamente acima da demanda em {abs(bias):.1f}%"
        desc = (f"Nas últimas {n} semanas, as vendas ficaram em média <b>{bias:.1f}%</b> "
                f"abaixo do plano. O plano está criando expectativas acima da demanda real "
                f"observada — risco de frustração de metas.")
        # Faixa de revisão: bias ± 0,5σ, limitada a não ultrapassar -3%
        limite_inf = min(bias - cv * 0.5, -3)
        limite_sup = min(bias + cv * 0.5, -1)
        acao = (f"<b>Alerta de Overforecasting:</b> O plano está sistematicamente acima "
                f"da capacidade de realização. Com base no bias observado ({bias:+.1f}%) e na "
                f"volatilidade histórica (σ={cv:.1f}%), a <b>faixa de revisão sugerida</b> para "
                f"o próximo ciclo S&OE é de <b>[{limite_inf:.0f}%, {limite_sup:.0f}%]</b>. "
                f"Esta é uma faixa de tolerância estatística — não um número fixo. "
                f"Avalie com o time de planejamento antes de ajustar.")

    plano_label = "S&OP" if col_meta == "meta_sop" else "S&OE"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{COR_PRIMARIA} 0%,#1a3a6b 100%);
                color:white;border-radius:12px;padding:24px 32px;margin-bottom:16px;
                border-left:8px solid {cor};">
      <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;">
        <div style="font-size:48px;line-height:1">{emoji}</div>
        <div style="flex:1;min-width:300px">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                      letter-spacing:1.2px;color:rgba(255,255,255,0.65);margin-bottom:6px">
            Diagnóstico Plano {plano_label} — {n} semanas completas analisadas
          </div>
          <div style="font-size:26px;font-weight:900;color:{cor};margin-bottom:10px;
                      letter-spacing:.3px;line-height:1.2">{titulo}</div>
          <div style="font-size:13px;color:rgba(255,255,255,0.90);margin-bottom:10px;
                      line-height:1.6">{desc}</div>
          <div style="font-size:12px;background:rgba(255,255,255,0.10);border-radius:8px;
                      padding:10px 14px;color:white;border-left:3px solid {cor};">
            💡 <b>Ação sugerida:</b> {acao}
          </div>
        </div>
        <div style="text-align:right;min-width:140px">
          <div style="font-size:52px;font-weight:900;color:{cor};line-height:1">{bias:+.1f}%</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.6)">bias médio</div>
          <div style="font-size:18px;font-weight:700;color:rgba(255,255,255,0.85);margin-top:8px">
            MAPE {mape:.1f}%
          </div>
          <div style="font-size:11px;color:rgba(255,255,255,0.5)">erro médio absoluto</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


def _render_kpis(m: dict) -> None:
    mape     = m.get('mape', 0)
    bias     = m.get('bias', 0)
    hit_rate = m.get('hit_rate', 0)
    cv       = m.get('cv', 0)
    mae      = m.get('mae', 0)

    cor_mape = COR_VERDE if mape < 10 else COR_AMARELO if mape < 20 else COR_VERMELHO
    cor_bias = COR_VERDE if abs(bias) < 5 else COR_AMARELO if abs(bias) < 15 else COR_VERMELHO
    cor_hit  = COR_VERDE if hit_rate >= 60 else COR_AMARELO if hit_rate >= 40 else COR_VERMELHO
    cor_cv   = COR_VERDE if cv < 15 else COR_AMARELO if cv < 30 else COR_VERMELHO

    def _kpi(col, label, valor, sub, cor, tooltip=""):
        col.markdown(f"""
        <div style="background:#fff;border-radius:10px;padding:16px 18px;
                    border-top:4px solid {cor};box-shadow:0 2px 8px rgba(0,0,0,.08);">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#6C757D;margin-bottom:4px">{label}</div>
          <div style="font-size:32px;font-weight:900;color:{COR_PRIMARIA};line-height:1">{valor}</div>
          <div style="font-size:11px;color:#6C757D;margin-top:4px">{sub}</div>
        </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, "📊 MAPE",        f"{mape:.1f}%",    "erro médio absoluto %",              cor_mape)
    _kpi(c2, "📐 Bias",        f"{bias:+.1f}%",   "+ supra · − infra plano",            cor_bias)
    _kpi(c3, "🎯 Assertividade", f"{hit_rate:.0f}%", f"semanas dentro de ±{HIT_THRESH:.0%}", cor_hit)
    _kpi(c4, "〰️ Volatilidade", f"{cv:.1f}%",     "desvio padrão dos erros",            cor_cv)
    _kpi(c5, "📦 MAE",         f"{_fmt_ton(mae)} ton", "erro médio absoluto em volume",  COR_ACENTO)
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


def _render_erro_historico(df_hist: pd.DataFrame, kp: str) -> None:
    if df_hist.empty:
        return

    erros  = df_hist['erro'].values * 100
    labels = df_hist['label'].values
    vols   = df_hist['vol_ton'].values
    metas  = df_hist['meta'].values
    mape   = float(np.abs(erros).mean())
    bias   = float(erros.mean())

    cores = [COR_VERDE if e >= 0 else COR_VERMELHO for e in erros]

    fig = go.Figure()

    # Barras de erro
    fig.add_trace(go.Bar(
        x=labels, y=erros,
        marker_color=cores,
        marker_line=dict(color="rgba(0,0,0,0.08)", width=1),
        text=[f"{e:+.1f}%" for e in erros],
        textposition="outside",
        textfont=dict(size=10, color=COR_TEXTO, family="Arial"),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Erro: <b>%{y:+.1f}%</b><br>"
            "Realizado: %{customdata[0]} ton<br>"
            "Plano: %{customdata[1]} ton"
            "<extra></extra>"
        ),
        customdata=list(zip(
            [f"{v:,.0f}".replace(",",".") for v in vols],
            [f"{v:,.0f}".replace(",",".") for v in metas],
        )),
        name="Erro semanal",
        cliponaxis=False,
    ))

    # Linha de MAPE (envelope)
    fig.add_trace(go.Scatter(
        x=labels, y=[mape]*len(labels),
        mode="lines", line=dict(color=COR_VERDE, dash="dot", width=1.5),
        name=f"MAPE +{mape:.1f}%", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=[-mape]*len(labels),
        mode="lines", line=dict(color=COR_VERDE, dash="dot", width=1.5),
        name=f"MAPE −{mape:.1f}%", hoverinfo="skip",
    ))

    # Linha de bias
    fig.add_hline(y=bias, line_dash="dash", line_color=COR_ACENTO, line_width=2.5,
                  annotation_text=f"Bias {bias:+.1f}%", annotation_position="bottom right",
                  annotation_font=dict(size=11, color=COR_ACENTO, family="Arial"))
    fig.add_hline(y=0, line_color="#B0BEC5", line_width=1)

    fig.update_layout(
        height=340,
        title=dict(
            text="<b>Erro Histórico Semanal — Realizado vs Plano</b>  "
                 "<span style='font-size:12px;font-weight:normal;color:#666'>"
                 "(verde = acima do plano · vermelho = abaixo)</span>",
            font=dict(size=14, color=COR_PRIMARIA, family="Arial"), x=0,
        ),
        margin=dict(t=48, b=64, l=65, r=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10), gridcolor=COR_GRID, tickangle=-35),
        yaxis=dict(title="Erro (%)", ticksuffix="%", gridcolor=COR_GRID,
                   zeroline=False, tickfont=dict(size=11)),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right",
                    font=dict(size=10)),
        font=dict(family="Arial", size=11, color=COR_TEXTO),
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False}, key=f"{kp}_hist_chart")


def _render_volume_historico(df_hist: pd.DataFrame, kp: str) -> None:
    """
    Gráfico de volume realizado vs plano com barras de erro em toneladas.
    Complementa o gráfico de erro percentual mostrando a magnitude absoluta.
    """
    if df_hist.empty:
        return

    labels = df_hist['label'].values
    vols   = df_hist['vol_ton'].values
    metas  = df_hist['meta'].values
    erros  = vols - metas          # erro em ton (positivo = acima do plano)
    mae    = float(np.abs(erros).mean())

    fig = go.Figure()

    # ── Barras de meta (fundo, mais clara) ───────────────────────
    fig.add_trace(go.Bar(
        x=labels, y=metas,
        name="Plano",
        marker_color=COR_PRIMARIA,
        opacity=0.35,
        marker_line=dict(color=COR_PRIMARIA, width=1),
        hovertemplate="<b>%{x}</b><br>Plano: <b>%{y:,.0f} ton</b><extra></extra>",
    ))

    # ── Barras de realizado ───────────────────────────────────────
    cores_vol = [COR_VERDE if v >= m else COR_VERMELHO
                 for v, m in zip(vols, metas)]
    fig.add_trace(go.Bar(
        x=labels, y=vols,
        name="Realizado",
        marker_color=cores_vol,
        marker_line=dict(color="rgba(0,0,0,0.10)", width=1),
        opacity=0.85,
        text=[_fmt_ton(v) for v in vols],
        textposition="outside",
        textfont=dict(size=9, color=COR_TEXTO, family="Arial"),
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Realizado: <b>%{y:,.0f} ton</b><extra></extra>",
    ))

    # ── Linha de erro em volume (eixo secundário) ─────────────────
    fig.add_trace(go.Scatter(
        x=labels, y=erros,
        name="Erro (ton)",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color=COR_ACENTO, width=2, dash="dot"),
        marker=dict(size=7, color=COR_ACENTO, symbol="circle",
                    line=dict(color="white", width=1.5)),
        hovertemplate="<b>%{x}</b><br>Erro: <b>%{y:+,.0f} ton</b><extra></extra>",
    ))

    # ── MAE como banda de referência no eixo secundário ──────────
    fig.add_trace(go.Scatter(
        x=list(labels) + list(labels[::-1]),
        y=[mae]*len(labels) + [-mae]*len(labels),
        fill="toself",
        fillcolor="rgba(244,130,42,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        yaxis="y2",
        name=f"MAE ±{_fmt_ton(mae)} ton",
        hoverinfo="skip",
    ))

    # Linha zero no eixo secundário
    fig.add_hline(y=0, line_color="#B0BEC5", line_width=1,
                  line_dash="solid", secondary_y=False)

    y_max_vol = float(max(vols.max(), metas.max())) * 1.25 if len(vols) else 1
    y_max_err = float(np.abs(erros).max()) * 1.6 if len(erros) else 1

    fig.update_layout(
        height=320,
        title=dict(
            text="<b>Volume Realizado vs Plano</b>  "
                 "<span style='font-size:12px;font-weight:normal;color:#666'>"
                 "(barras sobrepostas · linha laranja = erro em ton · "
                 f"MAE = ±{_fmt_ton(mae)} ton)</span>",
            font=dict(size=14, color=COR_PRIMARIA, family="Arial"), x=0,
        ),
        barmode="overlay",
        margin=dict(t=48, b=64, l=70, r=70),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10), gridcolor=COR_GRID, tickangle=-35),
        yaxis=dict(
            title="Volume (ton)", gridcolor=COR_GRID,
            tickformat=",", tickfont=dict(size=11),
            range=[0, y_max_vol],
        ),
        yaxis2=dict(
            title=dict(text="Erro (ton)", font=dict(color=COR_ACENTO, family="Arial", size=11)),
            overlaying="y", side="right",
            tickformat="+,", tickfont=dict(size=10, color=COR_ACENTO),
            range=[-y_max_err, y_max_err],
            showgrid=False, zeroline=True,
            zerolinecolor="#B0BEC5", zerolinewidth=1,
        ),
        legend=dict(orientation="h", y=1.10, x=1, xanchor="right",
                    font=dict(size=10), bgcolor="rgba(255,255,255,0.85)"),
        font=dict(family="Arial", size=11, color=COR_TEXTO),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False}, key=f"{kp}_vol_chart")


def _render_exec_summary(metricas: dict, df_hist: pd.DataFrame, col_meta: str) -> None:
    """
    Bloco de texto dinâmico — executive summary para o coordenador.
    Gerado automaticamente a partir dos dados históricos reais.
    """
    mape     = metricas.get('mape', 0)
    bias     = metricas.get('bias', 0)
    hit_rate = metricas.get('hit_rate', 0)
    cv       = metricas.get('cv', 0)
    n        = metricas.get('n', 0)

    if n == 0 or df_hist.empty:
        return

    plano = "S&OP" if col_meta == "meta_sop" else "S&OE"

    # ── Interpretação automática de cada métrica ──────────────────────────────
    if mape < 10:
        mape_txt = (f"<b>MAPE de {mape:.1f}%</b> — erro médio baixo, o modelo histórico "
                    f"tem boa aderência ao comportamento real.")
    elif mape < 20:
        mape_txt = (f"<b>MAPE de {mape:.1f}%</b> — erro moderado. Há variabilidade relevante "
                    f"nas semanas, mas o padrão geral é capturável.")
    else:
        mape_txt = (f"<b>MAPE de {mape:.1f}%</b> — erro elevado. A demanda apresenta "
                    f"comportamento irregular; projeções devem ser tratadas com cautela.")

    if abs(bias) < 5:
        bias_txt = (f"O <b>Bias de {bias:+.1f}%</b> indica que o plano {plano} está "
                    f"bem calibrado — sem tendência sistemática de super ou subestimação.")
    elif bias > 0:
        bias_txt = (f"O <b>Bias positivo de +{bias:.1f}%</b> indica que a demanda real "
                    f"supera sistematicamente o plano {plano}. Há potencial de volume "
                    f"não capturado nas metas.")
    else:
        bias_txt = (f"O <b>Bias negativo de {bias:.1f}%</b> é um sinal claro de "
                    f"<b>Overforecasting</b>: o plano {plano} está sendo elaborado acima "
                    f"da capacidade real de realização nas últimas {n} semanas.")

    if hit_rate >= 60:
        hit_txt = (f"A <b>Assertividade de {hit_rate:.0f}%</b> mostra que o plano acerta "
                   f"dentro de ±10% na maioria das semanas — base confiável para decisão.")
    elif hit_rate >= 40:
        hit_txt = (f"A <b>Assertividade de {hit_rate:.0f}%</b> é moderada: o plano fica "
                   f"dentro de ±10% em menos da metade das semanas. Revisão metodológica "
                   f"pode melhorar a previsibilidade.")
    else:
        hit_txt = (f"A <b>Assertividade de {hit_rate:.0f}%</b> é baixa — o plano raramente "
                   f"fica dentro de ±10% do realizado. Há ruído estrutural significativo.")

    if cv < 15:
        vol_txt = f"Volatilidade de {cv:.1f}% — demanda estável e previsível."
    elif cv < 30:
        vol_txt = f"Volatilidade de {cv:.1f}% — variação moderada entre semanas."
    else:
        vol_txt = f"Volatilidade de {cv:.1f}% — alta variação entre semanas, sinal de sazonalidade ou eventos pontuais."

    # ── Recomendação síntese ──────────────────────────────────────────────────
    if abs(bias) < 5 and hit_rate >= 60:
        rec_cor = "#1A7A40"
        rec_bg  = "#F0FFF4"
        rec_borda = "#1A7A40"
        rec = ("✅ O processo de planejamento está funcionando bem. Mantenha o monitoramento "
               "semanal e acione revisão apenas se o bias sair da faixa ±5% por 3+ semanas consecutivas.")
    elif bias < -10 or (bias < -5 and hit_rate < 50):
        rec_cor = "#C0392B"
        rec_bg  = "#FFF5F5"
        rec_borda = "#C0392B"
        rec = (f"🚨 Revisão do plano {plano} recomendada para o próximo ciclo. "
               f"O Overforecasting sistemático de {abs(bias):.1f}% está criando expectativas "
               f"que a equipe comercial não consegue sustentar. Priorize alinhamento com o "
               f"time de planejamento antes de publicar o próximo plano.")
    elif bias > 10:
        rec_cor = "#C0392B"
        rec_bg  = "#FFF8F0"
        rec_borda = "#FFA726"
        rec = (f"⚠️ A demanda está consistentemente acima do plano. Considere revisar as "
               f"metas para cima ({bias:+.0f}% de bias) para evitar subplanejamento de "
               f"recursos e estoque.")
    else:
        rec_cor = "#C0392B"
        rec_bg  = "#FFF8F0"
        rec_borda = "#FFA726"
        rec = (f"⚠️ O plano apresenta desvios que merecem atenção no próximo ciclo de S&OE. "
               f"Monitore as próximas 2–3 semanas antes de uma revisão formal.")

    st.markdown(
        f"""<div style="background:#F8F9FA;border-radius:10px;padding:18px 22px;
                        margin:16px 0;border:1px solid #E0E6F0;
                        border-left:5px solid {COR_PRIMARIA};">
          <div style="font-size:13px;font-weight:800;color:{COR_PRIMARIA};
                      margin-bottom:12px;letter-spacing:.3px;">
            📋 Leitura do Coordenador — Síntese do Diagnóstico {plano}
          </div>
          <div style="font-size:12px;color:#444;line-height:1.9;">
            <span style="display:block;padding:3px 0">① {mape_txt}</span>
            <span style="display:block;padding:3px 0">② {bias_txt}</span>
            <span style="display:block;padding:3px 0">③ {hit_txt}</span>
            <span style="display:block;padding:3px 0">④ {vol_txt}</span>
          </div>
          <div style="margin-top:14px;background:{rec_bg};border-left:4px solid {rec_borda};
                      border-radius:0 8px 8px 0;padding:10px 14px;
                      font-size:12px;color:{rec_cor};line-height:1.7;">
            <b>Recomendação:</b> {rec}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_mc_intro(metricas: dict, pace: float, std: float, bias_frac: float) -> None:
    """
    Card didático: o que é Monte Carlo + como os cenários são calculados
    + evidência de validade com os dados históricos reais.
    Usa st.columns() para o layout de 2 colunas (evita grid CSS que Streamlit não suporta).
    """
    mape     = metricas.get('mape', 0)
    hit_rate = metricas.get('hit_rate', 0)
    n        = metricas.get('n', 0)
    bias_pct = bias_frac * 100

    cor_hit  = COR_VERDE if hit_rate >= 60 else COR_AMARELO if hit_rate >= 40 else COR_VERMELHO
    cor_mape = COR_VERDE if mape < 10 else COR_AMARELO if mape < 20 else COR_VERMELHO

    if abs(bias_pct) < 3:
        bias_txt = "O plano está bem calibrado — sem correção de tendência aplicada."
    elif bias_pct > 0:
        bias_txt = (f"O realizado ficou em média <b>+{bias_pct:.1f}%</b> acima do plano nas últimas "
                    f"{n} semanas → os cenários são <b>ajustados para cima</b> para refletir esse padrão.")
    else:
        bias_txt = (f"O realizado ficou em média <b>{bias_pct:.1f}%</b> abaixo do plano nas últimas "
                    f"{n} semanas → os cenários são <b>ajustados para baixo</b> para refletir esse padrão.")

    # ── Cabeçalho do bloco ────────────────────────────────────────
    st.markdown(
        f"""<div style="border-left:5px solid {COR_PRIMARIA};border-radius:12px;
                        background:linear-gradient(135deg,#F8F9FA 0%,#EEF2FF 100%);
                        padding:18px 22px 4px 22px;margin:12px 0 6px 0;">
              <div style="font-size:15px;font-weight:800;color:{COR_PRIMARIA};margin-bottom:14px;">
                🎲 Como funciona a Simulação Monte Carlo?
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns(2, gap="medium")

    # ── Coluna esquerda: O que é ──────────────────────────────────
    col_l.markdown(
        f"""<div style="background:white;border-radius:10px;padding:16px 18px;
                        border-top:3px solid {COR_PRIMARIA};height:100%">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.8px;color:#7B8EA6;margin-bottom:8px">O QUE É</div>
              <div style="font-size:13px;color:#444;line-height:1.8;">
                Imagine pedir para <b>1.000 consultores</b> estimarem as vendas da próxima semana.
                Cada um olharia para o histórico e chegaria a uma resposta ligeiramente diferente —
                alguns mais otimistas, outros mais conservadores.<br><br>
                O Monte Carlo faz exatamente isso: gera <b>1.000 cenários possíveis</b> e mostra
                a distribuição dos resultados, revelando o que é provável, o que é pessimista
                e o que é otimista — em vez de um único número que cria falsa certeza.
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    # ── Coluna direita: Como calculamos ──────────────────────────
    col_r.markdown(
        f"""<div style="background:white;border-radius:10px;padding:16px 18px;
                        border-top:3px solid {COR_ACENTO};height:100%">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.8px;color:#7B8EA6;margin-bottom:8px">COMO CALCULAMOS</div>
              <div style="font-size:13px;color:#444;line-height:1.8;">
                Cada simulação parte de <b>3 ingredientes</b>:<br>
                <span style="color:{COR_ACENTO};font-weight:700">① Ritmo base:</span>
                média das últimas {N_PACE} semanas <b>encerradas</b>
                → <b>{_fmt_ton(pace)} ton/semana</b><br>
                <span style="color:{COR_ACENTO};font-weight:700">② Tendência histórica:</span>
                {bias_txt}<br>
                <span style="color:{COR_ACENTO};font-weight:700">③ Variação natural:</span>
                volatilidade do histórico
                → <b>±{_fmt_ton(std)} ton</b> de desvio típico
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin:10px 0 0 0'></div>", unsafe_allow_html=True)

    # ── Faixa de validade + nota sobre semana parcial ─────────────
    st.markdown(
        f"""<div style="background:white;border-radius:10px;padding:14px 18px;
                        border:1px solid #D0DCF0;border-left:5px solid {COR_VERDE};
                        margin-bottom:18px;">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                          letter-spacing:.8px;color:#7B8EA6;margin-bottom:8px">
                ✅ EVIDÊNCIA DE VALIDADE — O MODELO FUNCIONA?
              </div>
              <div style="font-size:13px;color:#444;line-height:1.8;">
                Testamos contra as <b>{n} semanas já encerradas</b> disponíveis no histórico:<br>
                🎯 <b>Assertividade:</b>
                <span style="color:{cor_hit};font-weight:800;font-size:14px">&nbsp;{hit_rate:.0f}%</span>
                das semanas ficaram dentro de ±10% do realizado
                &nbsp;&nbsp;·&nbsp;&nbsp;
                📊 <b>MAPE médio:</b>
                <span style="color:{cor_mape};font-weight:800;font-size:14px">&nbsp;{mape:.1f}%</span>
                de erro absoluto
              </div>
              <div style="font-size:12px;color:#7B8EA6;margin-top:10px;
                          background:#F8F9FA;border-radius:6px;padding:8px 12px;">
                ⚠️ <b>Por que o cenário central pode parecer alto se o mês atual está fraco?</b>
                O ritmo base usa apenas semanas <b>já encerradas</b> — a semana atual
                em andamento <i>não entra no cálculo</i>, pois é um período parcial que distorceria
                a média. O impacto de um mês fraco é incorporado progressivamente conforme
                cada semana fecha. Se o ritmo cair de forma consistente, os próximos cálculos
                já vão refletir isso automaticamente.
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def _render_mc_scenarios(semanas: list, mc: dict, badge: str = "Consolidado") -> None:
    """
    3 cards hero com totais acumulados de P10, P50 e P90 nas próximas semanas.
    Mostra o que cada cenário significa em toneladas concretas.
    """
    if not semanas or not mc:
        return

    n = len(semanas)
    total_p10 = float(mc['p10'].sum())
    total_p50 = float(mc['p50'].sum())
    total_p90 = float(mc['p90'].sum())
    total_p25 = float(mc['p25'].sum())
    total_p75 = float(mc['p75'].sum())

    # Rótulo do período
    label_ini = _tw_label(*semanas[0][:3])
    label_fim = _tw_label(*semanas[-1][:3])
    periodo_txt = label_ini if n == 1 else f"{label_ini} → {label_fim}"

    _badge_suffix = f' · {badge}' if badge and badge != "Consolidado" else ''
    st.markdown(
        f'<div style="font-size:14px;font-weight:700;color:{COR_PRIMARIA};margin:4px 0 10px 0">'
        f'📊 Resumo dos Cenários — {n} próximas semanas ({periodo_txt}){_badge_suffix}'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    # ── Pior Cenário (P10) ────────────────────────────────────────────
    col1.markdown(f"""
    <div style="background:linear-gradient(135deg,#FFF5F5 0%,#FFE5E5 100%);
                border-radius:12px;padding:20px;border-top:5px solid {COR_VERMELHO};
                text-align:center;height:190px;display:flex;flex-direction:column;
                justify-content:center;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1px;color:{COR_VERMELHO};margin-bottom:6px">
        ⬇️ Cenário Conservador
      </div>
      <div style="font-size:11px;color:#999;margin-bottom:2px">P10 — Pior caso esperado</div>
      <div style="font-size:34px;font-weight:900;color:{COR_VERMELHO};line-height:1.1;margin:6px 0">
        {_fmt_ton(total_p10)} ton
      </div>
      <div style="font-size:11px;color:#777;line-height:1.5">
        Em 9 de cada 10 simulações,<br>as vendas ficaram <b>acima</b> deste valor
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cenário Central (P50) ─────────────────────────────────────────
    col2.markdown(f"""
    <div style="background:linear-gradient(135deg,#FFF8F0 0%,#FDEBD0 100%);
                border-radius:12px;padding:20px;border-top:5px solid {COR_ACENTO};
                text-align:center;height:190px;display:flex;flex-direction:column;
                justify-content:center;box-shadow:0 4px 16px rgba(244,130,42,.20);">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1px;color:{COR_ACENTO};margin-bottom:6px">
        ⭐ Cenário Central
      </div>
      <div style="font-size:11px;color:#999;margin-bottom:2px">P50 — Mediana (mais provável)</div>
      <div style="font-size:36px;font-weight:900;color:{COR_ACENTO};line-height:1.1;margin:6px 0">
        {_fmt_ton(total_p50)} ton
      </div>
      <div style="font-size:11px;color:#777;line-height:1.5">
        Faixa central: <b>{_fmt_ton(total_p25)}–{_fmt_ton(total_p75)} ton</b><br>
        (50% das simulações ficaram aqui)
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Melhor Cenário (P90) ──────────────────────────────────────────
    col3.markdown(f"""
    <div style="background:linear-gradient(135deg,#F0FFF4 0%,#DCFCE7 100%);
                border-radius:12px;padding:20px;border-top:5px solid {COR_VERDE};
                text-align:center;height:190px;display:flex;flex-direction:column;
                justify-content:center;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1px;color:{COR_VERDE};margin-bottom:6px">
        ⬆️ Cenário Otimista
      </div>
      <div style="font-size:11px;color:#999;margin-bottom:2px">P90 — Melhor caso esperado</div>
      <div style="font-size:34px;font-weight:900;color:{COR_VERDE};line-height:1.1;margin:6px 0">
        {_fmt_ton(total_p90)} ton
      </div>
      <div style="font-size:11px;color:#777;line-height:1.5">
        Em 9 de cada 10 simulações,<br>as vendas ficaram <b>abaixo</b> deste valor
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

    # Frase narrativa de interpretação
    amplitude = total_p90 - total_p10
    st.markdown(f"""
    <div style="background:#FFF8F0;border-radius:8px;padding:12px 18px;
                border-left:4px solid {COR_ACENTO};font-size:13px;color:#444;
                margin-bottom:16px;">
      📌 <b>Interpretação:</b> Em <b>8 de cada 10 simulações</b>, as vendas das próximas {n} semanas
      ficaram entre <b style="color:{COR_VERMELHO}">{_fmt_ton(total_p10)} ton</b> e
      <b style="color:{COR_VERDE}">{_fmt_ton(total_p90)} ton</b> — uma amplitude de
      <b>{_fmt_ton(amplitude)} ton</b>. O cenário central aponta para
      <b style="color:{COR_ACENTO}">{_fmt_ton(total_p50)} ton</b>.
      Use esses valores para calibrar o plano: se o S&OP estiver fora da faixa P10–P90,
      considere revisão.
    </div>
    """, unsafe_allow_html=True)


def _render_mc_reading_guide() -> None:
    """Guia de leitura do gráfico Monte Carlo."""
    with st.expander("📖 Como ler este gráfico? (Guia passo a passo)", expanded=False):
        st.markdown(f"""
**O gráfico de projeção Monte Carlo tem 4 elementos visuais principais:**

| Elemento | O que representa | Como usar |
|---|---|---|
| 🟠 **Faixa laranja escura** | Faixa P25–P75: onde ficaram **50% das simulações** | Região mais provável da demanda |
| 🔶 **Faixa laranja clara** | Faixa P10–P90: onde ficaram **80% das simulações** | Limite razoável de variação |
| 🟠 **Linha laranja sólida** | **Forecast central (P50)** — mediana de 1.000 cenários | Use como referência principal de planejamento |
| 🔴 **Linha vermelha pontilhada** | **Pior cenário (P10)** — apenas 10% das sim. ficaram abaixo | Piso de segurança para não ser surpreendido |
| 🟢 **Linha verde pontilhada** | **Melhor cenário (P90)** — apenas 10% das sim. ficaram acima | Teto otimista — máximo esperado |
| 🔵 **Linha azul pontilhada** | **Plano S&OP** | Compare: está dentro ou fora da faixa? |
| 🟣 **Linha roxa traço-ponto** | **Programa S&OE** | Compare: está dentro ou fora da faixa? |

---

**Passo a passo para interpretar:**

1. **Veja onde o Plano S&OP e o S&OE estão em relação à faixa laranja.**
   - Se o plano está *dentro* da faixa → ✅ plano bem calibrado
   - Se o plano está *acima* da faixa laranja clara → ⚠️ plano otimista demais — risco de frustrar expectativa
   - Se o plano está *abaixo* da faixa → ⚠️ plano conservador — possível subestimação da demanda

2. **Olhe a largura da faixa (amplitude P10–P90).**
   - Faixa estreita → demanda estável e previsível
   - Faixa larga → demanda volátil, mais difícil de prever

3. **Use o P50 como referência central** para revisão do plano semanal.

4. **Use o P10 como piso de segurança** — se a semana parece ruim, é provável que fique acima do P10.

5. **Use o P90 para dimensionamento de capacidade** — se quiser garantir atendimento no cenário otimista.

> 💡 **Dica prática:** Se a sua meta atual está sistematicamente acima do P90, é um sinal claro de
> que o plano precisa ser revisado para baixo. Se está abaixo do P10, revise para cima.
        """)


def _render_monte_carlo(
    semanas: list,
    mc: dict,
    df_f: pd.DataFrame,
    kp: str,
    pace: float,
    badge: str = "Consolidado",
) -> None:
    if not semanas or not mc:
        return

    labels   = [_tw_label(a, m, s) for (a, m, s, _, _) in semanas]
    periodos = [f"{di:02d}/{m:02d}–{df_:02d}/{m:02d}" for (a, m, s, di, df_) in semanas]

    p10 = mc['p10']; p25 = mc['p25']
    p50 = mc['p50']; p75 = mc['p75']; p90 = mc['p90']

    fig = go.Figure()

    # ── Banda P10–P90 (pior–melhor cenário) ─────────────────────────
    fig.add_trace(go.Scatter(
        x=labels + labels[::-1],
        y=list(p90) + list(p10[::-1]),
        fill="toself",
        fillcolor="rgba(244,130,42,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Faixa P10–P90 (80% das simulações)",
        hoverinfo="skip",
    ))

    # ── Banda P25–P75 (cenário mais provável) ────────────────────────
    fig.add_trace(go.Scatter(
        x=labels + labels[::-1],
        y=list(p75) + list(p25[::-1]),
        fill="toself",
        fillcolor="rgba(244,130,42,0.30)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Faixa P25–P75 (50% das simulações)",
        hoverinfo="skip",
    ))

    # ── P90 — melhor cenário ────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=labels, y=p90,
        mode="lines+markers",
        line=dict(color=COR_VERDE, width=1.8, dash="dot"),
        marker=dict(size=6, color=COR_VERDE, symbol="triangle-up",
                    line=dict(color="white", width=1)),
        name="⬆ Otimista P90",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "🟢 Otimista (P90): <b>%{y:,.0f} ton</b><br>"
            "<span style='font-size:10px;color:#888'>90% das simulações ficaram abaixo</span>"
            "<extra></extra>"
        ),
    ))

    # ── P10 — pior cenário ──────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=labels, y=p10,
        mode="lines+markers",
        line=dict(color=COR_VERMELHO, width=1.8, dash="dot"),
        marker=dict(size=6, color=COR_VERMELHO, symbol="triangle-down",
                    line=dict(color="white", width=1)),
        name="⬇ Conservador P10",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "🔴 Conservador (P10): <b>%{y:,.0f} ton</b><br>"
            "<span style='font-size:10px;color:#888'>90% das simulações ficaram acima</span>"
            "<extra></extra>"
        ),
    ))

    # ── P50 — forecast central ──────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=labels, y=p50,
        mode="lines+markers",
        line=dict(color=COR_ACENTO, width=3.5),
        marker=dict(size=10, color=COR_ACENTO, symbol="circle",
                    line=dict(color="white", width=2)),
        name="⭐ Forecast Central P50",
        hovertemplate=(
            "<b>%{x}</b> (%{customdata})<br>"
            "🟠 Forecast Central (P50): <b>%{y:,.0f} ton</b><br>"
            "<span style='font-size:10px;color:#888'>Mediana de 1.000 simulações</span>"
            "<extra></extra>"
        ),
        customdata=periodos,
    ))

    # ── Plano S&OP ───────────────────────────────────────────────────
    if 'meta_sop' in df_f.columns:
        sop_vals = [_meta_semana(df_f,'meta_sop',a,m,s) for (a,m,s,_,_) in semanas]
        sop_mask = [v > 0 for v in sop_vals]
        if any(sop_mask):
            x_sop = [labels[i] for i,v in enumerate(sop_mask) if v]
            y_sop = [sop_vals[i] for i,v in enumerate(sop_mask) if v]
            fig.add_trace(go.Scatter(
                x=x_sop, y=y_sop,
                mode="lines+markers",
                line=dict(color=COR_PRIMARIA, width=2.5, dash="dot"),
                marker=dict(size=8, color=COR_PRIMARIA, symbol="square",
                            line=dict(color="white", width=1.5)),
                name="🔵 Plano S&OP",
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "🔵 Plano S&OP: <b>%{y:,.0f} ton</b>"
                    "<extra></extra>"
                ),
            ))

    # ── Programa S&OE ────────────────────────────────────────────────
    if 'meta_soe' in df_f.columns:
        soe_vals = [_meta_semana(df_f,'meta_soe',a,m,s) for (a,m,s,_,_) in semanas]
        soe_mask = [v > 0 for v in soe_vals]
        if any(soe_mask):
            x_soe = [labels[i] for i,v in enumerate(soe_mask) if v]
            y_soe = [soe_vals[i] for i,v in enumerate(soe_mask) if v]
            fig.add_trace(go.Scatter(
                x=x_soe, y=y_soe,
                mode="lines+markers",
                line=dict(color="#9C27B0", width=2.5, dash="dashdot"),
                marker=dict(size=8, color="#9C27B0", symbol="diamond",
                            line=dict(color="white", width=1.5)),
                name="🟣 Programa S&OE",
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "🟣 Programa S&OE: <b>%{y:,.0f} ton</b>"
                    "<extra></extra>"
                ),
            ))

    # ── Anotações na última semana (labels flutuantes) ────────────────
    last_label = labels[-1]
    fig.add_annotation(
        x=last_label, y=float(p90[-1]),
        text="Otimista<br>(P90)",
        showarrow=False,
        xanchor="left", yanchor="middle",
        font=dict(size=9, color=COR_VERDE, family="Arial Bold"),
        xshift=8,
    )
    fig.add_annotation(
        x=last_label, y=float(p50[-1]),
        text="Central<br>(P50)",
        showarrow=False,
        xanchor="left", yanchor="middle",
        font=dict(size=9, color=COR_ACENTO, family="Arial Bold"),
        xshift=8,
    )
    fig.add_annotation(
        x=last_label, y=float(p10[-1]),
        text="Conservador<br>(P10)",
        showarrow=False,
        xanchor="left", yanchor="middle",
        font=dict(size=9, color=COR_VERMELHO, family="Arial Bold"),
        xshift=8,
    )

    fig.update_layout(
        height=480,
        title=dict(
            text=(
                f"<b>Projeção Monte Carlo — Próximas Semanas</b><br>"
                "<span style='font-size:11px;font-weight:normal;color:#888'>"
                "1.000 simulações · faixa laranja escura = 50% mais prováveis · "
                "faixa clara = 80% de confiança</span>"
            ),
            font=dict(size=14, color=COR_PRIMARIA, family="Arial"), x=0,
            pad=dict(b=8),
        ),
        margin=dict(t=72, b=110, l=75, r=110),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11), gridcolor=COR_GRID, tickangle=-20),
        yaxis=dict(
            title="Volume (ton)", gridcolor=COR_GRID,
            tickformat=",", tickfont=dict(size=11),
        ),
        legend=dict(
            orientation="h",
            y=-0.22,          # abaixo do eixo X — sem sobrepor o título
            x=0.5, xanchor="center",
            font=dict(size=10), bgcolor="rgba(255,255,255,0.90)",
            bordercolor="#E0E0E0", borderwidth=1,
            tracegroupgap=4,
        ),
        font=dict(family="Arial", size=11, color=COR_TEXTO),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False}, key=f"{kp}_mc_chart")


def _render_tabela(semanas: list, mc: dict, df_f: pd.DataFrame) -> None:
    if not semanas or not mc:
        return

    _COR = {
        "Demanda acima ↑": ("#FEF0E6", "#C0392B"),
        "Demanda abaixo ↓": ("#F5E9C8", "#B8860B"),
        "Alinhado ✓":        ("#D6EDE0", "#1A7A40"),
        "Sem plano":          ("#F5F5F5", "#757575"),
    }

    rows = []
    for i, (ano, mes, sem, di, df_) in enumerate(semanas):
        sop = _meta_semana(df_f, 'meta_sop', ano, mes, sem) if 'meta_sop' in df_f.columns else 0
        soe = _meta_semana(df_f, 'meta_soe', ano, mes, sem) if 'meta_soe' in df_f.columns else 0
        p50 = mc['p50'][i]; p10 = mc['p10'][i]; p90 = mc['p90'][i]

        ref = sop if sop > 0 else soe
        diff_sop = (p50 - sop) / sop if sop > 0 else None
        diff_soe = (p50 - soe) / soe if soe > 0 else None

        if ref == 0:
            status = "Sem plano"
        elif p50 > ref * 1.10:
            status = "Demanda acima ↑"
        elif p50 < ref * 0.90:
            status = "Demanda abaixo ↓"
        else:
            status = "Alinhado ✓"

        rows.append({
            "Semana":        _tw_label(ano, mes, sem),
            "Período":       f"{di:02d}/{mes:02d}–{df_:02d}/{mes:02d}/{ano}",
            "Forecast P50":  f"{_fmt_ton(p50)} ton",
            "Pior (P10)":    f"{_fmt_ton(p10)} ton",
            "Melhor (P90)":  f"{_fmt_ton(p90)} ton",
            "Plano S&OP":    f"{_fmt_ton(sop)} ton" if sop > 0 else "—",
            "Prog. S&OE":    f"{_fmt_ton(soe)} ton" if soe > 0 else "—",
            "Dif. vs S&OP":  f"{diff_sop:+.1%}" if diff_sop is not None else "—",
            "Dif. vs S&OE":  f"{diff_soe:+.1%}" if diff_soe is not None else "—",
            "Status":        status,
        })

    df_tab = pd.DataFrame(rows)

    def _style(row):
        bg, cor_s = _COR.get(row["Status"], ("#fff", COR_TEXTO))
        s = []
        for c in row.index:
            if c == "Status":
                s.append(f"background:{bg};color:{cor_s};font-weight:700;text-align:center")

            elif c == "Forecast P50":
                s.append(f"background:{bg};font-weight:800;color:{COR_ACENTO};font-size:13px;text-align:right")

            elif c in ("Pior (P10)", "Melhor (P90)"):
                # Gradiente suave baseado no status da linha
                cor_c = "#C0392B" if c == "Pior (P10)" else "#1A7A40"
                s.append(f"background:{bg};color:{cor_c};text-align:right;opacity:0.85")

            elif c.startswith("Dif."):
                try:
                    v = float(row[c].replace("%","").replace("+","").replace("—","0").replace(",","."))
                    if v > 15:
                        s.append("background:#F5D5D1;color:#C0392B;font-weight:700;text-align:right")
                    elif v > 5:
                        s.append("background:#FEF0E6;color:#C0392B;font-weight:600;text-align:right")
                    elif v < -15:
                        s.append("background:#D6EDE0;color:#1A7A40;font-weight:700;text-align:right")
                    elif v < -5:
                        s.append("background:#D6EDE0;color:#1A7A40;font-weight:600;text-align:right")
                    else:
                        s.append(f"background:{bg};color:#555;text-align:right")
                except Exception:
                    s.append(f"background:{bg};text-align:right")

            elif c in ("Plano S&OP", "Prog. S&OE"):
                s.append(f"background:{bg};color:#546E7A;text-align:right")

            elif c == "Semana":
                s.append(f"background:{bg};font-weight:700;color:{COR_PRIMARIA}")

            elif c == "Período":
                s.append(f"background:{bg};color:#888;font-size:11px;text-align:left")

            else:
                s.append(f"background:{bg};text-align:right")
        return s

    styled = (
        df_tab.style
        .apply(_style, axis=1)
        .set_table_styles([{"selector":"th","props":[
            ("background-color",COR_PRIMARIA),("color","white"),
            ("font-size","11px"),("text-align","center"),("padding","7px 10px"),
        ]}])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 height=min(550, 44 + len(df_tab) * 40))

    st.markdown(
        '<div style="font-size:10px;color:#9AA5B4;margin-top:-4px">'
        'Forecast P50 = mediana de 1.000 simulações · Pior (P10) / Melhor (P90) = percentis Monte Carlo · '
        'Dif. = (Forecast P50 − Plano) / Plano'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
# 3. FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def render(
    df_f: pd.DataFrame,
    pesos: dict,
    col_meta: str,
    label_meta: str,
    ano_sel: int,
    mes_sel: int,
    semana_atual: int,
    n_semanas: int,
    filtros_ativos: list[str],
) -> None:
    st.markdown(
        '<div class="secao-titulo">📡 Demand Sensing — Diagnóstico e Projeção Probabilística</div>',
        unsafe_allow_html=True,
    )

    if df_f.empty:
        st.warning("Dados insuficientes para o Demand Sensing.")
        return

    kp = col_meta  # key_prefix único por aba

    # ── Histórico completo (só semanas com vol > 0) ────────────────
    df_hist = _historico_completo(df_f, col_meta, n=N_HIST)

    if df_hist.empty:
        st.info(
            "Histórico insuficiente. São necessárias ao menos 4 semanas completas "
            "(com realizado e plano registrados) para ativar o Demand Sensing."
        )
        return

    metricas = _calcular_metricas(df_hist)

    # ── Hero ───────────────────────────────────────────────────────
    _render_hero(metricas, col_meta)

    # ── KPIs ────────────────────────────────────────────────────────
    _render_kpis(metricas)

    # ── Gráfico de erro histórico % (largura total) ───────────────
    _render_erro_historico(df_hist, kp)

    # ── Gráfico de volume realizado vs plano + erro absoluto ──────
    _render_volume_historico(df_hist, kp)

    # ── Executive summary — leitura automática para o coordenador ─
    _render_exec_summary(metricas, df_hist, col_meta)

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # ── Pace e desvio para Monte Carlo ────────────────────────────
    pace, std = _pace_e_std(
        df_f,
        semana_excl=(ano_sel, mes_sel, semana_atual),
        n=N_PACE,
    )

    if pace <= 0:
        st.info("Sem histórico de vendas suficiente para gerar projeção.")
        return

    bias_frac = metricas.get('bias', 0) / 100.0

    # ── Semanas futuras ────────────────────────────────────────────
    semanas = _semanas_futuras(ano_sel, mes_sel, semana_atual, n_semanas, n=N_FUTURO)
    if not semanas:
        st.info("Não há semanas futuras para projetar.")
        return

    # ── Monte Carlo ────────────────────────────────────────────────
    mc = _monte_carlo(pace, std, bias_frac, pesos, semanas, n_sim=N_SIM)

    # ── Introdução didática ────────────────────────────────────────
    _render_mc_intro(metricas, pace, std, bias_frac)

    # ── Cards de cenários (P10 / P50 / P90 totais) ────────────────
    _render_mc_scenarios(semanas, mc)

    # ── Gráfico Monte Carlo (largura total) ────────────────────────
    _render_monte_carlo(semanas, mc, df_f, kp, pace)

    # ── Guia de leitura do gráfico ────────────────────────────────
    _render_mc_reading_guide()

    # ── Tabela detalhada ───────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:14px;font-weight:700;color:{COR_PRIMARIA};'
        f'margin:12px 0 6px 0">Detalhamento por Semana</div>',
        unsafe_allow_html=True,
    )
    _render_tabela(semanas, mc, df_f)

    # ── Metodologia ────────────────────────────────────────────────
    with st.expander("ℹ️ Metodologia do Demand Sensing", expanded=False):
        st.markdown(f"""
**Métricas de qualidade do plano** (calculadas sobre semanas completas com vol > 0 e meta > 0)

| Métrica | Fórmula | Interpretação |
|---|---|---|
| **MAPE** | média(|real − plano| / plano) × 100 | Erro médio absoluto em % — menor = melhor |
| **Bias** | média((real − plano) / plano) × 100 | + = subestimando · − = superestimando |
| **Assertividade** | % semanas com erro ≤ ±{HIT_THRESH:.0%} | Meta: ≥ 60% |
| **Volatilidade** | desvio padrão dos erros (%) | Mede consistência da demanda |
| **MAE** | média(|real − plano|) em ton | Erro médio em volume absoluto |

**Monte Carlo** ({N_SIM:,} simulações · seed fixo para reprodutibilidade)
- **Pace base**: média das últimas {N_PACE} semanas completas (ton/semana)
- **Ajuste sazonal**: peso histórico da semana ÷ peso médio de referência
- **Ruído**: distribuído como Normal(bias, volatilidade_histórica)
- **P10**: pior cenário (10% das simulações ficaram abaixo)
- **P50**: cenário central / mediana (forecast principal)
- **P90**: melhor cenário (10% das simulações ficaram acima)

**Filtro de semanas válidas**: apenas semanas com `vol_ton > 0` E `meta > 0` são usadas.
Isso exclui semanas futuras que possuem meta cadastrada mas ainda não têm realizado.
        """)
