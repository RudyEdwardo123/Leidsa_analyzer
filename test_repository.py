"""Pruebas unitarias para la capa de persistencia (DrawRepository)."""

from datetime import date
import pytest
from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType


@pytest.fixture
def temp_repo(tmp_path):
    """Fixture que crea una base de datos SQLite limpia en un directorio temporal."""
    db_file = str(tmp_path / "test_leidsa.db")
    init_db(db_file)
    return DrawRepository(db_path=db_file)


def test_repository_save_and_get(temp_repo):
    """Verifica guardar y recuperar un sorteo completo de Loto."""
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
        source="YeluTest",
    )

    assert not temp_repo.exists(GameType.LOTO, date(2026, 8, 30))
    saved = temp_repo.save_draw(draw)
    assert saved
    assert temp_repo.exists(GameType.LOTO, date(2026, 8, 30))

    retrieved = temp_repo.get_draw(GameType.LOTO, date(2026, 8, 30))
    assert retrieved is not None
    assert retrieved.game == GameType.LOTO
    assert retrieved.draw_date == date(2026, 8, 30)
    assert retrieved.main_numbers == [1, 5, 12, 16, 25, 27]
    assert retrieved.plus_number == 7
    assert retrieved.super_plus_number == 4


def test_repository_deduplication(temp_repo):
    """Verifica que rechace insertar un sorteo exactamente igual (mismo juego y fecha)."""
    draw = DrawData(
        game=GameType.QUINIELA,
        draw_date=date(2026, 8, 31),
        numbers=[
            DrawNumber(77, "main", position=1),
            DrawNumber(89, "main", position=2),
            DrawNumber(19, "main", position=3),
        ],
    )

    assert temp_repo.save_draw(draw)
    assert not temp_repo.save_draw(draw)

    draws = temp_repo.get_draws_by_game(GameType.QUINIELA)
    assert len(draws) == 1


def test_repository_delete_single_draw(temp_repo):
    """Verifica la eliminación de un sorteo individual por juego y fecha."""
    draw = DrawData(
        game=GameType.QUINIELA,
        draw_date=date(2026, 8, 31),
        numbers=[
            DrawNumber(77, "main", position=1),
            DrawNumber(89, "main", position=2),
            DrawNumber(19, "main", position=3),
        ],
    )
    temp_repo.save_draw(draw)
    assert temp_repo.exists(GameType.QUINIELA, date(2026, 8, 31))

    deleted = temp_repo.delete_draw(GameType.QUINIELA, date(2026, 8, 31))
    assert deleted
    assert not temp_repo.exists(GameType.QUINIELA, date(2026, 8, 31))


def test_repository_clear_all_draws(temp_repo):
    """Verifica el borrado total de la base de datos."""
    draw = DrawData(
        game=GameType.LOTO_POOL,
        draw_date=date(2026, 8, 30),
        numbers=[DrawNumber(v, "main") for v in [12, 24, 27, 29, 31]],
    )
    temp_repo.save_draw(draw)
    assert temp_repo.exists(GameType.LOTO_POOL, date(2026, 8, 30))

    deleted_count = temp_repo.clear_all_draws()
    assert deleted_count == 1
    assert not temp_repo.exists(GameType.LOTO_POOL, date(2026, 8, 30))