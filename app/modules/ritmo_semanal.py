"""
Módulo de interface Streamlit — Aba "Ritmo Semanal".

Extraído do dashboard.py original. Toda a lógica de renderização
da aba de ritmo semanal está aqui, exposta via render().
"""
from __future__ import annotations

import calendar as _cal_mod
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Calendário TW — importado do módulo centralizado ─────────────────────────
from utils.calendar_tw import get_month_tw_ranges, day_to_semana_tw

# ── Visual — importado do módulo centralizado ─────────────────────────────────
from utils.visual import (
    COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_FUNDO, COR_CARD, COR_TEXTO, COR_GRID,
    fmt_ton as _fmt_ton, cor_ritmo, icone_ritmo, cor_bg_ritmo, seta_tendencia,
)

MESES = {1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',
         6:'Junho',7:'Julho',8:'Agosto',9:'Setembro',
         10:'Outubro',11:'Novembro',12:'Dezembro'}


# ── Helpers de formatação e cor ───────────────────────────────────────────────
def _fmt_ton(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ''
    return f'{int(round(v)):,}'.replace(',', '.')


def cor_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return '#6C757D'
    if pct >= 0.90:
        return COR_VERDE
    elif pct >= 0.75:
        return COR_AMARELO
    return COR_VERMELHO


def icone_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return '—'
    if pct >= 0.90: return '🟢'
    if pct >= 0.75: return '🟡'
    return '🔴'


def cor_bg_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return '#F8F9FA'
    if pct >= 0.90: return '#D4EDDA'
    if pct >= 0.75: return '#FFF3CD'
    return '#F8D7DA'


def seta_tendencia(var) -> str:
    if var is None or (isinstance(var, float) and np.isnan(var)):
        return '→'
    if var > 0.05:  return '↑'
    if var < -0.05: return '↓'
    return '→'


# ── Pesos históricos ──────────────────────────────────────────────────────────
def get_peso(pesos: dict, linha: str, semana: int) -> float:
    fallback = {1: 0.160, 2: 0.226, 3: 0.233, 4: 0.381}
    if linha in pesos and semana in pesos[linha]:
        return pesos[linha][semana]
    return fallback.get(semana, 0.25)


def peso_acumulado(pesos: dict, linha: str, semana_atual: int) -> float:
    return sum(get_peso(pesos, linha, s) for s in range(1, semana_atual + 1))


# ── Gauge Plotly ──────────────────────────────────────────────────────────────
def make_gauge(valor_pct, titulo: str, height: int = 180) -> go.Figure:
    if valor_pct is None or (isinstance(valor_pct, float) and np.isnan(valor_pct)):
        valor_pct = 0.0
    cor = cor_ritmo(valor_pct)
    pct_display = min(valor_pct * 100, 130)

    fig = go.Figure(go.Indicator(
        mode="gauge", value=pct_display,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 120], 'tickwidth': 1, 'tickcolor': '#B0BEC5',
                     'tickfont': {'size': 8, 'color': '#90A4AE'}, 'nticks': 7},
            'bar': {'color': cor, 'thickness': 0.65},
            'bgcolor': '#F8F9FA', 'borderwidth': 0,
            'steps': [
                {'range': [0,  75],  'color': '#F5D5D1'},
                {'range': [75, 90],  'color': '#F5E9C8'},
                {'range': [90, 120], 'color': '#D6EDE0'},
            ],
            'threshold': {'line': {'color': COR_PRIMARIA, 'width': 3},
                          'thickness': 0.8, 'value': 100},
        },
    ))
    fig.add_annotation(
        x=0.5, y=0.18, xref='paper', yref='paper',
        text=f'<b>{pct_display:.1f}%</b>', showarrow=False,
        font=dict(size=20, color=cor, family='Arial'),
        align='center', xanchor='center', yanchor='middle',
    )
    fig.update_layout(
        title={'text': f'<b>{titulo}</b>', 'x': 0.5, 'xanchor': 'center',
               'font': {'size': 13, 'color': COR_PRIMARIA, 'family': 'Arial'},
               'y': 0.97, 'yanchor': 'top'},
        height=height, margin=dict(t=36, b=16, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Arial'},
    )
    return fig


def _gauge_sub(realizado, meta) -> str:
    if realizado is None or meta is None:
        return ''
    r_fmt = f'{realizado:,.0f}'.replace(',', '.')
    m_fmt = f'{meta:,.0f}'.replace(',', '.')
    return (f'<div style="text-align:center;font-size:11px;color:#546E7A;'
            f'margin-top:-8px;padding-bottom:4px;"><b>{r_fmt}</b> / {m_fmt} ton</div>')


# ── Gráfico diário ────────────────────────────────────────────────────────────
def graf_diario(df_v_mes: pd.DataFrame, meta_mes_vol: float,
                ano: int, mes: int, dia_ref_externo=None) -> go.Figure:
    # timedelta já importado no topo do módulo — não precisa re-importar aqui
    dias_no_mes = _cal_mod.monthrange(ano, mes)[1]
    todos_dias  = pd.DataFrame({'dia': range(1, dias_no_mes + 1)})
    vendas_dia  = (df_v_mes.groupby('dia')['vol_ton'].sum().reset_index()
                   if not df_v_mes.empty
                   else pd.DataFrame({'dia': pd.Series(dtype=int),
                                      'vol_ton': pd.Series(dtype=float)}))
    diario = todos_dias.merge(vendas_dia, on='dia', how='left').fillna(0)

    dias_uteis_mes   = [d for d in range(1, dias_no_mes+1) if date(ano, mes, d).weekday() < 5]
    n_dias_uteis_mes = max(1, len(dias_uteis_mes))
    ritmo_dia        = meta_mes_vol / n_dias_uteis_mes

    hoje_loc = date.today()
    if dia_ref_externo is not None:
        dia_ref = dia_ref_externo
    elif hoje_loc.year == ano and hoje_loc.month == mes:
        dia_ref = hoje_loc.day
    else:
        dia_ref = dias_no_mes

    vol_realizado    = diario[diario['dia'] < dia_ref]['vol_ton'].sum()
    dias_uteis_rest  = [d for d in dias_uteis_mes if d >= dia_ref]
    n_rest           = max(1, len(dias_uteis_rest))
    meta_restante    = max(0, meta_mes_vol - vol_realizado)
    ctg_dia          = meta_restante / n_rest

    fig   = go.Figure()
    cores = ['#CFD8DC' if date(ano, mes, int(d)).weekday() >= 5 else '#1B6CA8'
             for d in diario['dia']]
    fig.add_trace(go.Bar(x=diario['dia'], y=diario['vol_ton'], name='Realizado',
                         marker_color=cores,
                         hovertemplate='Dia %{x}: <b>%{y:,.0f} ton</b><extra></extra>'))

    gap_x_pos, gap_y_pos, gap_x_neg, gap_y_neg = [], [], [], []
    for _, row in diario.iterrows():
        d = int(row['dia'])
        if date(ano, mes, d).weekday() >= 5 or d >= dia_ref or row['vol_ton'] == 0:
            continue
        delta = row['vol_ton'] - ritmo_dia
        if delta >= 0:
            gap_x_pos.append(d); gap_y_pos.append(delta)
        else:
            gap_x_neg.append(d); gap_y_neg.append(abs(delta))

    BAR_GAP_W = 0.25
    if gap_x_pos:
        bases = [float(diario.loc[diario['dia']==d, 'vol_ton'].iloc[0]) for d in gap_x_pos]
        fig.add_trace(go.Bar(x=gap_x_pos, y=gap_y_pos, name='Acima da meta/dia',
                             base=bases, width=BAR_GAP_W,
                             marker_color='rgba(40,167,69,0.70)',
                             marker_line=dict(color='rgba(40,167,69,0.9)', width=1),
                             customdata=[round(v) for v in gap_y_pos],
                             hovertemplate='Dia %{x}: +%{customdata:,.0f} ton acima da meta/dia<extra></extra>'))
    if gap_x_neg:
        bases = [float(diario.loc[diario['dia']==d, 'vol_ton'].iloc[0]) for d in gap_x_neg]
        alt   = [ritmo_dia - b for b in bases]
        fig.add_trace(go.Bar(x=gap_x_neg, y=alt, name='Abaixo da meta/dia',
                             base=bases, width=BAR_GAP_W,
                             marker_color='rgba(220,53,69,0.60)',
                             marker_line=dict(color='rgba(220,53,69,0.85)', width=1),
                             customdata=[round(v) for v in gap_y_neg],
                             hovertemplate='Dia %{x}: -%{customdata:,.0f} ton abaixo da meta/dia<extra></extra>'))

    fig.add_trace(go.Scatter(x=dias_uteis_mes, y=[ritmo_dia]*len(dias_uteis_mes),
                             name=f'Meta/dia útil ({_fmt_ton(ritmo_dia)} ton)',
                             mode='markers',
                             marker=dict(symbol='line-ew', size=10, color=COR_ACENTO,
                                         line=dict(color=COR_ACENTO, width=2)),
                             hovertemplate=f'Meta/dia útil: {ritmo_dia:,.0f} ton<extra></extra>'))
    if dias_uteis_rest and meta_restante > 0:
        fig.add_trace(go.Scatter(x=dias_uteis_rest, y=[ctg_dia]*len(dias_uteis_rest),
                                 name=f'Close the gap ({_fmt_ton(ctg_dia)} ton/d.ú.)',
                                 mode='lines+markers',
                                 line=dict(color='#7B1FA2', width=2.5, dash='dashdot'),
                                 marker=dict(size=7, color='#7B1FA2'),
                                 hovertemplate=(f'Dia %{{x}} — necessário: <b>{ctg_dia:,.0f} ton</b><br>'
                                                f'Faltam {_fmt_ton(meta_restante)} ton em {n_rest} d.ú.<extra></extra>')))
        fig.add_annotation(x=dias_uteis_rest[0], y=ctg_dia,
                           text=f'<b>{_fmt_ton(ctg_dia)}</b> ton/d',
                           showarrow=False, yshift=14,
                           font=dict(size=10, color='#7B1FA2', family='Arial'),
                           bgcolor='rgba(255,255,255,0.7)')

    y_max = max(diario['vol_ton'].max() if not diario.empty else 0,
                ritmo_dia,
                ctg_dia if (dias_uteis_rest and meta_restante > 0) else 0) * 1.30
    fig.update_layout(
        height=300, margin=dict(t=10, b=40, l=60, r=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Dia do mês', tickmode='linear', dtick=1,
                   range=[0.5, dias_no_mes+0.5], gridcolor=COR_GRID, gridwidth=1),
        yaxis=dict(title='Volume (ton)', gridcolor=COR_GRID, gridwidth=1, range=[0, y_max]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=10)),
        font=dict(family='Arial', size=11, color=COR_TEXTO), barmode='overlay',
    )
    return fig


