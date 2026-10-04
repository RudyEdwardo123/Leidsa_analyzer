"""Pruebas unitarias para el generador de jugadas estadísticas (generator.py)."""

from datetime import date
from app.generation.generator import GenerationStrategy, PlayGenerator
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType
from app.validation.validator import validate_draw


def test_generate_loto_play_structure():
    """Verifica que la jugada generada de Loto contenga Main (6), Plus (1) y Súper Más (1)."""
    generator = PlayGenerator()
    play = generator.generate_play(
        game_type=GameType.LOTO,
        strategy=GenerationStrategy.RANDOM_UNIFORM,
    )

    draw = play.draw_data
    assert len(draw.main_numbers) == 6
    assert draw.plus_number is not None
    assert draw.super_plus_number is not None

    # Validar que cumple con todas las reglas de dominio
    val_res = validate_draw(draw)
    assert val_res.is_valid


def test_generate_quiniela_play_structure():
    """Verifica la generación de jugadas de Quiniela (3 números con posicionalidad)."""
    generator = PlayGenerator()
    play = generator.generate_play(
        game_type=GameType.QUINIELA,
        strategy=GenerationStrategy.RANDOM_UNIFORM,
    )

    draw = play.draw_data
    assert len(draw.numbers) == 3
    assert [n.position for n in draw.numbers] == [1, 2, 3]

    val_res = validate_draw(draw)
    assert val_res.is_valid


def test_generate_kino_tv_play_structure():
    """Verifica la generación de jugadas de Kino TV (20 números únicos ordenados)."""
    generator = PlayGenerator()
    play = generator.generate_play(
        game_type=GameType.KINO_TV,
        strategy=GenerationStrategy.RANDOM_UNIFORM,
    )

    draw = play.draw_data
    assert len(draw.main_numbers) == 20
    assert draw.main_numbers == sorted(draw.main_numbers)

    val_res = validate_draw(draw)
    assert val_res.is_valid


def test_generate_play_with_historical_weighted_strategy():
    """Verifica la generación con estrategias basadas en historial (HOT / COLD)."""
    draws = [
        DrawData(
            game=GameType.LOTO_POOL,
            draw_date=date(2026, 8, 30),
            numbers=[DrawNumber(v, "main") for v in [12, 24, 27, 29, 31]],
        )
    ]

    generator = PlayGenerator()
    play = generator.generate_play(
        game_type=GameType.LOTO_POOL,
        strategy=GenerationStrategy.HOT_NUMBERS,
        historical_draws=draws,
    )

    draw = play.draw_data
    assert len(draw.main_numbers) == 5
    val_res = validate_draw(draw)
    assert val_res.is_valid
    assert play.disclaimer != ""