"""
Módulo "Assertividade do Plano" — Aba 5  (v2 — Storytelling redesign)

Narrativa: Situação → Diagnóstico → Causa → Ação → Detalhe

Flow de leitura
───────────────
  [1] Banner de Status Geral           — "estou bem ou mal?"
  [2] KPI Cards (4) com sparkline      — números e delta vs mês anterior
  [3] Quadrante WMAPE × Bias           — "qual é o tipo do meu problema?"
      + Diagnóstico automático
      + Recomendações acionáveis
  [4] Heatmap Gerência × Linha         — "onde está concentrado?"
  [5] Tendência do Bias por Semana     — "está melhorando ou piorando?"
  [6] FVA — S&OE vs S&OP (waterfall)   — "o ajuste comercial ajudou?"
      + Histórico 6 meses
  [7] Pareto de Linhas                 — "quais linhas concentram 80% do desvio?"
  [8] Waterfall semanal                — detalhe técnico
  [9] Tabela Detalhada + export Excel
  [10] Glossário (colapsado)

Métricas
────────
  WMAPE  = Σ|Real−Plano|/ΣReal × 100
  Bias   = Σ(Plano−Real)/ΣReal × 100  (+= sobreplanejamento)
  Aderência = % semanas dentro de ±10% do plano
  GAP   = ΣReal − ΣPlano (ton)
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

# ── Constantes visuais ────────────────────────────────────────────────────────
_FONT = "Inter, Arial, sans-serif"
_BG   = "rgba(0,0,0,0)"

_MESES_ABR = {
    1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
    7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez",
}

# Thresholds de qualidade
_TH_WMAPE = (10.0, 20.0)   # Verde ≤10 · Amarelo ≤20 · Vermelho >20
_TH_BIAS  = (5.0,  12.0)   # Verde |b|≤5 · Amarelo ≤12 · Vermelho >12
_TH_ADER  = (85.0, 70.0)   # Verde ≥85 · Amarelo ≥70 · Vermelho <70

_GLOSSARIO: dict[str, str] = {
    "WMAPE": (
        "Weighted Mean Absolute Percentage Error — Erro percentual médio "
        "ponderado pelo volume. Mede o tamanho do erro sem distinguir "
        "se foi para cima ou para baixo. "
        "Verde ≤ 10% · Amarelo 10–20% · Vermelho > 20%."
    ),
    "Bias": (
        "Viés sistemático — indica se o plano tende a superestimar (+) "
        "ou subestimar (−) o realizado. "
        "Bias positivo = plano acima do real (sobreplanejamento). "
        "Verde |bias| ≤ 5% · Amarelo 5–12% · Vermelho > 12%."
    ),
    "Aderência": (
        "% de semanas em que o erro absoluto ficou dentro de ±10% do plano. "
        "Meta: ≥ 85% das semanas dentro da faixa."
    ),
    "GAP Acumulado": (
        "Diferença total entre Realizado e Plano em toneladas. "
        "Positivo = realizado superou o plano. "
        "Negativo = realizado ficou abaixo do plano."
    ),
    "FVA": (
        "Forecast Value Added — mede se o ajuste do S&OE ao S&OP "
        "melhorou a acuracidade. Se WMAPE(S&OE) < WMAPE(S&OP): "
        "o S&OE agregou valor."
    ),
    "S&OP": (
        "Sales & Operations Planning — plano de vendas de médio prazo, "
        "elaborado 30–60 dias antes do mês de execução."
    ),
    "S&OE": (
        "Sales & Operations Execution — programa de curto prazo que "
        "ajusta o S&OP com base em sinais da semana anterior."
    ),
    "Sobreplanejamento": (
        "Quando o plano é consistentemente maior que o realizado. "
        "Bias positivo alto. Risco: excesso de estoque e pressão sobre time comercial."
    ),
    "Subplanejamento": (
        "Quando o plano é consistentemente menor que o realizado. "
        "Bias negativo alto. Risco: ruptura e sobrecarga operacional."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# GERÊNCIA  (espelha plano_comercial._gerencia_efetiva)
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


def _aderencia(real: pd.Series, plano: pd.Series, tol: float = 0.10) -> float:
    mask = plano > 0
    if mask.sum() == 0:
        return float("nan")
    r, p = real[mask], plano[mask]
    return float((r - p).abs().div(p).le(tol).sum() / mask.sum() * 100)


def _calc(df: pd.DataFrame, col: str) -> dict:
    r, p = df["vol_ton"], df[col]
    return {
        "wmape":     _wmape(r, p),
        "bias":      _bias(r, p),
        "gap":       float((r - p).sum()),
        "aderencia": _aderencia(r, p),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SEMÁFOROS
# ═══════════════════════════════════════════════════════════════════════════════

def _cw(v: float) -> str:
    if np.isnan(v): return "#94A3B8"
    return COR_VERDE if v <= _TH_WMAPE[0] else (COR_AMARELO if v <= _TH_WMAPE[1] else COR_VERMELHO)

def _cb(v: float) -> str:
    av = abs(v) if not np.isnan(v) else float("nan")
    if np.isnan(av): return "#94A3B8"
    return COR_VERDE if av <= _TH_BIAS[0] else (COR_AMARELO if av <= _TH_BIAS[1] else COR_VERMELHO)

def _ca(v: float) -> str:
    if np.isnan(v): return "#94A3B8"
    return COR_VERDE if v >= _TH_ADER[0] else (COR_AMARELO if v >= _TH_ADER[1] else COR_VERMELHO)

def _cg(v: float) -> str:
    if np.isnan(v): return "#94A3B8"
    return COR_VERDE if v >= 0 else COR_VERMELHO


# ═══════════════════════════════════════════════════════════════════════════════
# SPARKLINE SVG (sem dependência kaleido)
# ═══════════════════════════════════════════════════════════════════════════════

def _sparkline_svg(vals: list, cor: str, w: int = 80, h: int = 24) -> str:
    """Gera polyline SVG inline para embed em HTML."""
    clean = [float(v) for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))]
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

def _secao(txt: str) -> None:
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;color:#94A3B8;'
        f'text-transform:uppercase;letter-spacing:1.5px;'
        f'border-bottom:1px solid #E2E8F0;padding-bottom:8px;'
        f'margin:28px 0 16px 0;font-family:{_FONT};">{txt}</div>',
        unsafe_allow_html=True,
    )


def _banner_status(wmape: float, bias: float, aderencia: float) -> str:
    """Faixa colorida de status geral — primeira coisa que o coordenador lê."""
    if np.isnan(wmape):
        return ""
    if wmape <= 10 and abs(bias) <= 5 and aderencia >= 85:
        cor, icone, label, frase = (
            COR_VERDE, "&#x2713;", "PLANO SAUD&#xC1;VEL",
            f"Assertividade dentro da meta &mdash; WMAPE {wmape:.1f}%, Ader&ecirc;ncia {aderencia:.0f}%",
        )
    elif wmape > 20 or abs(bias) > 15:
        cor, icone, label, frase = (
            COR_VERMELHO, "&#x26A0;", "ATEN&#xC7;&#xC3;O CR&#xCD;TICA",
            f"Desvio relevante identificado &mdash; WMAPE {wmape:.1f}%, Bias {bias:+.1f}%",
        )
    else:
        cor, icone, label, frase = (
            COR_AMARELO, "&#x7E;", "ATEN&#xC7;&#xC3;O MODERADA",
            f"Plano com desvios control&aacute;veis &mdash; WMAPE {wmape:.1f}%, Ader&ecirc;ncia {aderencia:.0f}%",
        )
    return f"""
    <div style="background:{cor}18;border-left:4px solid {cor};border-radius:8px;
                padding:12px 20px;margin-bottom:20px;display:flex;align-items:center;gap:14px;">
      <span style="font-size:22px;color:{cor};font-weight:700;">{icone}</span>
      <div>
        <span style="font-weight:800;color:{cor};font-size:12px;
                     letter-spacing:1px;text-transform:uppercase;
                     font-family:{_FONT};">{label}</span>
        <span style="color:#374151;font-size:13.5px;margin-left:12px;
                     font-family:{_FONT};">{frase}</span>
      </div>
    </div>"""


def _kpi_card(
    label: str, valor: str, cor: str, sub: str,
    delta_str: str, delta_pos: bool | None,
    spark_vals: list, tooltip: str = "",
) -> str:
    spark = _sparkline_svg(spark_vals, cor)
    if delta_str and delta_pos is not None:
        dc = COR_VERDE if delta_pos else COR_VERMELHO
        seta = "&#x25B2;" if delta_pos else "&#x25BC;"
        delta_html = (
            f'<span style="font-size:11px;color:{dc};font-weight:700;">'
            f'{seta} {delta_str}</span>'
        )
    else:
        delta_html = f'<span style="font-size:11px;color:#94A3B8;">{sub}</span>'

    tt = f'title="{tooltip}"' if tooltip else ""
    return f"""
    <div {tt} style="background:#FFFFFF;border-radius:12px;padding:16px 18px 12px;
                border:1px solid #E2E8F0;border-left:4px solid {cor};
                box-shadow:0 1px 3px rgba(0,0,0,0.05);
                position:relative;overflow:hidden;
                cursor:{'help' if tooltip else 'default'};">
      <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1.2px;color:#94A3B8;margin-bottom:6px;
                  font-family:{_FONT};">{label}</div>
      <div style="font-size:26px;font-weight:800;color:{cor};line-height:1.05;
                  letter-spacing:-0.8px;font-family:{_FONT};">{valor}</div>
      <div style="margin-top:6px;">{delta_html}</div>
      <div style="position:absolute;bottom:4px;right:8px;opacity:0.45;">{spark}</div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNÓSTICO AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════════════════════