# ── Gráfico semanal ───────────────────────────────────────────────────────────
def graf_semanal(df_mes: pd.DataFrame, col_meta: str, semana_atual: int,
                 col_meta_label: str, tw_ranges=None) -> go.Figure:
    if tw_ranges is None:
        tw_ranges = [(1,1,7),(2,8,14),(3,15,21),(4,22,31)]
    semanas = [r[0] for r in tw_ranges]
    nomes   = [f'Sem {r[0]}\n({r[1]}–{r[2]})' for r in tw_ranges]
    real_sem = df_mes.groupby('semana_mes')['vol_ton'].sum()
    meta_sem = df_mes.groupby('semana_mes')[col_meta].sum()
    real_vals = [real_sem.get(s, 0) for s in semanas]
    meta_vals = [meta_sem.get(s, 0) for s in semanas]
    cores_real = []
    for s in semanas:
        if s > semana_atual:
            cores_real.append('#CFD8DC')
        else:
            r, m = real_sem.get(s, 0), meta_sem.get(s, 0)
            cores_real.append(cor_ritmo(r/m if m > 0 else None))
    annotations = []
    for i, s in enumerate(semanas):
        if s <= semana_atual:
            r, m = real_sem.get(s, 0), meta_sem.get(s, 0)
            if m > 0:
                pct = r/m*100
                y_ann = max(real_vals[i], meta_vals[i]) * 1.14
                annotations.append(dict(x=nomes[i], y=y_ann, text=f'<b>{pct:.0f}%</b>',
                                        showarrow=False,
                                        font=dict(size=13, color=cor_ritmo(r/m), family='Arial'),
                                        xanchor='center'))
    y_max = max((max(real_vals+meta_vals) if real_vals+meta_vals else 1), 1) * 1.35
    fig = go.Figure()
    fig.add_trace(go.Bar(name=col_meta_label, x=nomes, y=meta_vals,
                         marker_color=COR_ACENTO, opacity=0.45,
                         text=[_fmt_ton(v) if v > 0 else '' for v in meta_vals],
                         textposition='inside', textfont=dict(size=10, color='#555'),
                         hovertemplate='<b>%{x}</b><br>'+col_meta_label+': %{customdata} ton<extra></extra>',
                         customdata=[_fmt_ton(v) for v in meta_vals]))
    fig.add_trace(go.Bar(name='Realizado', x=nomes, y=real_vals,
                         marker_color=cores_real,
                         marker_line=dict(color='rgba(0,0,0,0.12)', width=1),
                         text=[_fmt_ton(v) if v > 0 else '' for v in real_vals],
                         textposition='inside', textfont=dict(size=11, color='white', family='Arial'),
                         hovertemplate='<b>%{x}</b><br>Realizado: %{customdata} ton<extra></extra>',
                         customdata=[_fmt_ton(v) for v in real_vals], cliponaxis=False))
    fig.update_layout(
        barmode='group', bargap=0.30, bargroupgap=0.06, height=270,
        margin=dict(t=10, b=10, l=60, r=20), annotations=annotations,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor=COR_GRID, tickfont=dict(size=11)),
        yaxis=dict(title='Volume (ton)', gridcolor=COR_GRID, range=[0, y_max], tickformat=','),
        legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
    )
    return fig


