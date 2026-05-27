"""Testes unitários para utils/calendar_tw.py."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
import pandas as pd
import pytest

from utils.calendar_tw import get_month_tw_ranges, day_to_semana_tw, vectorize_semana_tw


class TestGetMonthTwRanges:
    def test_janeiro_2026_tem_5_semanas(self):
        ranges = get_month_tw_ranges(2026, 1)
        assert len(ranges) == 5

    def test_semanas_cobrem_todo_o_mes(self):
        for month in range(1, 13):
            ranges = get_month_tw_ranges(2026, month)
            dias_cobertos = sum(e - s + 1 for _, s, e in ranges)
            import calendar
            dias_no_mes = calendar.monthrange(2026, month)[1]
            assert dias_cobertos == dias_no_mes, f"Mês {month}: {dias_cobertos} != {dias_no_mes}"

    def test_semanas_sequenciais(self):
        ranges = get_month_tw_ranges(2026, 3)
        nums = [r[0] for r in ranges]
        assert nums == list(range(1, len(nums) + 1))

    def test_sem_sobreposicao(self):
        ranges = get_month_tw_ranges(2026, 5)
        for i in range(len(ranges) - 1):
            assert ranges[i][2] < ranges[i + 1][1], "Semanas se sobrepõem"


class TestDayToSemanaTw:
    def test_primeiro_dia_e_semana_1(self):
        assert day_to_semana_tw(2026, 1, 1) == 1

    def test_ultimo_dia_e_ultima_semana(self):
        ranges = get_month_tw_ranges(2026, 1)
        ultima_sem = ranges[-1][0]
        ultimo_dia = ranges[-1][2]
        assert day_to_semana_tw(2026, 1, ultimo_dia) == ultima_sem

    def test_dia_invalido_retorna_none(self):
        # Dia 0 não existe
        assert day_to_semana_tw(2026, 1, 0) is None


class TestVectorizeSemana:
    def _make_series(self, dates: list[date]):
        df = pd.DataFrame({"data": pd.to_datetime(dates)})
        return df["data"].dt.year, df["data"].dt.month, df["data"].dt.day

    def test_resultado_igual_ao_escalar(self):
        """vectorize_semana_tw deve dar o mesmo resultado que day_to_semana_tw."""
        test_dates = [
            date(2026, 1, 1),
            date(2026, 1, 7),
            date(2026, 1, 8),
            date(2026, 3, 15),
            date(2026, 5, 31),
        ]
        years, months, days = self._make_series(test_dates)
        result = vectorize_semana_tw(years, months, days)

        for i, d in enumerate(test_dates):
            esperado = day_to_semana_tw(d.year, d.month, d.day)
            assert result.iloc[i] == esperado, f"Divergência em {d}: {result.iloc[i]} != {esperado}"

    def test_preserva_indice_original(self):
        test_dates = [date(2026, 2, 10), date(2026, 2, 20)]
        years, months, days = self._make_series(test_dates)
        result = vectorize_semana_tw(years, months, days)
        assert list(result.index) == list(years.index)

    def test_performance_vs_apply(self):
        """vectorize_semana_tw deve ser pelo menos 5x mais rápido que apply."""
        import time
        import numpy as np

        # Gera 50k datas de 2026
        n = 50_000
        rng = pd.date_range("2026-01-01", periods=n, freq="h")
        df = pd.DataFrame({"data": rng})
        years  = df["data"].dt.year
        months = df["data"].dt.month
        days   = df["data"].dt.day

        # Tempo do apply
        t0 = time.time()
        _ = df.apply(lambda r: day_to_semana_tw(int(r["data"].year),
                                                 int(r["data"].month),
                                                 int(r["data"].day)), axis=1)
        t_apply = time.time() - t0

        # Tempo do vectorize
        t1 = time.time()
        _ = vectorize_semana_tw(years, months, days)
        t_vec = time.time() - t1

        assert t_vec < t_apply / 5, (
            f"vectorize ({t_vec:.2f}s) não foi 5x mais rápido que apply ({t_apply:.2f}s)"
        )