def _tipo_desvio(wmape: float, bias: float, aderencia: float,
                 tendencia_coef: float | None = None) -> list[dict]:
    """Classifica o tipo de desvio e retorna lista de diagnósticos com ações."""
    diag: list[dict] = []

    if np.isnan(wmape) or np.isnan(bias):
        return diag

    # ── Padrão principal ─────────────────────────────────────────────────────
    if wmape > 15 and bias > 5:
        diag.append({
            "sev": "CRITICO", "codigo": "SOBRE_SIS",
            "titulo": "Sobreplanejamento Sistem&#xe1;tico",
            "descricao": (
                f"O plano est&aacute; sistematicamente acima do realizado. "
                f"Com Bias de <b>{bias:+.1f}%</b>, a empresa planeja "
                f"<b>{abs(bias):.0f}%</b> a mais do que vende na pr&aacute;tica."
            ),
            "acao": (
                "Revisar par&acirc;metros de uplift nas metas S&OP. "
                "Investigar linhas com maior bias positivo abaixo."
            ),
        })
    elif wmape > 15 and bias < -5:
        diag.append({
            "sev": "CRITICO", "codigo": "SUB_SIS",
            "titulo": "Subplanejamento Sistem&#xe1;tico",
            "descricao": (
                f"O plano est&aacute; consistentemente abaixo do realizado. "
                f"Com Bias de <b>{bias:+.1f}%</b>, h&aacute; demanda n&atilde;o "
                f"capturada no planejamento."
            ),
            "acao": (
                "Revisar sazonalidade e tend&ecirc;ncia nas premissas do plano. "
                "Verificar se h&aacute; pedidos at&iacute;picos recorrentes n&atilde;o modelados."
            ),
        })
    elif wmape > 15 and abs(bias) <= 5:
        diag.append({
            "sev": "ATENCAO", "codigo": "ERRO_ALEAT",
            "titulo": "Alta Variabilidade Sem Vi&eacute;s",
            "descricao": (
                f"WMAPE de <b>{wmape:.1f}%</b> com Bias pr&oacute;ximo de zero. "
                "O erro &eacute; aleat&oacute;rio, n&atilde;o sistem&aacute;tico. "
                "Pode ser variabilidade operacional ou clientes concentrados."
            ),
            "acao": (
                "Investigar semanas com maior desvio. "
                "Verificar se pedidos grandes e pontuais distorcem a m&eacute;dia."
            ),
        })

    # ── Viés com tendência crescente ─────────────────────────────────────────
    if tendencia_coef is not None and abs(tendencia_coef) > 1.5:
        dir_pt = "crescente &#x2191;" if tendencia_coef > 0 else "decrescente &#x2193;"
        diag.append({
            "sev": "ATENCAO", "codigo": "TEND_BIAS",
            "titulo": f"Vi&eacute;s {dir_pt}",
            "descricao": (
                f"O bias est&aacute; mudando <b>{abs(tendencia_coef):.1f} p.p./semana</b> "
                "— sinal de que o plano n&atilde;o est&aacute; acompanhando a tend&ecirc;ncia real."
            ),
            "acao": (
                "Verificar se h&aacute; sazonalidade ou tend&ecirc;ncia de crescimento/queda "
                "n&atilde;o capturada nas premissas."
            ),
        })

    # ── Aderência ─────────────────────────────────────────────────────────────
    if not np.isnan(aderencia) and aderencia < 70:
        diag.append({
            "sev": "CRITICO", "codigo": "ADER_CRIT",
            "titulo": "Ader&ecirc;ncia Cr&iacute;tica",
            "descricao": (
                f"Apenas <b>{aderencia:.0f}%</b> das combina&ccedil;&otilde;es linha/semana "
                "est&atilde;o dentro da toler&acirc;ncia de &plusmn;10%."
            ),
            "acao": (
                "Revisar processo de S&OE. "
                "Verificar se h&aacute; linhas sem atualiza&ccedil;&atilde;o de plano."
            ),
        })
    elif not np.isnan(aderencia) and aderencia < 85:
        diag.append({
            "sev": "ATENCAO", "codigo": "ADER_BAIXA",
            "titulo": "Ader&ecirc;ncia Abaixo da Meta",
            "descricao": (
                f"Ader&ecirc;ncia de <b>{aderencia:.0f}%</b> abaixo da meta de 85%."
            ),
            "acao": (
                "Identificar ger&ecirc;ncias com menor ader&ecirc;ncia "
                "e priorizar revis&atilde;o do processo."
            ),
        })

    # ── Situação saudável ─────────────────────────────────────────────────────
    if not diag:
        diag.append({
            "sev": "OK", "codigo": "SAUDAVEL",
            "titulo": "Plano Saud&aacute;vel",
            "descricao": (
                f"Assertividade dentro dos limites. "
                f"WMAPE <b>{wmape:.1f}%</b>, Bias <b>{bias:+.1f}%</b>, "
                f"Ader&ecirc;ncia <b>{aderencia:.0f}%</b>."
            ),
            "acao": "Manter processo de revis&atilde;o semanal.",
        })

    return diag


def _tipo_concentracao(df_linhas: pd.DataFrame) -> dict | None:
    """Analisa concentração de desvio — retorna diagnóstico Pareto."""
    if df_linhas.empty:
        return None
    df = df_linhas.copy()
    df["gap_abs"] = df["gap"].abs()
    total = df["gap_abs"].sum()
    if total == 0:
        return None
    df = df.sort_values("gap_abs", ascending=False).reset_index(drop=True)
    df["acum_pct"] = df["gap_abs"].cumsum() / total * 100
    n80 = int((df["acum_pct"] <= 80).sum()) + 1
    n80 = min(n80, len(df))
    linhas_crit = df.head(n80)["linha"].tolist()
    pct_linhas = n80 / len(df) * 100
    nomes = ", ".join(linhas_crit[:3]) + ("…" if len(linhas_crit) > 3 else "")
    if pct_linhas <= 30:
        return {
            "sev": "ATENCAO", "codigo": "CONC_PARETO",
            "titulo": "Desvio Concentrado (Pareto)",
            "descricao": (
                f"80% do desvio est&aacute; em apenas <b>{n80} linha(s)</b>: {nomes}."
            ),
            "acao": (
                f"Foco imediato nas linhas: <b>{nomes}</b>. "
                "Problema &eacute; pontual, n&atilde;o sist&ecirc;mico."
            ),
        }
    else:
        return {
            "sev": "ATENCAO", "codigo": "CONC_DISTR",
            "titulo": "Desvio Distribu&iacute;do",
            "descricao": (
                f"Desvio distribu&iacute;do em <b>{n80} de {len(df)} linhas</b> "
                f"({pct_linhas:.0f}%). Problema sistem&acirc;tico."
            ),
            "acao": (
                "Revisar metodologia geral de planejamento. "
                "N&atilde;o &eacute; um problema pontual."
            ),
        }


