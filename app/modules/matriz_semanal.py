"""
Módulo Matriz Semanal — heat map Semana × Linha de Produto.

Responde: "Em qual semana e em qual linha estamos bem ou mal?"

Células passadas  = % do plano semanal (realizado / meta), cor semáforo
Células futuras   = meta planejada em tons (fundo neutro)
Coluna PROJEÇÃO   = estimativa de fechamento mensal por linha
Badges de risco   = 🔴 < 75% · 🟡 75–90% · 🟢 ≥ 90%
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.calendar_tw import get_month_tw_ranges, tw_label
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_TEXTO, COR_GRID, fmt_ton as _fmt_ton,
)

# ── Thresholds de semáforo ──────────────────────────────────────────────────
THRESH_ACIMA   = 1.00   # ≥ 100% → verde escuro
THRESH_OK      = 0.95   # ≥  95% → verde
THRESH_ATENCAO = 0.75   # ≥  75% → amarelo
THRESH_RISCO   = 0.50   # ≥  50% → laranja
# < 50% → vermelho crítico

# Valor sentinel para semanas futuras no z do heatmap
_Z_FUTURO = -0.05
_ZMIN, _ZMAX = -0.10, 1.30

# Colorscale: [0.0] → gray (futuro) … [1.0] → verde escuro
# Com zmin=-0.10 e zmax=1.30, o range é 1.40:
#   z=-0.05 → pos (0.05/1.40)=0.036 → cinza
#   z= 0.00 → pos (0.10/1.40)=0.071 → vermelho
#   z= 0.50 → pos (0.60/1.40)=0.429 → laranja
#   z= 0.75 → pos (0.85/1.40)=0.607 → amarelo
#   z= 0.95 → pos (1.05/1.40)=0.750 → verde claro
#   z= 1.30 → pos (1.40/1.40)=1.000 → verde escuro
_COLORSCALE = [
    [0.000, '#F1F5F9'],  # futuro (cinza neutro)
    [0.071, '#FEF2F2'],  # 0% → vermelho muito suave
    [0.250, '#FECACA'],  # 25% → vermelho suave
    [0.429, '#FDE68A'],  # 50% → âmbar suave
    [0.607, '#FEF3C7'],  # 75% → âmbar claro
    [0.750, '#A7F3D0'],  # 95% → verde menta
    [0.857, '#10B981'],  # 100% → esmeralda
    [1.000, '#059669'],  # 130% → esmeralda escuro
]


# ══════════════════════════════════════════════════════════════════════════════
# CÁLCULOS
# ══════════════════════════════════════════════════════════════════════════════

def _aggregate(
    df_f: pd.DataFrame,
    col_meta: str,
    ano_sel: int,
    mes_sel: int,
    n_semanas: int,
) -> pd.DataFrame:
    """
    Agrega vol_ton e meta por (linha, semana_mes) do mês selecionado.
    Garante que todas as combinações (linha × semana 1..n_semanas) existam.
    """
    df_mes = df_f[(df_f['ano'] == ano_sel) & (df_f['mes'] == mes_sel)].copy()
    if df_mes.empty:
        return pd.DataFrame()

    # semana_mes pode vir como float quando há NaN no DataFrame original — forçar int
    df_mes['semana_mes'] = df_mes['semana_mes'].fillna(1).astype(int)

    agg = (
        df_mes
        .groupby(['linha', 'semana_mes'])[[col_meta, 'vol_ton']]
        .sum()
        .reset_index()
        .rename(columns={col_meta: 'meta'})
    )

    # Garante todas as semanas (1..n_semanas) para todas as linhas
    linhas  = sorted(agg['linha'].unique())
    semanas = list(range(1, n_semanas + 1))
    idx = pd.MultiIndex.from_product([linhas, semanas], names=['linha', 'semana_mes'])
    agg = (
        agg.set_index(['linha', 'semana_mes'])
           .reindex(idx, fill_value=0.0)
           .reset_index()
    )
    return agg


def _build_pivots(
    agg: pd.DataFrame,
    semana_atual: int,
    n_semanas: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Retorna (df_pct, df_vol, df_meta, labels_x).
    df_pct: pct realizados para semanas passadas, NaN para futuras.
    """
    # % do plano — só semanas encerradas com meta > 0
    agg['pct'] = agg.apply(
        lambda r: r['vol_ton'] / r['meta']
        if r['meta'] > 0 and r['semana_mes'] <= semana_atual else np.nan,
        axis=1,
    )

    # Ordena linhas por volume realizado (maior no topo)
    vol_total = agg.groupby('linha')['vol_ton'].sum().sort_values(ascending=False)
    linhas_ord = vol_total.index.tolist()

    df_pct  = agg.pivot(index='linha', columns='semana_mes', values='pct').reindex(linhas_ord)
    df_vol  = agg.pivot(index='linha', columns='semana_mes', values='vol_ton').reindex(linhas_ord)
    df_meta = agg.pivot(index='linha', columns='semana_mes', values='meta').reindex(linhas_ord)

    # Labels TW para as colunas
    labels = [tw_label(int(agg['linha'].iloc[0] and 1 or 1), 1, 1)]  # placeholder
    # Usa a função correta:
    # Precisamos do ano/mes — passamos via caller
    # Simplificação: usa Sn como fallback (será sobrescrito pelo caller)
    labels = [f"S{s}" for s in range(1, n_semanas + 1)]

    return df_pct, df_vol, df_meta, labels


