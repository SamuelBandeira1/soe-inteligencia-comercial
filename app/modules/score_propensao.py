"""
Módulo de interface Streamlit — Aba "Prioridade de Contato".

Exibe tabela ranqueada de clientes por índice de prioridade de contato,
com filtros por linha/região/UF/tier, indicadores visuais e
gráfico de distribuição.

v3 — Polimento UI/UX:
- Cards com border-left:4px (coerência do design system)
- "Exibindo N de Total" com contexto da população
- Coluna "Ação Sugerida" na tabela — o que fazer com cada cliente
- Seção "Top Urgentes" (top 3) para visibilidade imediata
- Gráficos movidos para expander (tabela é a superfície principal)
- Explicação do cálculo movida para o final
- Dead code removido
- Empty states com orientação acionável
"""
from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engines.propensao_engine import PropensaoEngine

# ── Visual — importado do módulo centralizado ─────────────────────────────────
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO, COR_TEXTO,
    fmt_ton as _fmt_ton, cor_ritmo,
)

# ── Tier config ───────────────────────────────────────────────────────────────
TIER_CONFIG = {
    "QUENTE":   {"emoji": "🔥", "cor_bg": "#FEF2F2", "cor_txt": "#DC2626", "label": "Quente"},
    "MORNO":    {"emoji": "🌡️", "cor_bg": "#FFFBEB", "cor_txt": "#D97706", "label": "Morno"},
    "FRIO":     {"emoji": "🧊", "cor_bg": "#EFF6FF", "cor_txt": "#2563EB", "label": "Frio"},
    "DORMENTE": {"emoji": "💤", "cor_bg": "#F8FAFC", "cor_txt": "#64748B", "label": "Dormente"},
}


# ── Helpers visuais ───────────────────────────────────────────────────────────
def _badge_score(score: float) -> str:
    if score >= 60:
        bg, cor, label = "#ECFDF5", "#059669", "ALTO"
    elif score >= 30:
        bg, cor, label = "#FFFBEB", "#D97706", "MÉDIO"
    else:
        bg, cor, label = "#FEF2F2", "#DC2626", "BAIXO"
    return (
        f'<span style="background:{bg};color:{cor};font-weight:700;'
        f'font-size:11px;padding:2px 8px;border-radius:10px;">'
        f'{label} {score:.0f}</span>'
    )


def _fmt_data(d) -> str:
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return "—"
    try:
        return pd.Timestamp(d).strftime("%d/%m/%Y")
    except Exception:
        return "—"


def _cor_score(score: float) -> str:
    if score >= 60: return "#059669"
    if score >= 30: return "#D97706"
    return "#DC2626"


def _badge_tier(tier: str) -> str:
    cfg = TIER_CONFIG.get(tier, TIER_CONFIG["DORMENTE"])
    return (
        f'<span style="background:{cfg["cor_bg"]};color:{cfg["cor_txt"]};'
        f'font-weight:700;font-size:11px;padding:2px 8px;border-radius:10px;">'
        f'{cfg["emoji"]} {cfg["label"]}</span>'
    )


# ── Ação sugerida por cliente ─────────────────────────────────────────────────
def _gerar_acao_sugerida(row) -> str:
    """Retorna uma instrução curta de ação comercial baseada no perfil do cliente."""
    tier      = row.get("tier", "DORMENTE")
    dias      = int(row.get("dias_sem_comprar", 0) or 0)
    flag_novo = bool(row.get("flag_novo", False))
    score     = float(row.get("score_propensao", 0) or 0)

    if flag_novo:
        return "Fidelizar — cliente em descoberta da linha"
    if tier == "QUENTE":
        if dias <= 7:
            return "Aguardar — comprou esta semana"
        return "Acompanhar — comprou recentemente"
    if tier == "MORNO":
        if score >= 60:
            return "Ligar esta semana — janela ideal de recompra"
        return "Agendar ligação no mês"
    if tier == "FRIO":
        if score >= 40:
            return "Reativação — oferecer condição especial"
        return "Reativação — contato de relacionamento"
    # DORMENTE
    if dias > 365:
        return "Investigar perda — sem compra há mais de 1 ano"
    return "Reativação urgente — mais de 180 dias sem compra"


