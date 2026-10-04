"""Pruebas unitarias para el motor de validación (validator.py)."""

from datetime import date
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType
from app.validation.validator import validate_draw


def test_validate_loto_valid():
    """Sorteo de Loto completo válido (6 main + 1 plus + 1 super_plus)."""
    draw = DrawData(
        game=GameType.LOTO,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(1, "main"),
            DrawNumber(5, "main"),
            DrawNumber(12, "main"),
            DrawNumber(16, "main"),
            DrawNumber(25, "main"),
            DrawNumber(27, "main"),
            DrawNumber(7, "plus"),
            DrawNumber(4, "super_plus"),
        ],
    )
    res = validate_draw(draw)
    assert res.is_valid
    assert len(res.errors) == 0


def test_validate_loto_out_of_range():
    """Sorteo de Loto con número principal 41 (fuera de rango 1-40)."""
    draw = DrawData(
        game=GameType.LOTO,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(1, "main"),
            DrawNumber(5, "main"),
            DrawNumber(12, "main"),
            DrawNumber(16, "main"),
            DrawNumber(25, "main"),
            DrawNumber(41, "main"),  # Inválido (> 40)
        ],
    )
    res = validate_draw(draw)
    assert not res.is_valid
    assert any("fuera del rango" in err for err in res.errors)


def test_validate_loto_insufficient_main_numbers():
    """Sorteo de Loto con solo 5 números principales (debe requerir 6)."""
    draw = DrawData(
        game=GameType.LOTO,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(1, "main"),
            DrawNumber(5, "main"),
            DrawNumber(12, "main"),
            DrawNumber(16, "main"),
            DrawNumber(25, "main"),
        ],
    )
    res = validate_draw(draw)
    assert not res.is_valid
    assert any("se esperaban 6 números" in err for err in res.errors)


def test_validate_loto_duplicate_numbers():
    """Sorteo de Loto con número duplicado en el grupo principal."""
    draw = DrawData(
        game=GameType.LOTO,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(5, "main"),
            DrawNumber(5, "main"),  # Duplicado
            DrawNumber(12, "main"),
            DrawNumber(16, "main"),
            DrawNumber(25, "main"),
            DrawNumber(27, "main"),
        ],
    )
    res = validate_draw(draw)
    assert not res.is_valid
    assert any("duplicados no permitidos" in err for err in res.errors)


def test_validate_loto_plus_out_of_range():
    """Sorteo de Loto con grupo 'plus' = 13 (máximo permitido es 12)."""
    draw = DrawData(
        game=GameType.LOTO,
        draw_date=date(2026, 8, 30),
        numbers=[
            DrawNumber(1, "main"),
            DrawNumber(5, "main"),
            DrawNumber(12, "main"),
            DrawNumber(16, "main"),
            DrawNumber(25, "main"),
            DrawNumber(27, "main"),
            DrawNumber(13, "plus"),  # Inválido (> 12)
        ],
    )
    res = validate_draw(draw)
    assert not res.is_valid
    assert any("fuera del rango 1-12" in err for err in res.errors)


def test_validate_kino_duplicate():
    """Kino TV con un número repetido."""
    numbers = [DrawNumber(i, "main") for i in range(1, 20)] + [DrawNumber(1, "main")]
    draw = DrawData(
        game=GameType.KINO_TV,
        draw_date=date(2026, 8, 30),
        numbers=numbers,
    )
    res = validate_draw(draw)
    assert not res.is_valid
    assert any("duplicados no permitidos" in err for err in res.errors)


def test_validate_quiniela_with_duplicates():
    """Quiniela permite números iguales en diferentes posiciones."""
    draw = DrawData(
        game=GameType.QUINIELA,
        draw_date=date(2026, 8, 31),
        numbers=[
            DrawNumber(77, "main", position=1),
            DrawNumber(77, "main", position=2),
            DrawNumber(19, "main", position=3),
        ],
    )
    res = validate_draw(draw)
    assert res.is_valid