"""Pruebas de integración para el pipeline de importación (YeluImporter)."""

from datetime import date
import pytest
from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.importers.yelu_importer import YeluImporter
from app.rules.game_rules import GameType


@pytest.fixture
def temp_importer(tmp_path):
    """Fixture que inicializa una BD temporal y retorna una instancia de YeluImporter."""
    db_file = str(tmp_path / "test_import.db")
    init_db(db_file)
    repo = DrawRepository(db_path=db_file)
    return YeluImporter(repository=repo)


def test_import_batch_with_duplicates_and_errors(temp_importer):
    """Prueba la ingesta completa con registros válidos, duplicados y errores."""
    raw_text = """Fecha del Sorteo\tJuega\tNúmeros Ganadores\tSorteo
30 de Agosto 2026 - Domingo\tKino TV
1216222325323436374043475356596770727778
29 de Agosto 2026 - Sábado\tKino TV
12467193841434652555964666973747677
30 de Agosto 2026 - Domingo\tKino TV
1216222325323436374043475356596770727778
31 de Agosto 2026 - Lunes\tJuegoDesconocido
123456
"""
    summary = temp_importer.import_text(raw_text)

    assert summary.total == 4
    assert summary.saved == 2
    assert summary.duplicates == 1
    assert summary.errors == 1

    # Verificar persistencia en base de datos
    saved_draws = temp_importer.repository.get_draws_by_game(GameType.KINO_TV)
    assert len(saved_draws) == 2