"""
Módulo "Plano & Ação Semanal" — Aba 3 (unificada)

Substitui as antigas abas "Prioridade de Contato" (aba3) e
"Plano Comercial Semanal" (aba4) com uma visão integrada:

Seção A  Lista de ação da semana selecionada (default: semana atual)
Seção B  Gráfico de horizonte de volume — clique filtra Seção A
Seção C  What-If Simulator (Zona Líquida apenas)

Design system
─────────────
• Grid de 8px — padding mínimo 16px, gap entre seções 24px
• Tipografia: peso 800 títulos, 700 labels, 400 corpo
• Cores semânticas: verde=#1A7A40, âmbar=#B07D00, vermelho=#C0392B, azul=#1B4F8A
• Nulos tratados explicitamente em toda função de cálculo
"""
from __future__ import annotations

import html as _html
import re as _re
import warnings
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engines.potencial_engine import PotencialSemanalEngine
from engines.propensao_engine import PropensaoEngine
from engines.sazonalidade_semanal import SemanalPropensaoEngine
from modules.plano_comercial import (
    _horizonte_semanas,
    _zone,
    _graf_horizonte,
    _render_whatiif,
    _calc_desvios,
    _render_alertas_desvio,
    _legenda_zonas,
    IDX_ZONE_FROZEN,
    IDX_ZONE_LIQUID,
    N_PASSADO,
    THRESHOLD_DESVIO,
)
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_TEXTO, fmt_ton as _fmt_ton,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════════════════════════════

_ENGINE_VERSION = "acao_v1"

# HC2 — mapeamento zona → ação sugerida
_ZONE_ACTION: dict[str, str] = {
    "frozen": "Confirmar pedido ou rastrear entrega",
    "liquid": "Negociar volume ou simular what-if",
    "fluid":  "Qualificar interesse ou prospectar",
}

_ZONE_LABEL: dict[str, str] = {
    "frozen": "Congelada",
    "liquid": "Líquida",
    "fluid":  "Fluida",
    "past":   "Histórico",
}

_ZONE_BADGE_EMOJI: dict[str, str] = {
    "frozen": "🔒",
    "liquid": "🔄",
    "fluid":  "📡",
    "past":   "◀",
}

