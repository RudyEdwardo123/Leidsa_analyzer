"""Punto de entrada principal para LEIDSA ANALYZER."""

import sys
from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.gui.main_window import launch_gui
from app.importers.batch_importer import ensure_historico_structure
from app.importers.yelu_importer import YeluImporter
from app.rules.game_rules import GameType

SAMPLE_YELU_DATA = """Fecha del Sorteo\tJuega\tNúmeros Ganadores\tSorteo
30 de Agosto 2026 - Domingo\tKino TV
1216222325323436374043475356596770727778
29 de Agosto 2026 - Sábado\tKino TV
12467193841434652555964666973747677
28 de Agosto 2026 - Viernes\tKino TV
213182228303336374046475161626466737478
30 de Agosto 2026 - Domingo\tLoto Pool
1224272931
29 de Agosto 2026 - Sábado\tLoto Pool
89182128
28 de Agosto 2026 - Viernes\tLoto Pool
516202729
31 de Agosto 2026 - Lunes\tQuiniela Palé
778919
30 de Agosto 2026 - Domingo\tQuiniela Palé
48962
29 de Agosto 2026 - Sábado\tQuiniela Palé
465272
30 de Agosto 2026 - Domingo\tLoto Más Domingo
151216252774
"""


def run_cli_pipeline():
    """Ejecuta la demostración por consola (CLI)."""
    print("=" * 65)
    print("        LEIDSA ANALYZER - SISTEMA DE ANÁLISIS ESTADÍSTICO")
    print("=" * 65)

    db_path = "data/leidsa.db"
    init_db(db_path)
    ensure_historico_structure("data/historico")
    repository = DrawRepository(db_path=db_path)
    importer = YeluImporter(repository=repository)

    print("\n[1] Estructura 'data/historico' verificada/creada correctamente.")

    print("\n[2] Ingestionando datos históricos de muestra...")
    summary = importer.import_text(SAMPLE_YELU_DATA)
    print(f"    - Total procesados: {summary.total}")
    print(f"    - Válidos e insertados: {summary.saved}")
    print(f"    - Duplicados omitidos: {summary.duplicates}")
    print(f"    - Errores / ignorados: {summary.errors}")

    print("\n[3] Registros en base de datos por juego:")
    for game in GameType:
        draws = repository.get_draws_by_game(game)
        print(f"    - {game.value:<12}: {len(draws)} sorteo(s)")

    print("=" * 65)


# Alias de compatibilidad
run_pipeline = run_cli_pipeline


if __name__ == "__main__":
    ensure_historico_structure("data/historico")
    if "--cli" in sys.argv:
        run_cli_pipeline()
    else:
        launch_gui()