# ── Cache via session_state (evita serializar DataFrame inteiro para JSON) ────
_ENGINE_VERSION = "v3"


def _get_engine(df_filt: pd.DataFrame, df_hash: str) -> PropensaoEngine:
    key = f"_propensao_engine_{_ENGINE_VERSION}_{df_hash}"
    if key not in st.session_state:
        for k in list(st.session_state.keys()):
            if k.startswith("_propensao_engine_") and k != key:
                del st.session_state[k]
        st.session_state[key] = PropensaoEngine(df_filt)
    return st.session_state[key]


# ── Cards de métricas resumo ──────────────────────────────────────────────────
def _render_metricas(df_scores: pd.DataFrame, total_populacao: int) -> None:
    total    = len(df_scores)
    quente   = (df_scores["tier"] == "QUENTE").sum()
    morno    = (df_scores["tier"] == "MORNO").sum()
    frio     = (df_scores["tier"] == "FRIO").sum()
    dormente = (df_scores["tier"] == "DORMENTE").sum()
    idx_med  = df_scores["score_propensao"].mean() if total > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def _card(col, label, valor, cor, subtexto: str = ""):
        sub_html = (
            f'<div style="font-size:10px;color:#9EA8B3;margin-top:2px">{subtexto}</div>'
            if subtexto else ""
        )
        col.markdown(
            f'<div style="background:#FFFFFF;border-radius:12px;padding:14px 16px;'
            f'border-left:4px solid {cor};box-shadow:0 1px 3px rgba(0,0,0,0.06),0 4px 12px rgba(0,0,0,0.04);'
            f'border:1px solid #E2E8F0;">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.8px;color:#94A3B8;margin-bottom:6px">{label}</div>'
            f'<div style="font-size:22px;font-weight:800;color:#1E293B;letter-spacing:-0.5px">{valor}</div>'
            f'{sub_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    _card(c1, "Exibindo",
          f"{total:,}",
          COR_PRIMARIA,
          subtexto=f"de {total_populacao:,} clientes" if total < total_populacao else f"{total_populacao:,} clientes")
    _card(c2, "🔥 Quente (0-30d)",   quente,            "#C0392B")
    _card(c3, "🌡️ Morno (31-100d)",  morno,             "#8A6000")
    _card(c4, "🧊 Frio (101-180d)",  frio,              "#1B4F8A")
    _card(c5, "💤 Dormente (>180d)", dormente,          "#6C7A89")
    _card(c6, "Índice médio",         f"{idx_med:.1f}", COR_ACENTO)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Strip "Top Urgentes" ──────────────────────────────────────────────────────
