"""Pruebas unitarias para el módulo de análisis estadístico (statistics.py)."""

from datetime import date
from app.analysis.statistics import (
    compute_frequencies,
    compute_overdue,
    compute_pairs,
    compute_position_frequencies,
    filter_draws_by_days,
    get_game_statistics,
)
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType


def test_frequencies_and_overdue():
    """Verifica el cálculo de frecuencias y atrasos en un histórico controlado."""
    draw1 = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 28),
        numbers=[DrawNumber(v, "main") for v in [5, 16, 20, 27, 29]],
    )
    draw2 = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 29),
        numbers=[DrawNumber(v, "main") for v in [8, 9, 18, 21, 28]],
    )
    draw3 = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 30),
        numbers=[DrawNumber(v, "main") for v in [12, 24, 27, 29, 31]],
    )

    draws = [draw1, draw2, draw3]

    # Frecuencias
    freqs = compute_frequencies(draws)
    assert freqs[27] == 2
    assert freqs[29] == 2
    assert freqs[12] == 1
    assert freqs.get(1, 0) == 0

    # Atrasos
    overdues = compute_overdue(draws, min_val=0, max_val=31)
    assert overdues[12] == 0  # Salió en el sorteo más reciente (draw3)
    assert overdues[27] == 0  # Salió en draw3
    assert overdues[8] == 1  # Salió en draw2 (1 sorteo atrás)
    assert overdues[5] == 2  # Salió en draw1 (2 sorteos atrás)
    assert overdues[0] is None  # Nunca ha salido


def test_compute_pairs():
    """Verifica el cálculo de coapariciones de pares de números."""
    draw1 = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 28),
        numbers=[DrawNumber(v, "main") for v in [5, 16, 20, 27, 29]],
    )
    draw2 = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 30),
        numbers=[DrawNumber(v, "main") for v in [12, 20, 27, 29, 31]],
    )

    pairs = compute_pairs([draw1, draw2])
    # El par (27, 29) y (20, 27) salieron en ambos sorteos
    assert pairs[(27, 29)] == 2
    assert pairs[(20, 27)] == 2
    assert pairs.get((5, 12), 0) == 0


def test_compute_position_frequencies():
    """Verifica frecuencias posicionales para Quiniela."""
    draw1 = DrawData(
        game=GameType.QUINIELA,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(77, "main", position=1),
            DrawNumber(89, "main", position=2),
            DrawNumber(19, "main", position=3),
        ],
    )
    draw2 = DrawData(
        game=GameType.QUINIELA,
        draw_date=date(2026, 8, 31),
        numbers=[
            DrawNumber(77, "main", position=1),
            DrawNumber(10, "main", position=2),
            DrawNumber(89, "main", position=3),
        ],
    )

    pos_freqs = compute_position_frequencies([draw1, draw2])
    assert pos_freqs[1][77] == 2
    assert pos_freqs[2][89] == 1
    assert pos_freqs[3][89] == 1


def test_get_game_statistics_window():
    """Verifica la generación de reporte consolidado con filtrado por ventana de días."""
    draws = [
        DrawData(
            game=GameType.LOTO_POOL,
            draw_date=date(2026, 8, 10),
            numbers=[DrawNumber(v, "main") for v in [1, 2, 3, 4, 5]],
        ),
        DrawData(
            game=GameType.LOTO_POOL,
            draw_date=date(2026, 8, 30),
            numbers=[DrawNumber(v, "main") for v in [1, 10, 11, 12, 13]],
        ),
    ]

    # Filtrar solo últimos 5 días respecto a la última fecha (30 Ago 2026 -> desde 25 Ago)
    stats_window = get_game_statistics(draws, GameType.LOTO_POOL, days_window=5)

    # Número 1 salió en el sorteo dentro de la ventana de 5 días
    stat_num1 = next(s for s in stats_window if s.number == 1)
    assert stat_num1.absolute_frequency == 1

    # Número 2 salió el 10 Ago (fuera de la ventana de 5 días)
    stat_num2 = next(s for s in stats_window if s.number == 2)
    assert stat_num2.absolute_frequency == 0