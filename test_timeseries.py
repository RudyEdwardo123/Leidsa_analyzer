"""Pruebas unitarias para el módulo de series temporales (timeseries.py)."""

from datetime import date
import pandas as pd
from app.forecasting.timeseries import (
    analyze_time_series,
    build_binary_time_series,
    compute_rolling_frequency,
)
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType


def test_build_binary_time_series():
    """Verifica la construcción de una serie temporal binaria ordenada por fecha."""
    draws = [
        DrawData(
            game=GameType.LOTO_POOL,
            draw_date=date(2026, 8, 30),
            numbers=[DrawNumber(v, "main") for v in [12, 24, 27, 29, 31]],
        ),
        DrawData(
            game=GameType.LOTO_POOL,
            draw_date=date(2026, 8, 28),
            numbers=[DrawNumber(v, "main") for v in [5, 16, 20, 27, 29]],
        ),
    ]

    series = build_binary_time_series(draws, target_number=12)
    assert len(series) == 2
    # Debe estar ordenado por fecha: 28 de Agosto primero, luego 30 de Agosto
    assert series.iloc[0] == 0  # 28 Ago no tiene el 12
    assert series.iloc[1] == 1  # 30 Ago sí tiene el 12


def test_analyze_time_series_white_noise():
    """Verifica el cálculo de autocorrelación y test de Ljung-Box sobre una serie ficticia."""
    draws = []
    # Generar 50 sorteos ficticios para prueba estadística
    for i in range(1, 51):
        # El número 7 aparece en sorteos alternados
        nums = [7, 10, 15, 20, 25] if i % 2 == 0 else [1, 2, 3, 4, 5]
        draws.append(
            DrawData(
                game=GameType.LOTO_POOL,
                draw_date=date(2026, 1, 1) + pd.Timedelta(days=i),
                numbers=[DrawNumber(v, "main") for v in nums],
            )
        )

    series = build_binary_time_series(draws, target_number=7)
    res = analyze_time_series(series, target_number=7, max_lag=5)

    assert res.total_observations == 50
    assert res.confidence_bound > 0
    assert 1 in res.autocorrelations
    assert isinstance(res.is_white_noise, bool)


def test_compute_rolling_frequency():
    """Verifica el cálculo de promedios móviles."""
    s = pd.Series([1, 0, 1, 0, 1])
    rf = compute_rolling_frequency(s, window=2)
    assert rf.iloc[0] == 1.0
    assert rf.iloc[1] == 0.5  # (1 + 0) / 2
    assert rf.iloc[2] == 0.5  # (0 + 1) / 2