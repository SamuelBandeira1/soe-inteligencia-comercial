"""
Utilitários visuais compartilhados — paleta de cores, formatadores e helpers de cor.

Centraliza funções que estavam duplicadas em dashboard.py, ritmo_semanal.py
e score_propensao.py.
"""
from __future__ import annotations

import numpy as np

# ── Paleta de cores ───────────────────────────────────────────────────────────
COR_PRIMARIA = "#1B2A4A"   # Azul marinho profundo — marca
COR_ACENTO   = "#D96B2D"   # Laranja amadeirado — ligeiramente mais sóbrio
COR_VERDE    = "#1A7A40"   # Verde floresta — semáforo "bom"
COR_AMARELO  = "#B07D00"   # Âmbar escuro — semáforo "atenção" (vs FFC107 Bootstrap)
COR_VERMELHO = "#C0392B"   # Carmim profundo — semáforo "crítico"
COR_FUNDO    = "#F4F6F9"   # Fundo levemente azulado
COR_CARD     = "#FFFFFF"
COR_TEXTO    = "#2C3E50"
COR_GRID     = "#E4E9F0"


# ── Formatadores ──────────────────────────────────────────────────────────────
def fmt_ton(v) -> str:
    """Formata volume em toneladas com separador de milhar PT-BR (ponto)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return f"{int(round(v)):,}".replace(",", ".")


# ── Helpers de cor baseados em ritmo (%) ─────────────────────────────────────
def cor_ritmo(pct) -> str:
    """Retorna cor hex baseada no percentual de ritmo vs meta."""
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "#6C757D"
    if pct >= 0.90:
        return COR_VERDE
    elif pct >= 0.75:
        return COR_AMARELO
    return COR_VERMELHO


def icone_ritmo(pct) -> str:
    """Retorna emoji de semáforo baseado no percentual de ritmo."""
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "—"
    if pct >= 0.90:
        return "🟢"
    elif pct >= 0.75:
        return "🟡"
    return "🔴"


def cor_bg_ritmo(pct) -> str:
    """Retorna cor de fundo (para células de tabela) baseada no ritmo."""
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "#F8F9FA"
    if pct >= 0.90:
        return "#D6EDE0"   # verde-água suave (combina com COR_VERDE escuro)
    elif pct >= 0.75:
        return "#F5E9C8"   # âmbar claro (combina com COR_AMARELO escuro)
    return "#F5D5D1"       # rosa claro (combina com COR_VERMELHO escuro)


def seta_tendencia(var) -> str:
    """Retorna seta de tendência baseada na variação percentual."""
    if var is None or (isinstance(var, float) and np.isnan(var)):
        return "→"
    if var > 0.05:
        return "↑"
    elif var < -0.05:
        return "↓"
    return "→"