# Cores de cabeçalho por zona (C1 — impossível misturar visualmente)
_ZONE_HEADER_BG: dict[str, str] = {
    "frozen": "#FEF2F2",   # vermelho suave
    "liquid": "#F0FDF4",   # verde suave
    "fluid":  "#F0F4FF",   # azul acinzentado
    "past":   "#F8FAFC",   # cinza neutro
}
_ZONE_HEADER_BORDER: dict[str, str] = {
    "frozen": "#C0392B",
    "liquid": "#1A7A40",
    "fluid":  "#546E7A",
    "past":   "#90A4AE",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Funções puras exportadas (testáveis sem Streamlit)
# ═══════════════════════════════════════════════════════════════════════════════

def _badge_zona(zona: str) -> str:
    """Retorna badge de texto com emoji para a zona operacional."""
    emoji = _ZONE_BADGE_EMOJI.get(zona, "?")
    label = _ZONE_LABEL.get(zona, zona.capitalize())
    return f"{emoji} {label}"


def _gerar_motivo_potencial(row: dict, n_meses: int = 8) -> str:
    """
    Gera texto auditable de explicação do flag_potencial_semana (AC-P2-7).

    Drivers:
    - n_meses_comprou / n_meses
    - historico_datas (última data)
    - vol_medio_semana
    - score_sazonalidade (ou '—⚠️' se flag_sazon_insuficiente)
    """
    n_comprou   = int(row.get("n_meses_comprou", 0) or 0)
    pct         = float(row.get("pct_meses", 0.0) or 0.0)
    vol         = float(row.get("vol_medio_semana", 0.0) or 0.0)
    _raw_datas  = row.get("historico_datas")
    datas       = _raw_datas if isinstance(_raw_datas, list) else []
    insuf       = bool(row.get("flag_sazon_insuficiente", False))
    saz_val     = row.get("score_sazonalidade")

    partes: list[str] = [
        f"Comprou nesta semana em {n_comprou}/{n_meses} meses ({pct:.0%})",
    ]

    if datas:
        ultima = datas[0]
        if hasattr(ultima, "strftime"):
            partes.append(f"Última compra nesta semana: {ultima.strftime('%d/%m/%Y')}")
        else:
            partes.append(f"Última compra nesta semana: {ultima}")

    if vol > 0:
        partes.append(f"Vol. médio na semana: {vol:.1f} ton")

    if insuf or saz_val is None or (isinstance(saz_val, float) and np.isnan(saz_val)):
        partes.append("Sazonalidade: —⚠️ (histórico insuficiente)")
    else:
        partes.append(f"Índice de sazonalidade: {float(saz_val):.1f}")

    return " · ".join(partes)


def _truncar_email_vendedor(
    df_vend: pd.DataFrame,
    limit: int = 10,
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Limita df_vend a `limit` clientes por score_propensao desc (AC-P2-9).

    Returns
    -------
    (df_truncado, nota_str | None)
    """
    if df_vend.empty:
        return df_vend, None

    df_sorted = df_vend.sort_values("score_propensao", ascending=False)
    total = len(df_sorted)
    if total <= limit:
        return df_sorted.reset_index(drop=True), None

    nota = f"(mostrando 10 de {total} clientes — prioridade mais alta)"
    return df_sorted.head(limit).reset_index(drop=True), nota


def generate_email_text(
    df_scores: pd.DataFrame,
    semana_label: str,
    zona: str,
    gerencia_sel: str,
    alertas: list[dict],
) -> str:
    """
    Gera o corpo do e-mail de ação semanal (AC-P2-8).

    Estrutura:
    1. Cabeçalho (referência, zona, gerência, data)
    2. Metas por linha (se disponível em df_scores)
    3. Alertas de desvio
    4. Clientes por vendedor (máx 10 por vendedor — AC-P2-9)
    """
    zona_label = _ZONE_LABEL.get(zona, zona.capitalize())
    hoje_str   = date.today().strftime("%d/%m/%Y")

    linhas: list[str] = [
        "=== PLANO DE AÇÃO SEMANAL ===",
        f"Semana de referência: {semana_label} | Zona: {zona_label}",
        f"Gerência: {gerencia_sel} | Data de geração: {hoje_str}",
        "",
    ]

    # ── Alertas de Desvio ─────────────────────────────────────────────────────
    if alertas:
        linhas.append("--- Alertas de Desvio ---")
        for alerta in alertas:
            linha_a = alerta.get("linha", "?")
            gap     = alerta.get("gap_pct", 0.0)
            meta    = alerta.get("meta", 0.0)
            est     = alerta.get("estimada", 0.0)
            sinal   = "⬆" if gap > 0 else "⬇"
            linhas.append(
                f"  {sinal} {linha_a}: Meta={_fmt_ton(meta)}t | "
                f"Histórico={_fmt_ton(est)}t | Desvio={gap:.0%}"
            )
        linhas.append("")

    # ── Clientes por vendedor ─────────────────────────────────────────────────
    if df_scores.empty:
        linhas.append("=== CLIENTES POR VENDEDOR ===")
        linhas.append("  (nenhum cliente encontrado para esta seleção)")
        return "\n".join(linhas)

    linhas.append("=== CLIENTES POR VENDEDOR ===")

    vendedores = sorted(df_scores["vendedor"].dropna().unique())
    for vend in vendedores:
        df_v = df_scores[df_scores["vendedor"] == vend].copy()
        df_v_trunc, nota = _truncar_email_vendedor(df_v)
        linhas.append(f"\nVENDEDOR: {vend}")
        if nota:
            linhas.append(f"  {nota}")

        for rank, (_, row) in enumerate(df_v_trunc.iterrows(), start=1):
            nome  = row.get("cliente_nome", row.get("cliente_id", "?"))
            score = float(row.get("score_propensao", 0) or 0)
            tier  = row.get("tier", "—")
            tel   = row.get("telefone", "—") or "—"
            zona_cli = _ZONE_LABEL.get(str(row.get("zona", zona)), zona_label)
            pot  = row.get("flag_potencial_semana", False)
            n_mc = int(row.get("n_meses_comprou", 0) or 0)
            pct  = float(row.get("pct_meses", 0.0) or 0.0)
            acao = row.get("acao_sugerida", _ZONE_ACTION.get(zona, "—"))

            # Por que potencial — linha única para o email
            motivo_row = {
                "n_meses_comprou": n_mc,
                "pct_meses": pct,
                "vol_medio_semana": float(row.get("vol_medio_semana", 0.0) or 0.0),
                "historico_datas": row.get("historico_datas") or [],
                "score_sazonalidade": row.get("score_sazonalidade"),
                "flag_sazon_insuficiente": bool(row.get("flag_sazon_insuficiente", False)),
            }
            motivo = _gerar_motivo_potencial(motivo_row)
            pot_str = f"⭐ SIM — comprou {n_mc}/8 meses" if pot else "NÃO"

            linhas.extend([
                f"  {rank}. {nome} | Score: {score:.0f} | Tier: {tier} | "
                f"Zona: {zona_cli} | Tel: {tel}",
                f"     Potencial: {pot_str}",
                f"     Ação: {acao}",
                f"     Por que: {motivo}",
            ])

    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════════════════════
# Cache de engines
# ═══════════════════════════════════════════════════════════════════════════════

def _get_engines(df_v: pd.DataFrame, df_hash: str):
    kp = f"_acao_prop_{_ENGINE_VERSION}_{df_hash}"
    ks = f"_acao_sem_{_ENGINE_VERSION}_{df_hash}"
    for k in list(st.session_state):
        if k.startswith(("_acao_prop_", "_acao_sem_")) and k not in (kp, ks):
            del st.session_state[k]
    if kp not in st.session_state:
        st.session_state[kp] = PropensaoEngine(df_v)
    if ks not in st.session_state:
        st.session_state[ks] = SemanalPropensaoEngine(df_v)
    return st.session_state[kp], st.session_state[ks]


def _get_potencial_engine(df_v: pd.DataFrame, df_hash: str) -> PotencialSemanalEngine:
    k = f"_acao_potencial_{_ENGINE_VERSION}_{df_hash}"
    for old in list(st.session_state):
        if old.startswith("_acao_potencial_") and old != k:
            del st.session_state[old]
    if k not in st.session_state:
        st.session_state[k] = PotencialSemanalEngine(df_v)
    return st.session_state[k]


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F1 — Filtros obrigatórios
# ═══════════════════════════════════════════════════════════════════════════════

def _render_filtros_obrigatorios(
    df_v_raw: pd.DataFrame,
    filtros_globais: dict,
) -> tuple[str, str]:
    """
    Renderiza os selectboxes obrigatórios de gerência e vendedor.

    Retorna (gerencia_sel, vendedor_sel). Nunca retorna None.
    """
    col_ger, col_vend = st.columns([1, 1])

    # ── Gerências disponíveis ─────────────────────────────────────────────────
    ger_col = "gerencia_efetiva" if "gerencia_efetiva" in df_v_raw.columns else "gerencia"
    if ger_col in df_v_raw.columns:
        gerencias = sorted(df_v_raw[ger_col].dropna().unique().tolist())
    else:
        gerencias = ["(Geral)"]
    if not gerencias:
        gerencias = ["(Geral)"]

    with col_ger:
        gerencia_sel = st.selectbox(
            "🏢 Gerência",
            options=gerencias,
            index=0,
            key="acao_gerencia_sel",
        )

    # ── Vendedores dentro da gerência ─────────────────────────────────────────
    if ger_col in df_v_raw.columns and "vendedor" in df_v_raw.columns:
        df_ger = df_v_raw[df_v_raw[ger_col] == gerencia_sel]
        vendedores = ["Todos"] + sorted(df_ger["vendedor"].dropna().unique().tolist())
    else:
        vendedores = ["Todos"]

    with col_vend:
        vendedor_sel = st.selectbox(
            "👤 Vendedor",
            options=vendedores,
            index=0,
            key="acao_vendedor_sel",
        )

    return gerencia_sel, vendedor_sel


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F2 — Tabela de clientes com colunas especificadas
# ═══════════════════════════════════════════════════════════════════════════════

def _build_client_df(
    scores: pd.DataFrame,
    potencial: pd.DataFrame,
    zona: str,
    vendedor_sel: str,
) -> pd.DataFrame:
    """
    Junta scores + potencial e retorna df com as colunas da spec (AC-P2-5).

    Colunas de saída:
      Rank, Nome, Telefone, Zona, ⭐ Potencial, Score (score_propensao),
      Tier, Última Compra, Dias s/ Comprar, Vol. Méd./Mês,
      Por que potencial, Ação sugerida, Vendedor
    """
    if scores.empty:
        return pd.DataFrame()

    # Filtra por vendedor
    if vendedor_sel != "Todos" and "vendedor" in scores.columns:
        scores = scores[scores["vendedor"] == vendedor_sel].copy()

    if scores.empty:
        return pd.DataFrame()

    # Garante que cliente_id é string para join
    scores = scores.copy()
    scores["cliente_id"] = scores["cliente_id"].astype(str)

    if not potencial.empty:
        potencial = potencial.copy()
        potencial["cd_cliente"] = potencial["cd_cliente"].astype(str)
        scores = scores.merge(
            potencial[[
                "cd_cliente", "linha", "flag_potencial_semana",
                "n_meses_comprou", "pct_meses", "vol_medio_semana", "historico_datas",
            ]],
            left_on=["cliente_id", "linha"],
            right_on=["cd_cliente", "linha"],
            how="left",
        ).drop(columns=["cd_cliente"], errors="ignore")
    else:
        scores["flag_potencial_semana"] = False
        scores["n_meses_comprou"]       = 0
        scores["pct_meses"]             = 0.0
        scores["vol_medio_semana"]      = 0.0
        scores["historico_datas"]       = None

    scores["flag_potencial_semana"] = scores["flag_potencial_semana"].fillna(False)
    scores["n_meses_comprou"]       = scores["n_meses_comprou"].fillna(0).astype(int)
    scores["pct_meses"]             = scores["pct_meses"].fillna(0.0)
    scores["vol_medio_semana"]      = scores["vol_medio_semana"].fillna(0.0)

    # Zona (mesma para todos nesta visão — determinada pela semana selecionada)
    scores["zona"]         = zona
    scores["zona_badge"]   = scores["zona"].apply(_badge_zona)
    scores["acao_sugerida"] = _ZONE_ACTION.get(zona, "—")

    # Por que potencial (linha única por cliente)
    scores["por_que_potencial"] = scores.apply(
        lambda r: _gerar_motivo_potencial({
            "n_meses_comprou": r.get("n_meses_comprou", 0),
            "pct_meses": r.get("pct_meses", 0.0),
            "vol_medio_semana": r.get("vol_medio_semana", 0.0),
            "historico_datas": r.get("historico_datas") or [],
            "score_sazonalidade": r.get("score_sazonalidade"),
            "flag_sazon_insuficiente": bool(r.get("flag_sazon_insuficiente", False)),
        }), axis=1
    )

    # Rank 1-based dentro do resultado
    scores = scores.sort_values("score_propensao", ascending=False).reset_index(drop=True)
    scores["rank"] = range(1, len(scores) + 1)

    return scores


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F3 — Decomposição de score (score drawer)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_score_decomposicao(engine: PropensaoEngine, cliente_id: str, linha: str) -> None:
    """
    Renderiza os 5 componentes de score em um st.expander (AC-P2-6).
    Se flag_sazon_insuficiente: exibe '—⚠️' na sazonalidade (AC-P2-12).
    """
    decomp = engine.get_decomposition(cliente_id, linha)
    if decomp is None:
        st.caption("Dados de decomposição não disponíveis.")
        return

    insuf = decomp.get("flag_sazon_insuficiente", False)
    saz   = decomp.get("score_sazonalidade")
    saz_str = "—⚠️ insuficiente" if (insuf or saz is None) else f"{saz:.1f}"

    componentes = [
        ("Recência",     decomp.get("score_recencia"),    30, "0-30 dias → 30 pts"),
        ("Frequência",   decomp.get("score_frequencia"),  25, "compras/mês × 60, clip 25"),
        ("Sazonalidade", saz,                             15, "padrão mensal da linha"),
        ("Volume",       decomp.get("score_volume"),      20, "log1p(vol/mediana) × 8.37"),
        ("Tendência",    decomp.get("score_tendencia"),   10, "vol_3m / (vol_12m/4) × 5"),
    ]

    st.markdown(
        f'<div style="font-size:11px;color:#546E7A;margin-bottom:8px;">'
        f'Score total: <b>{decomp.get("score_propensao", 0):.1f}</b> / 100</div>',
        unsafe_allow_html=True,
    )

    for nome, valor, peso_max, descr in componentes:
        if nome == "Sazonalidade":
            v_str = saz_str
            pct   = 0 if (insuf or valor is None) else min(valor / peso_max, 1.0)
        else:
            v_str = f"{valor:.1f}" if valor is not None else "—"
            pct   = 0 if valor is None else min(valor / peso_max, 1.0)
        cor = "#1A7A40" if pct > 0.6 else "#B07D00" if pct > 0.3 else "#C0392B"
        bar_w = int(pct * 100)
        st.markdown(
            f'<div style="margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:11px;font-weight:700;color:#2C3E50;">'
            f'<span>{nome}</span>'
            f'<span style="color:{cor};">{v_str} / {peso_max}</span></div>'
            f'<div style="background:#E8EDF2;border-radius:4px;height:6px;margin-top:2px;">'
            f'<div style="width:{bar_w}%;background:{cor};border-radius:4px;height:6px;"></div>'
            f'</div>'
            f'<div style="font-size:10px;color:#90A4AE;">{descr}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F7 — Email staging flow
# ═══════════════════════════════════════════════════════════════════════════════

def _render_email_flow(
    df_scores: pd.DataFrame,
    semana_label: str,
    zona: str,
    gerencia_sel: str,
    alertas: list[dict],
) -> None:
    """
    State machine: idle → rascunho → aprovado (AC-P2-8).
    st.download_button aparece SOMENTE no estado 'aprovado'.
    """
    st.markdown(
        '<div style="margin-top:24px;padding-top:16px;'
        'border-top:1px solid #E0E7EF;">'
        '<span style="font-size:14px;font-weight:800;color:#2C3E50;">'
        '📧 E-mail de Ação para Coordenadores</span></div>',
        unsafe_allow_html=True,
    )

    estado = st.session_state.get("acao_email_estado", "idle")

    if estado == "idle":
        if st.button("✉️ Gerar e-mail para revisão", key="acao_email_gerar"):
            texto = generate_email_text(
                df_scores=df_scores,
                semana_label=semana_label,
                zona=zona,
                gerencia_sel=gerencia_sel,
                alertas=alertas,
            )
            st.session_state["acao_email_texto"]  = texto
            st.session_state["acao_email_estado"] = "rascunho"
            st.rerun()

    elif estado == "rascunho":
        st.info(
            "📋 **Rascunho gerado.** Revise o conteúdo abaixo. "
            "Você pode editar antes de aprovar.",
            icon="📝",
        )
        texto_editado = st.text_area(
            "Conteúdo do e-mail (editável)",
            value=st.session_state.get("acao_email_texto", ""),
            height=400,
            key="acao_email_textarea",
        )
        st.session_state["acao_email_texto"] = texto_editado

        col_ap, col_cancel = st.columns([1, 1])
        with col_ap:
            if st.button("✅ Aprovar e baixar", key="acao_email_aprovar", type="primary"):
                st.session_state["acao_email_estado"] = "aprovado"
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancelar", key="acao_email_cancelar"):
                st.session_state["acao_email_estado"] = "idle"
                st.session_state.pop("acao_email_texto", None)
                st.rerun()

    elif estado == "aprovado":
        st.success("✅ E-mail aprovado. Clique abaixo para baixar.")
        texto_final  = st.session_state.get("acao_email_texto", "")
        zona_label   = _ZONE_LABEL.get(zona, zona)
        _ger_safe    = _re.sub(r"[^\w\-]", "_", gerencia_sel)
        _sem_safe    = _re.sub(r"[^\w\-]", "_", semana_label)
        _zona_safe   = _re.sub(r"[^\w\-]", "_", zona_label)
        nome_arquivo = f"acao_semanal_{_ger_safe}_{_sem_safe}_zona{_zona_safe}.txt"
        st.download_button(
            label="⬇️ Baixar e-mail (.txt)",
            data=texto_final.encode("utf-8"),
            file_name=nome_arquivo,
            mime="text/plain",
            key="acao_email_download",
        )
        if st.button("🔄 Novo e-mail", key="acao_email_novo"):
            st.session_state["acao_email_estado"] = "idle"
            st.session_state.pop("acao_email_texto", None)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F4 — KPIs da semana
# ═══════════════════════════════════════════════════════════════════════════════

def _render_kpis_semana(df: pd.DataFrame) -> None:
    if df.empty:
        return
    total  = len(df)
    n_pot  = int(df["flag_potencial_semana"].sum()) if "flag_potencial_semana" in df.columns else 0
    pct_p  = n_pot / total if total else 0.0
    score_med = float(df["score_propensao"].mean()) if "score_propensao" in df.columns else 0.0

    col_total, col_pot, col_score_med = st.columns(3)
    with col_total:
        st.metric("Clientes na lista", total)
    with col_pot:
        st.metric("⭐ Com padrão confirmado", n_pot, f"{pct_p:.0%}")
    with col_score_med:
        st.metric("Score médio (Índice de Prioridade)", f"{score_med:.1f}")


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F5 — Top-5 cards
# ═══════════════════════════════════════════════════════════════════════════════

def _render_top5_cards(df: pd.DataFrame, zona: str) -> None:
    if df.empty:
        return
    top5 = df.head(5)
    bg   = _ZONE_HEADER_BG.get(zona, "#F8FAFC")
    border_col = _ZONE_HEADER_BORDER.get(zona, "#90A4AE")

    cols = st.columns(min(len(top5), 5))
    for col, (_, row) in zip(cols, top5.iterrows()):
        pot_badge  = "⭐ " if row.get("flag_potencial_semana") else ""
        tier       = row.get("tier", "DORMENTE")
        score      = float(row.get("score_propensao", 0) or 0)
        nome       = str(row.get("cliente_nome", row.get("cliente_id", "?")))
        nome_short = nome[:20] + "…" if len(nome) > 20 else nome
        _nome_short_e = _html.escape(nome_short)
        _tier_e       = _html.escape(str(tier))
        with col:
            st.markdown(
                f'<div style="background:{bg};border-left:4px solid {border_col};'
                f'border-radius:0 8px 8px 0;padding:10px 12px;margin-bottom:8px;">'
                f'<div style="font-size:11px;font-weight:800;color:#2C3E50;">'
                f'{pot_badge}{_nome_short_e}</div>'
                f'<div style="font-size:20px;font-weight:800;color:{border_col};">'
                f'{score:.0f}</div>'
                f'<div style="font-size:10px;color:#78909C;">{_tier_e}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F2 — Render da tabela de clientes
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tabela_clientes(
    df: pd.DataFrame,
    engine: PropensaoEngine,
    zona: str,
) -> None:
    """Renderiza tabela de clientes com expanders de decomposição (AC-P2-6)."""
    if df.empty:
        st.info(
            "Nenhum cliente encontrado para a seleção atual. "
            "Verifique os filtros de gerência e vendedor.",
        )
        return

    n_pot = int(df["flag_potencial_semana"].sum()) if "flag_potencial_semana" in df.columns else 0
    if n_pot == 0:
        st.info("ℹ️ Nenhum cliente com padrão confirmado nesta semana.")

    # Cabeçalho da tabela
    st.markdown(
        f'<div style="font-size:12px;font-weight:700;color:#78909C;'
        f'text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">'
        f'{len(df)} clientes · ordenado por Índice de Prioridade ↓</div>',
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():
        nome       = str(row.get("cliente_nome", row.get("cliente_id", "?")))
        cliente_id = str(row.get("cliente_id", ""))
        linha      = str(row.get("linha", ""))
        score      = float(row.get("score_propensao", 0) or 0)
        tier       = row.get("tier", "DORMENTE")
        tel        = row.get("telefone", "") or "—"
        pot        = bool(row.get("flag_potencial_semana", False))
        vend       = row.get("vendedor", "") or "—"
        dias       = int(row.get("dias_sem_comprar", 0) or 0)
        vol        = float(row.get("volume_medio_mensal", 0.0) or 0.0)
        uc         = row.get("ultima_compra")
        uc_str     = pd.Timestamp(uc).strftime("%d/%m/%Y") if pd.notna(uc) else "—"
        acao       = row.get("acao_sugerida", _ZONE_ACTION.get(zona, "—"))
        motivo     = row.get("por_que_potencial", "")

        pot_badge  = "⭐ " if pot else ""
        zona_badge = _badge_zona(zona)
        bg         = _ZONE_HEADER_BG.get(zona, "#F8FAFC")
        border_col = _ZONE_HEADER_BORDER.get(zona, "#90A4AE")

        # Score color
        score_cor = "#059669" if score >= 60 else "#D97706" if score >= 30 else "#DC2626"

        with st.expander(
            f"#{int(row.get('rank', 0))} {pot_badge}{nome} — "
            f"Score: {score:.0f} | {tier} | {zona_badge}",
            expanded=False,
        ):
            col_info, col_decomp = st.columns([2, 1])

            with col_info:
                _nome_e   = _html.escape(str(nome))
                _tel_e    = _html.escape(str(tel))
                _vend_e   = _html.escape(str(vend))
                _linha_e  = _html.escape(str(linha))
                _acao_e   = _html.escape(str(acao))
                _motivo_e = _html.escape(str(motivo))
                st.markdown(
                    f'<div style="background:{bg};border-left:4px solid {border_col};'
                    f'border-radius:0 8px 8px 0;padding:12px 16px;">'
                    f'<div style="font-size:13px;font-weight:700;color:#2C3E50;">'
                    f'{pot_badge}{_nome_e}</div>'
                    f'<div style="font-size:11px;color:#546E7A;margin-top:4px;">'
                    f'📞 {_tel_e} &nbsp;·&nbsp; 👤 {_vend_e} &nbsp;·&nbsp; 📦 {_linha_e}</div>'
                    f'<div style="font-size:11px;color:#546E7A;margin-top:4px;">'
                    f'Última compra: {uc_str} ({dias} dias atrás) &nbsp;·&nbsp; '
                    f'Vol. médio: {vol:.1f} ton/mês</div>'
                    f'<div style="font-size:11px;color:{score_cor};font-weight:700;margin-top:6px;">'
                    f'Índice de Prioridade: {score:.1f}</div>'
                    f'<div style="font-size:11px;color:#2C3E50;margin-top:6px;font-weight:700;">'
                    f'Ação: {_acao_e}</div>'
                    f'<div style="font-size:10px;color:#90A4AE;margin-top:4px;">'
                    f'{_motivo_e}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_decomp:
                st.markdown(
                    '<div style="font-size:11px;font-weight:700;color:#546E7A;'
                    'margin-bottom:6px;">Decomposição do Score</div>',
                    unsafe_allow_html=True,
                )
                _render_score_decomposicao(engine, cliente_id, linha)


# ═══════════════════════════════════════════════════════════════════════════════
# P2-F8 — What-If gate
# ═══════════════════════════════════════════════════════════════════════════════

def _render_whatiif_section(
    horizonte: list[dict],
    df_f: pd.DataFrame,
    gerencia_sel: str,
    semana_sel_idx: int,
    zona: str,
) -> None:
    st.markdown(
        '<div style="margin-top:24px;padding-top:16px;'
        'border-top:1px solid #E0E7EF;">'
        '<span style="font-size:14px;font-weight:800;color:#2C3E50;">'
        '🛠️ Simulador What-If</span></div>',
        unsafe_allow_html=True,
    )

    if zona != "liquid":
        st.markdown(
            '<div style="background:#FEF2F2;border-left:4px solid #C0392B;'
            'border-radius:0 8px 8px 0;padding:14px 18px;">'
            '🔒 <b>What-If bloqueado.</b> '
            'Selecione uma semana na <b>Zona Líquida</b> para simular ajustes. '
            '(Zonas Congelada, Fluida e semanas passadas não permitem simulação.)'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Zona Líquida — renderiza o what-if importado
    _render_whatiif(
        horizonte=horizonte,
        df_f=df_f,
        gerencia_sel=gerencia_sel,
        semana_sel_idx=semana_sel_idx,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# P2 — render() principal
# ═══════════════════════════════════════════════════════════════════════════════

def render(
    df_f: pd.DataFrame,
    df_v_raw: pd.DataFrame,
    filtros: dict,
    semana_atual: int,
    ano_sel: int,
    mes_sel: int,
    tw_ranges: list,
) -> None:
    """
    Ponto de entrada do módulo (chamado de dashboard.py).

    Parameters
    ----------
    df_f        : DataFrame de forecast/metas (df_forecast)
    df_v_raw    : DataFrame de vendas brutas (sem filtro de linha/UF)
    filtros     : dict com chaves empresas / linhas / regioes / ufs
    semana_atual: semana do mês correspondente à data de hoje no período selecionado
    ano_sel     : ano selecionado no seletor global
    mes_sel     : mês selecionado no seletor global
    tw_ranges   : lista de tuplas (semana, dia_ini, dia_fim) do mês selecionado
    """
    # ── Inicialização de session state ────────────────────────────────────────
    if "acao_sem_idx" not in st.session_state:
        st.session_state["acao_sem_idx"] = N_PASSADO  # semana atual (default AC-P2-2)
    if "acao_linha_sel" not in st.session_state:
        st.session_state["acao_linha_sel"] = None
    if "acao_email_estado" not in st.session_state:
        st.session_state["acao_email_estado"] = "idle"

    # ── Hash para cache dos engines ──────────────────────────────────────────
    try:
        df_hash = str(hash(pd.util.hash_pandas_object(df_v_raw).sum()))
    except Exception as _e:
        st.warning(f"Erro ao calcular dados: {_e}")
        df_hash = str(len(df_v_raw))

    # ── Engines ───────────────────────────────────────────────────────────────
    with st.spinner("Calculando scores e flags…"):
        engine_prop, engine_sem = _get_engines(df_v_raw, df_hash)
        engine_pot  = _get_potencial_engine(df_v_raw, df_hash)

    # ── Horizonte de semanas ──────────────────────────────────────────────────
    horizonte = _horizonte_semanas(ano_sel, mes_sel, semana_atual)

    # ── Filtros obrigatórios (AC-P2-3) ────────────────────────────────────────
    st.markdown(
        '<div style="margin-bottom:16px;">'
        '<span style="font-size:18px;font-weight:800;color:#2C3E50;">'
        '📋 Plano & Ação Semanal</span></div>',
        unsafe_allow_html=True,
    )
    gerencia_sel, vendedor_sel = _render_filtros_obrigatorios(df_v_raw, filtros)

    # ── Seletor de semana ─────────────────────────────────────────────────────
    sem_idx = st.session_state["acao_sem_idx"]
    sem_idx = st.select_slider(
        "📅 Semana de referência",
        options=list(range(len(horizonte))),
        value=min(sem_idx, len(horizonte) - 1),
        format_func=lambda i: horizonte[i]["label_full"],
        key="acao_sem_slider",
    )
    st.session_state["acao_sem_idx"] = sem_idx

    w_sel  = horizonte[sem_idx]
    zona   = _zone(sem_idx)

    # ── Cabeçalho colorido por zona (C1 — impossível misturar) ───────────────
    bg_h    = _ZONE_HEADER_BG.get(zona, "#F8FAFC")
    bord_h  = _ZONE_HEADER_BORDER.get(zona, "#90A4AE")
    badge_z = _badge_zona(zona)
    st.markdown(
        f'<div style="background:{bg_h};border-left:6px solid {bord_h};'
        f'border-radius:0 8px 8px 0;padding:12px 18px;margin-bottom:16px;">'
        f'<span style="font-size:16px;font-weight:800;color:{bord_h};">'
        f'{badge_z} — {w_sel["label_full"]}</span>'
        f'<span style="font-size:12px;color:#546E7A;margin-left:12px;">'
        f'Ação: {_ZONE_ACTION.get(zona, "—")}</span></div>',
        unsafe_allow_html=True,
    )

    # ── Alertas de desvio (M2) ────────────────────────────────────────────────
    with st.expander("🚨 Alertas de Desvio Crítico", expanded=False):
        alertas = _calc_desvios(df_f, horizonte)
        _render_alertas_desvio(alertas)
    # Filtra alertas para email — só os relevantes para a semana selecionada
    alertas_email = [
        alerta for alerta in alertas
        if alerta.get("zona") == zona
    ] if alertas else []

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO A — Lista de ação
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div style="margin-top:24px;margin-bottom:8px;">'
        '<span style="font-size:15px;font-weight:800;color:#2C3E50;">'
        '🎯 Seção A — Lista de Ação da Semana</span></div>',
        unsafe_allow_html=True,
    )

    # ── Calcula scores para a gerência selecionada ───────────────────────────
    ger_col = "gerencia_efetiva" if "gerencia_efetiva" in df_v_raw.columns else "gerencia"
    if ger_col in df_v_raw.columns:
        df_v_ger = df_v_raw[df_v_raw[ger_col] == gerencia_sel].copy()
    else:
        df_v_ger = df_v_raw.copy()

    if df_v_ger.empty:
        st.warning(
            f"Nenhum dado encontrado para a gerência **{gerencia_sel}**. "
            "Verifique os filtros globais."
        )
        return

    with st.spinner("Calculando lista de ação…"):
        scores_raw = PropensaoEngine(df_v_ger).calcular_scores()
        if scores_raw.empty:
            st.info("Nenhum cliente com score calculado para esta gerência.")
            return

        # Potencial para a semana selecionada — cache por (gerência, semana_mes)
        sem_mes = w_sel["semana_mes"]
        pot_cache_key = f"_acao_pot_{df_hash}_{gerencia_sel}_{sem_mes}"
        if pot_cache_key not in st.session_state:
            st.session_state[pot_cache_key] = (
                PotencialSemanalEngine(df_v_ger).calcular_flag_potencial(semana_mes=sem_mes)
            )
        potencial = st.session_state[pot_cache_key]

    # ── Aplica filtro de linha via clique no gráfico (AC-P2-11) ──────────────
    linha_filtro = st.session_state.get("acao_linha_sel")
    _linhas_validas = set(scores_raw["linha"].dropna().unique()) if not scores_raw.empty else set()
    if linha_filtro and linha_filtro not in _linhas_validas:
        linha_filtro = None

    df_clientes = _build_client_df(
        scores=scores_raw.copy(),
        potencial=potencial.copy() if not potencial.empty else pd.DataFrame(),
        zona=zona,
        vendedor_sel=vendedor_sel,
    )

    if linha_filtro and not df_clientes.empty and "linha" in df_clientes.columns:
        df_clientes = df_clientes[df_clientes["linha"] == linha_filtro].copy()
        col_fl, _ = st.columns([2, 3])
        with col_fl:
            if st.button(f"✖ Limpar filtro: {linha_filtro}", key="acao_limpar_filtro"):
                st.session_state["acao_linha_sel"] = None
                st.rerun()

    # ── KPIs ─────────────────────────────────────────────────────────────────
    _render_kpis_semana(df_clientes)

    # ── Top-5 cards ───────────────────────────────────────────────────────────
    if not df_clientes.empty:
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#78909C;'
            'text-transform:uppercase;letter-spacing:.5px;margin:12px 0 6px;">'
            'Top 5 prioridades</div>',
            unsafe_allow_html=True,
        )
        _render_top5_cards(df_clientes, zona)

    # ── Tabela principal ──────────────────────────────────────────────────────
    # Instancia engine com df filtrado por gerência para acesso a decomposição
    engine_ger = PropensaoEngine(df_v_ger)
    _ = engine_ger.calcular_scores()  # popula _last_scores
    _render_tabela_clientes(df_clientes, engine_ger, zona)

    # ── Email flow ────────────────────────────────────────────────────────────
    _render_email_flow(
        df_scores=df_clientes,
        semana_label=w_sel["label_full"],
        zona=zona,
        gerencia_sel=gerencia_sel,
        alertas=alertas_email,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO B — Gráfico de horizonte (cross-navigation AC-P2-11)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div style="margin-top:32px;margin-bottom:8px;">'
        '<span style="font-size:15px;font-weight:800;color:#2C3E50;">'
        '📊 Seção B — Horizonte de Volume</span></div>',
        unsafe_allow_html=True,
    )
    _legenda_zonas()

    # Agrega metas por semana do horizonte
    metas: list[float] = []
    reais: list[float] = []
    for semana_w in horizonte:
        df_w = df_f[
            (df_f["ano"] == semana_w["ano"]) &
            (df_f["mes"] == semana_w["mes"]) &
            (df_f["semana_mes"] == semana_w["semana_mes"])
        ] if not df_f.empty else pd.DataFrame()
        metas.append(float(df_w["meta_soe"].sum()) if not df_w.empty and "meta_soe" in df_w.columns else 0.0)

        if not df_v_raw.empty and "data" in df_v_raw.columns:
            df_v_w = df_v_raw[
                (pd.to_datetime(df_v_raw["data"]).dt.year  == semana_w["ano"]) &
                (pd.to_datetime(df_v_raw["data"]).dt.month == semana_w["mes"])
            ]
            if "semana_mes" in df_v_raw.columns:
                df_v_w = df_v_w[df_v_w["semana_mes"] == semana_w["semana_mes"]]
            elif not df_v_w.empty:
                df_v_w = df_v_w.copy()
                df_v_w["_sm"] = pd.to_datetime(df_v_w["data"]).dt.day.apply(
                    lambda d: 1 if d <= 7 else 2 if d <= 14 else 3 if d <= 21 else 4
                )
                df_v_w = df_v_w[df_v_w["_sm"] == semana_w["semana_mes"]]
            reais.append(float(df_v_w["vol_ton"].sum()) if not df_v_w.empty else 0.0)
        else:
            reais.append(0.0)

    fig = _graf_horizonte(
        horizonte=horizonte,
        metas=metas,
        reais=reais,
        metas_ajustadas=metas,
        ano_ref=ano_sel,
        mes_ref=mes_sel,
        sem_ref=semana_atual,
        semana_sel_idx=sem_idx,
    )

    # on_select="rerun" — clique no gráfico atualiza acao_linha_sel (AC-P2-11)
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="acao_horizonte_chart")
    if event and hasattr(event, "selection") and event.selection:
        pts = event.selection.get("points", [])
        if pts:
            ponto = pts[0]
            # Tenta extrair a linha do hovertext / customdata
            curve_idx = ponto.get("curve_number", 0)
            x_val     = ponto.get("x", "")
            # Mapeia o label clicado para a semana do horizonte
            for i, semana_w in enumerate(horizonte):
                if semana_w["label"] == x_val or semana_w["label_full"] == x_val:
                    st.session_state["acao_sem_idx"] = i
                    break
            # Se há trace de linha específico, extrai o nome da linha
            trace_name = ""
            if fig.data and curve_idx < len(fig.data):
                trace_name = fig.data[curve_idx].name or ""
            if trace_name and trace_name not in ("Meta S&OE", "Meta Ajustada (What-If)"):
                st.session_state["acao_linha_sel"] = trace_name
            st.rerun()

    # ═══════════════════════════════════════════════════════════════════════════
    # SEÇÃO C — What-If (Zona Líquida apenas)
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div style="margin-top:32px;margin-bottom:8px;">'
        '<span style="font-size:15px;font-weight:800;color:#2C3E50;">'
        '🛠️ Seção C — Simulador What-If</span></div>',
        unsafe_allow_html=True,
    )
    _render_whatiif_section(
        horizonte=horizonte,
        df_f=df_f,
        gerencia_sel=gerencia_sel,
        semana_sel_idx=sem_idx,
        zona=zona,
    )