def _tipo_cronicidade(wmape_atual: float, hist_wmape: list[float | None]) -> dict | None:
    """Compara desvio atual com histórico dos últimos meses."""
    historico = [w for w in hist_wmape if w is not None and not np.isnan(w)]
    if len(historico) < 2 or np.isnan(wmape_atual):
        return None
    meses_crit = sum(1 for w in historico if w > 15)
    if meses_crit >= 3:
        media = sum(historico) / len(historico)
        return {
            "sev": "CRITICO", "codigo": "CRONICO",
            "titulo": "Desvio Cr&ocirc;nico",
            "descricao": (
                f"WMAPE acima de 15% em <b>{meses_crit} dos &uacute;ltimos "
                f"{len(historico)} meses</b> (m&eacute;dia hist&oacute;rica: {media:.1f}%). "
                "N&atilde;o &eacute; evento isolado."
            ),
            "acao": (
                "Revis&atilde;o estrutural das premissas de planejamento necess&aacute;ria."
            ),
        }
    elif wmape_atual > 15 and meses_crit == 0:
        return {
            "sev": "ATENCAO", "codigo": "NOVO",
            "titulo": "Desvio Novo (sem precedente)",
            "descricao": (
                f"WMAPE atual ({wmape_atual:.1f}%) n&atilde;o tem precedente "
                f"nos &uacute;ltimos {len(historico)} meses."
            ),
            "acao": (
                "Investigar evento espec&iacute;fico deste per&iacute;odo. "
                "Checar se h&aacute; lan&ccedil;amento, perda de cliente ou erro de lan&ccedil;amento."
            ),
        }
    return None


def _render_recomendacoes(diagnosticos: list[dict], extra: list[dict | None]) -> None:
    """Renderiza cards de recomendação ordenados por severidade."""
    todos = diagnosticos + [d for d in extra if d]
    todos.sort(key=lambda x: 0 if x.get("sev") == "CRITICO" else
                              (1 if x.get("sev") == "ATENCAO" else 2))

    cores_sev = {
        "CRITICO": (COR_VERMELHO, "#FEF2F2", "#FCA5A5"),
        "ATENCAO": (COR_AMARELO,  "#FFFBEB", "#FDE68A"),
        "OK":      (COR_VERDE,    "#F0FDF4", "#A7F3D0"),
    }
    html = ""
    for item in todos[:4]:
        ct, cf, cb = cores_sev.get(item.get("sev", "ATENCAO"), cores_sev["ATENCAO"])
        html += f"""
        <div style="background:{cf};border:1px solid {cb};border-left:4px solid {ct};
                    border-radius:8px;padding:14px 16px;margin-bottom:10px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="background:{ct};color:white;font-size:9px;font-weight:700;
                         padding:2px 8px;border-radius:12px;letter-spacing:.5px;
                         font-family:{_FONT};">{item.get('sev','')}</span>
            <span style="font-weight:700;color:#111827;font-size:13px;
                         font-family:{_FONT};">{item['titulo']}</span>
          </div>
          <p style="margin:0 0 8px;color:#374151;font-size:12.5px;line-height:1.55;
                    font-family:{_FONT};">{item['descricao']}</p>
          <div style="background:white;border-radius:5px;padding:8px 12px;
                      font-size:12px;color:{ct};font-weight:600;
                      font-family:{_FONT};">
            &#x1F4A1; A&ccedil;&atilde;o: {item['acao']}
          </div>
        </div>"""
    if html:
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.success("Nenhum desvio cr&iacute;tico identificado neste per&iacute;odo.")


# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ═══════════════════════════════════════════════════════════════════════════════

def _fig_quadrante(
    wmape: float, bias: float,
    hist_wmape: list | None = None,
    hist_bias: list | None = None,
    hist_labels: list | None = None,
) -> go.Figure:
    """
    Quadrante WMAPE × Bias.
    4 zonas: Sobreplanejamento · Subplanejamento · Erro Aleatório · Plano Saudável.
    Opcional: trilha histórica de meses anteriores.
    """
    fig = go.Figure()

    # Regiões de fundo
    zonas = [
        (0, 15, -5, 5,   "rgba(16,185,129,0.07)",  "Plano Saud&#xe1;vel",       COR_VERDE),
        (15, 55, -5, 5,  "rgba(245,158,11,0.07)",  "Erro Aleat&oacute;rio",     COR_AMARELO),
        (0, 15, 5, 45,   "rgba(245,158,11,0.07)",  "Plano Otimista",             COR_AMARELO),
        (0, 15, -45, -5, "rgba(245,158,11,0.07)",  "Plano Pessimista",           COR_AMARELO),
        (15, 55, 5, 45,  "rgba(239,68,68,0.07)",   "Sobreplanejamento",          COR_VERMELHO),
        (15, 55, -45, -5,"rgba(239,68,68,0.07)",   "Subplanejamento",            COR_VERMELHO),
    ]
    for x0, x1, y0, y1, cor, _lbl, _c in zonas:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=cor, line_width=0, layer="below")

    # Labels das zonas
    zona_labels = [
        (7.5, 0,   "Saud&aacute;vel",        COR_VERDE),
        (35,  0,   "Variabilidade",           COR_AMARELO),
        (7.5, 25,  "Sobreplano leve",         COR_AMARELO),
        (7.5, -25, "Subplano leve",           COR_AMARELO),
        (35,  25,  "Sobreplanejamento\nSist.", COR_VERMELHO),
        (35,  -25, "Subplanejamento\nSist.",  COR_VERMELHO),
    ]
    for x, y, txt, cor in zona_labels:
        fig.add_annotation(
            x=x, y=y, text=txt, showarrow=False,
            font=dict(size=9, color=cor, family=_FONT),
            align="center", opacity=0.65,
        )

    # Linhas de referência
    for y_val in (5, -5):
        fig.add_hline(y=y_val, line=dict(color="#CBD5E1", dash="dash", width=1))
    fig.add_vline(x=15, line=dict(color="#CBD5E1", dash="dash", width=1))
    fig.add_hline(y=0,  line=dict(color="#94A3B8", width=1))

    # Trilha histórica
    if hist_wmape and hist_bias and len(hist_wmape) >= 2:
        n = len(hist_wmape)
        hw = [w for w in hist_wmape if w is not None]
        hb = [b for b in hist_bias if b is not None]
        lbl = hist_labels or [str(i) for i in range(n)]
        for i in range(len(hw) - 1):
            fig.add_trace(go.Scatter(
                x=[hw[i], hw[i+1]], y=[hb[i], hb[i+1]],
                mode="lines",
                line=dict(color="#94A3B8", width=1.5, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ))
        fig.add_trace(go.Scatter(
            x=hw[:-1], y=hb[:-1],
            mode="markers",
            marker=dict(size=7, color="#CBD5E1",
                        line=dict(color="white", width=1.5)),
            text=lbl[:-1],
            hovertemplate="<b>%{text}</b><br>WMAPE: %{x:.1f}%<br>Bias: %{y:+.1f}%<extra></extra>",
            showlegend=False,
        ))

    # Ponto atual
    if not np.isnan(wmape) and not np.isnan(bias):
        fig.add_trace(go.Scatter(
            x=[wmape], y=[bias],
            mode="markers+text",
            marker=dict(size=18, color=COR_ACENTO,
                        line=dict(color="white", width=2.5)),
            text=["&#x25CF; Agora"],
            textposition="middle right",
            textfont=dict(size=10, color=COR_PRIMARIA, family=_FONT),
            hovertemplate=(
                f"<b>Período atual</b><br>"
                f"WMAPE: <b>{wmape:.1f}%</b><br>"
                f"Bias: <b>{bias:+.1f}%</b><extra></extra>"
            ),
            showlegend=False,
        ))

    fig.update_layout(
        height=290,
        margin=dict(l=44, r=16, t=24, b=44),
        paper_bgcolor=_BG, plot_bgcolor="#F9FAFB",
        font=dict(family=_FONT, size=11),
        xaxis=dict(
            title=dict(text="WMAPE (%)", font=dict(size=11, color="#94A3B8")),
            range=[0, 50], gridcolor="#F3F4F6",
            tickfont=dict(size=10, color="#94A3B8"), zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Bias (%)", font=dict(size=11, color="#94A3B8")),
            range=[-40, 40], gridcolor="#F3F4F6",
            tickfont=dict(size=10, color="#94A3B8"), zeroline=False,
        ),
    )
    return fig


def _fig_heatmap_ger_linha(
    df_mes: pd.DataFrame,
    col_plano: str,
    semanas_com_real: set[int],
) -> go.Figure:
    """
    Heatmap WMAPE por Gerência × Linha.
    Célula = WMAPE (%) + seta de Bias.
    Verde = assertivo · Vermelho = erro alto.
    """
    df_r = df_mes[df_mes["semana_mes"].isin(semanas_com_real)]
    if df_r.empty or "gerencia" not in df_r.columns:
        return go.Figure()

    rows = []
    for (ger, lin), sub in df_r.groupby(["gerencia", "linha"]):
        rows.append({
            "gerencia": ger, "linha": lin,
            "wmape": _wmape(sub["vol_ton"], sub[col_plano]),
            "bias":  _bias(sub["vol_ton"], sub[col_plano]),
        })
    if not rows:
        return go.Figure()

    dfg = pd.DataFrame(rows)
    piv_w = dfg.pivot_table(index="gerencia", columns="linha",
                             values="wmape", aggfunc="mean")
    piv_b = dfg.pivot_table(index="gerencia", columns="linha",
                             values="bias",  aggfunc="mean")

    # Colorscale: verde (0%) → amarelo (10%) → vermelho (25%+)
    cs = [
        [0.00, "#10B981"],
        [0.30, "#6EE7B7"],
        [0.50, "#FEF3C7"],
        [0.70, "#FCA5A5"],
        [1.00, "#EF4444"],
    ]

    # Texto nas células: wmape + seta bias
    texts = []
    hovers = []
    for ger in piv_w.index:
        row_t, row_h = [], []
        for lin in piv_w.columns:
            w = piv_w.loc[ger, lin] if lin in piv_w.columns else np.nan
            b = piv_b.loc[ger, lin] if lin in piv_b.columns else np.nan
            if pd.isna(w):
                row_t.append("")
                row_h.append(f"<b>{ger} / {lin}</b><br>Sem dados")
            else:
                seta = "&#x2191;" if (not pd.isna(b) and b > 3) else \
                       ("&#x2193;" if (not pd.isna(b) and b < -3) else "")
                row_t.append(f"{w:.0f}%{seta}")
                row_h.append(
                    f"<b>{ger}</b> / {lin}<br>"
                    f"WMAPE: <b>{w:.1f}%</b><br>"
                    f"Bias: <b>{b:+.1f}%</b>"
                )
        texts.append(row_t)
        hovers.append(row_h)

    fig = go.Figure(go.Heatmap(
        z=piv_w.values,
        x=piv_w.columns.tolist(),
        y=piv_w.index.tolist(),
        text=texts,
        texttemplate="%{text}",
        textfont=dict(size=11, family=_FONT, color="#1E293B"),
        hovertext=hovers,
        hoverinfo="text",
        colorscale=cs,
        zmin=0, zmax=25,
        colorbar=dict(
            title=dict(text="WMAPE (%)", font=dict(size=11, family=_FONT)),
            ticksuffix="%", len=0.8, thickness=12,
            tickfont=dict(size=10),
        ),
    ))

    n_linhas = len(piv_w.columns)
    n_ger    = len(piv_w.index)
    fig.update_layout(
        height=max(200, 80 + n_ger * 52),
        margin=dict(t=44, b=max(60, 20 + n_linhas * 8), l=140, r=80),
        paper_bgcolor=_BG, plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT, size=11),
        xaxis=dict(side="top", tickangle=-30,
                   tickfont=dict(size=10, color="#64748B")),
        yaxis=dict(tickfont=dict(size=11, color="#1E293B"),
                   autorange="reversed"),
    )
    return fig


