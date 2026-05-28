"""
Utilitários visuais compartilhados — paleta de cores, formatadores e helpers de cor.
"""
from __future__ import annotations
import numpy as np

# ── Paleta de cores ───────────────────────────────────────────────────────────
COR_PRIMARIA = "#1E3A5F"   # azul marinho profundo
COR_ACENTO   = "#D97706"   # âmbar dourado
COR_VERDE    = "#10B981"   # esmeralda moderna
COR_AMARELO  = "#F59E0B"   # âmbar
COR_VERMELHO = "#EF4444"   # vermelho claro
COR_FUNDO    = "#F8FAFC"   # fundo quase branco frio
COR_CARD     = "#FFFFFF"
COR_TEXTO    = "#1E293B"   # slate escuro
COR_GRID     = "#E2E8F0"   # borda suave

def fmt_ton(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return f"{int(round(v)):,}".replace(",", ".")

def cor_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "#94A3B8"
    if pct >= 0.90: return COR_VERDE
    elif pct >= 0.75: return COR_AMARELO
    return COR_VERMELHO

def icone_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "—"
    if pct >= 0.90: return "🟢"
    elif pct >= 0.75: return "🟡"
    return "🔴"

def cor_bg_ritmo(pct) -> str:
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "#F8FAFC"
    if pct >= 0.90: return "#ECFDF5"
    elif pct >= 0.75: return "#FFFBEB"
    return "#FEF2F2"

def seta_tendencia(var) -> str:
    if var is None or (isinstance(var, float) and np.isnan(var)):
        return "→"
    if var > 0.05: return "↑"
    elif var < -0.05: return "↓"
    return "→"
