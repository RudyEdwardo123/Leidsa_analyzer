"""Procesador por lotes para importar estructuras de carpetas históricas de texto."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from app.importers.yelu_importer import ImportSummary, YeluImporter
from app.rules.game_rules import GameType
from app.utils.logger import logger


def ensure_historico_structure(base_path: str = "data/historico") -> None:
    """Crea la estructura base de carpetas para cada juego soportado en data/historico."""
    root = Path(base_path)
    root.mkdir(parents=True, exist_ok=True)
    for game in GameType:
        game_folder = root / game.value
        game_folder.mkdir(parents=True, exist_ok=True)


@dataclass
class BatchImportSummary:
    """Resumen consolidado del procesamiento de múltiples archivos."""

    files_processed: int = 0
    total_draws_found: int = 0
    saved: int = 0
    duplicates: int = 0
    errors: int = 0
    file_summaries: List[tuple] = field(default_factory=list)


class BatchDirectoryImporter:
    """Escanea y procesa recursivamente archivos .txt dentro de una estructura de directorios."""

    def __init__(self, yelu_importer: YeluImporter):
        self.importer = yelu_importer

    def import_directory(self, root_path: str = "data/historico") -> BatchImportSummary:
        """Recorre recursivamente root_path buscando archivos .txt e importa su contenido."""
        base_dir = Path(root_path)
        batch_summary = BatchImportSummary()

        if not base_dir.exists() or not base_dir.is_dir():
            logger.warning(f"La ruta del directorio especificada no existe: {root_path}")
            return batch_summary

        txt_files = sorted(list(base_dir.rglob("*.txt")))
        logger.info(f"Iniciando importación por lotes en '{root_path}'. Archivos .txt encontrados: {len(txt_files)}")

        for file_path in txt_files:
            rel_path = str(file_path.relative_to(base_dir.parent))
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="latin-1")

            if not content.strip():
                logger.warning(f"Archivo omitido por estar vacío: {rel_path}")
                continue

            summary: ImportSummary = self.importer.import_text(content, file_context=rel_path)

            batch_summary.files_processed += 1
            batch_summary.total_draws_found += summary.total
            batch_summary.saved += summary.saved
            batch_summary.duplicates += summary.duplicates
            batch_summary.errors += summary.errors

            batch_summary.file_summaries.append((rel_path, summary))

        logger.info(
            f"Fin de proceso por lotes -> Procesados: {batch_summary.files_processed} archivos | "
            f"Guardados: {batch_summary.saved} | Omitidos (duplicados): {batch_summary.duplicates} | Errores: {batch_summary.errors}"
        )

        return batch_summary