def _fig_tendencia_bias(
    df_mes: pd.DataFrame,
    col_plano: str,
    semanas_com_real: set[int],
) -> tuple[go.Figure, float]:
    """
    Linha de Bias semanal + banda ±5% + WMAPE no eixo secundário + tendência.
    Retorna (fig, coef_angular).
    """
    grp = (
        df_mes.groupby("semana_mes")[["vol_ton", col_plano]]
        .sum().reset_index().sort_values("semana_mes")
    )
    grp = grp[grp["semana_mes"].isin(semanas_com_real)]
    if grp.empty:
        return go.Figure(), 0.0

    labels = [f"Sem {s}" for s in grp["semana_mes"]]
    bias_v = [
        _bias(
            grp.loc[grp["semana_mes"] == s, "vol_ton"],
            grp.loc[grp["semana_mes"] == s, col_plano],
        )
        for s in grp["semana_mes"]
    ]
    wmape_v = [
        _wmape(
            grp.loc[grp["semana_mes"] == s, "vol_ton"],
            grp.loc[grp["semana_mes"] == s, col_plano],
        )
        for s in grp["semana_mes"]
    ]

    # Coeficiente de tendência
    b_clean = [b for b in bias_v if not np.isnan(b)]
    coef = 0.0
    tend_y = None
    if len(b_clean) >= 3:
        x_arr = np.arange(len(b_clean), dtype=float)
        coef = float(np.polyfit(x_arr, b_clean, 1)[0])
        tend_vals = np.polyval([coef, np.mean(b_clean) - coef * np.mean(x_arr)], x_arr)
        tend_y = tend_vals.tolist()

    cor_tend = COR_VERMELHO if coef > 0.5 else (COR_VERDE if coef < -0.5 else "#94A3B8")

    fig = go.Figure()

    # Banda ±5%
    fig.add_hrect(y0=-5, y1=5, fillcolor="rgba(16,185,129,0.08)", line_width=0)

    # Linhas de referência
    for y_val in (5, -5):
        fig.add_hline(y=y_val, line=dict(color=COR_VERDE, width=1, dash="dash"))
    for y_val in (15, -15):
        fig.add_hline(y=y_val, line=dict(color=COR_VERMELHO, width=1, dash="dot"))
    fig.add_hline(y=0, line=dict(color="#CBD5E1", width=1.5))

    # Tendência
    if tend_y:
        fig.add_trace(go.Scatter(
            x=labels[:len(tend_y)], y=tend_y,
            mode="lines",
            line=dict(color=cor_tend, width=1.5, dash="longdash"),
            name=f"Tend. ({coef:+.1f}pp/sem)",
            opacity=0.7,
        ))

    # Bias
    cores_pts = [_cb(b) for b in bias_v]
    fig.add_trace(go.Scatter(
        x=labels, y=bias_v,
        mode="lines+markers",
        name="Bias (%)",
        line=dict(color=COR_PRIMARIA, width=2.5, shape="spline", smoothing=0.6),
        fill="tozeroy",
        fillcolor="rgba(30,58,95,0.09)",
        marker=dict(size=9, color=cores_pts, line=dict(color="white", width=2)),
        hovertemplate="<b>%{x}</b><br>Bias: <b>%{y:+.1f}%</b><extra></extra>",
    ))

    # WMAPE eixo secundário
    fig.add_trace(go.Scatter(
        x=labels, y=wmape_v,
        mode="lines",
        name="WMAPE (%)",
        yaxis="y2",
        line=dict(color=COR_ACENTO, width=1.5, dash="dot"),
        connectgaps=True,
        hovertemplate="WMAPE: <b>%{y:.1f}%</b><extra></extra>",
    ))

    fig.update_layout(
        height=280,
        margin=dict(t=28, b=40, l=52, r=60),
        paper_bgcolor=_BG, plot_bgcolor="#F9FAFB",
        font=dict(family=_FONT, size=11),
        xaxis=dict(tickfont=dict(size=11, color="#94A3B8"), linecolor="#E2E8F0",
                   gridcolor="#E2E8F0"),
        yaxis=dict(
            title=dict(text="Bias (%)", font=dict(size=11, color="#94A3B8")),
            ticksuffix="%", gridcolor="#E2E8F0", zeroline=False,
            tickfont=dict(size=10, color="#94A3B8"),
        ),
        yaxis2=dict(
            title=dict(text="WMAPE (%)", font=dict(size=11, color=COR_ACENTO)),
            overlaying="y", side="right", showgrid=False,
            ticksuffix="%", zeroline=False,
            tickfont=dict(size=10, color=COR_ACENTO),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=10, family=_FONT),
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0", borderwidth=1,
        ),
    )
    return fig, coef


