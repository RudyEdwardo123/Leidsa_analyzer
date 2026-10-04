"""Pipeline de ingesta que orquesta el Parser, Validator y Repository."""

from dataclasses import dataclass, field
from typing import List, Optional

from app.database.repository import DrawRepository
from app.parsers.yelu_parser import ParsedYeluRecord, parse_yelu_text
from app.utils.logger import logger
from app.validation.validator import validate_draw


@dataclass
class ImportResultRecordDetail:
    """Detalle individual del procesamiento de un registro."""

    raw_header: str
    status: str  # 'saved', 'duplicate', 'invalid_rules', 'parser_error', 'save_failed'
    game: Optional[str] = None
    draw_date: Optional[str] = None
    message: Optional[str] = None


@dataclass
class ImportSummary:
    """Resumen consolidado de la operación de importación."""

    total: int = 0
    valid: int = 0
    saved: int = 0
    duplicates: int = 0
    errors: int = 0
    details: List[ImportResultRecordDetail] = field(default_factory=list)


class YeluImporter:
    """Orquestador de importación para registros de Yelu hacia SQLite."""

    def __init__(self, repository: DrawRepository):
        self.repository = repository

    def import_text(self, raw_text: str, file_context: str = "Texto Directo") -> ImportSummary:
        """Procesa texto copiado de Yelu, valida reglas y persiste mediante el repository."""
        parsed_records: List[ParsedYeluRecord] = parse_yelu_text(raw_text)
        summary = ImportSummary(total=len(parsed_records))

        for record in parsed_records:
            if record.status != "success" or not record.draw_data:
                summary.errors += 1
                err_msg = record.error_message or f"Estado de parser: {record.status}"
                logger.error(
                    f"[{file_context}] Error de Parsing -> Header: '{record.raw_header}' | Motivo: {err_msg}"
                )
                summary.details.append(
                    ImportResultRecordDetail(
                        raw_header=record.raw_header,
                        status="parser_error",
                        game=record.game_type.value if record.game_type else None,
                        draw_date=record.draw_date.isoformat() if record.draw_date else None,
                        message=err_msg,
                    )
                )
                continue

            draw = record.draw_data

            # 1. Validar reglas de dominio del juego
            validation_res = validate_draw(draw)
            if not validation_res.is_valid:
                summary.errors += 1
                val_err = "; ".join(validation_res.errors)
                logger.warning(
                    f"[{file_context}] Regla Violada -> Juego: {draw.game.value} | Fecha: {draw.draw_date} | Motivo: {val_err}"
                )
                summary.details.append(
                    ImportResultRecordDetail(
                        raw_header=record.raw_header,
                        status="invalid_rules",
                        game=draw.game.value,
                        draw_date=draw.draw_date.isoformat(),
                        message=val_err,
                    )
                )
                continue

            summary.valid += 1

            # 2. Verificar duplicados mediante Repository
            if self.repository.exists(draw.game, draw.draw_date):
                summary.duplicates += 1
                logger.info(
                    f"[{file_context}] Omitido Duplicado -> Juego: {draw.game.value} | Fecha: {draw.draw_date}"
                )
                summary.details.append(
                    ImportResultRecordDetail(
                        raw_header=record.raw_header,
                        status="duplicate",
                        game=draw.game.value,
                        draw_date=draw.draw_date.isoformat(),
                        message="El sorteo ya existe en la base de datos.",
                    )
                )
            else:
                saved = self.repository.save_draw(draw)
                if saved:
                    summary.saved += 1
                    logger.info(
                        f"[{file_context}] Guardado OK -> Juego: {draw.game.value} | Fecha: {draw.draw_date}"
                    )
                    summary.details.append(
                        ImportResultRecordDetail(
                            raw_header=record.raw_header,
                            status="saved",
                            game=draw.game.value,
                            draw_date=draw.draw_date.isoformat(),
                            message="Sorteo guardado correctamente.",
                        )
                    )
                else:
                    summary.errors += 1
                    logger.error(
                        f"[{file_context}] Error al Guardar en BD -> Juego: {draw.game.value} | Fecha: {draw.draw_date}"
                    )
                    summary.details.append(
                        ImportResultRecordDetail(
                            raw_header=record.raw_header,
                            status="save_failed",
                            game=draw.game.value,
                            draw_date=draw.draw_date.isoformat(),
                            message="Error al intentar insertar el sorteo en SQLite.",
                        )
                    )

        return summary