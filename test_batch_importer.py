"""Pruebas unitarias para la importación por lotes desde directorios (batch_importer.py)."""

import pytest
from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.importers.batch_importer import BatchDirectoryImporter, ensure_historico_structure
from app.importers.yelu_importer import YeluImporter
from app.rules.game_rules import GameType


def test_ensure_historico_structure(tmp_path):
    """Verifica que se creen automáticamente las carpetas de todos los juegos."""
    historico_dir = tmp_path / "historico"
    ensure_historico_structure(str(historico_dir))

    assert historico_dir.exists()
    for game in GameType:
        game_folder = historico_dir / game.value
        assert game_folder.exists()
        assert game_folder.is_dir()


@pytest.fixture
def temp_batch_env(tmp_path):
    """Crea una estructura de carpetas simulada con archivos de prueba."""
    db_file = str(tmp_path / "batch_test.db")
    init_db(db_file)
    repo = DrawRepository(db_path=db_file)
    importer = YeluImporter(repository=repo)
    batch_importer = BatchDirectoryImporter(yelu_importer=importer)

    kino_dir = tmp_path / "historico" / "Kino TV" / "2026"
    kino_dir.mkdir(parents=True, exist_ok=True)

    file_content = """30 de Agosto 2026 - Domingo\tKino TV
1216222325323436374043475356596770727778
29 de Agosto 2026 - Sábado\tKino TV
12467193841434652555964666973747677
"""
    (kino_dir / "2026-08.txt").write_text(file_content, encoding="utf-8")

    return batch_importer, tmp_path / "historico", repo


def test_batch_directory_import(temp_batch_env):
    """Verifica el escaneo y procesamiento masivo de carpetas."""
    batch_importer, historico_path, repo = temp_batch_env

    batch_summary = batch_importer.import_directory(str(historico_path))

    assert batch_summary.files_processed == 1
    assert batch_summary.total_draws_found == 2
    assert batch_summary.saved == 2
    assert batch_summary.duplicates == 0

    draws = repo.get_draws_by_game(GameType.KINO_TV)
    assert len(draws) == 2