def _render_top_urgentes(df_scores: pd.DataFrame) -> None:
    """Destaca os 3 clientes de maior prioridade com cards horizontais."""
    df_top = df_scores.head(3)
    if df_top.empty:
        return

    st.markdown(
        '<div style="font-size:12px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:.8px;color:#6C757D;margin-bottom:8px;">⚡ Top Urgentes</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(df_top))
    for i, (_, row) in enumerate(df_top.iterrows()):
        tier   = row.get("tier", "DORMENTE")
        cfg    = TIER_CONFIG.get(tier, TIER_CONFIG["DORMENTE"])
        score  = float(row.get("score_propensao", 0) or 0)
        acao   = _gerar_acao_sugerida(row)
        dias   = int(row.get("dias_sem_comprar", 0) or 0)
        linha  = str(row.get("linha", ""))

        # Nome: usa cliente_nome se preenchido e diferente do código
        cod   = str(row.get("cliente_id", "")).strip()
        nome  = str(row.get("cliente_nome", "")).strip()
        nome  = nome if nome and nome != cod else cod

        # Telefone
        tel_raw = str(row.get("telefone", "")).strip()
        tel_html = (
            f'<div style="font-size:11px;color:#1A7A40;font-weight:600;margin-bottom:6px">'
            f'📞 {tel_raw}</div>'
            if tel_raw and tel_raw not in ("", "—", "nan", "None")
            else '<div style="margin-bottom:6px"></div>'
        )

        cor_score = _cor_score(score)
        rank_num  = i + 1

        cols[i].markdown(
            f'<div style="background:#FFFFFF;border-radius:12px;padding:16px 18px;'
            f'border-left:4px solid {cor_score};'
            f'box-shadow:0 1px 3px rgba(0,0,0,0.06),0 4px 16px rgba(0,0,0,0.06);'
            f'border:1px solid #E2E8F0;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
            f'  <span style="font-size:11px;font-weight:700;color:#9EA8B3">#{rank_num} PRIORIDADE</span>'
            f'  <span style="font-size:18px;font-weight:900;color:{cor_score}">{score:.0f}</span>'
            f'</div>'
            f'<div style="font-size:13px;font-weight:700;color:{COR_PRIMARIA};margin-bottom:2px">'
            f'  {cfg["emoji"]} {nome}</div>'
            f'<div style="font-size:11px;color:#546E7A;margin-bottom:4px">{linha} · {dias}d sem comprar</div>'
            f'{tel_html}'
            f'<div style="font-size:11px;background:{cfg["cor_bg"]};color:{cfg["cor_txt"]};'
            f'padding:4px 8px;border-radius:6px;font-weight:600">{acao}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)


# ── Gráfico de distribuição de scores ────────────────────────────────────────
def _render_distribuicao(df_scores: pd.DataFrame) -> None:
    """Histograma de distribuição do índice + breakdown por tier."""
    scores = df_scores["score_propensao"].dropna()
    if scores.empty:
        return

    col_hist, col_tier = st.columns([3, 2])

    with col_hist:
        fig = go.Figure()
        bins = list(range(0, 110, 10))
        counts, edges = np.histogram(scores, bins=bins)
        bin_labels = [f"{edges[i]:.0f}–{edges[i+1]:.0f}" for i in range(len(counts))]

        bar_colors = []
        for i in range(len(counts)):
            mid = (edges[i] + edges[i+1]) / 2
            if mid >= 60:
                bar_colors.append(COR_VERDE)
            elif mid >= 30:
                bar_colors.append(COR_AMARELO)
            else:
                bar_colors.append(COR_VERMELHO)

        fig.add_trace(go.Bar(
            x=bin_labels, y=counts,
            marker_color=bar_colors,
            marker_line=dict(color="rgba(0,0,0,0.1)", width=1),
            text=counts, textposition="outside",
            textfont=dict(size=10, color=COR_TEXTO),
            hovertemplate="Índice %{x}<br>%{y} clientes<extra></extra>",
        ))
        fig.add_vline(x=2.5, line_dash="dash", line_color=COR_VERMELHO,
                      annotation_text="< 30", annotation_position="top left",
                      annotation_font=dict(size=10, color=COR_VERMELHO))
        fig.add_vline(x=5.5, line_dash="dash", line_color=COR_VERDE,
                      annotation_text="≥ 60", annotation_position="top right",
                      annotation_font=dict(size=10, color=COR_VERDE))
        fig.update_layout(
            height=220, title_text="Distribuição do Índice de Prioridade",
            title_font=dict(size=12), title_x=0,
            margin=dict(t=40, b=40, l=50, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Faixa do Índice", tickfont=dict(size=10), gridcolor="#E2E8F0"),
            yaxis=dict(title="Clientes", gridcolor="#E2E8F0"),
            font=dict(family="Arial", size=11, color=COR_TEXTO),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False},
                        key="propensao_dist_chart")

    with col_tier:
        tier_counts = df_scores["tier"].value_counts()
        tier_order  = ["QUENTE", "MORNO", "FRIO", "DORMENTE"]
        tier_vals   = [tier_counts.get(t, 0) for t in tier_order]
        tier_colors = ["#EF4444", "#F59E0B", "#3B82F6", "#94A3B8"]
        tier_labels = [f"{TIER_CONFIG[t]['emoji']} {TIER_CONFIG[t]['label']}" for t in tier_order]

        fig2 = go.Figure(go.Bar(
            x=tier_labels, y=tier_vals,
            marker_color=tier_colors,
            marker_line=dict(color="rgba(0,0,0,0.1)", width=1),
            text=tier_vals, textposition="outside",
            textfont=dict(size=11, color=COR_TEXTO),
            hovertemplate="%{x}<br>%{y} clientes<extra></extra>",
        ))
        fig2.update_layout(
            height=220, title_text="Clientes por Tier de Recência",
            title_font=dict(size=12), title_x=0,
            margin=dict(t=40, b=40, l=30, r=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(size=11), gridcolor="#E2E8F0"),
            yaxis=dict(title="Clientes", gridcolor="#E2E8F0"),
            font=dict(family="Arial", size=11, color=COR_TEXTO),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True,
                        config={"displayModeBar": False},
                        key="propensao_tier_chart")


# ── Explicação do cálculo ─────────────────────────────────────────────────────
def _render_explicacao_score() -> None:
    with st.expander("ℹ️ Como o índice de prioridade é calculado?", expanded=False):
        st.markdown("""
> ⚠️ **Este índice NÃO é uma probabilidade de compra.**
> É um **índice de prioridade de contato comercial** — quanto maior, mais vale a
> pena ligar agora. Um cliente com índice 72 tem histórico e momento favoráveis,
> mas isso não significa 72% de chance de comprar.

---

**Índice de Prioridade = soma de 5 componentes (0–100 pts absolutos)**

| Componente | Máx | Fórmula |
|---|---|---|
| **Recência** | 30 | ≤30d=30 · ≤60d=20 · ≤90d=10 · ≤180d=5 · >180d=0 |
| **Frequência** | 25 | compras/mês × 60, clip 0-25 (ex: compra todo mês = 25 pts) |
| **Sazonalidade** | 15 | peso histórico da linha no mês atual |
| **Volume** | 20 | log(vol/mediana_linha) × 8.37, clip 0-20 |
| **Tendência** | 10 | vol_3m / (vol_12m÷4) × 5 — aceleração recente |

---

**Penalidade por recência (não ligar para quem acabou de comprar):**

| Intervalo | Fator | Razão |
|---|---|---|
| ≤ 7 dias | × 0,75 | Acabou de comprar esta semana |
| 8–30 dias | × 0,92 | No ciclo mensal |
| 31–100 dias | × 1,00 | Janela ideal de recompra |
| 101–180 dias | × 0,70 | Esfriando |
| > 180 dias | × 0,30 | Inativo |

---

**Tier de recência (cor do badge):**

🔥 **QUENTE** — comprou nos últimos 30 dias · 🌡️ **MORNO** — 31-100 dias
· 🧊 **FRIO** — 101-180 dias · 💤 **DORMENTE** — mais de 180 dias

---

**Flags especiais:**

| Flag | Significado |
|---|---|
| 🆕 **NOVO** | Primeira compra desta linha nos últimos 90 dias — cliente em fase de descoberta |
| ⚠️ **INDEFINIDO** | Linha com < 3 meses de histórico — score estatisticamente não confiável |

*Score calibrado em 251.717 pares cliente × linha · base Mai/2026*
        """)


# ── Tabela ranqueada ──────────────────────────────────────────────────────────
def _render_tabela(df_scores: pd.DataFrame, total_populacao: int) -> None:
    if df_scores.empty:
        st.markdown(
            '<div style="background:#F3F5F7;border-radius:10px;border-left:4px solid #9EA8B3;'
            'padding:20px 24px;color:#546E7A;">'
            '<strong>Nenhum cliente encontrado para os filtros selecionados.</strong><br>'
            '<span style="font-size:13px">Tente ampliar os filtros de Tier, Faixa do Índice '
            'ou aumentar o Top N.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Monta coluna Tier com flags NOVO e INDEFINIDO embutidos
    def _tier_com_flags(row) -> str:
        t    = row.get("tier", "DORMENTE")
        novo = row.get("flag_novo", False)
        ind  = row.get("flag_indefinido", False)
        sufixo = (" 🆕" if novo else "") + (" ⚠️" if ind else "")
        return t + sufixo

    tier_col  = df_scores.apply(_tier_com_flags, axis=1).values
    acao_col  = df_scores.apply(_gerar_acao_sugerida, axis=1).values

    # Nome do cliente: usa cliente_nome se disponível e diferente do código
    def _nome_cliente(row) -> str:
        nome = str(row.get("cliente_nome", "")).strip()
        cod  = str(row.get("cliente_id",   "")).strip()
        return nome if nome and nome != cod else cod

    # Telefone: formata ou retorna traço
    def _fmt_tel(t) -> str:
        v = str(t).strip() if pd.notna(t) else ""
        return v if v and v not in ("", "nan", "None") else "—"

    df_tab = pd.DataFrame({
        "Rank":             [f"#{i+1} / {total_populacao:,}" for i in range(len(df_scores))],
        "Nome":             df_scores.apply(_nome_cliente, axis=1).values,
        "Telefone":         (df_scores["telefone"].apply(_fmt_tel).values
                             if "telefone" in df_scores.columns
                             else ["—"] * len(df_scores)),
        "Linha":            df_scores["linha"].values,
        "Tier":             tier_col,
        "Índice":           df_scores["score_propensao"].round(1).values,
        "Ação Sugerida":    acao_col,
        "Última Compra":    df_scores["ultima_compra"].apply(_fmt_data).values,
        "Dias s/ Comprar":  df_scores["dias_sem_comprar"].values,
        "Vol. Méd./Mês":    df_scores["volume_medio_mensal"].apply(_fmt_ton).values,
        "Freq./Mês":        df_scores["frequencia_compras"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "—").values,
        "Motivo":           df_scores["motivo_score"].values,
    })

    _TIER_BG = {
        "QUENTE":   "#FEF0E6",
        "MORNO":    "#FDF5DC",
        "FRIO":     "#E8F2FB",
        "DORMENTE": "#F3F5F7",
    }

    def _style_row(row):
        tier = row["Tier"].split()[0] if row["Tier"] else "DORMENTE"
        bg   = _TIER_BG.get(tier, "#FFFFFF")
        try:
            score = float(row["Índice"])
        except Exception:
            score = 0
        score_cor = _cor_score(score)

        styles = []
        for c in row.index:
            if c == "Índice":
                styles.append(
                    f"background-color:{bg};color:{score_cor};font-weight:800;"
                    f"text-align:center;font-size:14px"
                )
            elif c == "Rank":
                styles.append(
                    f"background-color:{bg};font-weight:700;text-align:center;"
                    f"font-size:11px;color:#546E7A"
                )
            elif c == "Tier":
                tier_cor = TIER_CONFIG.get(tier, TIER_CONFIG["DORMENTE"])["cor_txt"]
                styles.append(
                    f"background-color:{bg};color:{tier_cor};font-weight:700;"
                    f"text-align:center;font-size:12px"
                )
            elif c == "Dias s/ Comprar":
                try:
                    dias = int(row[c])
                    d_cor = "#C0392B" if dias > 90 else "#8A6000" if dias > 45 else "#1A7A40"
                    styles.append(
                        f"background-color:{bg};color:{d_cor};font-weight:600;text-align:center"
                    )
                except Exception:
                    styles.append(f"background-color:{bg};text-align:center")
            elif c == "Ação Sugerida":
                styles.append(
                    f"background-color:{bg};font-size:11px;color:{COR_PRIMARIA};font-weight:600"
                )
            elif c in ("Motivo", "Fornecedor"):
                styles.append(f"background-color:{bg};font-size:11px;color:#546E7A")
            elif c in ("Freq./Mês", "Última Compra", "Vol. Méd./Mês"):
                styles.append(f"background-color:{bg};text-align:center")
            else:
                styles.append(f"background-color:{bg};text-align:left")
        return styles

    # Formata coluna Tier com emoji + label + flags
    def _fmt_tier(t: str) -> str:
        base = t.split()[0] if t else "DORMENTE"
        cfg  = TIER_CONFIG.get(base, TIER_CONFIG["DORMENTE"])
        rest = t[len(base):].strip()
        return f"{cfg['emoji']} {cfg['label']}{(' ' + rest) if rest else ''}"

    styled = (
        df_tab.style
        .apply(_style_row, axis=1)
        .set_table_styles([
            {"selector": "th", "props": [
                ("background-color", COR_PRIMARIA), ("color", "white"),
                ("font-size", "11px"), ("text-align", "center"), ("padding", "6px 8px"),
            ]},
        ])
        .format({"Tier": _fmt_tier, "Índice": lambda x: f"{x:.1f}"})
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=min(700, 42 + len(df_tab) * 36),
    )


# ── Gerador de e-mail para coordenadores ─────────────────────────────────────
def _gerar_email_coordenadores(df_scores: pd.DataFrame) -> str:
    hoje = date.today().strftime("%d/%m/%Y")
    linhas: list[str] = []

    gerencias = sorted(df_scores["gerencia"].dropna().unique()) if "gerencia" in df_scores.columns else [""]

    for ger in gerencias:
        if ger:
            df_ger = df_scores[df_scores["gerencia"] == ger]
        else:
            df_ger = df_scores

        if df_ger.empty:
            continue

        linhas.append("=" * 60)
        linhas.append(f"E-MAIL PARA: Coordenador(a) — {ger or 'Geral'}")
        linhas.append(f"Data: {hoje}")
        linhas.append("=" * 60)
        linhas.append("")
        linhas.append("Prezado(a) Coordenador(a),")
        linhas.append("")
        linhas.append(
            "Segue a lista de clientes prioritários para contato esta semana, "
            "separados por vendedor. Os clientes estão ordenados por índice de "
            "prioridade (maior = mais urgente)."
        )
        linhas.append("")

        vendedores = (
            df_ger.groupby("vendedor")["score_propensao"].max()
            .sort_values(ascending=False)
            .index.tolist()
            if "vendedor" in df_ger.columns
            else [""]
        )

        for vend in vendedores:
            df_v = df_ger[df_ger["vendedor"] == vend] if vend else df_ger
            df_v = df_v.sort_values("score_propensao", ascending=False)
            if df_v.empty:
                continue

            linhas.append("─" * 60)
            linhas.append(f"VENDEDOR: {vend or 'Sem vendedor'}")
            linhas.append("─" * 60)
            linhas.append("")

            for rank, (_, row) in enumerate(df_v.iterrows(), start=1):
                nome   = str(row.get("cliente_nome", row.get("cliente_id", "—")))
                score  = int(round(row.get("score_propensao", 0)))
                dias   = int(row.get("dias_sem_comprar", 0))
                tier   = row.get("tier", "")
                tel    = str(row.get("telefone", "")) or "sem telefone"
                acao   = _gerar_acao_sugerida(row)
                linha  = str(row.get("linha", ""))

                tier_emoji = {"QUENTE": "🔥", "MORNO": "🌡️", "FRIO": "🧊", "DORMENTE": "💤"}.get(tier, "")
                linhas.append(f"{rank}. {nome}")
                linhas.append(
                    f"   Score {score} | {tier_emoji} {dias} dias sem comprar | {linha}"
                )
                linhas.append(f"   Tel: {tel}")
                if acao:
                    linhas.append(f"   Ação: {acao}")
                linhas.append("")

        linhas.append("")

    linhas.append("─" * 60)
    linhas.append("Gerado automaticamente pelo Painel S&OE — Aço Cearense")
    linhas.append(f"Data de geração: {hoje}")

    return "\n".join(linhas)


# ── Exportação Excel ──────────────────────────────────────────────────────────
def _exportar_excel(df_scores: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df_exp = df_scores.copy()
    df_exp["acao_sugerida"] = df_exp.apply(_gerar_acao_sugerida, axis=1)
    df_exp["ultima_compra"] = df_exp["ultima_compra"].apply(
        lambda d: pd.Timestamp(d).strftime("%d/%m/%Y") if pd.notna(d) else ""
    )
    for c in ["score_bruto", "score_recencia", "score_frequencia",
              "score_sazonalidade", "score_volume", "score_tendencia"]:
        if c in df_exp.columns:
            df_exp.drop(columns=[c], inplace=True)
    df_exp.columns = [c.replace("_", " ").title() for c in df_exp.columns]
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_exp.to_excel(writer, index=False, sheet_name="Prioridade de Contato")
    return buf.getvalue()


# ── Função principal de renderização ─────────────────────────────────────────
def render(df_vendas: pd.DataFrame, filtros: dict) -> None:
    """
    Renderiza a aba de Prioridade de Contato.

    Parameters
    ----------
    df_vendas : DataFrame de vendas brutas (com cd_cliente)
    filtros   : dict com chaves empresas, regioes, ufs (filtros globais)
    """
    # ── Header ────────────────────────────────────────────────────
    st.markdown("""
    <div class="aba-header">
      <h2>🎯 Prioridade de Contato Comercial</h2>
      <p>Clientes ranqueados por índice de prioridade de contato — baseado em recência,
         frequência, sazonalidade, volume e tendência de compra.<br>
         <strong>⚠️ O índice indica quem ligar primeiro, não a probabilidade de compra.</strong>
         &nbsp;· 🔥 Quente: 0-30d &nbsp;· 🌡️ Morno: 31-100d &nbsp;· 🧊 Frio: 101-180d &nbsp;· 💤 Dormente: &gt;180d</p>
    </div>""", unsafe_allow_html=True)

    if df_vendas.empty:
        st.markdown(
            '<div style="background:#F3F5F7;border-radius:10px;border-left:4px solid #9EA8B3;'
            'padding:20px 24px;color:#546E7A;">'
            '<strong>Sem dados de vendas disponíveis.</strong><br>'
            '<span style="font-size:13px">Verifique se o pipeline de dados foi executado '
            '(<code>ATUALIZAR_E_RODAR.bat</code>) e se os filtros globais do painel não '
            'estão excluindo toda a base.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Filtros específicos da aba ────────────────────────────────
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2, 2, 1.5, 1.5, 1.5, 1])

    linhas_disp = sorted(df_vendas["linha"].dropna().unique().tolist())
    with col_f1:
        linha_sel = st.selectbox(
            "Linha de produto",
            options=["Todas"] + linhas_disp,
            key="propensao_linha",
        )

    regioes_disp = sorted(df_vendas["regiao"].dropna().unique().tolist())
    with col_f2:
        regiao_sel = st.selectbox(
            "Região",
            options=["Todas"] + regioes_disp,
            key="propensao_regiao",
        )

    ufs_disp = sorted(df_vendas["uf"].dropna().unique().tolist())
    with col_f3:
        uf_sel = st.selectbox(
            "UF",
            options=["Todas"] + ufs_disp,
            key="propensao_uf",
        )

    with col_f4:
        tier_sel = st.selectbox(
            "Tier (recência)",
            options=["Todos", "🔥 Quente", "🌡️ Morno", "🧊 Frio", "💤 Dormente"],
            key="propensao_tier",
            help="Filtra por tier de recência de compra",
        )

    with col_f5:
        faixa_sel = st.selectbox(
            "Faixa do índice",
            options=["Todas", "🟢 Alto (≥60)", "🟡 Médio (30–59)", "🔴 Baixo (<30)"],
            key="propensao_faixa",
            help="Filtra por faixa do índice de prioridade",
        )

    with col_f6:
        limite = st.number_input(
            "Top N",
            min_value=10, max_value=1000, value=100, step=10,
            key="propensao_limite",
        )

    linha_param  = None if linha_sel  == "Todas" else linha_sel
    regiao_param = None if regiao_sel == "Todas" else regiao_sel

    # ── Aplica filtros globais (empresa, região, UF do sidebar) ──────────────
    df_filt = df_vendas.copy()
    if filtros.get("empresas"):
        df_filt = df_filt[df_filt["empresa"].isin(filtros["empresas"])]
    if filtros.get("regioes"):
        df_filt = df_filt[df_filt["regiao"].isin(filtros["regioes"])]
    if filtros.get("ufs"):
        df_filt = df_filt[df_filt["uf"].isin(filtros["ufs"])]

    # Filtro de UF da aba (específico)
    if uf_sel != "Todas":
        df_filt = df_filt[df_filt["uf"] == uf_sel]

    if df_filt.empty:
        st.markdown(
            '<div style="background:#FEF0E6;border-radius:10px;border-left:4px solid #C0392B;'
            'padding:20px 24px;">'
            '<strong style="color:#C0392B">Nenhum dado para os filtros selecionados.</strong><br>'
            '<span style="font-size:13px;color:#546E7A">Ajuste os filtros de Empresa, '
            'Região ou UF no painel lateral.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Calcula scores com cache via session_state ────────────────
    with st.spinner("Calculando índice de prioridade..."):
        try:
            df_hash   = str(pd.util.hash_pandas_object(df_filt).sum())
            engine    = _get_engine(df_filt, df_hash)
            df_scores = engine.calcular_scores(
                linha=linha_param,
                regiao=regiao_param,
            )
        except Exception as e:
            st.error(f"Erro ao calcular índice: {e}")
            return

    if df_scores.empty:
        st.markdown(
            '<div style="background:#F3F5F7;border-radius:10px;border-left:4px solid #9EA8B3;'
            'padding:20px 24px;color:#546E7A;">'
            '<strong>Nenhum cliente encontrado para os filtros selecionados.</strong><br>'
            '<span style="font-size:13px">Tente selecionar "Todas" as linhas ou regiões.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    total_populacao = len(df_scores)

    # ── Aplica filtro de tier ANTES do head(N) ────────────────────
    tier_map = {
        "🔥 Quente":   "QUENTE",
        "🌡️ Morno":   "MORNO",
        "🧊 Frio":    "FRIO",
        "💤 Dormente": "DORMENTE",
    }
    if tier_sel != "Todos":
        df_scores = df_scores[df_scores["tier"] == tier_map.get(tier_sel, "")]

    # ── Aplica filtro de faixa ANTES do head(N) ──────────────────
    if faixa_sel == "🟢 Alto (≥60)":
        df_scores = df_scores[df_scores["score_propensao"] >= 60]
    elif faixa_sel == "🟡 Médio (30–59)":
        df_scores = df_scores[(df_scores["score_propensao"] >= 30) &
                               (df_scores["score_propensao"] < 60)]
    elif faixa_sel == "🔴 Baixo (<30)":
        df_scores = df_scores[df_scores["score_propensao"] < 30]

    if df_scores.empty:
        filtro_ativo = tier_sel if tier_sel != "Todos" else faixa_sel
        st.markdown(
            f'<div style="background:#F3F5F7;border-radius:10px;border-left:4px solid #9EA8B3;'
            f'padding:20px 24px;color:#546E7A;">'
            f'<strong>Nenhum cliente no filtro "{filtro_ativo}".</strong><br>'
            f'<span style="font-size:13px">Selecione "Todos" ou outro tier/faixa para '
            f'visualizar clientes.</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # Limita após os filtros
    df_scores = df_scores.head(int(limite))

    # ── Métricas resumo ───────────────────────────────────────────
    _render_metricas(df_scores, total_populacao)

    # ── Top Urgentes ──────────────────────────────────────────────
    _render_top_urgentes(df_scores)

    # ── Tabela ranqueada (superfície de ação principal) ───────────
    st.markdown('<div class="secao-titulo">Ranking de Prioridade de Contato</div>',
                unsafe_allow_html=True)
    _render_tabela(df_scores, total_populacao)

    # ── Exportação ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_exp, col_email, _ = st.columns([1, 1.5, 2])
    with col_exp:
        excel_bytes = _exportar_excel(df_scores)
        st.download_button(
            label="📥 Exportar Excel",
            data=excel_bytes,
            file_name=f"prioridade_contato_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="propensao_export",
        )
    with col_email:
        email_txt = _gerar_email_coordenadores(df_scores)
        st.download_button(
            label="📧 E-mail para Coordenadores",
            data=email_txt.encode("utf-8"),
            file_name=f"email_coordenadores_{date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            key="propensao_email",
            help="Gera um arquivo .txt com a lista de clientes por vendedor, "
                 "separada por gerência, pronto para encaminhar aos coordenadores.",
        )

    # ── Gráficos (secundários — em expander) ──────────────────────
    with st.expander("📊 Distribuição do Índice de Prioridade", expanded=False):
        _render_distribuicao(df_scores)

    # ── Explicação do cálculo (referência — ao final) ─────────────
    _render_explicacao_score()

    # ── Legenda ───────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:11px;color:#888;margin-top:8px;">'
        '🟢 Índice ≥ 60 — Alta prioridade &nbsp;&nbsp;'
        '🟡 Índice 30–59 — Média prioridade &nbsp;&nbsp;'
        '🔴 Índice &lt; 30 — Baixa prioridade &nbsp;&nbsp;|&nbsp;&nbsp;'
        '🔥 Quente (0-30d) · 🌡️ Morno (31-100d) · 🧊 Frio (101-180d) · 💤 Dormente (&gt;180d)'
        '</div>',
        unsafe_allow_html=True,
    )