# ── Gráfico por família ───────────────────────────────────────────────────────
def graf_familia_barras(df_sub: pd.DataFrame, familia_nome: str,
                        fator_proj: float, chart_key: str) -> None:
    if df_sub.empty:
        return
    df_sub  = df_sub.sort_values('vol_real', ascending=False)
    linhas  = df_sub['linha'].tolist()
    real    = df_sub['vol_real'].tolist()
    meta_ac = df_sub['meta_acum'].tolist()
    proj    = [r * fator_proj for r in real]
    cores_real = [cor_ritmo(r/m if m > 0 else None) for r, m in zip(real, meta_ac)]
    y_max = max((max(real+meta_ac+proj) if real else 1), 1) * 1.28
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Projeção', x=linhas, y=proj,
                         marker_color=COR_PRIMARIA, opacity=0.15,
                         hovertemplate='%{x}<br>Projeção: %{customdata} ton<extra></extra>',
                         customdata=[_fmt_ton(v) for v in proj]))
    fig.add_trace(go.Bar(name='Meta acum.', x=linhas, y=meta_ac,
                         marker_color=COR_ACENTO, opacity=0.50,
                         hovertemplate='%{x}<br>Meta acum.: %{customdata} ton<extra></extra>',
                         customdata=[_fmt_ton(v) for v in meta_ac]))
    fig.add_trace(go.Bar(name='Realizado', x=linhas, y=real,
                         marker_color=cores_real,
                         marker_line=dict(color='rgba(0,0,0,0.12)', width=1),
                         text=[_fmt_ton(v) for v in real], textposition='outside',
                         textfont=dict(size=11, color=COR_TEXTO), cliponaxis=False,
                         hovertemplate='%{x}<br>Realizado: %{customdata} ton<extra></extra>',
                         customdata=[_fmt_ton(v) for v in real]))
    h = max(230, 200 + len(linhas) * 18)
    fig.update_layout(
        title=dict(text=f'<b>{familia_nome}</b>',
                   font=dict(size=13, color=COR_PRIMARIA, family='Arial'), x=0, xanchor='left'),
        barmode='group', bargap=0.28, bargroupgap=0.06, height=h,
        margin=dict(t=40, b=60, l=55, r=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickangle=-30, gridcolor=COR_GRID, tickfont=dict(size=11)),
        yaxis=dict(title='ton', gridcolor=COR_GRID, gridwidth=1, range=[0, y_max], tickformat=','),
        legend=dict(orientation='h', y=1.12, x=1, xanchor='right', font=dict(size=10)),
        uniformtext=dict(mode='hide', minsize=8),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)


# ── Tabela estilizada ─────────────────────────────────────────────────────────
def tabela_styled(df_tab: pd.DataFrame, chave_col: str = 'Linha'):
    def style_row(row):
        rh = row.get('Ritmo (%)', None)
        try:
            rh_val = float(str(rh).replace('%','').replace(',','.').strip()) / 100
        except Exception:
            rh_val = None
        bg = cor_bg_ritmo(rh_val)
        styles = []
        for c in row.index:
            if c in ('Ritmo (%)', 'Status', 'Tend.'):
                styles.append(f'background-color:{bg};text-align:center')
            elif c in (chave_col, 'UF'):
                styles.append('font-weight:600;text-align:left')
            elif c in ('Gap Fech. (ton)', 'Gap Fech. (%)', 'Gap (ton)', 'Gap (%)'):
                try:
                    gv = float(str(row[c]).replace(',','').replace('+',''))
                    g_bg = '#F8D7DA' if gv > 0 else '#D4EDDA' if gv < 0 else ''
                    styles.append(f'background-color:{g_bg};text-align:right')
                except Exception:
                    styles.append('text-align:right')
            else:
                styles.append('text-align:right')
        return styles
    return df_tab.style.apply(style_row, axis=1)


