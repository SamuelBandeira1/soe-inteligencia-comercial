"""
Métricas canônicas do S&OE — fonte única de verdade.

Governança (parecer vinculante do Consultor Metodológico, 2026-05-30):
  - O rótulo "Bias" na UI designa UMA única grandeza: HC-02.
  - O termo de ruído do Monte Carlo é um objeto estatístico DISTINTO do Bias
    exibido — mora aqui como `mc_drift`, NUNCA confundir com `bias`.

Funções disponíveis:
  bias(real, plano, base="real")     → Bias exibido HC-02 — razão-de-somas P−R, %
  assertividade(real, plano, base)   → 1 − MAPE (razão-de-somas), % limitado a [0, 100]
  mc_drift(real, plano)              → drift do Monte Carlo — média-de-razões R−P, %

# HC-02/HC-T4: NAO unificar bias() e mc_drift() — objetos estatisticos distintos.
# Ver parecer 2026-05-30.
"""
from __future__ import annotations

import pandas as pd


def bias(real: pd.Series, plano: pd.Series, base: str = "real") -> float:
    """
    Bias EXIBIDO (HC-02) — viés sistemático do plano vs realizado.

    Fórmula: Σ(Plano − Real) / Σbase × 100  (razão-de-somas).
      base="real"  → denominador = ΣReal
      base="plano" → denominador = ΣPlano

    Convenção de sinal: positivo = plano ACIMA do real (overforecasting);
    negativo = plano abaixo do real (underforecasting).

    Retorna nan quando o denominador é zero (evita divisão por zero).
    """
    base_vals = real if base == "real" else plano
    d = base_vals.sum()
    return float((plano - real).sum() / d * 100) if d > 0 else float("nan")


def assertividade(real: pd.Series, plano: pd.Series, base: str = "real") -> float:
    """
    Assertividade = 1 − MAPE, calculado sobre a série acumulada (razão-de-somas).

    base="real"  → MAPE = Σ|Real−Plano| / ΣReal   (Forecast Accuracy clássico)
    base="plano" → MAPE = Σ|Real−Plano| / ΣPlano  (perspectiva do planejador)

    Retorna valor em % (0–100), limitado inferiormente a 0.
    Retorna nan quando a base é zero (evita divisão por zero).
    """
    base_vals = real if base == "real" else plano
    d = base_vals.sum()
    if d == 0:
        return float("nan")
    mape = float((real - plano).abs().sum() / d)
    return float(max(0.0, (1.0 - mape) * 100))


def mc_drift(real: pd.Series, plano: pd.Series) -> float:
    """
    Drift do Monte Carlo — termo que CENTRA o ruído multiplicativo do forecast.

    Fórmula: média((Real − Plano) / Plano) × 100  (média-de-razões).

    Convenção R−P, exigida por `base*(1+noise)` no Monte Carlo: positivo = real
    acima do plano. ATENÇÃO: sinal OPOSTO ao de bias() (P−R) para o mesmo dado —
    isto é intencional, não é bug (HC-T4-4).

    NÃO é uma métrica exibida e NÃO deve ser rotulada "Bias" na UI (HC-T4-1/2).

    Modo de falha da média-de-razões: instável quando Plano → 0 (a razão explode).
    Guarda numérica: semanas com plano ≤ 0 são excluídas antes da média. No
    Demand Sensing o filtro `vol_ton > 0 & meta > 0` já cobre esse caso (HC-T4-6).
    """
    razoes = (real - plano) / plano
    razoes = razoes[plano > 0]
    if razoes.empty:
        return float("nan")
    return float(razoes.mean() * 100)
