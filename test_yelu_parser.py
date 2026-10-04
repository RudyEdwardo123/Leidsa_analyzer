"""Pruebas unitarias para el parser de datos copiados desde Yelu (yelu_parser.py)."""

from datetime import date
from app.parsers.yelu_parser import parse_spanish_date, parse_yelu_text
from app.rules.game_rules import GameType


def test_parse_spanish_date():
    """Prueba el parseo de varios formatos de fechas en español."""
    assert parse_spanish_date("30 de Agosto 2026 - Domingo") == date(2026, 8, 30)
    assert parse_spanish_date("29 de Agosto 2026 - Sábado") == date(2026, 8, 29)
    assert parse_spanish_date("1 de Enero 2025") == date(2025, 1, 1)
    assert parse_spanish_date("30/08/2026") == date(2026, 8, 30)
    assert parse_spanish_date("2026-08-30") == date(2026, 8, 30)
    assert parse_spanish_date("fecha invalida") is None


def test_parse_yelu_tab_separated_kino():
    """Prueba la ingesta del formato TAB con registros reales de Kino TV."""
    raw_text = """Fecha del Sorteo\tJuega\tNúmeros Ganadores\tSorteo
30 de Agosto 2026 - Domingo\tKino TV
1216222325323436374043475356596770727778
29 de Agosto 2026 - Sábado\tKino TV
12467193841434652555964666973747677
"""
    records = parse_yelu_text(raw_text)
    assert len(records) == 2

    r1 = records[0]
    assert r1.status == "success"
    assert r1.game_type == GameType.KINO_TV
    assert r1.draw_date == date(2026, 8, 30)
    assert len(r1.draw_data.numbers) == 20
    assert r1.draw_data.main_numbers == [
        12, 16, 22, 23, 25, 32, 34, 36, 37, 40,
        43, 47, 53, 56, 59, 67, 70, 72, 77, 78
    ]

    r2 = records[1]
    assert r2.status == "success"
    assert r2.game_type == GameType.KINO_TV
    assert r2.draw_date == date(2026, 8, 29)
    assert r2.draw_data.main_numbers == [
        1, 2, 4, 6, 7, 19, 38, 41, 43, 46,
        52, 55, 59, 64, 66, 69, 73, 74, 76, 77
    ]


def test_parse_yelu_loto_pool():
    """Prueba la ingesta de Loto Pool copiado de Yelu."""
    raw_text = """30 de Agosto 2026 - Domingo\tLoto Pool
1224272931
"""
    records = parse_yelu_text(raw_text)
    assert len(records) == 1
    rec = records[0]
    assert rec.status == "success"
    assert rec.game_type == GameType.LOTO_POOL
    assert rec.draw_data.main_numbers == [12, 24, 27, 29, 31]


def test_parse_yelu_quiniela():
    """Prueba la ingesta de Quiniela (mapeada desde 'Quiniela Palé')."""
    raw_text = """31 de Agosto 2026 - Lunes\tQuiniela Palé
778919
"""
    records = parse_yelu_text(raw_text)
    assert len(records) == 1
    rec = records[0]
    assert rec.status == "success"
    assert rec.game_type == GameType.QUINIELA
    assert rec.draw_data.main_numbers == [77, 89, 19]