# ── Função principal de renderização ─────────────────────────────────────────
def render(df_f: pd.DataFrame, df_v_raw: pd.DataFrame, pesos: dict,
           col_meta: str, label_meta: str,
           ano_sel: int, mes_sel: int, filtros_ativos: list[str]) -> None:
    """
    Renderiza a aba de Ritmo Semanal completa.

    Parameters
    ----------
    df_f           : dados agregados por semana (já filtrados)
    df_v_raw       : vendas diárias (já filtradas)
    pesos          : dict de pesos históricos por linha
    col_meta       : 'meta_sop' ou 'meta_soe'
    label_meta     : 'Plano S&OP' ou 'Programa S&OE'
    ano_sel        : ano selecionado
    mes_sel        : mês selecionado
    filtros_ativos : lista de strings descrevendo filtros ativos (para o header)
    """
    hoje     = date.today()
    dia_hoje = (hoje.day if (hoje.year == ano_sel and hoje.month == mes_sel)
                else _cal_mod.monthrange(ano_sel, mes_sel)[1])

    if ano_sel >= 2026:
        tw_ranges    = get_month_tw_ranges(ano_sel, mes_sel)
        semana_atual = day_to_semana_tw(ano_sel, mes_sel, dia_hoje) or len(tw_ranges)
        n_semanas    = len(tw_ranges)
    else:
        tw_ranges    = [(1,1,7),(2,8,14),(3,15,21),(4,22,_cal_mod.monthrange(ano_sel,mes_sel)[1])]
        semana_atual = int(pd.cut([dia_hoje], bins=[0,7,14,21,31], labels=[1,2,3,4])[0])
        n_semanas    = 4

    pct_esperado = sum(1/n_semanas for s in range(1, semana_atual+1))
    df_mes  = df_f[(df_f['ano'] == ano_sel) & (df_f['mes'] == mes_sel)].copy()
    df_acum = df_mes[df_mes['semana_mes'] <= semana_atual].copy()

    # ── Header ────────────────────────────────────────────────────
    mes_label  = MESES[mes_sel]
    filtro_str = ' · '.join(filtros_ativos) if filtros_ativos else 'Todas as empresas'
    ctx_pct    = f'{pct_esperado:.0%}'
    st.markdown(f"""
    <div class="aba-header">
      <h2>{label_meta} <span class="badge-semana">Sem. {semana_atual} de {n_semanas}</span></h2>
      <p>{filtro_str} &nbsp;|&nbsp; {mes_label}/{ano_sel} &nbsp;|&nbsp;
         Você está na semana {semana_atual}. O padrão histórico espera
         <strong>{ctx_pct}</strong> do volume mensal neste ponto.</p>
    </div>""", unsafe_allow_html=True)

    if df_mes.empty:
        st.warning(f"Sem dados para {mes_label}/{ano_sel} com os filtros selecionados.")
        return

    _render_body(df_f, df_v_raw, df_mes, df_acum, pesos, col_meta, label_meta,
                 ano_sel, mes_sel, semana_atual, n_semanas, pct_esperado,
                 tw_ranges, dia_hoje)


