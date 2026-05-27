import sys
import os
import traceback

# Garante que app/ está no path independente de como o arquivo é chamado
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import streamlit as st

# Captura erros de import logo no início para exibir na tela
try:
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
except Exception as _e:
    st.error(f"❌ Erro ao importar dependências: {_e}\n\n```\n{traceback.format_exc()}\n```")
    st.stop()
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime, timedelta
from pathlib import Path
import calendar as _cal_mod
import warnings
warnings.filterwarnings('ignore')

# ── set_page_config DEVE ser o primeiro comando Streamlit ─────────────────────
st.set_page_config(
    page_title="S&OE — Inteligência Comercial | Aço Cearense",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Importações pesadas — dentro de try/except para mostrar erro na tela ──────
try:
    from modules import score_propensao, demand_sensing, matriz_semanal, dashboard_uf, plano_comercial
    from config import (
        MESES,
        LINHAS_EXCLUIR, MAPA_NOME_LINHA, FAMILIA_OVERRIDE,
    )
    from utils.calendar_tw import get_month_tw_ranges, day_to_semana_tw, vectorize_semana_tw, tw_label
    from utils.visual import (
        COR_PRIMARIA, COR_ACENTO, COR_VERDE, COR_AMARELO, COR_VERMELHO,
        COR_FUNDO, COR_CARD, COR_TEXTO, COR_GRID,
        fmt_ton as _fmt_ton, cor_ritmo, icone_ritmo, cor_bg_ritmo, seta_tendencia,
    )
except Exception as _e:
    st.error(f"❌ Erro ao importar módulos internos:\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Fundo geral */
  .stApp {{ background-color: {COR_FUNDO}; }}

  /* Compensa a barra de navegação do Streamlit/HF no topo */
  .block-container {{
    padding-top: 4rem !important;
  }}
  /* Esconde o header fixo do Streamlit para liberar espaço */
  header[data-testid="stHeader"] {{
    display: none !important;
  }}

  /* Sidebar */
  [data-testid="stSidebar"] {{
    background-color: #EEF1F7;
    border-right: 1px solid #D8DEE9;
  }}
  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {{
    color: {COR_PRIMARIA};
  }}

  /* Cards customizados */
  .card {{
    background: {COR_CARD};
    border-radius: 10px;
    padding: 14px 18px 12px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
    margin-bottom: 4px;
    border-left: 4px solid {COR_PRIMARIA};
    border-top: 1px solid rgba(0,0,0,0.05);
  }}
  .card-acento  {{ border-left-color: {COR_ACENTO};   background: linear-gradient(135deg, #fff 85%, rgba(217,107,45,0.05) 100%); }}
  .card-verde   {{ border-left-color: {COR_VERDE};    background: linear-gradient(135deg, #fff 85%, rgba(26,122,64,0.05) 100%); }}
  .card-amarelo {{ border-left-color: {COR_AMARELO};  background: linear-gradient(135deg, #fff 85%, rgba(176,125,0,0.05) 100%); }}
  .card-vermelho{{ border-left-color: {COR_VERMELHO}; background: linear-gradient(135deg, #fff 85%, rgba(192,57,43,0.05) 100%); }}

  .card-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8A9BB0;
    margin-bottom: 6px;
  }}
  .card-value {{
    font-size: 26px;
    font-weight: 800;
    color: {COR_PRIMARIA};
    line-height: 1.05;
    letter-spacing: -0.5px;
  }}
  .card-sub {{
    font-size: 11px;
    color: #8A9BB0;
    margin-top: 5px;
  }}
  .card-delta-pos {{ color: {COR_VERDE};    font-weight: 700; }}
  .card-delta-neg {{ color: {COR_VERMELHO}; font-weight: 700; }}
  .card-delta-neu {{ color: {COR_AMARELO};  font-weight: 700; }}

  /* Títulos de seção */
  .secao-titulo {{
    font-size: 15px;
    font-weight: 700;
    color: {COR_PRIMARIA};
    margin: 20px 0 10px 0;
    padding: 6px 14px 6px 12px;
    border-left: 4px solid {COR_ACENTO};
    background: linear-gradient(90deg, rgba(244,130,42,0.07) 0%, transparent 100%);
    border-radius: 0 6px 6px 0;
    display: block;
    letter-spacing: .2px;
  }}

  /* Header da aba */
  .aba-header {{
    background: linear-gradient(135deg, {COR_PRIMARIA} 0%, #2C4A7C 100%);
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    margin-bottom: 16px;
  }}
  .aba-header h2 {{
    color: white;
    margin: 0 0 4px 0;
    font-size: 20px;
  }}
  .aba-header p {{
    color: rgba(255,255,255,0.8);
    margin: 0;
    font-size: 13px;
  }}
  .badge-semana {{
    display: inline-block;
    background: {COR_ACENTO};
    color: white;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 8px;
  }}

  /* Tabela customizada */
  .tabela-head {{
    background: {COR_PRIMARIA};
    color: white;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 6px;
    text-align: center;
  }}
  .tabela-cell {{
    font-size: 12px;
    padding: 6px 8px;
    text-align: right;
    border-bottom: 1px solid #E9ECEF;
  }}

  /* Oculta elementos padrão do Streamlit */
  #MainMenu, footer {{ visibility: hidden; }}
  .block-container {{ padding-top: 1rem; }}
</style>
""", unsafe_allow_html=True)


# ── Carregamento de dados ──────────────────────────────────────────────────────
from utils.data_loader import load_vendas, load_meta

@st.cache_data(show_spinner="Carregando dados...")
def carrega_dados():
    df_v = load_vendas()
    df_m = load_meta()

    df_v['data'] = pd.to_datetime(df_v['data'])
    df_m['data'] = pd.to_datetime(df_m['data'])

    for col in ['empresa','linha','regiao','uf']:
        if col in df_v.columns:
            df_v[col] = df_v[col].str.strip().str.upper()
        if col in df_m.columns:
            df_m[col] = df_m[col].str.strip().str.upper()

    # Normaliza grafia de região (meta tem 'CENTRO-OESTE' com hífen, vendas sem)
    if 'regiao' in df_m.columns:
        df_m['regiao'] = df_m['regiao'].str.replace('CENTRO-OESTE', 'CENTRO OESTE',
                                                     regex=False)
    if 'regiao' in df_v.columns:
        df_v['regiao'] = df_v['regiao'].str.replace('CENTRO-OESTE', 'CENTRO OESTE',
                                                     regex=False)

    # Normaliza nomes de linha vendas → meta (ex.: BOBINA → BOBINA SLITTER)
    if 'linha' in df_v.columns:
        df_v['linha'] = df_v['linha'].replace(MAPA_NOME_LINHA)

    # Remove linhas inativas — guard defensivo (atualiza_dados.py já faz isso no preprocessing)
    df_v = df_v[~df_v['linha'].isin(LINHAS_EXCLUIR)].copy()
    df_m = df_m[~df_m['linha'].isin(LINHAS_EXCLUIR)].copy()

    df_v['dia'] = df_v['data'].dt.day
    df_v['ano'] = df_v['data'].dt.year
    df_v['mes'] = df_v['data'].dt.month

    # Pre-2026: bins fixos para manter compatibilidade com meta_semanal histórica
    pre_mask = df_v['ano'] < 2026
    if pre_mask.any():
        df_v.loc[pre_mask, 'semana_mes'] = (
            pd.cut(df_v.loc[pre_mask, 'dia'], bins=[0,7,14,21,31], labels=[1,2,3,4])
            .astype(int)
        )
    # 2026+: semana_mes baseado em Semanas Técnicas (TW) reais do calendário
    # vectorize_semana_tw faz lookup de combinações únicas — ~50× mais rápido que apply(axis=1)
    post_mask = df_v['ano'] >= 2026
    if post_mask.any():
        df_v.loc[post_mask, 'semana_mes'] = vectorize_semana_tw(
            df_v.loc[post_mask, 'ano'],
            df_v.loc[post_mask, 'mes'],
            df_v.loc[post_mask, 'dia'],
        ).values

    df_m['ano']        = df_m['data'].dt.year
    df_m['mes']        = df_m['data'].dt.month

    # Agrega realizado com val_mm
    real_sem = (df_v.groupby(['empresa','linha','regiao','uf','ano','mes','semana_mes'])
                .agg(vol_ton=('vol_ton','sum'), val_mm=('val_mm','sum'))
                .reset_index())

    meta_sem = (df_m.groupby(['empresa','linha','regiao','uf','ano','mes','semana_mes'])
                [['meta_sop','meta_soe']].sum().reset_index())

    # outer join: preserva linhas de meta sem venda correspondente
    # (how='left' descartava 84K linhas de meta = 313K ton perdidos)
    df = real_sem.merge(meta_sem,
                        on=['empresa','linha','regiao','uf','ano','mes','semana_mes'],
                        how='outer')
    df['vol_ton']  = df['vol_ton'].fillna(0)
    df['val_mm']   = df['val_mm'].fillna(0)
    df['meta_soe'] = df['meta_soe'].fillna(0)
    df['meta_sop'] = df['meta_sop'].fillna(0)

    return df, df_v


@st.cache_data(show_spinner=False)
def calcula_pesos(df_v):
    """Pesos históricos intra-mês por linha (calculados do histórico real)."""
    padrao = (df_v.groupby(['linha','ano','mes','semana_mes'])['vol_ton']
              .sum().reset_index())
    peso_medio = (padrao.groupby(['linha','semana_mes'])['vol_ton']
                  .mean().reset_index())
    total = (peso_medio.groupby('linha')['vol_ton']
             .sum().reset_index().rename(columns={'vol_ton':'vol_total'}))
    peso_medio = peso_medio.merge(total, on='linha')
    peso_medio['peso'] = (peso_medio['vol_ton'] / peso_medio['vol_total']).fillna(0.25)
    # pivot: linha -> {semana: peso}
    pesos = {}
    for _, row in peso_medio.iterrows():
        if row['linha'] not in pesos:
            pesos[row['linha']] = {}
        pesos[row['linha']][int(row['semana_mes'])] = row['peso']
    return pesos


def get_peso(pesos, linha, semana):
    """Retorna peso para uma linha/semana, com fallback."""
    fallback = {1: 0.160, 2: 0.226, 3: 0.233, 4: 0.381}
    if linha in pesos and semana in pesos[linha]:
        return pesos[linha][semana]
    return fallback.get(semana, 0.25)


def peso_acumulado(pesos, linha, semana_atual):
    return sum(get_peso(pesos, linha, s) for s in range(1, semana_atual + 1))


def projeta_mes(realizado, pesos, linha, semana_atual):
    p = peso_acumulado(pesos, linha, semana_atual)
    return realizado / p if p > 0 else None


def ritmo_pct(realizado, meta_mes, pesos, linha, semana_atual):
    p = peso_acumulado(pesos, linha, semana_atual)
    meta_acum = meta_mes * p
    return realizado / meta_acum if meta_acum > 0 else None



# ── Gauge Plotly ──────────────────────────────────────────────────────────────
def make_gauge(valor_pct, titulo, height=180):
    """Gauge semicircular limpo — sem texto interno sobreposto."""
    if valor_pct is None or (isinstance(valor_pct, float) and np.isnan(valor_pct)):
        valor_pct = 0.0

    cor = cor_ritmo(valor_pct)
    pct_display = min(valor_pct * 100, 130)

    # Usa mode="gauge" sem número nativo do Plotly para evitar clipping
    # O valor é injetado como annotation centralizado em coordenadas de papel
    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=pct_display,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {
                'range': [0, 120],
                'tickwidth': 1,
                'tickcolor': '#B0BEC5',
                'tickfont': {'size': 8, 'color': '#90A4AE'},
                'nticks': 7,
            },
            'bar': {'color': cor, 'thickness': 0.65},
            'bgcolor': '#F8F9FA',
            'borderwidth': 0,
            'steps': [
                {'range': [0,  75],  'color': '#F5D5D1'},  # rosa suave
                {'range': [75, 90],  'color': '#F5E9C8'},  # âmbar suave
                {'range': [90, 120], 'color': '#D6EDE0'},  # verde suave
            ],
            'threshold': {
                'line': {'color': COR_PRIMARIA, 'width': 3},
                'thickness': 0.8,
                'value': 100,
            },
        },
    ))

    fig.add_annotation(
        x=0.5, y=0.18,
        xref='paper', yref='paper',
        text=f'<b>{pct_display:.1f}%</b>',
        showarrow=False,
        font=dict(size=20, color=cor, family='Arial'),
        align='center',
        xanchor='center',
        yanchor='middle',
    )

    fig.update_layout(
        title={
            'text': f'<b>{titulo}</b>',
            'x': 0.5, 'xanchor': 'center',
            'font': {'size': 13, 'color': COR_PRIMARIA, 'family': 'Arial'},
            'y': 0.97, 'yanchor': 'top',
        },
        height=height,
        margin=dict(t=36, b=16, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Arial'},
    )
    return fig


def _gauge_sub(realizado, meta):
    """HTML da linha de realizado/meta abaixo do gauge."""
    if realizado is None or meta is None:
        return ''
    r_fmt = f'{realizado:,.0f}'.replace(',', '.')
    m_fmt = f'{meta:,.0f}'.replace(',', '.')
    return (
        f'<div style="text-align:center; font-size:11px; color:#546E7A; '
        f'margin-top:-8px; padding-bottom:4px;">'
        f'<b>{r_fmt}</b> / {m_fmt} ton</div>'
    )


# ── Card HTML ─────────────────────────────────────────────────────────────────
def card_html(label, valor, sub='', delta=None, cor_borda=COR_PRIMARIA):
    delta_html = ''
    if delta is not None:
        css = 'card-delta-pos' if delta >= 0 else 'card-delta-neg'
        sinal = '+' if delta >= 0 else ''
        delta_html = f'<span class="{css}">{sinal}{delta:.1%}</span>'

    return f"""
    <div class="card" style="border-top-color:{cor_borda}">
      <div class="card-label">{label}</div>
      <div class="card-value">{valor}</div>
      <div class="card-sub">{sub} {delta_html}</div>
    </div>
    """


# ── Gráfico barras diárias ─────────────────────────────────────────────────────
def graf_diario(df_v_mes, meta_mes_vol, ano, mes, dia_ref_externo=None):
    """Barras diárias com:
    - Barra de desvio (gap vs meta/dia) em verde/vermelho empilhada sobre cada barra
    - Linha close-the-gap nos dias restantes
    - Ritmo esperado como marcadores apenas nos dias úteis
    """
    dias_no_mes = _cal_mod.monthrange(ano, mes)[1]

    todos_dias = pd.DataFrame({'dia': range(1, dias_no_mes + 1)})
    if not df_v_mes.empty:
        vendas_dia = df_v_mes.groupby('dia')['vol_ton'].sum().reset_index()
    else:
        vendas_dia = pd.DataFrame({'dia': pd.Series(dtype=int),
                                   'vol_ton': pd.Series(dtype=float)})
    diario = todos_dias.merge(vendas_dia, on='dia', how='left').fillna(0)

    # Dias úteis reais (Seg–Sex)
    dias_uteis_mes   = [d for d in range(1, dias_no_mes + 1) if date(ano, mes, d).weekday() < 5]
    n_dias_uteis_mes = max(1, len(dias_uteis_mes))
    ritmo_dia = meta_mes_vol / n_dias_uteis_mes

    # Dia de referência (hoje, incompleto)
    hoje_loc = date.today()
    if dia_ref_externo is not None:
        dia_ref = dia_ref_externo
    elif hoje_loc.year == ano and hoje_loc.month == mes:
        dia_ref = hoje_loc.day
    else:
        dia_ref = dias_no_mes

    # Volume realizado até dia_ref - 1 (dias completos), dia_ref ainda em andamento
    vol_realizado = diario[diario['dia'] < dia_ref]['vol_ton'].sum()
    # Dias úteis restantes: dia_ref em diante (inclusive, pois hoje não terminou)
    dias_uteis_rest = [d for d in dias_uteis_mes if d >= dia_ref]
    n_rest = max(1, len(dias_uteis_rest))
    # Meta restante = meta total - realizado completo
    meta_restante = max(0, meta_mes_vol - vol_realizado)
    ctg_dia = meta_restante / n_rest  # close-the-gap por dia útil restante

    fig = go.Figure()

    # ── Barras principais ──────────────────────────────────────────
    cores = []
    for d in diario['dia']:
        wd = date(ano, mes, int(d)).weekday()
        cores.append('#CFD8DC' if wd >= 5 else '#1B6CA8')

    fig.add_trace(go.Bar(
        x=diario['dia'], y=diario['vol_ton'],
        name='Realizado', marker_color=cores,
        hovertemplate='Dia %{x}: <b>%{y:,.0f} ton</b><extra></extra>',
    ))

    # ── Barra de desvio vs meta/dia (apenas dias úteis com dados) ──
    gap_x_pos, gap_y_pos = [], []  # acima da meta → verde
    gap_x_neg, gap_y_neg = [], []  # abaixo da meta → vermelho
    for _, row in diario.iterrows():
        d = int(row['dia'])
        if date(ano, mes, d).weekday() >= 5:
            continue   # pula fins de semana
        if d >= dia_ref:
            continue   # pula dias ainda não concluídos
        if row['vol_ton'] == 0:
            continue
        delta = row['vol_ton'] - ritmo_dia
        if delta >= 0:
            gap_x_pos.append(d); gap_y_pos.append(delta)
        else:
            gap_x_neg.append(d); gap_y_neg.append(abs(delta))

    BAR_GAP_W = 0.25   # largura fina para as barras de desvio

    if gap_x_pos:
        bases_pos = [float(diario.loc[diario['dia']==d, 'vol_ton'].iloc[0]) for d in gap_x_pos]
        # customdata = delta real (gap_y_pos); %{y} com base = posição absoluta (errado para hover)
        fig.add_trace(go.Bar(
            x=gap_x_pos, y=gap_y_pos,
            name='Acima da meta/dia',
            base=bases_pos,
            width=BAR_GAP_W,
            marker_color='rgba(40,167,69,0.70)',
            marker_line=dict(color='rgba(40,167,69,0.9)', width=1),
            customdata=[round(v) for v in gap_y_pos],
            hovertemplate='Dia %{x}: +%{customdata:,.0f} ton acima da meta/dia<extra></extra>',
        ))
    if gap_x_neg:
        bases_neg = [float(diario.loc[diario['dia']==d, 'vol_ton'].iloc[0]) for d in gap_x_neg]
        alt_neg   = [ritmo_dia - b for b in bases_neg]
        fig.add_trace(go.Bar(
            x=gap_x_neg, y=alt_neg,
            name='Abaixo da meta/dia',
            base=bases_neg,
            width=BAR_GAP_W,
            marker_color='rgba(220,53,69,0.60)',
            marker_line=dict(color='rgba(220,53,69,0.85)', width=1),
            hovertemplate='Dia %{x}: -%{customdata:,.0f} ton abaixo da meta/dia<extra></extra>',
            customdata=[round(v) for v in gap_y_neg],
        ))

    # ── Ritmo esperado — marcadores apenas nos dias úteis passados ──
    fig.add_trace(go.Scatter(
        x=dias_uteis_mes,
        y=[ritmo_dia] * len(dias_uteis_mes),
        name=f'Meta/dia útil ({_fmt_ton(ritmo_dia)} ton)',
        mode='markers',
        marker=dict(symbol='line-ew', size=10, color=COR_ACENTO,
                    line=dict(color=COR_ACENTO, width=2)),
        hovertemplate=f'Meta/dia útil: {ritmo_dia:,.0f} ton<extra></extra>',
    ))

    # ── Close-the-gap: quanto fazer por dia útil restante ──────────
    if dias_uteis_rest and meta_restante > 0:
        fig.add_trace(go.Scatter(
            x=dias_uteis_rest,
            y=[ctg_dia] * len(dias_uteis_rest),
            name=f'Close the gap ({_fmt_ton(ctg_dia)} ton/d.ú.)',
            mode='lines+markers',
            line=dict(color='#7B1FA2', width=2.5, dash='dashdot'),
            marker=dict(size=7, color='#7B1FA2'),
            hovertemplate=(f'Dia %{{x}} — necessário: <b>{ctg_dia:,.0f} ton</b><br>'
                           f'Faltam {_fmt_ton(meta_restante)} ton em {n_rest} d.ú.<extra></extra>'),
        ))
        # Anotação do valor no primeiro dia restante
        fig.add_annotation(
            x=dias_uteis_rest[0], y=ctg_dia,
            text=f'<b>{_fmt_ton(ctg_dia)}</b> ton/d',
            showarrow=False, yshift=14,
            font=dict(size=10, color='#7B1FA2', family='Arial'),
            bgcolor='rgba(255,255,255,0.7)',
        )

    y_max = max(
        diario['vol_ton'].max() if not diario.empty else 0,
        ritmo_dia,
        ctg_dia if (dias_uteis_rest and meta_restante > 0) else 0,
    ) * 1.30

    fig.update_layout(
        height=300,
        margin=dict(t=10, b=40, l=60, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='Dia do mês', tickmode='linear', dtick=1,
                   range=[0.5, dias_no_mes + 0.5],
                   gridcolor=COR_GRID, gridwidth=1),
        yaxis=dict(title='Volume (ton)', gridcolor=COR_GRID, gridwidth=1,
                   range=[0, y_max]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=10)),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
        barmode='overlay',
    )
    return fig


# ── Gráfico barras por linha ───────────────────────────────────────────────────
# _fmt_ton importado de utils.visual

def graf_linhas(df_linha, col_meta, pesos):
    if df_linha.empty:
        return go.Figure()

    linhas  = df_linha['linha'].tolist()
    real    = df_linha['vol_real'].tolist()
    meta_ac = df_linha['meta_acum'].tolist()
    proj    = [v if pd.notna(v) else 0 for v in df_linha['projecao'].tolist()]

    cores_real = [cor_ritmo(r / m if m > 0 else None)
                  for r, m in zip(real, meta_ac)]

    fig = go.Figure()

    # ── Projeção (fundo, sem label — só hover) ──
    fig.add_trace(go.Bar(
        name='Projeção mês', x=linhas, y=proj,
        marker_color=COR_PRIMARIA, opacity=0.18,
        hovertemplate='<b>%{x}</b><br>Projeção: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in proj],
    ))

    # ── Meta acumulada ──
    fig.add_trace(go.Bar(
        name='Meta acum.', x=linhas, y=meta_ac,
        marker_color=COR_ACENTO,
        marker_line=dict(color=COR_ACENTO, width=1),
        opacity=0.55,
        hovertemplate='<b>%{x}</b><br>Meta acum.: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in meta_ac],
    ))

    # ── Realizado (com label formatado em PT-BR) ──
    fig.add_trace(go.Bar(
        name='Realizado', x=linhas, y=real,
        marker_color=cores_real,
        marker_line=dict(color='rgba(0,0,0,0.15)', width=1),
        text=[_fmt_ton(v) for v in real],
        textposition='outside',
        textfont=dict(size=10, color=COR_TEXTO, family='Arial'),
        hovertemplate='<b>%{x}</b><br>Realizado: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in real],
        cliponaxis=False,
    ))

    # Valor máximo para dar espaço ao label externo
    y_max = max((max(real) if real else 0,
                 max(meta_ac) if meta_ac else 0,
                 max(proj) if proj else 0)) * 1.22

    fig.update_layout(
        barmode='group',
        bargap=0.25,
        bargroupgap=0.08,
        height=380,
        margin=dict(t=20, b=90, l=60, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            tickangle=-38,
            tickfont=dict(size=11),
            gridcolor=COR_GRID,
        ),
        yaxis=dict(
            title='Volume (ton)',
            gridcolor=COR_GRID,
            gridwidth=1,
            range=[0, y_max],
            tickformat=',',
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.01,
            xanchor='right', x=1,
            font=dict(size=11),
        ),
        uniformtext=dict(mode='hide', minsize=8),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
    )
    return fig


# ── Mapeamento linha → família ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_linha_familia(df_v):
    """Retorna dict {linha: familia} combinando dados históricos com overrides manuais."""
    if 'familia' not in df_v.columns:
        mapa = {}
    else:
        mapa = (df_v[['linha','familia']].dropna()
                .drop_duplicates('linha')
                .set_index('linha')['familia']
                .str.strip().str.upper()
                .to_dict())
    # Aplica overrides manuais (prevalece sobre o dado histórico)
    mapa.update(FAMILIA_OVERRIDE)
    return mapa


# ── Gráfico semanal: plano x realizado por semana ────────────────────────────
def graf_semanal(df_mes, col_meta, semana_atual, col_meta_label,
                 tw_ranges=None, ano_sel=None, mes_sel=None):
    """Barras agrupadas: plano vs realizado por semana técnica."""
    if tw_ranges is None:
        tw_ranges = [(1,1,7),(2,8,14),(3,15,21),(4,22,31)]

    semanas = [r[0] for r in tw_ranges]

    # Labels com TW real (ex: "TW22\n26–31 Mai") — fallback simples para histórico
    def _label(r):
        d1, d2 = r[1], r[2]
        if ano_sel and mes_sel:
            lbl = tw_label(ano_sel, mes_sel, r[0])
            return f'{lbl}\n({d1}–{d2})'
        return f'Sem {r[0]}\n({d1}–{d2})'

    nomes = [_label(r) for r in tw_ranges]

    real_sem = df_mes.groupby('semana_mes')['vol_ton'].sum()
    meta_sem = df_mes.groupby('semana_mes')[col_meta].sum()

    real_vals = [real_sem.get(s, 0) for s in semanas]
    meta_vals = [meta_sem.get(s, 0) for s in semanas]

    # Cores: semanas futuras = cinza, passadas = por ritmo
    cores_real = []
    for s in semanas:
        if s > semana_atual:
            cores_real.append('#CFD8DC')
        else:
            r = real_sem.get(s, 0)
            m = meta_sem.get(s, 0)
            cores_real.append(cor_ritmo(r / m if m > 0 else None))

    # % realizado/meta sobre cada barra
    annotations = []
    for i, s in enumerate(semanas):
        rv = real_vals[i]
        mv = meta_vals[i]
        if s < semana_atual and mv > 0:
            # Semanas encerradas — mostra % final
            pct = rv / mv
            cor_ann = cor_ritmo(pct)
            y_pos = max(rv, mv) * 1.12
            annotations.append(dict(
                x=nomes[i], y=y_pos,
                text=f'<b>{pct:.0%}</b>',
                showarrow=False,
                font=dict(size=12, color=cor_ann, family='Arial Black'),
                xanchor='center',
            ))
        elif s == semana_atual and mv > 0:
            # Semana atual — badge "em curso"
            pct = rv / mv
            cor_ann = cor_ritmo(pct)
            y_pos = max(rv, mv) * 1.12
            annotations.append(dict(
                x=nomes[i], y=y_pos,
                text=f'<b>{pct:.0%}</b> ▶',
                showarrow=False,
                font=dict(size=12, color=cor_ann, family='Arial Black'),
                xanchor='center',
            ))

    y_max = max((max(real_vals + meta_vals) if real_vals + meta_vals else 1), 1) * 1.40

    fig = go.Figure()

    # ── Plano (fundo) ─────────────────────────────────────────────────────────
    fig.add_trace(go.Bar(
        name=col_meta_label,
        x=nomes, y=meta_vals,
        marker_color=COR_ACENTO, opacity=0.40,
        text=[_fmt_ton(v) if v > 0 else '' for v in meta_vals],
        textposition='inside',
        textfont=dict(size=10, color='#444'),
        hovertemplate='<b>%{x}</b><br>' + col_meta_label + ': <b>%{customdata} ton</b><extra></extra>',
        customdata=[_fmt_ton(v) for v in meta_vals],
    ))

    # ── Realizado ─────────────────────────────────────────────────────────────
    fig.add_trace(go.Bar(
        name='Realizado',
        x=nomes, y=real_vals,
        marker_color=cores_real,
        marker_line=dict(color='rgba(0,0,0,0.10)', width=1),
        text=[_fmt_ton(v) if v > 0 else '' for v in real_vals],
        textposition='inside',
        textfont=dict(size=11, color='white', family='Arial'),
        hovertemplate='<b>%{x}</b><br>Realizado: <b>%{customdata} ton</b><extra></extra>',
        customdata=[_fmt_ton(v) for v in real_vals],
        cliponaxis=False,
    ))

    # Destaque visual na semana atual — retângulo leve atrás da coluna
    if semana_atual <= len(nomes):
        # Em eixo categórico o índice começa em 0; usamos x0/x1 em torno do índice
        idx_atual = semana_atual - 1
        fig.add_shape(
            type='rect',
            xref='x', yref='paper',
            x0=idx_atual - 0.48, x1=idx_atual + 0.48,
            y0=0, y1=1,
            fillcolor='rgba(27,42,74,0.06)',
            line=dict(color='rgba(27,42,74,0.25)', width=1.5, dash='dot'),
            layer='below',
        )
        fig.add_annotation(
            x=nomes[idx_atual], y=1.0,
            xref='x', yref='paper',
            text='▼ atual',
            showarrow=False,
            font=dict(size=9, color=COR_PRIMARIA),
            yanchor='bottom',
        )

    fig.update_layout(
        barmode='group',
        bargap=0.28,
        bargroupgap=0.06,
        height=320,
        margin=dict(t=28, b=52, l=60, r=20),
        annotations=annotations,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor=COR_GRID, tickfont=dict(size=10)),
        yaxis=dict(title='Volume (ton)', gridcolor=COR_GRID,
                   range=[0, y_max], tickformat=','),
        legend=dict(
            orientation='h',
            yanchor='top', y=-0.14,
            xanchor='center', x=0.5,
            font=dict(size=11),
        ),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
    )
    return fig


# ── Gráfico por família de produto ───────────────────────────────────────────
def graf_familia_barras(df_sub, familia_nome, fator_proj, chart_key):
    """Barras agrupadas para linhas de uma família."""
    if df_sub.empty:
        return

    df_sub = df_sub.sort_values('vol_real', ascending=False)
    linhas  = df_sub['linha'].tolist()
    real    = df_sub['vol_real'].tolist()
    meta_ac = df_sub['meta_acum'].tolist()
    proj    = [r * fator_proj for r in real]

    cores_real = [cor_ritmo(r / m if m > 0 else None)
                  for r, m in zip(real, meta_ac)]

    # y_max: ignora a projeção quando ela estica muito o eixo (ex.: INOX com fator_proj alto)
    # usa o maior entre realizado e meta_acum × 1.35 — mais equilibrado visualmente
    y_max_base = max((max(real + meta_ac) if real else 1), 1)
    y_max_proj = max(proj) if proj else 0
    # só deixa projeção influenciar se for até 40% acima de y_max_base
    y_max = y_max_base * 1.35 if y_max_proj < y_max_base * 1.40 else max(y_max_base * 1.35, y_max_proj * 1.10)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Projeção', x=linhas, y=proj,
        marker_color=COR_PRIMARIA, opacity=0.15,
        hovertemplate='%{x}<br>Projeção: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in proj],
    ))
    fig.add_trace(go.Bar(
        name='Meta acum.', x=linhas, y=meta_ac,
        marker_color=COR_ACENTO, opacity=0.50,
        hovertemplate='%{x}<br>Meta acum.: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in meta_ac],
    ))
    fig.add_trace(go.Bar(
        name='Realizado', x=linhas, y=real,
        marker_color=cores_real,
        marker_line=dict(color='rgba(0,0,0,0.12)', width=1),
        text=[_fmt_ton(v) for v in real],
        textposition='outside',
        textfont=dict(size=11, color=COR_TEXTO),
        cliponaxis=False,
        hovertemplate='%{x}<br>Realizado: %{customdata} ton<extra></extra>',
        customdata=[_fmt_ton(v) for v in real],
    ))

    # Altura: mínimo 260, mais espaço para rótulos externos conforme nº de linhas
    h = max(260, 220 + len(linhas) * 28)

    fig.update_layout(
        title=dict(
            text=f'<b>{familia_nome}</b>',
            font=dict(size=13, color=COR_PRIMARIA, family='Arial'),
            x=0, xanchor='left',
        ),
        barmode='group',
        bargap=0.28,
        bargroupgap=0.06,
        height=h,
        margin=dict(t=40, b=60, l=55, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickangle=-30, gridcolor=COR_GRID, tickfont=dict(size=11)),
        yaxis=dict(
            title='ton', gridcolor=COR_GRID, gridwidth=1,
            range=[0, y_max], tickformat=',',
        ),
        legend=dict(orientation='h', y=1.12, x=1, xanchor='right',
                    font=dict(size=10)),
        uniformtext=dict(mode='hide', minsize=8),
        font=dict(family='Arial', size=11, color=COR_TEXTO),
    )

    st.plotly_chart(fig, use_container_width=True,
                    config={'displayModeBar': False},
                    key=chart_key)


# ── Tabela estilizada ──────────────────────────────────────────────────────────
def tabela_styled(df_tab, chave_col='Linha'):
    def style_row(row):
        rh = row['Ritmo (%)'] if 'Ritmo (%)' in row.index else None
        try:
            rh_str = str(rh).replace('%', '').replace(',', '.').strip()
            rh_val = float(rh_str) / 100
        except Exception:
            rh_val = None
        bg = cor_bg_ritmo(rh_val)
        styles = []
        for c in row.index:
            if c in ('Ritmo (%)', 'Status', 'Tend.'):
                styles.append(f'background-color: {bg}; text-align: center')
            elif c == chave_col or c == 'UF':
                styles.append('font-weight: 600; text-align: left')
            elif c in ('Gap Fech. (ton)', 'Gap Fech. (%)', 'Gap (ton)', 'Gap (%)'):
                # Destaca gap positivo (falta) em vermelho claro, negativo (sobra) em verde claro
                try:
                    gv = float(str(row[c]).replace(',','').replace('+',''))
                    g_bg = '#F8D7DA' if gv > 0 else '#D4EDDA' if gv < 0 else ''
                    styles.append(f'background-color: {g_bg}; text-align: right')
                except Exception:
                    styles.append('text-align: right')
            else:
                styles.append('text-align: right')
        return styles

    return df_tab.style.apply(style_row, axis=1)


# ── Seção principal de cada aba ────────────────────────────────────────────────
def render_aba(df_f, df_v_raw, pesos, col_meta, label_meta,
               ano_sel, mes_sel, filtros_ativos):
    """
    df_f        : dados agregados (semana) já filtrados
    df_v_raw    : vendas diárias já filtradas (para gráfico diário)
    pesos       : dict de pesos por linha
    col_meta    : 'meta_sop' ou 'meta_soe'
    label_meta  : 'Plano S&OP' ou 'Programa S&OE'
    """
    hoje = date.today()
    dia_hoje = hoje.day if (hoje.year == ano_sel and hoje.month == mes_sel) else \
               _cal_mod.monthrange(ano_sel, mes_sel)[1]

    # Garante que ano_sel e mes_sel são int puro (podem vir como numpy.float64)
    ano_sel = int(ano_sel)
    mes_sel = int(mes_sel)

    # Semanas do mês: TW-based para 2026+, fixo para histórico
    if ano_sel >= 2026:
        tw_ranges = get_month_tw_ranges(ano_sel, mes_sel)
        semana_atual = day_to_semana_tw(ano_sel, mes_sel, dia_hoje) or len(tw_ranges)
        n_semanas = len(tw_ranges)
    else:
        tw_ranges = [(1,1,7),(2,8,14),(3,15,21),(4,22,_cal_mod.monthrange(ano_sel,mes_sel)[1])]
        semana_atual = int(pd.cut([dia_hoje], bins=[0,7,14,21,31], labels=[1,2,3,4])[0])
        n_semanas = 4

    pesos_hist_global = {s: 1/n_semanas for s in range(1, n_semanas+1)}
    pct_esperado = sum(pesos_hist_global[s] for s in range(1, semana_atual + 1))

    # Filtrar apenas até semana atual (dados do mês)
    df_mes = df_f[(df_f['ano'] == ano_sel) & (df_f['mes'] == mes_sel)].copy()

    # ── SEÇÃO 1: Header ────────────────────────────────────────────
    mes_label = MESES[mes_sel]
    filtro_str = ' · '.join(filtros_ativos) if filtros_ativos else 'Todas as empresas'
    ctx_pct = f"{pct_esperado:.0%}"

    from utils.calendar_tw import tw_label as _tw_label_local
    tw_label_atual = _tw_label_local(ano_sel, mes_sel, semana_atual)
    semanas_restantes = n_semanas - semana_atual

    st.markdown(f"""
    <div class="aba-header">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div>
          <h2 style="margin:0 0 4px 0">{label_meta}
            <span class="badge-semana">{tw_label_atual} · Sem. {semana_atual}/{n_semanas}</span>
          </h2>
          <p style="margin:0;color:rgba(255,255,255,0.80);font-size:13px;">
            {filtro_str} &nbsp;|&nbsp; {mes_label}/{ano_sel} &nbsp;|&nbsp;
            Padrão histórico: <strong style="color:white">{ctx_pct}</strong> do mês concluído
            {"&nbsp;|&nbsp; <strong style='color:#FFD54F'>Última semana do mês</strong>"
             if semanas_restantes == 0 else
             f"&nbsp;|&nbsp; {semanas_restantes} semana{'s' if semanas_restantes>1 else ''} restante{'s' if semanas_restantes>1 else ''}"}
          </p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if df_mes.empty:
        st.warning(f"Sem dados para {mes_label}/{ano_sel} com os filtros selecionados.")
        return

    # ── Agregações consolidadas ────────────────────────────────────
    import calendar as _cal
    dias_no_mes = _cal.monthrange(ano_sel, mes_sel)[1]

    # Dia de referência: último dia com dados (para projeção linear)
    df_v_mes_tmp = df_v_raw[(df_v_raw['ano'] == ano_sel) & (df_v_raw['mes'] == mes_sel)]
    if not df_v_mes_tmp.empty and 'dia' in df_v_mes_tmp.columns:
        dia_ref = int(df_v_mes_tmp['dia'].max())
    else:
        hoje_loc = date.today()
        dia_ref = hoje_loc.day if (hoje_loc.year == ano_sel and hoje_loc.month == mes_sel) else dias_no_mes
    dia_ref = max(1, dia_ref)

    # Fator de projeção linear: extrapola do ritmo diário para o mês completo
    fator_proj = dias_no_mes / dia_ref

    df_acum = df_mes[df_mes['semana_mes'] <= semana_atual].copy()

    total_real_vol = df_acum['vol_ton'].sum()
    total_real_val = df_acum['val_mm'].sum()
    total_meta_mes = df_mes[col_meta].sum()  # meta mês completo

    # Meta acumulada esperada = meta_mes * peso_acumulado semanal (para Ritmo%)
    meta_acum_esp = total_meta_mes * pct_esperado

    ritmo_geral = total_real_vol / meta_acum_esp if meta_acum_esp > 0 else None
    # Projeção linear: realizado × (dias_mês / dia_ref) — independente do peso semanal
    proj_vol_geral = total_real_vol * fator_proj

    # Preço médio realizado (val_mm está em kR$; *1000 → R$/ton)
    preco_real = (total_real_val / total_real_vol * 1000) if total_real_vol > 0 else None

    # Preço mês anterior (mesmo período, mês anterior)
    mes_ant   = mes_sel - 1 if mes_sel > 1 else 12
    ano_ant   = ano_sel if mes_sel > 1 else ano_sel - 1
    df_ant_p  = df_f[(df_f['ano'] == ano_ant) & (df_f['mes'] == mes_ant) &
                     (df_f['semana_mes'] <= semana_atual)]
    vol_ant_p = df_ant_p['vol_ton'].sum()
    val_ant_p = df_ant_p['val_mm'].sum()
    preco_ant = (val_ant_p / vol_ant_p * 1000) if vol_ant_p > 0 else None
    var_preco = (preco_real - preco_ant) / preco_ant if (preco_real and preco_ant and preco_ant > 0) else None

    gap_vol = (proj_vol_geral - total_meta_mes) if proj_vol_geral else None
    gap_pct = gap_vol / total_meta_mes if (gap_vol is not None and total_meta_mes > 0) else None

    desvio_vol = (total_real_vol - meta_acum_esp) / meta_acum_esp if meta_acum_esp > 0 else None

    # ── Banner de alerta crítico ───────────────────────────────────
    if ritmo_geral is not None and ritmo_geral < 0.75:
        gap_fech_alerta = total_meta_mes - proj_vol_geral
        st.markdown(
            f'<div style="background:linear-gradient(90deg,#C0392B,#D32F2F);'
            f'color:white;border-radius:8px;padding:12px 20px;margin-bottom:12px;'
            f'display:flex;align-items:center;gap:16px;">'
            f'<span style="font-size:22px">🚨</span>'
            f'<div>'
            f'<div style="font-weight:800;font-size:14px;letter-spacing:.3px">'
            f'ALERTA DE RITMO — {ritmo_geral:.0%} vs meta acumulada</div>'
            f'<div style="font-size:12px;opacity:.9;margin-top:2px">'
            f'Projeção de fechamento: <b>{proj_vol_geral:,.0f} ton</b> '
            f'({proj_vol_geral/total_meta_mes:.0%} da meta) &nbsp;·&nbsp; '
            f'Gap a recuperar: <b>{gap_fech_alerta:,.0f} ton</b>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
    elif ritmo_geral is not None and ritmo_geral < 0.90:
        gap_fech_alerta = total_meta_mes - proj_vol_geral
        st.markdown(
            f'<div style="background:linear-gradient(90deg,#C0392B,#8A6000);'
            f'color:white;border-radius:8px;padding:10px 20px;margin-bottom:12px;">'
            f'⚠️ &nbsp;<b>Atenção:</b> ritmo em {ritmo_geral:.0%} — '
            f'projeção de {proj_vol_geral/total_meta_mes:.0%} da meta. '
            f'Gap: {gap_fech_alerta:,.0f} ton a recuperar.'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── SEÇÃO 2: Cards de Ritmo ────────────────────────────────────
    st.markdown('<div class="secao-titulo">Ritmo Geral</div>', unsafe_allow_html=True)

    # ── Calculos comuns aos cards ─────────────────────────────────
    cor_vol      = cor_ritmo(ritmo_geral)
    desvio_abs   = total_real_vol - meta_acum_esp
    desvio_sinal = '+' if desvio_abs >= 0 else ''
    gap_fech     = total_meta_mes - proj_vol_geral
    gap_cor      = '#C0392B' if gap_fech > 0 else '#1A7A40'
    gap_fech_abs = abs(gap_fech)
    gap_label    = (f'{_fmt_ton(gap_fech_abs)} ton a fechar' if gap_fech > 0
                    else f'{_fmt_ton(gap_fech_abs)} ton acima do plano')
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

    val_mm_disp  = total_real_val / 1000
    proj_val_mm  = total_real_val * fator_proj / 1000
    val_ant_mm   = df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                        (df_f['semana_mes']<=semana_atual)]['val_mm'].sum() / 1000
    var_val_mm   = (total_real_val/1000 - val_ant_mm) / val_ant_mm if val_ant_mm > 0 else None
    var_val_cor  = '#1A7A40' if (var_val_mm or 0) >= 0 else '#C0392B'
    _vval_sinal  = '+' if (var_val_mm or 0) >= 0 else ''
    var_val_txt  = f'{_vval_sinal}{var_val_mm:.1%} vs mes ant.' if var_val_mm is not None else ''

    preco_txt     = f"R$ {int(preco_real):,}/ton".replace(',', '.') if preco_real else '—'
    preco_ant_txt = f"R$ {int(preco_ant):,}/ton".replace(',', '.') if preco_ant else '—'
    var_preco_cor = '#1A7A40' if (var_preco or 0) >= 0 else '#C0392B'
    _vp_sinal     = '+' if (var_preco or 0) >= 0 else ''
    var_preco_txt = f'{_vp_sinal}{var_preco:.1%}' if var_preco is not None else '—'

    c1, c2, c3, c4 = st.columns([1, 1.1, 0.9, 0.9])

    with c1:
        fig_g = make_gauge(ritmo_geral or 0.0, 'Ritmo Geral', height=200)
        st.plotly_chart(fig_g, use_container_width=True,
                        config={'displayModeBar': False},
                        key=f'{col_meta}_gauge_geral')
        st.markdown(_gauge_sub(total_real_vol, meta_acum_esp), unsafe_allow_html=True)

    with c2:
        html_vol = (
            '<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            f'border-top:4px solid {cor_vol};box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.6px;color:#6C757D;margin-bottom:4px">VOLUME REALIZADO</div>'
            f'<div style="font-size:26px;font-weight:800;color:{cor_vol};line-height:1.1;'
            f'margin-bottom:8px">{_fmt_ton(total_real_vol)} ton</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Meta acum.: <b>{_fmt_ton(meta_acum_esp)} ton</b> &nbsp;|&nbsp; '
            f'<span style="color:{cor_vol}">{desvio_sinal}{_fmt_ton(desvio_abs)} ton {desvio_pct_txt}</span></div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Proj. mes: <b>{_fmt_ton(proj_vol_geral)} ton</b> '
            f'<span style="color:{ating_cor}">({ating_txt})</span></div>'
            f'<div style="font-size:11px">Gap: <span style="color:{gap_cor};font-weight:700">{gap_label}</span> &nbsp;|&nbsp; '
            f'<span style="color:{var_vol_cor}">{var_vol_txt}</span></div>'
            '</div>'
        )
        st.markdown(html_vol, unsafe_allow_html=True)

    with c3:
        html_preco = (
            '<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            'border-top:4px solid #F4822A;box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.6px;color:#6C757D;margin-bottom:4px">PRECO MEDIO</div>'
            f'<div style="font-size:26px;font-weight:800;color:#1B2A4A;line-height:1.1;'
            f'margin-bottom:8px">{preco_txt}</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Mes ant.: <b>{preco_ant_txt}</b></div>'
            f'<div style="font-size:11px;color:#2C3E50">Variacao: <span style="color:{var_preco_cor};font-weight:700">{var_preco_txt}</span></div>'
            '</div>'
        )
        st.markdown(html_preco, unsafe_allow_html=True)

    with c4:
        html_val = (
            '<div style="background:#fff;border-radius:8px;padding:14px 16px;'
            'border-top:4px solid #1B2A4A;box-shadow:0 2px 8px rgba(0,0,0,.07);height:100%">'
            '<div style="font-size:10px;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.6px;color:#6C757D;margin-bottom:4px">VALOR REALIZADO</div>'
            f'<div style="font-size:26px;font-weight:800;color:#1B2A4A;line-height:1.1;'
            f'margin-bottom:8px">R$ {val_mm_disp:.1f} MM</div>'
            f'<div style="font-size:11px;color:#2C3E50;margin-bottom:3px">Proj. mes: <b>R$ {proj_val_mm:.1f} MM</b></div>'
            f'<div style="font-size:11px;color:{var_val_cor}">{var_val_txt}</div>'
            '</div>'
        )
        st.markdown(html_val, unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # ── SEÇÃO 3: Gauges por empresa ────────────────────────────────
    st.markdown('<div class="secao-titulo">Ritmo por Empresa</div>',
                unsafe_allow_html=True)

    empresas = ['ACC', 'ACI', 'SIN']
    cols_emp = st.columns(3)

    for i, emp in enumerate(empresas):
        df_emp = df_acum[df_acum['empresa'] == emp]
        df_emp_mes = df_mes[df_mes['empresa'] == emp]

        real_emp = df_emp['vol_ton'].sum()
        meta_emp_mes = df_emp_mes[col_meta].sum()
        meta_emp_acum = meta_emp_mes * pct_esperado
        ritmo_emp = real_emp / meta_emp_acum if meta_emp_acum > 0 else None

        with cols_emp[i]:
            fig_emp = make_gauge(ritmo_emp or 0.0, emp, height=190)
            st.plotly_chart(fig_emp, use_container_width=True,
                            config={'displayModeBar': False},
                            key=f'{col_meta}_gauge_{emp}')
            st.markdown(_gauge_sub(real_emp, meta_emp_acum), unsafe_allow_html=True)

    # ── SEÇÃO 4a: Comparativo Semanal ────────────────────────────────
    col_meta_label = 'Plano S&OP' if col_meta == 'meta_sop' else 'Programa S&OE'
    st.markdown('<div class="secao-titulo">Comparativo Semanal — Realizado vs Plano</div>',
                unsafe_allow_html=True)

    fig_sem = graf_semanal(df_mes, col_meta, semana_atual, col_meta_label,
                          tw_ranges=tw_ranges, ano_sel=ano_sel, mes_sel=mes_sel)
    st.plotly_chart(fig_sem, use_container_width=True,
                    config={'displayModeBar': False},
                    key=f'{col_meta}_semanal_{ano_sel}_{mes_sel}')

    # ── SEÇÃO 4b: Matriz Semana × Linha ──────────────────────────
    risk_badges = matriz_semanal.render(
        df_f=df_f,
        col_meta=col_meta,
        ano_sel=ano_sel,
        mes_sel=mes_sel,
        semana_atual=semana_atual,
        n_semanas=n_semanas,
        kp=f"{col_meta}_{ano_sel}_{mes_sel}",
    )

    # ── SEÇÃO 4c: Histórico diário ────────────────────────────────
    st.markdown('<div class="secao-titulo">Venda Diária no Mês</div>',
                unsafe_allow_html=True)

    df_v_mes_filt = df_v_raw[
        (df_v_raw['ano'] == ano_sel) & (df_v_raw['mes'] == mes_sel)
    ].copy()

    fig_dia = graf_diario(df_v_mes_filt, total_meta_mes, ano_sel, mes_sel,
                          dia_ref_externo=dia_ref)
    st.plotly_chart(fig_dia, use_container_width=True,
                    config={'displayModeBar': False},
                    key=f'{col_meta}_diario_{ano_sel}_{mes_sel}')

    # ── Dados por linha para seções 5-6 ────────────────────────────
    por_linha_acum = (df_acum.groupby('linha')
                     .agg(vol_real=('vol_ton', 'sum'), val_real=('val_mm', 'sum'))
                     .reset_index())
    por_linha_mes = (df_mes.groupby('linha')[col_meta].sum().reset_index()
                    .rename(columns={col_meta: 'meta_mes'}))
    por_linha = por_linha_acum.merge(por_linha_mes, on='linha', how='outer').fillna(0)

    # Pesos por linha → meta acumulada esperada (para Ritmo%)
    def _peso_acum_linha(l):
        return sum(get_peso(pesos, l, s) for s in range(1, semana_atual + 1))

    por_linha['peso_acum'] = por_linha['linha'].map(_peso_acum_linha)
    por_linha['meta_acum'] = por_linha['meta_mes'] * por_linha['peso_acum']
    # Projeção linear pelo ritmo diário real — não por peso semanal
    por_linha['projecao']  = por_linha['vol_real'] * fator_proj
    por_linha['ritmo_pct'] = por_linha.apply(
        lambda r: r['vol_real'] / r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)
    por_linha['gap_ton']   = por_linha['meta_mes'] - por_linha['projecao'].fillna(0)
    por_linha['gap_pct']   = por_linha.apply(
        lambda r: r['gap_ton'] / r['meta_mes'] if r['meta_mes'] > 0 else None, axis=1)

    # Tendência vs semana anterior
    sem_ant = semana_atual - 1
    if sem_ant >= 1:
        df_ant = df_mes[df_mes['semana_mes'] == sem_ant].groupby('linha')['vol_ton'].sum()
        df_atual = df_mes[df_mes['semana_mes'] == semana_atual].groupby('linha')['vol_ton'].sum()
        tendencia = {}
        for l in por_linha['linha']:
            v_ant = df_ant.get(l, 0)
            v_at  = df_atual.get(l, 0)
            if v_ant > 0:
                tendencia[l] = (v_at - v_ant) / v_ant
            else:
                tendencia[l] = None
        por_linha['tendencia'] = por_linha['linha'].map(tendencia)
    else:
        por_linha['tendencia'] = None

    por_linha = por_linha.sort_values('vol_real', ascending=False)

    # ── SEÇÃO 5: Charts por família ────────────────────────────────
    st.markdown('<div class="secao-titulo">Ritmo por Linha de Produto — por Família</div>',
                unsafe_allow_html=True)

    linha_familia = get_linha_familia(df_v_raw)
    por_linha['familia'] = (
        por_linha['linha'].map(linha_familia)
        .fillna('OUTROS')
        .astype(str)
        .str.strip()
        .replace({"NAN": "OUTROS", "NONE": "OUTROS", "": "OUTROS"})
    )
    # Remove linhas sem família válida (sujeira de dados)
    por_linha = por_linha[~por_linha['familia'].isin(["NAN", "NONE", ""])].copy()

    familias_ord = (por_linha.groupby('familia')['vol_real'].sum()
                    .sort_values(ascending=False).index.tolist())

    n_fam = len(familias_ord)
    # Divide famílias em pares de colunas para poupar espaço vertical
    for idx in range(0, n_fam, 2):
        cols_fam = st.columns(2) if idx + 1 < n_fam else [st.container(), None]
        for j, fam in enumerate(familias_ord[idx:idx+2]):
            df_fam = por_linha[por_linha['familia'] == fam]
            container = cols_fam[j] if cols_fam[j] is not None else cols_fam[0]
            with container:
                # ── Card KPI da família ──────────────────────────────
                real_fam     = df_fam['vol_real'].sum()
                meta_fam_ac  = df_fam['meta_acum'].sum()
                meta_fam_mes = df_fam['meta_mes'].sum()
                proj_fam     = real_fam * fator_proj
                ritmo_fam    = real_fam / meta_fam_ac if meta_fam_ac > 0 else None
                gap_fam      = meta_fam_mes - proj_fam   # positivo = falta, negativo = acima

                # Mês anterior — mesmo período (até semana_atual)
                linhas_fam = df_fam['linha'].tolist()
                df_ant_fam = df_f[
                    (df_f['ano'] == ano_ant) & (df_f['mes'] == mes_ant) &
                    (df_f['semana_mes'] <= semana_atual) &
                    (df_f['linha'].isin(linhas_fam))
                ]
                real_fam_ant = df_ant_fam['vol_ton'].sum()
                var_mm_fam   = ((real_fam - real_fam_ant) / real_fam_ant
                                if real_fam_ant > 0 else None)

                # Atingimento vs meta do mês completo (projeção / meta)
                ating_fam   = proj_fam / meta_fam_mes if meta_fam_mes > 0 else None

                cor_f        = cor_ritmo(ritmo_fam)
                rit_txt      = f'{ritmo_fam:.1%}' if ritmo_fam is not None else '—'
                gap_cor      = '#C0392B' if gap_fam > 0 else '#1A7A40'
                gap_label    = f'{_fmt_ton(gap_fam):} ton a fechar' if gap_fam > 0 else f'{_fmt_ton(abs(gap_fam))} ton acima'
                proj_cor     = '#1A7A40' if (ating_fam or 0) >= 1.0 else '#C0392B'
                proj_label   = f'{ating_fam:.0%} da meta' if ating_fam is not None else '—'
                var_cor      = '#1A7A40' if (var_mm_fam or 0) >= 0 else '#C0392B'
                var_sinal    = '+' if (var_mm_fam or 0) >= 0 else ''
                var_label    = f'{var_sinal}{var_mm_fam:.1%} vs mês ant.' if var_mm_fam is not None else 'sem histórico'

                st.markdown(f"""
                <div style="background:#fff;border-radius:8px;padding:10px 14px;
                            margin-bottom:4px;border-left:5px solid {cor_f};
                            box-shadow:0 1px 6px rgba(0,0,0,0.08);">
                  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
                    <div style="font-size:14px;font-weight:800;color:{COR_PRIMARIA};
                                letter-spacing:.4px;min-width:80px">{fam}</div>
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
                </div>
                """, unsafe_allow_html=True)

                graf_familia_barras(
                    df_fam, fam, fator_proj,
                    chart_key=f'{col_meta}_fam_{fam.replace(" ","_")}_{idx}_{j}'
                )

    # ── SEÇÃO 5b: Score de Oportunidade por Linha ────────────────────
    st.markdown('<div class="secao-titulo">🎯 Score de Oportunidade — Valor em Risco por Linha</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px;color:#555;margin-top:-6px;margin-bottom:10px;">'
        'Mostra quanto cada linha está perdendo em receita com base no gap de volume projetado '
        'e no preço médio realizado. Ordenado do maior ao menor risco de receita.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Dados por linha e UF para calcular preço médio ──────────────
    opp_real = (df_acum.groupby('linha')
                .agg(vol_real=('vol_ton','sum'), val_real=('val_mm','sum'))
                .reset_index())
    opp_meta = (df_mes.groupby('linha')[col_meta].sum().reset_index()
                .rename(columns={col_meta:'meta_mes'}))
    opp = opp_real.merge(opp_meta, on='linha', how='outer').fillna(0)

    opp['peso_acum']   = opp['linha'].map(
        lambda l: sum(get_peso(pesos, l, s) for s in range(1, semana_atual + 1)))
    opp['meta_acum']   = opp['meta_mes'] * opp['peso_acum']
    opp['projecao']    = opp['vol_real'] * fator_proj
    opp['ritmo_pct']   = opp.apply(
        lambda r: r['vol_real'] / r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)
    opp['gap_ton']     = opp['meta_mes'] - opp['projecao']   # positivo = está atrás
    opp['desvio_pct']  = opp.apply(
        lambda r: r['gap_ton'] / r['meta_mes'] if r['meta_mes'] > 0 else None, axis=1)

    # Preço médio realizado em R$/ton  (val_mm está em kR$, ×1000 → R$)
    opp['preco_medio'] = opp.apply(
        lambda r: r['val_real'] / r['vol_real'] * 1000 if r['vol_real'] > 0 else None, axis=1)

    # Preço médio do mês anterior para mesma linha (período equivalente)
    opp_ant = (df_f[(df_f['ano']==ano_ant) & (df_f['mes']==mes_ant) &
                    (df_f['semana_mes']<=semana_atual)]
               .groupby('linha')
               .agg(vol_ant=('vol_ton','sum'), val_ant=('val_mm','sum'))
               .reset_index())
    opp_ant['preco_ant'] = opp_ant.apply(
        lambda r: r['val_ant'] / r['vol_ant'] * 1000 if r['vol_ant'] > 0 else None, axis=1)
    opp = opp.merge(opp_ant[['linha','preco_ant']], on='linha', how='left')

    # Variação de preço vs mês anterior
    opp['var_preco'] = opp.apply(
        lambda r: (r['preco_medio'] - r['preco_ant']) / r['preco_ant']
        if (pd.notna(r.get('preco_medio')) and pd.notna(r.get('preco_ant'))
            and r['preco_ant'] > 0) else None, axis=1)

    # Score de oportunidade: gap_ton × preco_medio → R$ de receita em risco
    # (apenas quando gap > 0, ou seja, está atrás da meta)
    opp['oportunidade_r'] = opp.apply(
        lambda r: max(0, r['gap_ton']) * r['preco_medio']
        if pd.notna(r.get('preco_medio')) else max(0, r['gap_ton']) * 0, axis=1)

    # Ordena: maior oportunidade primeiro, depois linhas acima do plano
    opp_show = opp[opp['meta_mes'] > 0].sort_values('oportunidade_r', ascending=False)

    if not opp_show.empty:
        def _fmt_rs(v):
            if v is None or pd.isna(v): return '—'
            if v >= 1_000_000:
                return f'R$ {v/1_000_000:.1f} MM'
            elif v >= 1_000:
                return f'R$ {v/1_000:.0f} k'
            return f'R$ {v:,.0f}'

        def _fmt_preco(v):
            if v is None or pd.isna(v): return '—'
            return f'R$ {int(v):,}/t'.replace(',','.')

        def _fmt_gap(v):
            if v is None or pd.isna(v): return '—'
            sinal = '+' if v > 0 else ''
            return f'{sinal}{_fmt_ton(v)} ton'

        def _fmt_pct(v):
            if v is None or pd.isna(v): return '—'
            return f'{v:+.1%}'

        # Incorpora tendência do por_linha (evita recomputar)
        opp_show = opp_show.merge(
            por_linha[['linha', 'tendencia']].drop_duplicates('linha'),
            on='linha', how='left',
        )

        tab_opp = pd.DataFrame({
            'St.':             opp_show['ritmo_pct'].map(icone_ritmo),
            'Linha':           opp_show['linha'],
            'Meta Mês':        opp_show['meta_mes'].map(lambda v: _fmt_ton(v) + ' t'),
            'Realizado':       opp_show['vol_real'].map(lambda v: _fmt_ton(v) + ' t'),
            'Ritmo':           opp_show['ritmo_pct'].map(lambda v: f'{v:.0%}' if pd.notna(v) else '—'),
            'Tend.':           opp_show['tendencia'].map(seta_tendencia),
            'Gap Vol.':        opp_show['gap_ton'].map(_fmt_gap),
            'Desvio Meta':     opp_show['desvio_pct'].map(_fmt_pct),
            'Preço Médio':     opp_show['preco_medio'].map(_fmt_preco),
            'Var Preço MM':    opp_show['var_preco'].map(_fmt_pct),
            'Oportunidade R$': opp_show['oportunidade_r'].map(_fmt_rs),
        })

        def _style_opp(row):
            styles = []
            for col in row.index:
                if col == 'Oportunidade R$':
                    # Gradiente: vermelho → amarelo conforme valor
                    try:
                        raw = opp_show[opp_show['linha']==row['Linha']]['oportunidade_r'].values[0]
                        max_v = opp_show['oportunidade_r'].max()
                        if raw > 0 and max_v > 0:
                            intensity = raw / max_v
                            if intensity > 0.60:
                                styles.append('background-color:#F5D5D1;color:#C0392B;font-weight:700;text-align:right')
                            elif intensity > 0.25:
                                styles.append('background-color:#FFF3E0;color:#C0392B;font-weight:700;text-align:right')
                            else:
                                styles.append('background-color:#F5E9C8;color:#8A6000;font-weight:600;text-align:right')
                        else:
                            styles.append('background-color:#D6EDE0;color:#1A7A40;font-weight:600;text-align:right')
                    except Exception:
                        styles.append('text-align:right')
                elif col == 'Ritmo':
                    try:
                        num = float(str(row[col]).replace('%','').replace(',','.')) / 100
                        if num >= 0.90:
                            styles.append('background-color:#D6EDE0;color:#1A7A40;font-weight:600;text-align:center')
                        elif num >= 0.75:
                            styles.append('background-color:#F5E9C8;color:#8A6000;font-weight:600;text-align:center')
                        else:
                            styles.append('background-color:#F5D5D1;color:#C0392B;font-weight:600;text-align:center')
                    except Exception:
                        styles.append('text-align:center')
                elif col == 'Gap Vol.':
                    try:
                        raw = opp_show[opp_show['linha']==row['Linha']]['gap_ton'].values[0]
                        if raw > 0:
                            styles.append('color:#C0392B;font-weight:600;text-align:right')
                        else:
                            styles.append('color:#1A7A40;font-weight:600;text-align:right')
                    except Exception:
                        styles.append('text-align:right')
                elif col == 'Desvio Meta':
                    try:
                        num = float(str(row[col]).replace('%','').replace('+','').replace(',','.')) / 100
                        if num > 0:
                            styles.append('color:#C0392B;text-align:right')
                        elif num < 0:
                            styles.append('color:#1A7A40;text-align:right')
                        else:
                            styles.append('text-align:right')
                    except Exception:
                        styles.append('text-align:right')
                elif col == 'Var Preço MM':
                    try:
                        num = float(str(row[col]).replace('%','').replace('+','').replace(',','.')) / 100
                        styles.append(f'color:{"#1A7A40" if num >= 0 else "#C0392B"};text-align:right')
                    except Exception:
                        styles.append('text-align:right')
                elif col in ('Linha',):
                    styles.append('font-weight:700;text-align:left')
                elif col in ('St.', 'Tend.'):
                    styles.append('text-align:center')
                else:
                    styles.append('text-align:right')
            return styles

        styled_opp = (tab_opp.style
                      .apply(_style_opp, axis=1)
                      .set_properties(**{'font-size': '12px', 'padding': '5px 8px'})
                      .set_table_styles([
                          {'selector': 'th', 'props': [
                              ('background-color', COR_PRIMARIA),
                              ('color', 'white'), ('font-size', '11px'),
                              ('text-align', 'center'), ('padding', '6px 8px'),
                          ]},
                          {'selector': 'th.row_heading', 'props': [('display', 'none')]},
                      ]))

        st.dataframe(styled_opp,
                     use_container_width=True,
                     hide_index=True,
                     height=min(760, 44 + len(tab_opp) * 36))

        st.markdown(
            '<div style="font-size:10px;color:#6C757D;margin-top:-4px;margin-bottom:16px;">'
            '<b>St.</b> = status de ritmo &nbsp;|&nbsp; '
            '<b>Tend.</b> = variação vs semana anterior &nbsp;|&nbsp; '
            '<b>Ritmo</b> = realizado ÷ meta acumulada esperada &nbsp;|&nbsp; '
            '<b>Gap Vol.</b> = meta mês − projeção linear &nbsp;|&nbsp; '
            '<b>Oportunidade R$</b> = gap de volume × preço médio (quanto de receita está em risco)'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── SEÇÃO 7: Dashboard UF — Mapa + Tabela ────────────────────
    st.markdown('<div class="secao-titulo">📍 Desempenho por Estado</div>',
                unsafe_allow_html=True)

    por_reg_acum = (df_acum.groupby(['regiao','uf'])
                   .agg(vol_real=('vol_ton','sum'), val_real=('val_mm','sum'))
                   .reset_index())
    por_reg_mes = (df_mes.groupby(['regiao','uf'])[col_meta].sum().reset_index()
                  .rename(columns={col_meta: 'meta_mes'}))
    por_reg = por_reg_acum.merge(por_reg_mes, on=['regiao','uf'], how='outer').fillna(0)

    por_reg['meta_acum'] = por_reg['meta_mes'] * pct_esperado
    por_reg['ritmo_pct'] = por_reg.apply(
        lambda r: r['vol_real'] / r['meta_acum'] if r['meta_acum'] > 0 else None, axis=1)
    por_reg['projecao']  = por_reg['vol_real'] * fator_proj
    por_reg['gap_ton']   = por_reg['meta_mes'] - por_reg['projecao'].fillna(0)
    por_reg['gap_pct']   = por_reg.apply(
        lambda r: r['gap_ton'] / r['meta_mes'] if r['meta_mes'] > 0 else None, axis=1)
    por_reg = por_reg.sort_values('vol_real', ascending=False)

    col_meta_label_local = 'Plano S&OP' if col_meta == 'meta_sop' else 'Programa S&OE'
    dashboard_uf.render(
        por_reg=por_reg,
        col_meta_label=col_meta_label_local,
        chart_key=f"{col_meta}_{ano_sel}_{mes_sel}",
    )

    # ── SEÇÃO 8: Demand Sensing ────────────────────────────────────
    st.markdown("---")
    demand_sensing.render(
        df_f=df_f,
        pesos=pesos,
        col_meta=col_meta,
        label_meta=label_meta,
        ano_sel=ano_sel,
        mes_sel=mes_sel,
        semana_atual=semana_atual,
        n_semanas=n_semanas,
        filtros_ativos=filtros_ativos,
    )


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

# ── Autenticação — bloqueia tudo antes de carregar qualquer dado ───────────────
try:
    from utils.auth import require_auth, render_sidebar_user
except Exception as _e:
    st.error(f"❌ Erro ao importar auth: {_e}\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

require_auth()

try:
    df, df_v_raw = carrega_dados()
    pesos = calcula_pesos(df_v_raw)
except Exception as _e:
    st.error(f"❌ Erro ao carregar dados: {_e}\n\n```\n{traceback.format_exc()}\n```")
    st.stop()

hoje = date.today()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 8px 0 16px 0;">
      <div style="font-size:22px; font-weight:800; color:{COR_PRIMARIA};">AÇO CEARENSE</div>
      <div style="font-size:11px; color:#6C757D; letter-spacing:1px;">S&OE — INTELIGÊNCIA COMERCIAL</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Usuário logado + botão de logout ────────────────────────────────────────
    render_sidebar_user()

    st.markdown("---")
    st.markdown("**Filtros**")

    empresas_disp = sorted(df['empresa'].dropna().unique())
    empresa_sel = st.multiselect(
        "Empresa", empresas_disp, default=[],
        placeholder="Todas as empresas",
    )

    regioes_disp = sorted(df['regiao'].dropna().unique())
    regiao_sel = st.multiselect(
        "Região", regioes_disp, default=[],
        placeholder="Todas as regiões",
    )

    ufs_disp = sorted(df['uf'].dropna().unique())
    uf_sel = st.multiselect(
        "Estado (UF)", ufs_disp, default=[],
        placeholder="Todos os estados",
    )

    linhas_disp = sorted(df['linha'].dropna().unique())
    linha_sel = st.multiselect(
        "Linha de Produto", linhas_disp, default=[],
        placeholder="Todas as linhas",
    )

    st.markdown("---")
    st.markdown("**Período**")

    anos_disp = sorted([int(a) for a in df['ano'].unique()], reverse=True)
    ano_sel = int(st.selectbox("Ano", anos_disp,
                               index=anos_disp.index(hoje.year) if hoje.year in anos_disp else 0))

    meses_disp = sorted([int(m) for m in df[df['ano'] == ano_sel]['mes'].unique()], reverse=True)
    mes_sel = int(st.selectbox("Mês", meses_disp,
                               format_func=lambda x: MESES[x],
                               index=meses_disp.index(hoje.month)
                               if hoje.month in meses_disp else 0))

    st.markdown("---")
    # Timestamp e aviso de dados desatualizados (req 4.5)
    data_max = df_v_raw['data'].max()
    dias_defasagem = (date.today() - data_max.date()).days
    if dias_defasagem > 3:
        st.warning(f"⚠️ Dados com {dias_defasagem}d de defasagem. Última atualização: {data_max.strftime('%d/%b/%Y')}")
    else:
        st.markdown(f"""
    <div style="font-size:10px; color:#9AA5B4; text-align:center;">
      Dados até {data_max.strftime('%d/%b/%Y')}<br>
      {len(df_v_raw):,} registros carregados
    </div>
    """, unsafe_allow_html=True)

# ── Aplica filtros ──────────────────────────────────────────────────────────────
# Task 2.2: filtro vazio → aviso visual + fallback para "todos" (não retorna base vazia)
# Vazio = "todos" — sem aviso, é o comportamento esperado
if not empresa_sel:
    empresa_sel = sorted(df['empresa'].dropna().unique())
if not regiao_sel:
    regiao_sel = sorted(df['regiao'].dropna().unique())
if not uf_sel:
    uf_sel = sorted(df['uf'].dropna().unique())
if not linha_sel:
    linha_sel = sorted(df['linha'].dropna().unique())

df_f = df[
    df['empresa'].isin(empresa_sel) &
    df['regiao'].isin(regiao_sel) &
    df['uf'].isin(uf_sel) &
    df['linha'].isin(linha_sel)
].copy()

df_v_f = df_v_raw[
    df_v_raw['empresa'].isin(empresa_sel) &
    df_v_raw['regiao'].isin(regiao_sel) &
    df_v_raw['uf'].isin(uf_sel) &
    df_v_raw['linha'].isin(linha_sel)
].copy()

filtros_ativos = []
if set(empresa_sel) != set(sorted(df['empresa'].dropna().unique())):
    filtros_ativos.append(' + '.join(sorted(empresa_sel)))
if set(regiao_sel) != set(sorted(df['regiao'].dropna().unique())):
    filtros_ativos.append(' + '.join(sorted(regiao_sel)))
if set(uf_sel) != set(sorted(df['uf'].dropna().unique())):
    filtros_ativos.append(' + '.join(sorted(uf_sel)))
if set(linha_sel) != set(sorted(df['linha'].dropna().unique())):
    filtros_ativos.append(' + '.join(sorted(linha_sel)))

# ── Logo / header global ───────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"""
    <div style="padding:4px 0 12px 0;">
      <span style="font-size:24px; font-weight:800; color:{COR_PRIMARIA};">
        Painel S&OE
      </span>
      <span style="font-size:14px; color:#6C757D; margin-left:8px;">
        Inteligência Comercial
      </span>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    st.markdown(f"""
    <div style="text-align:right; padding-top:8px; font-size:12px; color:#6C757D;">
      Atualizado: {hoje.strftime('%d/%m/%Y')}
    </div>
    """, unsafe_allow_html=True)

# ── Abas ───────────────────────────────────────────────────────────────────────
aba1, aba2, aba3, aba4 = st.tabs([
    "📋  Venda vs Plano S&OP",
    "📊  Venda vs Programa S&OE",
    "📞  Prioridade de Contato",
    "🗓️  Plano Comercial Semanal",
])

with aba1:
    render_aba(
        df_f, df_v_f, pesos,
        col_meta='meta_sop',
        label_meta='Venda vs Plano S&OP',
        ano_sel=ano_sel,
        mes_sel=mes_sel,
        filtros_ativos=filtros_ativos,
    )

with aba2:
    # S&OE só existe jan-jul/2026
    tem_soe = (ano_sel == 2026 and mes_sel <= 7)
    if not tem_soe:
        st.info(
            f"O Programa S&OE não está disponível para {MESES[mes_sel]}/{ano_sel}. "
            "O S&OE cobre Jan–Jul/2026. Utilize a aba **Plano S&OP** para períodos anteriores."
        )
    else:
        render_aba(
            df_f, df_v_f, pesos,
            col_meta='meta_soe',
            label_meta='Venda vs Programa S&OE',
            ano_sel=ano_sel,
            mes_sel=mes_sel,
            filtros_ativos=filtros_ativos,
        )

# Filtros globais para a aba de inteligência comercial
_filtros_globais = {
    "empresas": empresa_sel,
    "linhas":   [],
    "regioes":  regiao_sel,
    "ufs":      uf_sel,
}

with aba3:
    score_propensao.render(df_v_raw, _filtros_globais)

# ── Aba 4: Plano Comercial Semanal ─────────────────────────────────────────────
with aba4:
    # Recalcula tw_ranges e semana_atual para o período selecionado
    _dia_ref_plano = hoje.day if (hoje.year == ano_sel and hoje.month == mes_sel) else \
                     _cal_mod.monthrange(ano_sel, mes_sel)[1]
    if ano_sel >= 2026:
        _tw_ranges_plano  = get_month_tw_ranges(ano_sel, mes_sel)
        _semana_atual_plano = day_to_semana_tw(ano_sel, mes_sel, _dia_ref_plano) or \
                              len(_tw_ranges_plano)
    else:
        _tw_ranges_plano  = [(1, 1, 7), (2, 8, 14), (3, 15, 21),
                             (4, 22, _cal_mod.monthrange(ano_sel, mes_sel)[1])]
        _semana_atual_plano = int(
            pd.cut([_dia_ref_plano], bins=[0, 7, 14, 21, 31], labels=[1, 2, 3, 4])[0]
        )

    plano_comercial.render(
        df_f=df_f,
        df_v_raw=df_v_raw,
        filtros=_filtros_globais,
        semana_atual=_semana_atual_plano,
        ano_sel=ano_sel,
        mes_sel=mes_sel,
        tw_ranges=_tw_ranges_plano,
    )