def _compute_projection(
    df_vol: pd.DataFrame,
    df_meta: pd.DataFrame,
    semana_atual: int,
    n_semanas: int,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Retorna (vol_realizado, meta_mes, pct_projecao) por linha.
    Projeção linear: pace = vol_real / semana_atual × n_semanas.
    """
    cols_passadas = [c for c in df_vol.columns if c <= semana_atual]
    vol_real = df_vol[cols_passadas].fillna(0).sum(axis=1) if cols_passadas else pd.Series(0.0, index=df_vol.index)
    meta_mes = df_meta.fillna(0).sum(axis=1)

    pace = vol_real / semana_atual if semana_atual > 0 else vol_real
    proj = pace * n_semanas
    pct_proj = proj / meta_mes.replace(0.0, np.nan)

    return vol_real, meta_mes, pct_proj


def get_risk_badges(pct_proj: pd.Series) -> dict[str, str]:
    """Retorna {linha: badge_emoji} — público para uso externo."""
    badges: dict[str, str] = {}
    for linha, pct in pct_proj.items():
        if pd.isna(pct) or pct == 0:
            badges[linha] = '⚪'
        elif pct < THRESH_ATENCAO:
            badges[linha] = '🔴'
        elif pct < THRESH_OK:
            badges[linha] = '🟡'
        else:
            badges[linha] = '🟢'
    return badges


# ══════════════════════════════════════════════════════════════════════════════
# VISUAL
# ══════════════════════════════════════════════════════════════════════════════

def _render_legenda_cores() -> None:
    st.markdown(
        """<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:11px;
                       color:#555;margin:-4px 0 14px 0;align-items:center;">
          <b style="color:#444">Legenda:</b>
          <span style="background:#1A7A40;color:white;padding:2px 8px;border-radius:4px">≥100% Acima</span>
          <span style="background:#6BAE8A;color:#1A7A40;padding:2px 8px;border-radius:4px">≥95% No plano</span>
          <span style="background:#FFF176;color:#555;padding:2px 8px;border-radius:4px">75–94% Atenção</span>
          <span style="background:#FFA726;color:white;padding:2px 8px;border-radius:4px">50–74% Em risco</span>
          <span style="background:#C0392B;color:white;padding:2px 8px;border-radius:4px">&lt;50% Crítico</span>
          <span style="background:#E0E0E0;color:#888;padding:2px 8px;border-radius:4px">Semana futura</span>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_resumo_riscos(badges: dict[str, str], pct_proj: pd.Series) -> None:
    """Card de resumo rápido dos riscos identificados."""
    em_risco     = [(l, pct_proj.get(l)) for l, b in badges.items() if b == '🔴']
    em_atencao   = [(l, pct_proj.get(l)) for l, b in badges.items() if b == '🟡']
    acima_plano  = [(l, pct_proj.get(l)) for l, b in badges.items() if b == '🟢' and (pct_proj.get(l) or 0) >= THRESH_ACIMA]

    if not em_risco and not em_atencao:
        return

    partes = []
    if em_risco:
        nomes = ', '.join(f"<b>{l}</b> ({p:.0%})" for l, p in em_risco if p is not None)
        partes.append(
            f'🔴 <b>Crítico:</b> {nomes}'
        )
    if em_atencao:
        nomes = ', '.join(f"<b>{l}</b> ({p:.0%})" for l, p in em_atencao if p is not None)
        partes.append(f'🟡 <b>Atenção:</b> {nomes}')
    if acima_plano:
        nomes = ', '.join(f"<b>{l}</b> ({p:.0%})" for l, p in acima_plano if p is not None)
        partes.append(f'🟢 <b>Acima do plano:</b> {nomes}')

    st.markdown(
        f"""<div style="background:#FFF8F0;border-radius:8px;padding:12px 16px;
                        border-left:4px solid {COR_ACENTO};margin-bottom:12px;
                        font-size:13px;color:#444;line-height:1.8;">
              {'<br>'.join(partes)}
            </div>""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def render(
    df_f: pd.DataFrame,
    col_meta: str,
    ano_sel: int,
    mes_sel: int,
    semana_atual: int,
    n_semanas: int,
    kp: str,
) -> dict[str, str]:
    """
    Renderiza o heat map Semana × Linha de Produto.

    Retorna dict {linha: badge_emoji} para uso externo (ex.: destacar linhas em risco
    nos títulos de outras seções do dashboard).
    """
    if df_f.empty:
        return {}

    st.markdown(
        '<div class="secao-titulo">🗓️ Matriz Semanal — Realizado vs Plano por Linha</div>',
        unsafe_allow_html=True,
    )

    # ── Dados ─────────────────────────────────────────────────────────────────
    agg = _aggregate(df_f, col_meta, ano_sel, mes_sel, n_semanas)
    if agg.empty:
        st.info("Sem dados para a matriz semanal no mês selecionado.")
        return {}

    df_pct, df_vol, df_meta, _ = _build_pivots(agg, semana_atual, n_semanas)

    # Labels TW reais
    labels_tw = [tw_label(ano_sel, mes_sel, s) for s in range(1, n_semanas + 1)]

    vol_real, meta_mes, pct_proj = _compute_projection(df_vol, df_meta, semana_atual, n_semanas)
    badges = get_risk_badges(pct_proj)

    linhas  = df_pct.index.tolist()
    semanas = list(df_pct.columns)

    # ── Resumo de riscos ───────────────────────────────────────────────────────
    _render_resumo_riscos(badges, pct_proj)

    # ── Monta arrays z / text / hover ─────────────────────────────────────────
    z_mat, text_mat, hover_mat = [], [], []

    for linha in linhas:
        z_row, text_row, hover_row = [], [], []
        for sem in semanas:
            sem_i = int(sem)   # semana_mes pode ser float vindo do pivot
            vol  = float(df_vol.loc[linha, sem])
            meta = float(df_meta.loc[linha, sem])
            pct  = df_pct.loc[linha, sem]

            if sem_i > semana_atual:
                # Semana futura — mostra meta
                z_row.append(_Z_FUTURO)
                text_row.append(f"~{_fmt_ton(meta)}t" if meta > 0 else "—")
                hover_row.append(
                    f"<b>{linha}</b> | {labels_tw[sem_i-1]}<br>"
                    f"Meta planejada: <b>{meta:,.0f} ton</b><br>"
                    f"<i>Semana futura — sem realizado</i>"
                )
            elif meta == 0:
                z_row.append(np.nan)
                text_row.append("—")
                hover_row.append(f"<b>{linha}</b> | {labels_tw[sem_i-1]}<br>Sem plano cadastrado")
            else:
                pct_v = float(pct) if pd.notna(pct) else 0.0
                z_clamped = min(max(pct_v, 0.0), _ZMAX)
                z_row.append(z_clamped)
                cor_text = "white" if pct_v < 0.75 or pct_v >= 1.0 else "#333"
                text_row.append(f"{pct_v:.0%}")
                hover_row.append(
                    f"<b>{linha}</b> | {labels_tw[sem_i-1]}<br>"
                    f"Realizado: <b>{vol:,.0f} ton</b><br>"
                    f"Plano: {meta:,.0f} ton<br>"
                    f"% Plano: <b>{pct_v:.1%}</b>"
                )

        # Coluna PROJEÇÃO (total mensal)
        pct_p = pct_proj.get(linha)
        if pd.notna(pct_p):
            z_row.append(min(max(float(pct_p), 0.0), _ZMAX))
            text_row.append(f"{float(pct_p):.0%}")
        else:
            z_row.append(np.nan)
            text_row.append("—")
        hover_row.append(
            f"<b>{linha}</b> | Projeção mensal<br>"
            f"Realizado até S{semana_atual}: <b>{vol_real.get(linha, 0):,.0f} ton</b><br>"
            f"Meta mês: {meta_mes.get(linha, 0):,.0f} ton<br>"
            f"Projeção: <b>{float(pct_p):.1%}</b>" if pd.notna(pct_p) else
            f"<b>{linha}</b> | Projeção indisponível"
        )

        z_mat.append(z_row)
        text_mat.append(text_row)
        hover_mat.append(hover_row)

    # Y labels com badges
    y_labels = [f"{badges.get(l, '⚪')} {l}" for l in linhas]
    x_labels = labels_tw + ["📊 PROJEÇÃO"]

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z_mat,
        x=x_labels,
        y=y_labels,
        text=text_mat,
        texttemplate="%{text}",
        textfont=dict(size=11, family="Arial Bold", color="black"),
        colorscale=_COLORSCALE,
        zmin=_ZMIN, zmax=_ZMAX,
        showscale=False,
        hoverinfo="text",
        hovertext=hover_mat,
        xgap=3,
        ygap=3,
    ))

    # Linha divisória antes da coluna PROJEÇÃO
    n_sem = len(labels_tw)
    fig.add_shape(
        type="line",
        x0=n_sem - 0.5, x1=n_sem - 0.5,
        y0=-0.5, y1=len(linhas) - 0.5,
        line=dict(color="#424242", width=2.5, dash="dot"),
    )

    # Destaque retangular na semana atual
    if 1 <= semana_atual <= n_sem:
        fig.add_shape(
            type="rect",
            x0=semana_atual - 1.5, x1=semana_atual - 0.5,
            y0=-0.5, y1=len(linhas) - 0.5,
            line=dict(color=COR_PRIMARIA, width=2.5),
            fillcolor="rgba(0,0,0,0)",
        )

    altura = max(300, 60 + len(linhas) * 42)

    fig.update_layout(
        height=altura,
        title=dict(
            text=(
                "<b>Matriz Semanal — % do Plano por Linha</b><br>"
                "<span style='font-size:11px;font-weight:normal;color:#888'>"
                "Semanas passadas = realizado / plano · "
                "Semanas futuras = meta planejada · "
                "Borda azul = semana atual · "
                "Última coluna = projeção de fechamento</span>"
            ),
            font=dict(size=13, color=COR_PRIMARIA, family="Arial"), x=0,
        ),
        margin=dict(t=72, b=90, l=200, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            tickfont=dict(size=10, family="Arial"),
            tickangle=-30,
            side="bottom",
            gridcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(
            tickfont=dict(size=11, family="Arial"),
            autorange="reversed",
            gridcolor="rgba(0,0,0,0)",
        ),
        font=dict(family="Arial", size=11, color=COR_TEXTO),
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False}, key=f"{kp}_matriz_chart")

    _render_legenda_cores()

    return badges