# ── Corpo da renderização (separado para manter render() legível) ─────────────
def _render_body(df_f, df_v_raw, df_mes, df_acum, pesos, col_meta, label_meta,
                 ano_sel, mes_sel, semana_atual, n_semanas, pct_esperado,
                 tw_ranges, dia_hoje):
    import calendar as _cal
    dias_no_mes = _cal.monthrange(ano_sel, mes_sel)[1]

    df_v_mes_tmp = df_v_raw[(df_v_raw['ano']==ano_sel) & (df_v_raw['mes']==mes_sel)]
    if not df_v_mes_tmp.empty and 'dia' in df_v_mes_tmp.columns:
        dia_ref = int(df_v_mes_tmp['dia'].max())
    else:
        hoje_loc = date.today()
        dia_ref  = hoje_loc.day if (hoje_loc.year==ano_sel and hoje_loc.month==mes_sel) else dias_no_mes
    dia_ref = max(1, dia_ref)
    fator_proj = dias_no_mes / dia_ref

    total_real_vol = df_acum['vol_ton'].sum()
    total_real_val = df_acum['val_mm'].sum()
    total_meta_mes = df_mes[col_meta].sum()
    meta_acum_esp  = total_meta_mes * pct_esperado
    ritmo_geral    = total_real_vol / meta_acum_esp if meta_acum_esp > 0 else None
    proj_vol_geral = total_real_vol * fator_proj
    preco_real     = (total_real_val / total_real_vol * 1000) if total_real_vol > 0 else None

    mes_ant = mes_sel - 1 if mes_sel > 1 else 12
    ano_ant = ano_sel if mes_sel > 1 else ano_sel - 1
    df_ant_p  = df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                     (df_f['semana_mes']<=semana_atual)]
    vol_ant_p = df_ant_p['vol_ton'].sum()
    val_ant_p = df_ant_p['val_mm'].sum()
    preco_ant = (val_ant_p / vol_ant_p * 1000) if vol_ant_p > 0 else None
    var_preco = ((preco_real - preco_ant) / preco_ant
                 if (preco_real and preco_ant and preco_ant > 0) else None)

    gap_vol = proj_vol_geral - total_meta_mes
    gap_pct = gap_vol / total_meta_mes if total_meta_mes > 0 else None
    desvio_vol = (total_real_vol - meta_acum_esp) / meta_acum_esp if meta_acum_esp > 0 else None

    # ── Cards de Ritmo ────────────────────────────────────────────
    st.markdown('<div class="secao-titulo">Ritmo Geral</div>', unsafe_allow_html=True)

    cor_vol      = cor_ritmo(ritmo_geral)
    desvio_abs   = total_real_vol - meta_acum_esp
    desvio_sinal = '+' if desvio_abs >= 0 else ''
    gap_fech     = total_meta_mes - proj_vol_geral
    gap_cor      = '#C0392B' if gap_fech > 0 else '#1A7A40'
    gap_label    = (f'{_fmt_ton(abs(gap_fech))} ton a fechar' if gap_fech > 0
                    else f'{_fmt_ton(abs(gap_fech))} ton acima do plano')
    ating_pct    = proj_vol_geral / total_meta_mes if total_meta_mes > 0 else None
    ating_cor    = '#1A7A40' if (ating_pct or 0) >= 1.0 else '#C0392B'
    ating_txt    = f'{ating_pct:.0%} da meta' if ating_pct is not None else '—'
    desvio_pct_txt = f'({desvio_vol:+.1%})' if desvio_vol is not None else ''

    vol_ant_mes = df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                       (df_f['semana_mes']<=semana_atual)]['vol_ton'].sum()
    var_vol_mm  = (total_real_vol - vol_ant_mes) / vol_ant_mes if vol_ant_mes > 0 else None
    var_vol_cor = '#1A7A40' if (var_vol_mm or 0) >= 0 else '#C0392B'
    _vv_sinal   = '+' if (var_vol_mm or 0) >= 0 else ''
    var_vol_txt = f'{_vv_sinal}{var_vol_mm:.1%} vs mes ant.' if var_vol_mm is not None else 'sem historico'

    val_mm_disp = total_real_val / 1000
    proj_val_mm = total_real_val * fator_proj / 1000
    val_ant_mm  = df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                       (df_f['semana_mes']<=semana_atual)]['val_mm'].sum() / 1000
    var_val_mm  = (total_real_val/1000 - val_ant_mm) / val_ant_mm if val_ant_mm > 0 else None
    var_val_cor = '#1A7A40' if (var_val_mm or 0) >= 0 else '#C0392B'
    _vval_sinal = '+' if (var_val_mm or 0) >= 0 else ''
    var_val_txt = f'{_vval_sinal}{var_val_mm:.1%} vs mes ant.' if var_val_mm is not None else ''

    preco_txt     = f"R$ {int(preco_real):,}/ton".replace(',','.') if preco_real else '—'
    preco_ant_txt = f"R$ {int(preco_ant):,}/ton".replace(',','.') if preco_ant else '—'
    var_preco_cor = '#1A7A40' if (var_preco or 0) >= 0 else '#C0392B'
    _vp_sinal     = '+' if (var_preco or 0) >= 0 else ''
    var_preco_txt = f'{_vp_sinal}{var_preco:.1%}' if var_preco is not None else '—'

    c1, c2, c3, c4 = st.columns([1, 1.1, 0.9, 0.9])
    with c1:
        fig_g = make_gauge(ritmo_geral or 0.0, 'Ritmo Geral', height=200)
        st.plotly_chart(fig_g, use_container_width=True,
                        config={'displayModeBar': False}, key=f'{col_meta}_gauge_geral')
        st.markdown(_gauge_sub(total_real_vol, meta_acum_esp), unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            f'border-top:4px solid {cor_vol};box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#6C757D;margin-bottom:4px">VOLUME REALIZADO</div>'
            f'<div style="font-size:26px;font-weight:800;color:{cor_vol};line-height:1.1;margin-bottom:8px">{_fmt_ton(total_real_vol)} ton</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Meta acum.: <b>{_fmt_ton(meta_acum_esp)} ton</b> &nbsp;|&nbsp; '
            f'<span style="color:{cor_vol}">{desvio_sinal}{_fmt_ton(desvio_abs)} ton {desvio_pct_txt}</span></div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Proj. mes: <b>{_fmt_ton(proj_vol_geral)} ton</b> '
            f'<span style="color:{ating_cor}">({ating_txt})</span></div>'
            f'<div style="font-size:11px">Gap: <span style="color:{gap_cor};font-weight:700">{gap_label}</span> &nbsp;|&nbsp; '
            f'<span style="color:{var_vol_cor}">{var_vol_txt}</span></div></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            f'border-top:4px solid #F4822A;box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#6C757D;margin-bottom:4px">PRECO MEDIO</div>'
            f'<div style="font-size:26px;font-weight:800;color:#1B2A4A;line-height:1.1;margin-bottom:8px">{preco_txt}</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Mes ant.: <b>{preco_ant_txt}</b></div>'
            f'<div style="font-size:11px;color:#2C3E50">Variacao: <span style="color:{var_preco_cor};font-weight:700">{var_preco_txt}</span></div></div>',
            unsafe_allow_html=True)
    with c4:
        st.markdown(
            f'<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            f'border-top:4px solid #1B2A4A;box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#6C757D;margin-bottom:4px">VALOR REALIZADO</div>'
            f'<div style="font-size:26px;font-weight:800;color:#1B2A4A;line-height:1.1;margin-bottom:8px">R$ {val_mm_disp:.1f} MM</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Proj. mes: <b>R$ {proj_val_mm:.1f} MM</b></div>'
            f'<div style="font-size:11px;color:{var_val_cor}">{var_val_txt}</div></div>',
            unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)
    _render_gauges_empresa(df_acum, df_mes, col_meta, pct_esperado)
    _render_graficos(df_f, df_v_raw, df_mes, df_acum, pesos, col_meta, label_meta,
                     ano_sel, mes_sel, semana_atual, n_semanas, pct_esperado,
                     tw_ranges, fator_proj, dia_ref, ano_ant, mes_ant)