def _fig_fva_waterfall(wmape_sop: float, wmape_soe: float) -> go.Figure:
    """Waterfall FVA: S&OP → ajuste S&OE → resultado final."""
    delta = wmape_soe - wmape_sop
    cor_delta = COR_VERDE if delta < 0 else COR_VERMELHO
    label_delta = (
        f"S&OE melhorou<br>{abs(delta):.1f}pp" if delta < 0
        else f"S&OE piorou<br>{abs(delta):.1f}pp"
    )

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["S&OP\n(Planejamento)", f"&#x25B3; Revis&atilde;o\nComercial (S&OE)", "S&OE\n(Final)"],
        y=[wmape_sop, delta, wmape_soe],
        text=[f"{wmape_sop:.1f}%", f"{delta:+.1f}pp", f"{wmape_soe:.1f}%"],
        textposition="outside",
        textfont=dict(size=12, family=_FONT, color=COR_PRIMARIA),
        decreasing=dict(marker=dict(color="#10B981")),
        increasing=dict(marker=dict(color=COR_VERMELHO)),
        totals=dict(marker=dict(color=COR_ACENTO)),
        connector=dict(line=dict(color="#E2E8F0", dash="dot", width=1.5)),
        hovertemplate="<b>%{x}</b><br>WMAPE: <b>%{y:.1f}%</b><extra></extra>",
    ))

    # Meta
    fig.add_hline(y=10, line=dict(color=COR_VERDE, dash="dash", width=1.5),
                  annotation_text="Meta 10%", annotation_position="right",
                  annotation_font=dict(color=COR_VERDE, size=10))

    # Anotação do delta
    fig.add_annotation(
        x=1, y=wmape_sop + delta / 2,
        text=f"<b>{label_delta}</b>",
        showarrow=True, arrowhead=2,
        arrowcolor=cor_delta,
        font=dict(color=cor_delta, size=11, family=_FONT),
        bgcolor="white", bordercolor=cor_delta, borderpad=4,
        ax=40, ay=0,
    )

    fig.update_layout(
        height=300,
        showlegend=False,
        margin=dict(l=20, r=80, t=28, b=40),
        paper_bgcolor=_BG, plot_bgcolor="#F9FAFB",
        font=dict(family=_FONT, size=11),
        yaxis=dict(
            title=dict(text="WMAPE (%)", font=dict(size=11, color="#94A3B8")),
            ticksuffix="%", gridcolor="#E2E8F0",
            range=[0, max(wmape_sop, wmape_soe) * 1.45],
            tickfont=dict(size=10, color="#94A3B8"),
        ),
        xaxis=dict(tickfont=dict(size=11, color="#64748B"), linecolor="#E2E8F0"),
    )
    return fig


def _fig_fva_historico(
    df_all: pd.DataFrame, ano_ref: int, mes_ref: int, n_meses: int = 6,
) -> go.Figure:
    periodos: list[tuple[int, int]] = []
    a, m = ano_ref, mes_ref
    for _ in range(n_meses):
        periodos.insert(0, (a, m))
        m -= 1
        if m == 0:
            m, a = 12, a - 1

    labels_per = [f"{_MESES_ABR.get(m2,'')}/{str(a2)[-2:]}" for a2, m2 in periodos]
    w_soe, w_sop = [], []

    for a2, m2 in periodos:
        sub = df_all[(df_all["ano"] == a2) & (df_all["mes"] == m2)]
        if sub.empty or sub["vol_ton"].sum() == 0:
            w_soe.append(None); w_sop.append(None); continue
        sems = set(sub.groupby("semana_mes")["vol_ton"].sum().pipe(
            lambda s: s[s > 0].index).tolist())
        s2 = sub[sub["semana_mes"].isin(sems)]
        w_soe.append(_wmape(s2["vol_ton"], s2["meta_soe"]) if "meta_soe" in s2 else None)
        w_sop.append(_wmape(s2["vol_ton"], s2["meta_sop"]) if "meta_sop" in s2 else None)

    fig = go.Figure()
    for y_val, lbl, cor in [(_TH_WMAPE[0], "Meta 10%", COR_VERDE),
                              (_TH_WMAPE[1], "Limite 20%", COR_AMARELO)]:
        fig.add_hline(y=y_val, line=dict(color=cor, width=1, dash="dot"),
                      annotation_text=lbl, annotation_position="right",
                      annotation_font=dict(size=9, color=cor))

    fig.add_trace(go.Scatter(x=labels_per, y=w_sop, mode="lines+markers",
                             name="S&OP", connectgaps=True,
                             line=dict(color="#CBD5E1", width=2.5, shape="spline"),
                             marker=dict(size=8, color="#94A3B8",
                                         line=dict(color="white", width=2)),
                             hovertemplate="S&OP %{x}: <b>%{y:.1f}%</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=labels_per, y=w_soe, mode="lines+markers",
                             name="S&OE", connectgaps=True,
                             line=dict(color=COR_PRIMARIA, width=2.5, shape="spline"),
                             marker=dict(size=9, color=COR_PRIMARIA,
                                         line=dict(color="white", width=2)),
                             hovertemplate="S&OE %{x}: <b>%{y:.1f}%</b><extra></extra>"))
    fig.update_layout(
        height=230,
        margin=dict(t=20, b=36, l=44, r=60),
        paper_bgcolor=_BG, plot_bgcolor="#F9FAFB",
        font=dict(family=_FONT, size=11),
        xaxis=dict(tickfont=dict(size=11, color="#94A3B8"), gridcolor="#E2E8F0"),
        yaxis=dict(
            title=dict(text="WMAPE (%)", font=dict(size=11, color="#94A3B8")),
            tickfont=dict(size=10, color="#94A3B8"), gridcolor="#E2E8F0", zeroline=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10, family=_FONT),
                    bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0", borderwidth=1),
    )
    return fig


