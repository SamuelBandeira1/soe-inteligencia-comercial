"""
Módulo: Dashboard UF — Desempenho por Estado

Renderiza:
  1. Mapa de bolhas do Brasil por UF (100% offline — coordenadas embutidas)
  2. Cards laterais: maiores riscos e melhores desempenhos
  3. Tabela detalhada por UF

Não depende de GeoJSON externo — usa Plotly Scattergeo com coordenadas
dos centróides de cada estado brasileiro.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from utils.visual import COR_PRIMARIA, COR_ACENTO, COR_GRID, COR_TEXTO, fmt_ton as _fmt_ton
except ImportError:
    COR_PRIMARIA = "#1B2A4A"
    COR_ACENTO   = "#F4822A"
    COR_GRID     = "#E9ECEF"
    COR_TEXTO    = "#2C3E50"
    def _fmt_ton(v): return f"{v:,.0f}"

# ── Centróides aproximados de cada UF (lat, lon) ──────────────────────────────
_UF_COORDS: dict[str, tuple[float, float]] = {
    "AC": (-9.02,  -70.81),  "AL": (-9.57,  -36.78),  "AM": (-3.47,  -65.10),
    "AP": ( 1.41,  -51.77),  "BA": (-12.96, -41.70),  "CE": (-5.50,  -39.32),
    "DF": (-15.78, -47.93),  "ES": (-19.58, -40.67),  "GO": (-15.83, -49.62),
    "MA": (-5.42,  -45.44),  "MG": (-18.51, -44.55),  "MS": (-20.77, -54.79),
    "MT": (-12.64, -55.42),  "PA": (-3.79,  -52.48),  "PB": (-7.12,  -36.72),
    "PE": (-8.38,  -37.86),  "PI": (-7.72,  -42.73),  "PR": (-24.89, -51.55),
    "RJ": (-22.25, -42.66),  "RN": (-5.81,  -36.59),  "RO": (-10.83, -63.34),
    "RR": ( 1.99,  -61.33),  "RS": (-30.17, -53.50),  "SC": (-27.45, -50.94),
    "SE": (-10.57, -37.45),  "SP": (-22.19, -48.79),  "TO": (-10.25, -48.25),
}

_NOME_UF: dict[str, str] = {
    "AC":"Acre",          "AL":"Alagoas",       "AM":"Amazonas",
    "AP":"Amapá",         "BA":"Bahia",          "CE":"Ceará",
    "DF":"Dist. Federal", "ES":"Espírito Santo", "GO":"Goiás",
    "MA":"Maranhão",      "MG":"Minas Gerais",   "MS":"Mato Grosso do Sul",
    "MT":"Mato Grosso",   "PA":"Pará",            "PB":"Paraíba",
    "PE":"Pernambuco",    "PI":"Piauí",           "PR":"Paraná",
    "RJ":"Rio de Janeiro","RN":"Rio Gr. do Norte","RO":"Rondônia",
    "RR":"Roraima",       "RS":"Rio Gr. do Sul",  "SC":"Santa Catarina",
    "SE":"Sergipe",       "SP":"São Paulo",        "TO":"Tocantins",
}

# Escala de cor contínua: vermelho → amarelo → verde
_COLORSCALE = [
    [0.000, '#C0392B'],   # 0%   — crítico
    [0.625, '#F59E0B'],   # 75%  — atenção
    [0.833, '#10B981'],   # 100% — meta
    [1.000, '#0D4A28'],   # 120%+ — excelente
]


def _ritmo_badge(v: float | None) -> str:
    if v is None or pd.isna(v): return "⚪"
    if v < 0.75: return "🔴"
    if v < 0.90: return "🟡"
    return "🟢"


def _fmt_pct(v, plus: bool = False) -> str:
    if v is None or pd.isna(v): return "—"
    return f"{v:+.1%}" if plus else f"{v:.1%}"


# ── Função principal ───────────────────────────────────────────────────────────
def render(
    por_reg: pd.DataFrame,
    col_meta_label: str,
    chart_key: str,
) -> None:
    if por_reg.empty:
        st.info("Sem dados de UF para o período selecionado.")
        return

    # ── Prepara DataFrame por UF ─────────────────────────────────────────────
    df = por_reg.copy()
    df["uf"] = df["uf"].str.upper().str.strip()

    df_uf = (
        df.groupby("uf")
        .agg(
            vol_real =("vol_real",  "sum"),
            meta_mes =("meta_mes",  "sum"),
            meta_acum=("meta_acum", "sum"),
            projecao =("projecao",  "sum"),
            gap_ton  =("gap_ton",   "sum"),
            regiao   =("regiao",    "first"),
        )
        .reset_index()
    )
    df_uf["ritmo_pct"] = df_uf.apply(
        lambda r: r["vol_real"] / r["meta_acum"] if r["meta_acum"] > 0 else None, axis=1
    )
    df_uf["gap_pct"] = df_uf.apply(
        lambda r: r["gap_ton"] / r["meta_mes"] if r["meta_mes"] > 0 else None, axis=1
    )
    df_uf["nome"] = df_uf["uf"].map(_NOME_UF).fillna(df_uf["uf"])
    df_uf = df_uf[df_uf["meta_mes"] > 0].copy()

    if df_uf.empty:
        st.info("Sem UFs com meta para o período selecionado.")
        return

    # ── Layout: mapa (esq) + cards (dir) ─────────────────────────────────────
    col_mapa, col_cards = st.columns([3, 2], gap="medium")

    with col_mapa:
        _render_mapa(df_uf, col_meta_label, chart_key)

    with col_cards:
        _render_risk_cards(df_uf)

    # ── Tabela ────────────────────────────────────────────────────────────────
    _render_tabela(df_uf, col_meta_label)


def _render_mapa(df_uf: pd.DataFrame, col_meta_label: str, chart_key: str) -> None:
    """Mapa de bolhas com Scattergeo — funciona offline."""
    rows = []
    for _, r in df_uf.iterrows():
        coords = _UF_COORDS.get(r["uf"])
        if coords is None:
            continue
        rows.append({
            "uf": r["uf"], "nome": r["nome"],
            "lat": coords[0], "lon": coords[1],
            "vol_real": r["vol_real"],
            "meta_acum": r["meta_acum"],
            "ritmo_pct": r["ritmo_pct"] if pd.notna(r["ritmo_pct"]) else 0.0,
            "gap_ton": r["gap_ton"],
        })

    if not rows:
        st.info("Nenhuma UF mapeada.")
        return

    dm = pd.DataFrame(rows)

    # Tamanho da bolha: raiz do volume para não deixar SP/MG gigantes
    vol_max = dm["vol_real"].max()
    if not vol_max or vol_max == 0:
        dm["bubble_size"] = 8.0
    else:
        dm["bubble_size"] = (dm["vol_real"] / vol_max) ** 0.5 * 40 + 8
    dm["bubble_size"] = dm["bubble_size"].fillna(8.0)

    hover = [
        (
            f"<b>{r['uf']} — {r['nome']}</b><br>"
            f"Ritmo: <b>{_fmt_pct(r['ritmo_pct'])}</b>  {_ritmo_badge(r['ritmo_pct'])}<br>"
            f"Realizado: {_fmt_ton(r['vol_real'])} ton<br>"
            f"Meta acum.: {_fmt_ton(r['meta_acum'])} ton<br>"
            f"Gap fech.: {'↑ ' if r['gap_ton'] > 0 else '✓ '}"
            f"{_fmt_ton(abs(r['gap_ton']))} ton"
        )
        for _, r in dm.iterrows()
    ]

    # Labels de UF: omite texto em bolhas pequenas (< 5% do volume máximo)
    vol_max_dm = dm['vol_real'].max() if not dm.empty else 1
    text_uf = [
        uf if dm.loc[i, 'vol_real'] > vol_max_dm * 0.05 else ''
        for i, uf in enumerate(dm['uf'])
    ]

    fig = go.Figure()

    # Bolhas coloridas por ritmo
    fig.add_trace(go.Scattergeo(
        lat=dm["lat"].tolist(),
        lon=dm["lon"].tolist(),
        mode="markers+text",
        marker=dict(
            size=dm["bubble_size"].tolist(),
            color=dm["ritmo_pct"].tolist(),
            colorscale=_COLORSCALE,
            cmin=0, cmax=1.20,
            colorbar=dict(
                title=dict(text="Ritmo", font=dict(size=11)),
                tickformat=".0%",
                tickfont=dict(size=10),
                len=0.65,
                thickness=10,
                x=0.95,
            ),
            line=dict(color="white", width=1.2),
            opacity=0.92,
        ),
        text=text_uf,
        textfont=dict(size=9, color="white", family="Arial Black"),
        textposition="middle center",
        hovertext=hover,
        hovertemplate="%{hovertext}<extra></extra>",
        name="",
    ))

    fig.update_geos(
        scope="south america",
        showland=True,
        landcolor="#F0F2F6",
        showocean=True,
        oceancolor="#EBF3FB",
        showcountries=True,
        countrycolor="#C8D0DC",
        showcoastlines=True,
        coastlinecolor="#B0BEC5",
        showsubunits=True,
        subunitcolor="#CFD8DC",
        projection_type="mercator",
        center=dict(lat=-14, lon=-53),
        lataxis_range=[-35, 6],
        lonaxis_range=[-75, -33],
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        height=560,
        margin=dict(t=4, b=28, l=4, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        geo_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", size=11, color=COR_TEXTO),
        showlegend=False,
        annotations=[dict(
            text=(
                f"<b>Tamanho</b> = volume realizado &nbsp;&nbsp;"
                f"<b>Cor</b> = ritmo vs meta acum."
            ),
            xref="paper", yref="paper",
            x=0.5, y=-0.02,
            showarrow=False,
            font=dict(size=10, color="#6C757D"),
            align="center",
        )],
    )

    st.plotly_chart(
        fig, use_container_width=True,
        config={"displayModeBar": False},
        key=f"mapa_bolhas_{chart_key}",
    )


def _render_risk_cards(df_uf: pd.DataFrame) -> None:
    """Cards laterais — riscos e destaques."""

    # ── Maiores gaps ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{COR_PRIMARIA};'
        f'margin-bottom:8px;padding-bottom:4px;border-bottom:2px solid #F5D5D1">'
        f'⚠️ Maiores gaps a fechar</div>',
        unsafe_allow_html=True,
    )

    df_risco = df_uf[df_uf["gap_ton"] > 0].sort_values("gap_ton", ascending=False).head(5)

    if df_risco.empty:
        st.markdown(
            '<div style="font-size:12px;color:#1A7A40;background:#F0FFF4;'
            'border-radius:6px;padding:8px 12px;">✅ Todas as UFs acima da meta acumulada!</div>',
            unsafe_allow_html=True,
        )
    else:
        for _, row in df_risco.iterrows():
            badge = _ritmo_badge(row["ritmo_pct"])
            ritmo = _fmt_pct(row["ritmo_pct"])
            gap   = _fmt_ton(row["gap_ton"])
            pct   = _fmt_pct(row["gap_pct"], plus=True) if pd.notna(row.get("gap_pct")) else ""

            cor_fundo = "#FFF5F5" if (row["ritmo_pct"] or 1) < 0.75 else "#FFFDE7"
            cor_borda = "#C0392B" if (row["ritmo_pct"] or 1) < 0.75 else "#B07D00"

            st.markdown(
                f'<div style="background:{cor_fundo};border-left:4px solid {cor_borda};'
                f'border-radius:0 6px 6px 0;padding:7px 10px;margin-bottom:5px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'  <span style="font-weight:700;font-size:13px;color:{COR_PRIMARIA}">'
                f'    {badge} {row["uf"]}</span>'
                f'  <span style="font-size:11px;font-weight:700;color:{cor_borda}">'
                f'    {ritmo}</span>'
                f'</div>'
                f'<div style="font-size:11px;color:#555;margin-top:2px">'
                f'  {row["nome"]} &nbsp;·&nbsp; faltam '
                f'  <b style="color:#C0392B">{gap} ton</b> {pct}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Melhores desempenhos ───────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:13px;font-weight:700;color:{COR_PRIMARIA};'
        f'margin:14px 0 8px 0;padding-bottom:4px;border-bottom:2px solid #D6EDE0">'
        f'🏆 Melhores desempenhos</div>',
        unsafe_allow_html=True,
    )

    df_dest = (
        df_uf[df_uf["ritmo_pct"].notna() & (df_uf["vol_real"] > 0)]
        .sort_values("ritmo_pct", ascending=False)
        .head(4)
    )

    for _, row in df_dest.iterrows():
        badge = _ritmo_badge(row["ritmo_pct"])
        ritmo = _fmt_pct(row["ritmo_pct"])
        vol   = _fmt_ton(row["vol_real"])
        cor_fundo = "#F0FFF4" if (row["ritmo_pct"] or 0) >= 0.90 else "#FFFDE7"
        cor_borda = "#1A7A40" if (row["ritmo_pct"] or 0) >= 0.90 else "#B07D00"

        st.markdown(
            f'<div style="background:{cor_fundo};border-left:4px solid {cor_borda};'
            f'border-radius:0 6px 6px 0;padding:7px 10px;margin-bottom:5px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'  <span style="font-weight:700;font-size:13px;color:{COR_PRIMARIA}">'
            f'    {badge} {row["uf"]}</span>'
            f'  <span style="font-size:13px;font-weight:800;color:{cor_borda}">'
            f'    {ritmo}</span>'
            f'</div>'
            f'<div style="font-size:11px;color:#555;margin-top:2px">'
            f'  {row["nome"]} &nbsp;·&nbsp; <b>{vol} ton</b> realizados'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_tabela(df_uf: pd.DataFrame, col_meta_label: str) -> None:
    """Tabela detalhada por estado com estilo."""

    with st.expander("📋 Ver tabela completa por estado", expanded=False):
        df_tab = df_uf.sort_values("vol_real", ascending=False).copy()

        tab = pd.DataFrame({
            "Status":         df_tab["ritmo_pct"].map(_ritmo_badge),
            "UF":             df_tab["uf"],
            "Estado":         df_tab["nome"],
            "Região":         df_tab["regiao"],
            "Realizado (t)":  df_tab["vol_real"].map("{:,.0f}".format),
            "Meta acum. (t)": df_tab["meta_acum"].map("{:,.0f}".format),
            "Ritmo":          df_tab["ritmo_pct"].map(
                                  lambda v: _fmt_pct(v) if pd.notna(v) else "—"),
            "Projeção (t)":   df_tab["projecao"].map("{:,.0f}".format),
            "Gap (t)":        df_tab["gap_ton"].map("{:+,.0f}".format),
            "Gap (%)":        df_tab["gap_pct"].map(
                                  lambda v: _fmt_pct(v, plus=True) if pd.notna(v) else "—"),
        })

        def _style(row):
            styles = []
            for col in row.index:
                if col in ("Status", "Ritmo"):
                    try:
                        rp = df_tab[df_tab["uf"] == row["UF"]]["ritmo_pct"].values[0]
                        if rp is None or pd.isna(rp):
                            styles.append("text-align:center")
                        elif rp < 0.75:
                            styles.append("background:#F5D5D1;color:#C0392B;font-weight:700;text-align:center")
                        elif rp < 0.90:
                            styles.append("background:#F5E9C8;color:#C0392B;font-weight:700;text-align:center")
                        else:
                            styles.append("background:#D6EDE0;color:#1A7A40;font-weight:700;text-align:center")
                    except Exception:
                        styles.append("text-align:center")
                elif col in ("Gap (t)", "Gap (%)"):
                    try:
                        gv = float(str(row[col]).replace(",","").replace("+","").replace("%","").strip())
                        if gv > 0:
                            styles.append("color:#C0392B;font-weight:600;text-align:right")
                        elif gv < 0:
                            styles.append("color:#1A7A40;font-weight:600;text-align:right")
                        else:
                            styles.append("text-align:right")
                    except Exception:
                        styles.append("text-align:right")
                elif col in ("UF", "Estado", "Região"):
                    styles.append("font-weight:600;text-align:left")
                else:
                    styles.append("text-align:right")
            return styles

        styled = (
            tab.style
            .apply(_style, axis=1)
            .set_properties(**{"font-size": "12px", "padding": "5px 8px"})
            .set_table_styles([
                {"selector": "th", "props": [
                    ("background-color", COR_PRIMARIA), ("color", "white"),
                    ("font-size", "11px"), ("text-align", "center"),
                    ("padding", "7px 8px"),
                ]},
                {"selector": "th.row_heading", "props": [("display", "none")]},
            ])
        )

        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=min(560, 44 + len(tab) * 36),
        )