def _render_gauges_empresa(df_acum, df_mes, col_meta, pct_esperado):
    st.markdown('<div class="secao-titulo">Ritmo por Empresa</div>', unsafe_allow_html=True)
    empresas   = ['ACC', 'ACI', 'SIN']
    cols_emp   = st.columns(3)
    for i, emp in enumerate(empresas):
        df_emp     = df_acum[df_acum['empresa'] == emp]
        df_emp_mes = df_mes[df_mes['empresa'] == emp]
        real_emp      = df_emp['vol_ton'].sum()
        meta_emp_mes  = df_emp_mes[col_meta].sum()
        meta_emp_acum = meta_emp_mes * pct_esperado
        ritmo_emp     = real_emp / meta_emp_acum if meta_emp_acum > 0 else None
        with cols_emp[i]:
            fig_emp = make_gauge(ritmo_emp or 0.0, emp, height=190)
            st.plotly_chart(fig_emp, use_container_width=True,
                            config={'displayModeBar': False},
                            key=f'{col_meta}_gauge_{emp}')
            st.markdown(_gauge_sub(real_emp, meta_emp_acum), unsafe_allow_html=True)


def _render_graficos(df_f, df_v_raw, df_mes, df_acum, pesos, col_meta, label_meta,
                     ano_sel, mes_sel, semana_atual, n_semanas, pct_esperado,
                     tw_ranges, fator_proj, dia_ref, ano_ant, mes_ant):
    col_meta_label = 'Plano S&OP' if col_meta == 'meta_sop' else 'Programa S&OE'

    # Comparativo semanal
    st.markdown('<div class="secao-titulo">Comparativo Semanal — Realizado vs Plano</div>',
                unsafe_allow_html=True)
    fig_sem = graf_semanal(df_mes, col_meta, semana_atual, col_meta_label, tw_ranges=tw_ranges)
    st.plotly_chart(fig_sem, use_container_width=True, config={'displayModeBar': False},
                    key=f'{col_meta}_semanal_{ano_sel}_{mes_sel}')

    # Venda diária
    st.markdown('<div class="secao-titulo">Venda Diária no Mês</div>', unsafe_allow_html=True)
    df_v_mes_filt = df_v_raw[(df_v_raw['ano']==ano_sel) & (df_v_raw['mes']==mes_sel)].copy()
    total_meta_mes = df_mes[col_meta].sum()
    fig_dia = graf_diario(df_v_mes_filt, total_meta_mes, ano_sel, mes_sel,
                          dia_ref_externo=dia_ref)
    st.plotly_chart(fig_dia, use_container_width=True, config={'displayModeBar': False},
                    key=f'{col_meta}_diario_{ano_sel}_{mes_sel}')

    # Dados por linha
    por_linha_acum = (df_acum.groupby('linha')
                     .agg(vol_real=('vol_ton','sum'), val_real=('val_mm','sum'))
                     .reset_index())
    por_linha_mes  = (df_mes.groupby('linha')[col_meta].sum().reset_index()
                     .rename(columns={col_meta:'meta_mes'}))
    por_linha = por_linha_acum.merge(por_linha_mes, on='linha', how='outer').fillna(0)

    def _peso_acum_linha(l):
        return sum(get_peso(pesos, l, s) for s in range(1, semana_atual+1))

    por_linha['peso_acum'] = por_linha['linha'].map(_peso_acum_linha)
    por_linha['meta_acum'] = por_linha['meta_mes'] * por_linha['peso_acum']
    por_linha['projecao']  = por_linha['vol_real'] * fator_proj
    por_linha['ritmo_pct'] = por_linha.apply(
        lambda r: r['vol_real']/r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)
    por_linha['gap_ton']   = por_linha['meta_mes'] - por_linha['projecao'].fillna(0)
    por_linha['gap_pct']   = por_linha.apply(
        lambda r: r['gap_ton']/r['meta_mes'] if r['meta_mes'] > 0 else None, axis=1)

    sem_ant = semana_atual - 1
    if sem_ant >= 1:
        df_ant_s  = df_mes[df_mes['semana_mes']==sem_ant].groupby('linha')['vol_ton'].sum()
        df_atual_s = df_mes[df_mes['semana_mes']==semana_atual].groupby('linha')['vol_ton'].sum()
        tendencia = {}
        for l in por_linha['linha']:
            v_ant = df_ant_s.get(l, 0)
            v_at  = df_atual_s.get(l, 0)
            tendencia[l] = (v_at - v_ant) / v_ant if v_ant > 0 else None
        por_linha['tendencia'] = por_linha['linha'].map(tendencia)
    else:
        por_linha['tendencia'] = None

    por_linha = por_linha.sort_values('vol_real', ascending=False)

    # Famílias
    st.markdown('<div class="secao-titulo">Ritmo por Linha de Produto — por Família</div>',
                unsafe_allow_html=True)
    if 'familia' in df_v_raw.columns:
        mapa_fam = (df_v_raw[['linha','familia']].dropna().drop_duplicates('linha')
                    .set_index('linha')['familia'].str.strip().str.upper().to_dict())
    else:
        mapa_fam = {}
    por_linha['familia'] = por_linha['linha'].map(mapa_fam).fillna('OUTROS')
    familias_ord = (por_linha.groupby('familia')['vol_real'].sum()
                    .sort_values(ascending=False).index.tolist())

    for idx in range(0, len(familias_ord), 2):
        cols_fam = st.columns(2) if idx+1 < len(familias_ord) else [st.container(), None]
        for j, fam in enumerate(familias_ord[idx:idx+2]):
            df_fam = por_linha[por_linha['familia']==fam]
            container = cols_fam[j] if cols_fam[j] is not None else cols_fam[0]
            with container:
                _render_familia_kpi(df_fam, fam, fator_proj, df_f, ano_ant, mes_ant,
                                    semana_atual, col_meta)
                graf_familia_barras(df_fam, fam, fator_proj,
                                    chart_key=f'{col_meta}_fam_{fam.replace(" ","_")}_{idx}_{j}')

    _render_pivot_uf(df_acum, df_mes, col_meta, pct_esperado)
    _render_tabela_linha(por_linha, col_meta)
    _render_tabela_regiao(df_f, df_acum, df_mes, col_meta, pct_esperado,
                          semana_atual, fator_proj, ano_ant, mes_ant)


