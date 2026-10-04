"""Pruebas unitarias para el módulo de segmentación por backtracking (segmenter.py)."""

import pytest
from app.models.draw import DrawNumber
from app.parsers.segmenter import segment_numbers
from app.rules.game_rules import GameType


def test_segment_kino_tv_exact_cases():
    """Prueba casos reales de Kino TV donde la segmentación debe ser unívoca (1 resultado)."""
    # Caso 1: 20 números
    text1 = "1216222325323436374043475356596770727778"
    results1 = segment_numbers(text1, GameType.KINO_TV)
    assert len(results1) == 1
    expected1 = [
        12, 16, 22, 23, 25, 32, 34, 36, 37, 40,
        43, 47, 53, 56, 59, 67, 70, 72, 77, 78
    ]
    assert [n.value for n in results1[0]] == expected1
    assert all(n.role == "main" for n in results1[0])

    # Caso 2: 20 números con mezcla de 1 y 2 dígitos
    text2 = "12467193841434652555964666973747677"
    results2 = segment_numbers(text2, GameType.KINO_TV)
    assert len(results2) == 1
    expected2 = [
        1, 2, 4, 6, 7, 19, 38, 41, 43, 46,
        52, 55, 59, 64, 66, 69, 73, 74, 76, 77
    ]
    assert [n.value for n in results2[0]] == expected2


def test_segment_loto_pool_exact_cases():
    """Prueba casos de Loto Pool (5 números, rango 00-31)."""
    # Caso 1: Todos de 2 dígitos
    text1 = "1224272931"
    results1 = segment_numbers(text1, GameType.LOTO_POOL)
    assert len(results1) == 1
    assert [n.value for n in results1[0]] == [12, 24, 27, 29, 31]

    # Caso 2: Mezcla de 1 y 2 dígitos
    text2 = "89182128"
    results2 = segment_numbers(text2, GameType.LOTO_POOL)
    assert len(results2) == 1
    assert [n.value for n in results2[0]] == [8, 9, 18, 21, 28]


def test_segment_quiniela_exact_cases():
    """Prueba casos de Quiniela (3 números con posicionalidad y duplicados permitidos)."""
    # Caso 1: Tres números estándar
    text1 = "778919"
    results1 = segment_numbers(text1, GameType.QUINIELA)
    assert len(results1) == 1
    assert [n.value for n in results1[0]] == [77, 89, 19]
    assert [n.position for n in results1[0]] == [1, 2, 3]

    # Caso 2: Números duplicados permitidos entre posiciones
    text2 = "777719"
    results2 = segment_numbers(text2, GameType.QUINIELA)
    assert len(results2) == 1
    assert [n.value for n in results2[0]] == [77, 77, 19]
    assert [n.position for n in results2[0]] == [1, 2, 3]


def test_segment_loto_variants():
    """Prueba la detección de variantes de Loto (main + plus + super_plus)."""
    # Caso 1: Loto + Más + Súper Más (main: 6, plus: 1, super_plus: 1)
    text1 = "151216252774"
    results1 = segment_numbers(text1, GameType.LOTO)
    # Debe encontrar la interpretación: 1, 5, 12, 16, 25, 27 (main), 7 (plus), 4 (super_plus)
    assert len(results1) >= 1
    match = next(
        res for res in results1
        if len(res) == 8 and [n.value for n in res] == [1, 5, 12, 16, 25, 27, 7, 4]
    )
    assert [n.role for n in match] == [
        "main", "main", "main", "main", "main", "main", "plus", "super_plus"
    ]

    # Caso 2: Loto + Más (main: 6, plus: 1)
    text2 = "15121625277"
    results2 = segment_numbers(text2, GameType.LOTO)
    assert len(results2) >= 1
    match2 = next(
        res for res in results2
        if len(res) == 7 and [n.value for n in res] == [1, 5, 12, 16, 25, 27, 7]
    )
    assert [n.role for n in match2] == [
        "main", "main", "main", "main", "main", "main", "plus"
    ]

    # Caso 3: Loto tradicional (solo main: 6)
    text3 = "1516252730"
    results3 = segment_numbers(text3, GameType.LOTO)
    assert len(results3) >= 1
    match3 = next(
        res for res in results3
        if len(res) == 6 and [n.value for n in res] == [1, 5, 16, 25, 27, 30]
    )
    assert [n.role for n in match3] == ["main"] * 6


def test_segment_invalid_input():
    """Verifica que cadenas no numéricas o inválidas retornen lista vacía."""
    assert segment_numbers("ABC123", GameType.KINO_TV) == []
    assert segment_numbers("", GameType.LOTO) == []