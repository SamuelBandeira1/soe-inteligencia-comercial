"""
Utilitários de Calendário de Semanas Técnicas (TW — Technical Week).

Semanas Técnicas seguem o padrão ISO 8601:
  - A semana 1 do ano é a que contém o primeiro quinta-feira
  - Semanas começam na segunda-feira

Funções disponíveis:
  get_month_tw_ranges(year, month)  → lista de (semana_mes, dia_ini, dia_fim)
  day_to_semana_tw(year, month, day) → int | None
  vectorize_semana_tw(years, months, days) → pd.Series  (versão vetorizada)
  tw_label(ano, mes, semana_mes)    → str  ex.: "TW10B Mar/2026"
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, timedelta

import pandas as pd

_MESES_ABR = {1:'Jan',2:'Fev',3:'Mar',4:'Abr',5:'Mai',6:'Jun',
              7:'Jul',8:'Ago',9:'Set',10:'Out',11:'Nov',12:'Dez'}


def tw_label(ano: int, mes: int, semana_mes: int) -> str:
    """
    Retorna o label da Semana Técnica no formato "TW{n}[A|B] {Mês}/{Ano}".

    Sufixo A/B (semana que cruza virada de mês):
      B = a semana começou no mês anterior, termina neste mês
      A = a semana começa neste mês, termina no mês seguinte
      (sem sufixo) = semana inteiramente dentro do mês

    Exemplo: TW10B Mar/2026 → TW 10 começou em fev, restante cai em março.
    """
    last    = _cal.monthrange(ano, mes)[1]
    m_start = date(ano, mes, 1)
    m_end   = date(ano, mes, last)
    jan4    = date(ano, 1, 4)
    w1      = jan4 - timedelta(days=jan4.weekday())

    sem_count = 0
    tw_num    = 1
    while True:
        mon = w1 + timedelta(weeks=tw_num - 1)
        sun = mon + timedelta(days=6)
        if mon > m_end:
            break
        s = max(mon, m_start)
        e = min(sun, m_end)
        if s <= e:
            sem_count += 1
            if sem_count == semana_mes:
                if mon < m_start:
                    suffix = "B"
                elif sun > m_end:
                    suffix = "A"
                else:
                    suffix = ""
                return f"TW{tw_num}{suffix} {_MESES_ABR[mes]}/{ano}"
        tw_num += 1
    return f"S{semana_mes} {_MESES_ABR[mes]}/{ano}"


def get_month_tw_ranges(year: int, month: int) -> list[tuple[int, int, int]]:
    """
    Retorna [(semana_mes, dia_inicio, dia_fim), ...] baseado nas Semanas Técnicas.

    Cada TW que toca o mês vira uma semana_mes sequencial
    (1 = TW mais antiga que toca o mês, 2 = próxima, ...).
    """
    last    = _cal.monthrange(year, month)[1]
    m_start = date(year, month, 1)
    m_end   = date(year, month, last)
    jan4    = date(year, 1, 4)
    w1      = jan4 - timedelta(days=jan4.weekday())  # segunda da semana 1

    result: list[tuple[int, int, int]] = []
    sem = 0
    tw  = 1
    while True:
        mon = w1 + timedelta(weeks=tw - 1)
        sun = mon + timedelta(days=6)
        if mon > m_end:
            break
        s = max(mon, m_start)
        e = min(sun, m_end)
        if s <= e:
            sem += 1
            result.append((sem, s.day, e.day))
        tw += 1
    return result


def day_to_semana_tw(year: int, month: int, day: int) -> int | None:
    """Converte dia do mês em semana_mes usando calendário TW."""
    for sem, ds, de in get_month_tw_ranges(year, month):
        if ds <= day <= de:
            return sem
    return None


def vectorize_semana_tw(
    years: pd.Series,
    months: pd.Series,
    days: pd.Series,
) -> pd.Series:
    """
    Versão vetorizada de day_to_semana_tw via lookup table.

    Substitui df.apply(axis=1) em carrega_dados() — de ~5s para <100ms.

    Parameters
    ----------
    years, months, days : Series com os mesmos índices

    Returns
    -------
    Series com semana_mes alinhada ao índice original
    """
    # Monta DataFrame com as combinações únicas (ano, mes, dia)
    idx_original = years.index
    lookup = (
        pd.DataFrame({"ano": years.values, "mes": months.values, "dia": days.values})
        .drop_duplicates()
    )

    # Calcula semana_mes para cada combinação única
    lookup["semana_mes"] = [
        day_to_semana_tw(int(y), int(m), int(d))
        for y, m, d in lookup.itertuples(index=False)
    ]

    # Faz merge de volta para o DataFrame original
    df_orig = pd.DataFrame(
        {"ano": years.values, "mes": months.values, "dia": days.values},
        index=idx_original,
    )
    result = df_orig.merge(lookup, on=["ano", "mes", "dia"], how="left")["semana_mes"]
    result.index = idx_original
    return result