def _render_familia_kpi(df_fam, fam, fator_proj, df_f, ano_ant, mes_ant,
                        semana_atual, col_meta):
    real_fam     = df_fam['vol_real'].sum()
    meta_fam_ac  = df_fam['meta_acum'].sum()
    meta_fam_mes = df_fam['meta_mes'].sum()
    proj_fam     = real_fam * fator_proj
    ritmo_fam    = real_fam / meta_fam_ac if meta_fam_ac > 0 else None
    gap_fam      = meta_fam_mes - proj_fam

    linhas_fam   = df_fam['linha'].tolist()
    df_ant_fam   = df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                        (df_f['semana_mes']<=semana_atual) &
                        (df_f['linha'].isin(linhas_fam))]
    real_fam_ant = df_ant_fam['vol_ton'].sum()
    var_mm_fam   = ((real_fam - real_fam_ant) / real_fam_ant
                    if real_fam_ant > 0 else None)
    ating_fam    = proj_fam / meta_fam_mes if meta_fam_mes > 0 else None

    cor_f      = cor_ritmo(ritmo_fam)
    rit_txt    = f'{ritmo_fam:.1%}' if ritmo_fam is not None else '—'
    gap_cor    = '#C0392B' if gap_fam > 0 else '#1A7A40'
    gap_label  = f'{_fmt_ton(gap_fam)} ton a fechar' if gap_fam > 0 else f'{_fmt_ton(abs(gap_fam))} ton acima'
    proj_cor   = '#1A7A40' if (ating_fam or 0) >= 1.0 else '#C0392B'
    proj_label = f'{ating_fam:.0%} da meta' if ating_fam is not None else '—'
    var_cor    = '#1A7A40' if (var_mm_fam or 0) >= 0 else '#C0392B'
    var_sinal  = '+' if (var_mm_fam or 0) >= 0 else ''
    var_label  = f'{var_sinal}{var_mm_fam:.1%} vs mês ant.' if var_mm_fam is not None else 'sem histórico'

    st.markdown(f"""
    <div style="background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:4px;
                border-left:5px solid {cor_f};box-shadow:0 1px 6px rgba(0,0,0,0.08);">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div style="font-size:14px;font-weight:800;color:{COR_PRIMARIA};letter-spacing:.4px;min-width:80px">{fam}</div>
        <div style="display:flex;gap:18px;flex-wrap:wrap;align-items:center;">
          <div style="text-align:center">
            <div style="font-size:9px;color:#888;text-transform:uppercase;margin-bottom:2px">Realizado</div>
            <div style="font-size:14px;font-weight:700;color:{COR_TEXTO}">{_fmt_ton(real_fam)} ton</div>
            <div style="font-size:10px;color:{var_cor};font-weight:600">{var_label}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:9px;color:#888;text-transform:uppercase;margin-bottom:2px">Meta acum.</div>
            <div style="font-size:14px;font-weight:700;color:{COR_TEXTO}">{_fmt_ton(meta_fam_ac)} ton</div>
            <div style="font-size:10px;color:#888">de {_fmt_ton(meta_fam_mes)} ton mês</div>
          </div>
          <div style="text-align:center;padding:0 6px;border-left:1px solid #eee;border-right:1px solid #eee">
            <div style="font-size:9px;color:#888;text-transform:uppercase;margin-bottom:2px">Ritmo</div>
            <div style="font-size:22px;font-weight:800;color:{cor_f};line-height:1">{rit_txt}</div>
            <div style="font-size:9px;color:#888">real / meta acum.</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:9px;color:#888;text-transform:uppercase;margin-bottom:2px">Projeção Mês</div>
            <div style="font-size:14px;font-weight:700;color:{proj_cor}">{_fmt_ton(proj_fam)} ton</div>
            <div style="font-size:10px;color:{proj_cor};font-weight:600">{proj_label}</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:9px;color:#888;text-transform:uppercase;margin-bottom:2px">Gap Fech.</div>
            <div style="font-size:14px;font-weight:700;color:{gap_cor}">{_fmt_ton(abs(gap_fam))} ton</div>
            <div style="font-size:10px;color:{gap_cor};font-weight:600">{'↑ a fechar' if gap_fam > 0 else '✓ acima do plano'}</div>
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)


def _render_pivot_uf(df_acum, df_mes, col_meta, pct_esperado):
    st.markdown('<div class="secao-titulo">Posição do Mês — Linha × UF (Ritmo %)</div>',
                unsafe_allow_html=True)
    lu_real = (df_acum.groupby(['linha','uf'])['vol_ton'].sum().reset_index()
               .rename(columns={'vol_ton':'vol_real'}))
    lu_meta = (df_mes.groupby(['linha','uf'])[col_meta].sum().reset_index()
               .rename(columns={col_meta:'meta_mes'}))
    lu = lu_real.merge(lu_meta, on=['linha','uf'], how='outer').fillna(0)
    lu['meta_acum'] = lu['meta_mes'] * pct_esperado
    lu['ritmo']     = lu.apply(
        lambda r: r['vol_real']/r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)

    linhas_ord = (lu.groupby('linha')['meta_mes'].sum().sort_values(ascending=False)
                  .loc[lambda s: s > 0].index.tolist())
    ufs_ord    = (lu.groupby('uf')['meta_mes'].sum().sort_values(ascending=False)
                  .loc[lambda s: s > 0].index.tolist())

    if not (linhas_ord and ufs_ord):
        return

    lu_f = lu[lu['linha'].isin(linhas_ord) & lu['uf'].isin(ufs_ord)]
    piv_ritmo = (lu_f.pivot_table(index='linha', columns='uf', values='ritmo', aggfunc='first')
                 .reindex(index=linhas_ord, columns=ufs_ord))
    piv_ritmo['TOTAL'] = lu_f.groupby('linha').apply(
        lambda g: g['vol_real'].sum()/g['meta_acum'].sum() if g['meta_acum'].sum() > 0 else None,
        include_groups=False,
    ).reindex(linhas_ord)

    def _fmt_cell(v):
        if v is None or (isinstance(v, float) and np.isnan(v)): return '—'
        return f'{v:.0%}'

    def _color_cell(v):
        try:
            num = float(str(v).replace('%','').replace(',','.').replace('—','')) / 100
            if num >= 0.90: return 'background-color:#D6EDE0;color:#1A7A40;font-weight:600'
            if num >= 0.75: return 'background-color:#F5E9C8;color:#8A6000;font-weight:600'
            return 'background-color:#F5D5D1;color:#C0392B;font-weight:600'
        except Exception:
            return 'color:#999'

    piv_fmt    = piv_ritmo.map(_fmt_cell)
    styled_piv = (piv_fmt.style.map(_color_cell)
                  .set_properties(**{'text-align':'center','font-size':'12px'})
                  .set_table_styles([
                      {'selector':'th','props':[('background-color',COR_PRIMARIA),('color','white'),
                                                ('font-size','11px'),('text-align','center'),('padding','5px 8px')]},
                      {'selector':'th.row_heading','props':[('background-color','#EEF1F7'),
                                                            ('color',COR_PRIMARIA),('font-weight','700'),('text-align','left')]},
                  ]))
    st.dataframe(styled_piv, use_container_width=True, hide_index=False,
                 height=min(700, 42 + len(linhas_ord)*35))
    st.markdown('<div style="font-size:10px;color:#888;margin-top:-8px;margin-bottom:12px;">'
                '🟢 ≥ 90% &nbsp;&nbsp; 🟡 75–90% &nbsp;&nbsp; 🔴 &lt; 75% &nbsp;&nbsp;'
                '— = sem meta ou realizado</div>', unsafe_allow_html=True)


def _render_tabela_linha(por_linha, col_meta):
    st.markdown('<div class="secao-titulo">Detalhe por Linha</div>', unsafe_allow_html=True)
    tab_linha = pd.DataFrame({
        'Linha':              por_linha['linha'],
        'Meta Mês (ton)':     por_linha['meta_mes'].map('{:,.0f}'.format),
        'Realizado (ton)':    por_linha['vol_real'].map('{:,.0f}'.format),
        'Ritmo (%)':          por_linha['ritmo_pct'].map(lambda x: f'{x:.1%}' if pd.notna(x) else '—'),
        'Projeção Mês (ton)': por_linha['projecao'].map(lambda x: f'{x:,.0f}' if pd.notna(x) else '—'),
        'Gap Fech. (ton)':    por_linha['gap_ton'].map('{:+,.0f}'.format),
        'Gap Fech. (%)':      por_linha['gap_pct'].map(lambda x: f'{x:+.1%}' if pd.notna(x) else '—'),
        'Tend.':              por_linha['tendencia'].map(seta_tendencia),
        'Status':             por_linha['ritmo_pct'].map(icone_ritmo),
    })
    st.dataframe(tabela_styled(tab_linha, 'Linha'), use_container_width=True,
                 hide_index=True, height=min(600, 38 + len(tab_linha)*36))


def _render_tabela_regiao(df_f, df_acum, df_mes, col_meta, pct_esperado,
                          semana_atual, fator_proj, ano_ant, mes_ant):
    st.markdown('<div class="secao-titulo">Detalhe por Região / Estado</div>',
                unsafe_allow_html=True)
    por_reg_acum = (df_acum.groupby(['regiao','uf'])['vol_ton'].sum().reset_index()
                    .rename(columns={'vol_ton':'vol_real'}))
    por_reg_meta = (df_mes.groupby(['regiao','uf'])[col_meta].sum().reset_index()
                    .rename(columns={col_meta:'meta_mes'}))
    por_reg = por_reg_acum.merge(por_reg_meta, on=['regiao','uf'], how='outer').fillna(0)
    por_reg['meta_acum'] = por_reg['meta_mes'] * pct_esperado
    por_reg['projecao']  = por_reg['vol_real'] * fator_proj
    por_reg['ritmo_pct'] = por_reg.apply(
        lambda r: r['vol_real']/r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)
    por_reg['gap_ton']   = por_reg['meta_mes'] - por_reg['projecao'].fillna(0)
    por_reg['gap_pct']   = por_reg.apply(
        lambda r: r['gap_ton']/r['meta_mes'] if r['meta_mes'] > 0 else None, axis=1)
    por_reg = por_reg.sort_values(['regiao','vol_real'], ascending=[True, False])

    tab_reg = pd.DataFrame({
        'Região':             por_reg['regiao'],
        'UF':                 por_reg['uf'],
        'Meta Mês (ton)':     por_reg['meta_mes'].map('{:,.0f}'.format),
        'Realizado (ton)':    por_reg['vol_real'].map('{:,.0f}'.format),
        'Ritmo (%)':          por_reg['ritmo_pct'].map(lambda x: f'{x:.1%}' if pd.notna(x) else '—'),
        'Projeção Mês (ton)': por_reg['projecao'].map(lambda x: f'{x:,.0f}' if pd.notna(x) else '—'),
        'Gap (ton)':          por_reg['gap_ton'].map('{:+,.0f}'.format),
        'Gap (%)':            por_reg['gap_pct'].map(lambda x: f'{x:+.1%}' if pd.notna(x) else '—'),
        'Status':             por_reg['ritmo_pct'].map(icone_ritmo),
    })
    st.dataframe(tabela_styled(tab_reg, 'Região'), use_container_width=True,
                 hide_index=True, height=min(600, 38 + len(tab_reg)*36))