def _fig_pareto_linhas(df_linhas: pd.DataFrame) -> go.Figure:
    """Pareto: |GAP| por linha com % acumulado. Linha 80% em destaque."""
    if df_linhas.empty:
        return go.Figure()
    df = df_linhas.copy()
    df["gap_abs"] = df["gap"].abs()
    df = df.sort_values("gap_abs", ascending=False).reset_index(drop=True)
    total = df["gap_abs"].sum()
    if total == 0:
        return go.Figure()
    df["acum_pct"] = df["gap_abs"].cumsum() / total * 100
    cores = [COR_VERMELHO if g < 0 else COR_VERDE for g in df["gap"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["linha"], y=df["gap_abs"],
        marker_color=cores, marker_line=dict(width=0),
        name="|GAP| (ton)",
        text=[f"{v:+,.0f}" for v in df["gap"]],
        textposition="outside",
        textfont=dict(size=9, family=_FONT),
        hovertemplate="<b>%{x}</b><br>GAP: %{text} ton<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["linha"], y=df["acum_pct"],
        mode="lines+markers", name="% Acumulado",
        yaxis="y2",
        line=dict(color=COR_PRIMARIA, width=2),
        marker=dict(size=6),
        hovertemplate="%{y:.0f}% do desvio total<extra></extra>",
    ))
    fig.add_hline(y=80, yref="y2", line=dict(color=COR_ACENTO, dash="dash", width=1.5),
                  annotation_text="80%", annotation_position="right",
                  annotation_font=dict(color=COR_ACENTO, size=10))

    fig.update_layout(
        height=280,
        margin=dict(l=20, r=60, t=28, b=60),
        paper_bgcolor=_BG, plot_bgcolor="#F9FAFB",
        font=dict(family=_FONT, size=11),
        legend=dict(orientation="h", y=1.1, font=dict(size=10, family=_FONT),
                    bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0"),
        xaxis=dict(tickangle=-30, tickfont=dict(size=10, color="#64748B"),
                   gridcolor="#E2E8F0"),
        yaxis=dict(title=dict(text="|GAP| (ton)", font=dict(size=11, color="#94A3B8")),
                   gridcolor="#E2E8F0", tickfont=dict(size=10, color="#94A3B8")),
        yaxis2=dict(title=dict(text="% Acumulado", font=dict(size=11, color=COR_PRIMARIA)),
                    overlaying="y", side="right", range=[0, 110],
                    ticksuffix="%", showgrid=False,
                    tickfont=dict(size=10, color=COR_PRIMARIA)),
    )
    return fig


def _fig_desvio_linhas(
    df_mes: pd.DataFrame, col_plano: str, semanas_com_real: set[int],
) -> go.Figure:
    """Barras horizontais divergentes: desvio % acumulado por linha."""
    df_r = df_mes[df_mes["semana_mes"].isin(semanas_com_real)]
    if df_r.empty:
        return go.Figure()
    grp = df_r.groupby("linha")[["vol_ton", col_plano]].sum().reset_index()
    grp["desvio_pct"] = np.where(
        grp[col_plano] > 0,
        (grp["vol_ton"] - grp[col_plano]) / grp[col_plano] * 100, np.nan,
    )
    grp = grp.dropna(subset=["desvio_pct"]).sort_values("desvio_pct", ascending=True)
    if grp.empty:
        return go.Figure()

    cores = [COR_VERDE if v >= 0 else COR_VERMELHO for v in grp["desvio_pct"]]
    fig = go.Figure(go.Bar(
        x=grp["desvio_pct"], y=grp["linha"],
        orientation="h",
        marker=dict(color=cores, line=dict(width=0)),
        text=[f"{v:+.1f}%" for v in grp["desvio_pct"]],
        textposition="outside",
        textfont=dict(size=11, family=_FONT, color="#1E293B"),
        customdata=list(zip(grp["vol_ton"], grp[col_plano])),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Real: <b>%{customdata[0]:,.0f} ton</b><br>"
            "Plano: <b>%{customdata[1]:,.0f} ton</b><br>"
            "Desvio: <b>%{x:+.1f}%</b><extra></extra>"
        ),
    ))
    fig.add_vline(x=0,   line=dict(color="#94A3B8", width=1.5))
    for v, cor in [(-10, COR_VERMELHO), (10, COR_VERDE)]:
        fig.add_vline(x=v, line=dict(color=cor, width=1, dash="dot"))
    fig.add_annotation(x=10, y=1.04, xref="x", yref="paper",
                       text="+10%", showarrow=False, yanchor="bottom",
                       font=dict(size=9, color=COR_VERDE, family=_FONT))
    fig.add_annotation(x=-10, y=1.04, xref="x", yref="paper",
                       text="&#x2212;10%", showarrow=False, yanchor="bottom",
                       font=dict(size=9, color=COR_VERMELHO, family=_FONT))

    h = max(280, 60 + len(grp) * 36)
    fig.update_layout(
        height=h,
        margin=dict(t=36, b=40, l=180, r=60),
        paper_bgcolor=_BG, plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT, size=11),
        xaxis=dict(title=dict(text="Desvio % (Real &#x2212; Plano)",
                               font=dict(size=11, color="#94A3B8")),
                   gridcolor="#E2E8F0", ticksuffix="%",
                   tickfont=dict(size=10, color="#94A3B8"), zeroline=False),
        yaxis=dict(tickfont=dict(size=11, color="#1E293B"), linecolor="#E2E8F0"),
        showlegend=False,
    )
    return fig


def _fig_waterfall_semanal(
    df_mes: pd.DataFrame, col_plano: str, semanas_com_real: set[int],
) -> go.Figure:
    grp = (
        df_mes.groupby("semana_mes")[["vol_ton", col_plano]]
        .sum().reset_index().sort_values("semana_mes")
    )
    grp = grp[grp["semana_mes"].isin(semanas_com_real)]
    if grp.empty:
        return go.Figure()
    gaps   = (grp["vol_ton"] - grp[col_plano]).tolist()
    labels = [f"Sem {s}" for s in grp["semana_mes"].tolist()]

    fig = go.Figure(go.Waterfall(
        measure=["relative"] * len(gaps) + ["total"],
        x=labels + ["Total"],
        y=gaps + [sum(gaps)],
        text=[f"{v:+,.0f} t" for v in gaps + [sum(gaps)]],
        textposition="outside",
        textfont=dict(size=11, family=_FONT),
        increasing=dict(marker=dict(color="rgba(16,185,129,0.75)")),
        decreasing=dict(marker=dict(color="rgba(239,68,68,0.75)")),
        totals=dict(marker=dict(color=COR_PRIMARIA)),
        connector=dict(line=dict(color="#E2E8F0", width=1.5, dash="dot")),
        hovertemplate="<b>%{x}</b><br>GAP: <b>%{y:+,.0f} ton</b><extra></extra>",
    ))
    fig.update_layout(
        height=290, showlegend=False,
        margin=dict(t=28, b=40, l=60, r=24),
        paper_bgcolor=_BG, plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT, size=11),
        xaxis=dict(tickfont=dict(size=11, color="#64748B"), linecolor="#E2E8F0"),
        yaxis=dict(
            tickformat="+,", gridcolor="#E2E8F0",
            zeroline=True, zerolinecolor="#CBD5E1", zerolinewidth=1.5,
            tickfont=dict(size=10, color="#94A3B8"),
            title=dict(text="GAP (ton)", font=dict(size=11, color="#94A3B8")),
        ),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# TABELA DETALHADA
# ═══════════════════════════════════════════════════════════════════════════════

def _render_tabela(
    df_mes: pd.DataFrame, semanas_com_real: set[int],
    col_plano: str, key_suffix: str,
) -> None:
    df_r = df_mes[df_mes["semana_mes"].isin(semanas_com_real)].copy()
    if df_r.empty:
        st.info("Sem dados para exibir na tabela.")
        return

    metr = []
    for (ger, lin), sub in df_r.groupby(["gerencia", "linha"]):
        m = _calc(sub, col_plano)
        metr.append({
            "Gerência": ger, "Linha": lin,
            "WMAPE":     f"{m['wmape']:.1f}%"  if not np.isnan(m["wmape"])    else "—",
            "Bias":      f"{m['bias']:+.1f}%"  if not np.isnan(m["bias"])     else "—",
            "GAP (ton)": f"{m['gap']:+,.0f}"   if not np.isnan(m["gap"])      else "—",
            "Aderência": f"{m['aderencia']:.0f}%" if not np.isnan(m["aderencia"]) else "—",
        })

    piv_r = (
        df_r.pivot_table(index=["gerencia", "linha"], columns="semana_mes",
                          values="vol_ton", aggfunc="sum")
        .rename(columns=lambda s: f"Real Sem{s}")
    )
    piv_p = (
        df_r.pivot_table(index=["gerencia", "linha"], columns="semana_mes",
                          values=col_plano, aggfunc="sum")
        .rename(columns=lambda s: f"Plano Sem{s}")
    )
    piv = pd.concat([piv_r, piv_p], axis=1).reset_index()
    piv = piv.rename(columns={"gerencia": "Gerência", "linha": "Linha"})

    df_show = pd.merge(pd.DataFrame(metr), piv, on=["Gerência", "Linha"], how="left")
    st.dataframe(df_show, use_container_width=True,
                 height=min(500, 56 + len(df_show) * 36), hide_index=True)

    buf = io.BytesIO()
    df_show.to_excel(buf, index=False, sheet_name="Assertividade")
    buf.seek(0)
    st.download_button("&#x2B07;&#xFE0F; Baixar Excel", buf,
                        f"assertividade_{key_suffix}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{key_suffix}")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOSSÁRIO
# ═══════════════════════════════════════════════════════════════════════════════

