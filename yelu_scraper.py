"""Módulo de scraping web para descargar sorteos de LEIDSA desde Yelu."""

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Optional

from app.importers.yelu_importer import ImportSummary, YeluImporter
from app.utils.logger import logger


YELU_LEIDSA_HISTORY_URL = "https://www.yelu.do/leidsa/results/history"


class YeluWebScraper:
    """Scraper web para descargar e ingresar automáticamente sorteos desde Yelu."""

    def __init__(
        self,
        importer: YeluImporter,
        url: str = YELU_LEIDSA_HISTORY_URL,
    ):
        self.importer = importer
        self.url = url

    def fetch_month_html(
        self,
        game_name: str = "",
        date_month: str = "",
    ) -> Optional[str]:
        """Realiza una petición HTTP POST simulando el formulario de búsqueda de Yelu."""

        form_data = {
            "_method": "POST",
            "data[Lottery][name]": game_name,
            "data[Lottery][date]": date_month,
        }

        encoded_data = urllib.parse.urlencode(form_data).encode("utf-8")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
        }

        req = urllib.request.Request(
            self.url,
            data=encoded_data,
            headers=headers,
            method="POST",
        )

        try:
            logger.info(
                f"[Scraper] POST enviado -> "
                f"game='{game_name}' | date='{date_month}'"
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                html_bytes = response.read()

                try:
                    return html_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    return html_bytes.decode("latin-1")

        except Exception as e:
            logger.error(
                "[Scraper] Error de red al consultar Yelu "
                f"(Mes: {date_month or 'Últimos resultados'}): {e}"
            )
            return None

    def clean_html_to_text(self, html_content: str) -> str:
        """
        Convierte la respuesta de Yelu a texto compatible con yelu_parser.

        Soporta:
        - HTML real de Yelu.
        - Formato tabular Markdown utilizado por los tests.
        """

        if not html_content:
            return ""

        final_lines = []

        # ============================================================
        # 1. HTML REAL DE YELU
        # ============================================================

        rows = re.findall(
            r"<tr\b[^>]*>(.*?)</tr>",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        for row in rows:
            cells = re.findall(
                r"<td\b[^>]*>(.*?)</td>",
                row,
                flags=re.DOTALL | re.IGNORECASE,
            )

            if len(cells) < 3:
                continue

            # --------------------------------------------------------
            # Fecha
            # --------------------------------------------------------

            fecha = re.sub(r"<[^>]+>", " ", cells[0])
            fecha = re.sub(r"\s+", " ", fecha).strip()

            # --------------------------------------------------------
            # Juego
            # --------------------------------------------------------

            game_match = re.search(
                r'title=["\']([^"\']+)["\']',
                cells[1],
                flags=re.IGNORECASE,
            )

            juego = (
                game_match.group(1).strip()
                if game_match
                else ""
            )

            if not juego:
                juego = re.sub(r"<[^>]+>", " ", cells[1])
                juego = re.sub(r"\s+", " ", juego).strip()

            # --------------------------------------------------------
            # Números
            # --------------------------------------------------------

            numbers_match = re.search(
                r'<span\b[^>]*title=["\']([^"\']+)["\']',
                cells[2],
                flags=re.IGNORECASE,
            )

            if numbers_match:
                numeros = numbers_match.group(1).strip()
            else:
                numeros = re.sub(r"<[^>]+>", " ", cells[2])
                numeros = re.sub(r"\s+", " ", numeros).strip()

            # --------------------------------------------------------
            # Filtrar encabezados
            # --------------------------------------------------------

            if not fecha or "Fecha del Sorteo" in fecha:
                continue

            if not juego or juego in ("Juega", "Sorteo"):
                continue

            if not numeros or "Números Ganadores" in numeros:
                continue

            final_lines.append(f"{fecha} {juego}")
            final_lines.append(numeros)

        # Si encontramos filas HTML válidas, devolvemos ese resultado.
        if final_lines:
            return "\n".join(final_lines)

        # ============================================================
        # 2. FORMATO MARKDOWN/TABULAR DE LOS TESTS
        # ============================================================

        for raw_line in html_content.splitlines():
            line = raw_line.strip()

            if not line.startswith("|"):
                continue

            cells = [
                cell.strip()
                for cell in line.split("|")
                if cell.strip()
            ]

            if not cells:
                continue

            # Ignorar separadores Markdown:
            # | ------- | ----------- | ------- |
            if all(
                re.fullmatch(r"-+", cell.replace(" ", ""))
                for cell in cells
            ):
                continue

            # Eliminar ** utilizado para marcar negrita.
            cells = [
                re.sub(r"\*\*", "", cell).strip()
                for cell in cells
            ]

            if len(cells) < 6:
                continue

            # Según el formato del fixture:
            #
            # [1] fecha
            # [3] juego
            # [5:] datos del sorteo

            fecha = cells[1].strip("'\" ")
            juego = cells[3].strip("'\" ")

            if not fecha or not juego:
                continue

            if "Fecha del Sorteo" in fecha:
                continue

            # Las columnas posteriores al juego pueden contener:
            # - los números ganadores
            # - información adicional de la tabla
            #
            # Se conservan como líneas independientes para que el parser
            # pueda decidir qué corresponde al sorteo.

            number_lines = []

            for cell in cells[5:]:
                value = cell.strip("'\" ")

                if not value:
                    continue

                if re.fullmatch(r"[\d+\-]+", value):
                    number_lines.append(value)

            if not number_lines:
                continue

            final_lines.append(f"{fecha} {juego}")

            for number_line in number_lines:
                final_lines.append(number_line)

        return "\n".join(final_lines)

    # ================================================================
    # ESTADO DE SINCRONIZACIÓN
    # ================================================================

    def _load_sync_state(self):
        """Carga el último mes histórico procesado correctamente."""

        state_file = Path("data/yelu_sync_state.json")

        if not state_file.exists():
            return None

        try:
            with state_file.open("r", encoding="utf-8") as file:
                return json.load(file)

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "[Scraper] No se pudo leer el estado de "
                f"sincronización: {e}"
            )
            return None

    def _save_sync_state(self, year: int, month: int):
        """Guarda el último mes histórico completado."""

        state_file = Path("data/yelu_sync_state.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "last_year": year,
            "last_month": month,
        }

        try:
            with state_file.open("w", encoding="utf-8") as file:
                json.dump(
                    state,
                    file,
                    indent=4,
                )

        except OSError as e:
            logger.error(
                "[Scraper] No se pudo guardar el estado de "
                f"sincronización: {e}"
            )

    # ================================================================
    # SINCRONIZACIÓN RECIENTE
    # ================================================================

    def sync_latest_draws(self) -> ImportSummary:
        """Descarga y procesa los resultados recientes disponibles en Yelu."""

        logger.info(
            "[Scraper] Consultando resultados recientes "
            "en Yelu vía POST..."
        )

        html = self.fetch_month_html(
            game_name="",
            date_month="",
        )

        if not html:
            summary = ImportSummary()
            summary.errors = 1
            return summary

        raw_text = self.clean_html_to_text(html)

        if not raw_text.strip():
            logger.warning(
                "[Scraper] El HTML se descargó pero no se "
                "encontraron sorteos válidos."
            )

        summary = self.importer.import_text(
            raw_text,
            file_context="Web Yelu (Resultados recientes)",
        )

        logger.info(
            "[Scraper] Resultado Sincronización -> "
            f"Procesados: {summary.total} | "
            f"Guardados: {summary.saved} | "
            f"Duplicados: {summary.duplicates} | "
            f"Errores: {summary.errors}"
        )

        return summary

    # ================================================================
    # SINCRONIZACIÓN HISTÓRICA
    # ================================================================

    def sync_all_history(
        self,
        start_year: int = 2021,
        start_month: int = 7,
    ) -> ImportSummary:
        """
        Descarga el histórico mes a mes y continúa desde
        el último mes completado.
        """

        current_date = date.today()
        current_year = current_date.year
        current_month = current_date.month

        total_summary = ImportSummary()

        # ------------------------------------------------------------
        # Determinar desde qué mes comenzar
        # ------------------------------------------------------------

        state = self._load_sync_state()

        if state:
            last_year = state["last_year"]
            last_month = state["last_month"]

            if last_month == 12:
                sync_year = last_year + 1
                sync_month = 1
            else:
                sync_year = last_year
                sync_month = last_month + 1

            logger.info(
                "[Scraper] Estado encontrado. "
                f"Último mes completado: "
                f"{last_year}-{last_month:02d}. "
                f"Continuando desde "
                f"{sync_year}-{sync_month:02d}."
            )

        else:
            sync_year = start_year
            sync_month = start_month

            logger.info(
                "[Scraper] No existe estado previo. "
                f"Iniciando desde "
                f"{sync_year}-{sync_month:02d}."
            )

        # ------------------------------------------------------------
        # Si ya estamos al día
        # ------------------------------------------------------------

        if (
            sync_year > current_year
            or (
                sync_year == current_year
                and sync_month > current_month
            )
        ):
            logger.info(
                "[Scraper] El histórico ya está actualizado."
            )
            return total_summary

        # ------------------------------------------------------------
        # Procesar mes por mes
        # ------------------------------------------------------------

        for year in range(sync_year, current_year + 1):

            m_start = (
                sync_month
                if year == sync_year
                else 1
            )

            m_end = (
                current_month
                if year == current_year
                else 12
            )

            for month in range(m_start, m_end + 1):

                date_str = f"{year}-{month:02d}"

                logger.info(
                    f"[Scraper] Sincronizando mes: {date_str}..."
                )

                html = self.fetch_month_html(
                    game_name="",
                    date_month=date_str,
                )

                if not html:
                    total_summary.errors += 1

                    logger.error(
                        f"[Scraper] No se pudo descargar {date_str}. "
                        "El estado NO será actualizado para este mes."
                    )

                    continue

                raw_text = self.clean_html_to_text(html)

                if raw_text.strip():

                    summary = self.importer.import_text(
                        raw_text,
                        file_context=f"Web Yelu ({date_str})",
                    )

                    total_summary.total += summary.total
                    total_summary.valid += summary.valid
                    total_summary.saved += summary.saved
                    total_summary.duplicates += summary.duplicates
                    total_summary.errors += summary.errors

                else:
                    logger.warning(
                        "[Scraper] No se extrajeron sorteos válidos "
                        f"para {date_str}."
                    )

                # ----------------------------------------------------
                # El mes terminó. Guardamos el checkpoint.
                # ----------------------------------------------------

                self._save_sync_state(year, month)

                logger.info(
                    f"[Scraper] Estado actualizado -> {date_str}"
                )

                time.sleep(1.5)

        logger.info(
            "[Scraper] Histórico completado. "
            f"Guardados: {total_summary.saved}, "
            f"Duplicados: {total_summary.duplicates}"
        )

        return total_summary


    # ================================================================
    # RECUPERACIÓN DE DATOS
    # ================================================================

    def sync_month_range(
            self,
            start_year: int,
            start_month: int,
            end_year: int,
            end_month: int,
    ) -> ImportSummary:
        """
        Reprocesa un rango específico de meses sin modificar
        el checkpoint principal del histórico.

        Útil para recuperar datos que anteriormente no pudieron
        ser procesados correctamente.
        """

        total_summary = ImportSummary()

        # ------------------------------------------------------------
        # Validar rango
        # ------------------------------------------------------------

        if not 1 <= start_month <= 12:
            raise ValueError(
                f"Mes inicial inválido: {start_month}"
            )

        if not 1 <= end_month <= 12:
            raise ValueError(
                f"Mes final inválido: {end_month}"
            )

        start_value = start_year * 12 + (start_month - 1)
        end_value = end_year * 12 + (end_month - 1)

        if start_value > end_value:
            raise ValueError(
                "El período inicial no puede ser posterior "
                "al período final."
            )

        # ------------------------------------------------------------
        # Procesar mes por mes
        # ------------------------------------------------------------

        year = start_year
        month = start_month

        while True:
            date_str = f"{year}-{month:02d}"

            logger.info(
                f"[Scraper] Recuperando datos del mes: {date_str}..."
            )

            html = self.fetch_month_html(
                game_name="",
                date_month=date_str,
            )

            if not html:
                total_summary.errors += 1

                logger.error(
                    f"[Scraper] No se pudo descargar {date_str}."
                )

            else:
                raw_text = self.clean_html_to_text(html)

                if raw_text.strip():
                    summary = self.importer.import_text(
                        raw_text,
                        file_context=f"Web Yelu Recuperación ({date_str})",
                    )

                    total_summary.total += summary.total
                    total_summary.valid += summary.valid
                    total_summary.saved += summary.saved
                    total_summary.duplicates += summary.duplicates
                    total_summary.errors += summary.errors

                else:
                    logger.warning(
                        "[Scraper] No se extrajeron datos "
                        f"para {date_str}."
                    )

            # --------------------------------------------------------
            # ¿Terminamos?
            # --------------------------------------------------------

            if year == end_year and month == end_month:
                break

            if month == 12:
                year += 1
                month = 1
            else:
                month += 1

            time.sleep(1.5)

        logger.info(
            "[Scraper] Recuperación completada. "
            f"Procesados: {total_summary.total}, "
            f"Guardados: {total_summary.saved}, "
            f"Duplicados: {total_summary.duplicates}, "
            f"Errores: {total_summary.errors}"
        )

        return total_summary