def _render_glossario() -> None:
    with st.expander("&#x1F4D6; Gloss&#xe1;rio de termos t&#xe9;cnicos", expanded=False):
        cols = st.columns(2)
        items = list(_GLOSSARIO.items())
        mid = (len(items) + 1) // 2
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
    mes_nome = {
        1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
        7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro",
    }.get(mes_sel, str(mes_sel))

    # Injeta gerência globalmente
    if "gerencia" not in df_f.columns:
        df_f = _add_gerencia(df_f)

    n_sem = len(tw_ranges) if tw_ranges else 4

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E3A5F 0%,#0F2440 100%);
                color:white;padding:22px 28px;border-radius:14px;
                margin-bottom:20px;box-shadow:0 4px 20px rgba(30,58,95,0.20);">
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
            Por qu&ecirc; o plano est&aacute; desviando? Onde? O que fazer?
          </p>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.50);font-family:{_FONT};
                    text-align:right;line-height:1.6;">
          Verde = real acima do plano<br>
          Vermelho = real abaixo do plano
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Dados do mês ─────────────────────────────────────────────────────────
    df_mes_all = df_f[(df_f["ano"] == ano_sel) & (df_f["mes"] == mes_sel)].copy()
    if "gerencia" not in df_mes_all.columns:
        df_mes_all = _add_gerencia(df_mes_all)

    if df_mes_all.empty:
        st.warning(f"Sem dados para {mes_nome}/{ano_sel} com os filtros selecionados.")
        return

    real_por_sem = df_mes_all.groupby("semana_mes")["vol_ton"].sum()
    semanas_com_real: set[int] = set(real_por_sem[real_por_sem > 0].index.tolist())
    if not semanas_com_real:
        st.info(f"Ainda não há realizado registrado em {mes_nome}/{ano_sel}.")
        return

    # ── Filtros inline ────────────────────────────────────────────────────────
    fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
    ger_disp = sorted(df_mes_all["gerencia"].unique().tolist())
    ger_sel  = fcol1.multiselect("Gerência", ger_disp, default=ger_disp, key="assert_ger")
    lin_disp = sorted(df_mes_all["linha"].unique().tolist())
    lin_sel  = fcol2.multiselect("Linha", lin_disp, default=lin_disp, key="assert_lin")

    tem_soe = "meta_soe" in df_mes_all.columns and df_mes_all["meta_soe"].sum() > 0
    tem_sop = "meta_sop" in df_mes_all.columns and df_mes_all["meta_sop"].sum() > 0
    opcoes  = (["S&OE"] if tem_soe else []) + (["S&OP"] if tem_sop else [])
    if not opcoes:
        st.warning("Nenhum plano disponível para este período.")
        return
    plano_ref = fcol3.selectbox(
        "Plano de referência", opcoes,
        index=0, key="assert_plano",
        help="Plano usado nas métricas e gráficos",
    )
    col_plano = "meta_soe" if plano_ref == "S&OE" else "meta_sop"

    df_mes = df_mes_all.copy()
    if ger_sel:  df_mes = df_mes[df_mes["gerencia"].isin(ger_sel)]
    if lin_sel:  df_mes = df_mes[df_mes["linha"].isin(lin_sel)]
    if df_mes.empty:
        st.warning("Nenhum dado com os filtros selecionados.")
        return

    df_kpi = df_mes[df_mes["semana_mes"].isin(semanas_com_real)]
    m = _calc(df_kpi, col_plano)

    # Métricas do mês anterior (para delta nos cards)
    mes_ant = mes_sel - 1 if mes_sel > 1 else 12
    ano_ant = ano_sel if mes_sel > 1 else ano_sel - 1
    df_ant  = df_f[(df_f["ano"] == ano_ant) & (df_f["mes"] == mes_ant)]
    if not df_ant.empty and col_plano in df_ant.columns and df_ant["vol_ton"].sum() > 0:
        sems_ant = set(df_ant.groupby("semana_mes")["vol_ton"].sum()
                       .pipe(lambda s: s[s > 0].index.tolist()))
        df_ant_k = df_ant[df_ant["semana_mes"].isin(sems_ant)]
        m_ant = _calc(df_ant_k, col_plano) if not df_ant_k.empty else None
    else:
        m_ant = None

    # Histórico WMAPE últimos 6 meses (para quadrante + sparklines)
    hist_wmape: list[float | None] = []
    hist_bias:  list[float | None] = []
    hist_labels: list[str] = []
    a_h, m_h = ano_sel, mes_sel
    for _ in range(6):
        m_h -= 1
        if m_h == 0: m_h, a_h = 12, a_h - 1
        sub_h = df_f[(df_f["ano"] == a_h) & (df_f["mes"] == m_h)]
        if sub_h.empty or col_plano not in sub_h.columns or sub_h["vol_ton"].sum() == 0:
            hist_wmape.append(None); hist_bias.append(None)
        else:
            sems_h = set(sub_h.groupby("semana_mes")["vol_ton"].sum()
                         .pipe(lambda s: s[s > 0].index.tolist()))
            s_h = sub_h[sub_h["semana_mes"].isin(sems_h)]
            hist_wmape.append(_wmape(s_h["vol_ton"], s_h[col_plano]))
            hist_bias.append(_bias(s_h["vol_ton"], s_h[col_plano]))
        hist_labels.append(f"{_MESES_ABR.get(m_h,'')}/{str(a_h)[-2:]}")
    hist_wmape.reverse(); hist_bias.reverse(); hist_labels.reverse()

    # ── [1] Banner de Status ──────────────────────────────────────────────────
    banner = _banner_status(m["wmape"], m["bias"], m["aderencia"])
    if banner:
        st.markdown(banner, unsafe_allow_html=True)

    # ── [2] KPI Cards ─────────────────────────────────────────────────────────
    def _delta(cur, prev, inverso=False):
        """Calcula delta e se é positivo (bom)."""
        if prev is None or np.isnan(cur) or np.isnan(prev) or prev == 0:
            return "", None
        d = cur - prev
        if inverso:
            pos = d > 0   # aderência: subir é bom
        else:
            pos = d < 0   # wmape/bias: cair é bom
        return f"{abs(d):.1f}pp vs {_MESES_ABR.get(mes_ant,'ant.')}", pos

    wmape_ant  = m_ant["wmape"]    if m_ant else None
    bias_ant   = m_ant["bias"]     if m_ant else None
    ader_ant   = m_ant["aderencia"]if m_ant else None

    d_wmape_str, d_wmape_pos = _delta(m["wmape"],     wmape_ant)
    d_bias_str,  d_bias_pos  = _delta(abs(m["bias"]) if not np.isnan(m["bias"]) else float("nan"),
                                       abs(bias_ant)  if bias_ant and not np.isnan(bias_ant) else None)
    d_ader_str,  d_ader_pos  = _delta(m["aderencia"], ader_ant, inverso=True)

    spark_w = hist_wmape + [m["wmape"]]
    spark_b = [abs(b) if b is not None and not np.isnan(b) else None for b in hist_bias] + \
              [abs(m["bias"]) if not np.isnan(m["bias"]) else None]
    spark_a = [b for b in hist_bias] + [m["aderencia"]]  # aderência histórica não disponível — ok
    gap_fmt = f"{m['gap']:+,.0f} ton" if not np.isnan(m["gap"]) else "—"
    gap_cor = _cg(m["gap"])

    kc = st.columns(4)
    kc[0].markdown(_kpi_card(
        "WMAPE", f"{m['wmape']:.1f}%" if not np.isnan(m["wmape"]) else "—",
        _cw(m["wmape"]), "erro médio ponderado",
        d_wmape_str, d_wmape_pos, spark_w, _GLOSSARIO["WMAPE"],
    ), unsafe_allow_html=True)
    kc[1].markdown(_kpi_card(
        "Bias", f"{m['bias']:+.1f}%" if not np.isnan(m["bias"]) else "—",
        _cb(m["bias"]), "positivo = sobreplanejamento",
        d_bias_str, d_bias_pos, spark_b, _GLOSSARIO["Bias"],
    ), unsafe_allow_html=True)
    kc[2].markdown(_kpi_card(
        "Aderência", f"{m['aderencia']:.0f}%" if not np.isnan(m["aderencia"]) else "—",
        _ca(m["aderencia"]), "semanas dentro de ±10%",
        d_ader_str, d_ader_pos, spark_a, _GLOSSARIO["Aderência"],
    ), unsafe_allow_html=True)
    kc[3].markdown(_kpi_card(
        "GAP Acumulado", gap_fmt, gap_cor,
        "real vs plano (ton)", "", None,
        [v for v in hist_wmape if v is not None], _GLOSSARIO["GAP Acumulado"],
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

    # ── [3] Quadrante Diagnóstico + Recomendações ─────────────────────────────
    _secao("Diagnóstico — Qual é o tipo do problema?")

    # Tendência do bias (para diagnóstico de viés crescente)
    grp_bias = (
        df_kpi.groupby("semana_mes")[["vol_ton", col_plano]]
        .sum().reset_index().sort_values("semana_mes")
    )
    bias_por_sem = [
        _bias(grp_bias.loc[grp_bias["semana_mes"]==s, "vol_ton"],
              grp_bias.loc[grp_bias["semana_mes"]==s, col_plano])
        for s in grp_bias["semana_mes"]
    ]
    b_clean = [b for b in bias_por_sem if not np.isnan(b)]
    tend_coef: float | None = None
    if len(b_clean) >= 3:
        x_arr = np.arange(len(b_clean), dtype=float)
        tend_coef = float(np.polyfit(x_arr, b_clean, 1)[0])

    diag_tipos    = _tipo_desvio(m["wmape"], m["bias"], m["aderencia"], tend_coef)
    df_linhas_gap = (
        df_kpi.groupby("linha")[["vol_ton", col_plano]]
        .sum().reset_index()
        .assign(gap=lambda d: d["vol_ton"] - d[col_plano])
    )
    conc  = _tipo_concentracao(df_linhas_gap)
    croni = _tipo_cronicidade(m["wmape"], hist_wmape)

    q_col, r_col = st.columns([1, 1])
    with q_col:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
            f'margin-bottom:8px;font-family:{_FONT};">'
            f'Posicionamento: WMAPE × Bias</div>'
            f'<div style="font-size:11px;color:#94A3B8;margin-bottom:10px;'
            f'font-family:{_FONT};">Ponto laranja = período atual · '
            f'Cinza tracejado = meses anteriores</div>',
            unsafe_allow_html=True,
        )
        fig_q = _fig_quadrante(
            m["wmape"], m["bias"], hist_wmape, hist_bias, hist_labels,
        )
        st.plotly_chart(fig_q, use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"quad_{ano_sel}_{mes_sel}_{plano_ref}")

    with r_col:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
            f'margin-bottom:8px;font-family:{_FONT};">'
            f'Diagnóstico e Ações Recomendadas</div>',
            unsafe_allow_html=True,
        )
        _render_recomendacoes(diag_tipos, [conc, croni])

    # ── [4] Heatmap Gerência × Linha ──────────────────────────────────────────
    _secao("Onde está o problema? — Mapa Gerência × Linha")

    st.caption(
        "Cor = WMAPE da combinação. Verde = dentro da meta (≤10%) · "
        "Vermelho = desvio alto. Seta ↑ = sobreplanejamento · ↓ = subplanejamento."
    )
    fig_hm = _fig_heatmap_ger_linha(df_mes, col_plano, semanas_com_real)
    st.plotly_chart(fig_hm, use_container_width=True,
                    config={"displayModeBar": False},
                    key=f"hm_ger_{ano_sel}_{mes_sel}_{plano_ref}")

    # ── [5] Tendência do Bias ─────────────────────────────────────────────────
    _secao("Está melhorando ou piorando? — Tendência do Bias")

    st.caption(
        "Banda verde = zona OK (±5%). Linha azul = Bias semanal. "
        "Linha pontilhada = WMAPE (eixo direito). "
        "Linha tracejada = tendência do bias nas últimas semanas."
    )
    fig_tb, coef_final = _fig_tendencia_bias(df_mes, col_plano, semanas_com_real)
    st.plotly_chart(fig_tb, use_container_width=True,
                    config={"displayModeBar": False},
                    key=f"tend_bias_{ano_sel}_{mes_sel}_{plano_ref}")

    if abs(coef_final) > 1:
        dir_pt = "aumentando" if coef_final > 0 else "diminuindo"
        cor_info = COR_VERMELHO if coef_final > 0 else COR_VERDE
        st.markdown(
            f'<div style="background:{cor_info}15;border-left:3px solid {cor_info};'
            f'border-radius:6px;padding:8px 14px;font-size:12px;color:#374151;'
            f'font-family:{_FONT};margin-top:-8px;">'
            f'&#x1F4CA; Tend&ecirc;ncia do bias: <b style="color:{cor_info};">'
            f'{dir_pt} {abs(coef_final):.1f} p.p./semana</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── [6] FVA ───────────────────────────────────────────────────────────────
    if tem_soe and tem_sop:
        _secao("O ajuste comercial ajudou? — FVA (S&OE vs S&OP)")

        m_soe = _calc(df_kpi, "meta_soe")
        m_sop = _calc(df_kpi, "meta_sop")
        wmape_soe = m_soe["wmape"] if not np.isnan(m_soe["wmape"]) else None
        wmape_sop = m_sop["wmape"] if not np.isnan(m_sop["wmape"]) else None

        fva1, fva2 = st.columns([1, 1])
        with fva1:
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
                f'margin-bottom:8px;font-family:{_FONT};">Waterfall de Valor Adicionado</div>',
                unsafe_allow_html=True,
            )
            if wmape_soe is not None and wmape_sop is not None:
                fig_fva_wf = _fig_fva_waterfall(wmape_sop, wmape_soe)
                st.plotly_chart(fig_fva_wf, use_container_width=True,
                                config={"displayModeBar": False},
                                key=f"fva_wf_{ano_sel}_{mes_sel}")
            else:
                st.info("WMAPE de um dos planos não disponível.")

        with fva2:
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
                f'margin-bottom:8px;font-family:{_FONT};">Histórico WMAPE 6 meses</div>',
                unsafe_allow_html=True,
            )
            fig_fva_h = _fig_fva_historico(df_f, ano_sel, mes_sel)
            st.plotly_chart(fig_fva_h, use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"fva_hist_{ano_sel}_{mes_sel}")

    # ── [7] Pareto + Desvio por Linha ─────────────────────────────────────────
    _secao("Quais linhas concentram o desvio?")

    p_col, d_col = st.columns([1, 1])
    with p_col:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
            f'margin-bottom:6px;font-family:{_FONT};">Pareto de Concentração</div>'
            f'<div style="font-size:11px;color:#94A3B8;margin-bottom:8px;'
            f'font-family:{_FONT};">80% do desvio está em quais linhas?</div>',
            unsafe_allow_html=True,
        )
        fig_par = _fig_pareto_linhas(df_linhas_gap)
        st.plotly_chart(fig_par, use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"pareto_{ano_sel}_{mes_sel}_{plano_ref}")

    with d_col:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;color:{COR_PRIMARIA};'
            f'margin-bottom:6px;font-family:{_FONT};">Desvio % por Linha</div>'
            f'<div style="font-size:11px;color:#94A3B8;margin-bottom:8px;'
            f'font-family:{_FONT};">Verde = real acima · Vermelho = real abaixo · '
            f'Faixas = &plusmn;10%</div>',
            unsafe_allow_html=True,
        )
        fig_dev = _fig_desvio_linhas(df_mes, col_plano, semanas_com_real)
        st.plotly_chart(fig_dev, use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"desvio_lin_{ano_sel}_{mes_sel}_{plano_ref}")

    # ── [8] Waterfall técnico ─────────────────────────────────────────────────
    with st.expander("&#x1F4CA; Detalhe técnico — Decomposição do GAP por semana",
                     expanded=False):
        st.caption(
            "Cada barra = gap (Real − Plano) da semana. "
            "Verde = semana acima do plano · Vermelho = semana abaixo · "
            "Azul = total do período."
        )
        fig_wf = _fig_waterfall_semanal(df_mes, col_plano, semanas_com_real)
        st.plotly_chart(fig_wf, use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"wfall_{ano_sel}_{mes_sel}_{plano_ref}")

    # ── [9] Tabela ─────────────────────────────────────────────────────────────
    with st.expander("&#x1F4CB; Tabela Detalhada — Ger&ecirc;ncia &times; Linha &times; Semana",
                     expanded=False):
        _render_tabela(df_mes, semanas_com_real, col_plano,
                       f"{ano_sel}_{mes_sel}_{plano_ref}")

    # ── [10] Glossário ─────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
    _render_glossario()
