"""Parser especializado para registros en formato de texto de Yelu con soporte para variaciones de formato."""

from dataclasses import dataclass
from datetime import date
import re
from typing import List, Optional

from app.models.draw import DrawData, DrawNumber
from app.parsers.segmenter import segment_numbers
from app.rules.game_rules import GAME_RULES, GameType
from app.validation.validator import validate_draw


SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass
class ParsedYeluRecord:
    """Resultado del parsing de un bloque individual de Yelu."""

    raw_header: str
    game_type: Optional[GameType] = None
    draw_date: Optional[date] = None
    draw_data: Optional[DrawData] = None
    status: str = "pending"
    error_message: Optional[str] = None


def parse_spanish_date(date_str: str) -> Optional[date]:
    """Convierte cadenas de fecha a un objeto date."""

    if not date_str or not isinstance(date_str, str):
        return None

    s = date_str.strip()

    # 1. Formato ISO: YYYY-MM-DD
    m_iso = re.search(
        r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        s,
    )

    if m_iso:
        y, m, d = m_iso.groups()

        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            pass

    # 2. Formato Slash: DD/MM/YYYY
    m_slash = re.search(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
        s,
    )

    if m_slash:
        d, m, y = m_slash.groups()

        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            pass

    # 3. Formato Texto:
    # 30 de Agosto 2026
    # 30 de Agosto 2026 - Domingo
    m_text = re.search(
        r"(\d{1,2})\s+de\s+"
        r"([a-zA-ZáéíóúÁÉÍÓÚ]+)\s+"
        r"(\d{4})",
        s,
        re.IGNORECASE,
    )

    if m_text:
        d, month_str, y = m_text.groups()
        month = SPANISH_MONTHS.get(month_str.lower())

        if month:
            try:
                return date(int(y), month, int(d))
            except ValueError:
                pass

    return None


def match_game_type(text: str) -> Optional[GameType]:
    """Identifica el GameType a partir del texto del encabezado."""

    text_upper = text.upper()

    if "KINO" in text_upper:
        return GameType.KINO_TV

    if "POOL" in text_upper:
        return GameType.LOTO_POOL

    if (
        "QUINIELA" in text_upper
        or "PALÉ" in text_upper
        or "PALE" in text_upper
    ):
        return GameType.QUINIELA

    if "PEGA 3" in text_upper:
        return GameType.PEGA_3_MAS

    if "LOTO" in text_upper:
        return GameType.LOTO

    return None


def _parse_loto_structured_numbers(
    numbers_text: str,
) -> Optional[List[DrawNumber]]:
    """
    Interpreta el formato estructurado de Loto proveniente de Yelu.

    Ejemplo:

        11-26-27-31-33-39+7-3

    Representa:

        main       = 11, 26, 27, 31, 33, 39
        plus       = 7
        super_plus = 3

    Retorna None si el texto no tiene el formato esperado.
    """

    if not numbers_text:
        return None

    match = re.fullmatch(
        r"(\d{1,2}(?:-\d{1,2}){5})"
        r"(?:\+(\d{1,2}))?"
        r"(?:-(\d{1,2}))?",
        numbers_text.strip(),
    )

    if not match:
        return None

    main_text, plus_text, super_plus_text = match.groups()

    main_values = [
        int(value)
        for value in main_text.split("-")
    ]

    # Validación estructural básica.
    if len(main_values) != 6:
        return None

    numbers: List[DrawNumber] = []

    for value in main_values:
        numbers.append(
            DrawNumber(
                value=value,
                role="main",
                position=None,
            )
        )

    if plus_text is not None:
        numbers.append(
            DrawNumber(
                value=int(plus_text),
                role="plus",
                position=None,
            )
        )

    if super_plus_text is not None:
        numbers.append(
            DrawNumber(
                value=int(super_plus_text),
                role="super_plus",
                position=None,
            )
        )

    return numbers

def _parse_kino_compact_numbers(numbers_text: str) -> Optional[List[int]]:
    """
    Interpreta Kino TV cuando Yelu entrega los 20 números concatenados.

    Ejemplo:
        23142022252836384149515455586164767783

    Se interpreta como:
        02, 03, 14, 20, 22, 25, 28, 36, 38, 41,
        49, 51, 54, 55, 58, 61, 64, 76, 77, 83

    Reglas:
        - Exactamente 20 números.
        - Rango 1-84.
        - Sin duplicados.
        - Los números deben estar en orden ascendente.
        - Cada número puede tener 1 o 2 dígitos.
        - Los números de un solo dígito aparecen concatenados sin cero inicial.
    """

    if not numbers_text:
        return None

    digits = re.sub(r"\D", "", numbers_text)

    if not digits:
        return None

    results: List[int] = []

    def backtrack(
        position: int,
        previous_value: int,
        current: List[int],
    ) -> Optional[List[int]]:
        # Ya encontramos exactamente 20 números.
        if len(current) == 20:
            if position == len(digits):
                return current.copy()
            return None

        # Si quedan demasiados o muy pocos dígitos para completar
        # los 20 números, podemos descartar esta rama.
        remaining_digits = len(digits) - position
        remaining_numbers = 20 - len(current)

        if remaining_digits < remaining_numbers:
            return None

        if remaining_digits > remaining_numbers * 2:
            return None

        # Intentar número de 1 dígito.
        if position < len(digits):
            value = int(digits[position])

            if (
                1 <= value <= 9
                and value > previous_value
                and value not in current
            ):
                current.append(value)

                result = backtrack(
                    position + 1,
                    value,
                    current,
                )

                if result is not None:
                    return result

                current.pop()

        # Intentar número de 2 dígitos.
        if position + 1 < len(digits):
            value = int(digits[position:position + 2])

            if (
                10 <= value <= 84
                and value > previous_value
                and value not in current
            ):
                current.append(value)

                result = backtrack(
                    position + 2,
                    value,
                    current,
                )

                if result is not None:
                    return result

                current.pop()

        return None

    parsed = backtrack(
        position=0,
        previous_value=0,
        current=[],
    )

    return parsed


def _parse_numbers(
    number_lines: List[str],
    game_type: GameType,
) -> List[DrawNumber]:

    # ---------------------------------------------------------
    # LOTO
    # ---------------------------------------------------------
    if game_type == GameType.LOTO:
        for line in number_lines:
            structured_numbers = _parse_loto_structured_numbers(line)

            if structured_numbers is not None:
                return structured_numbers

    # ---------------------------------------------------------
    # KINO TV
    # ---------------------------------------------------------
    if game_type == GameType.KINO_TV:

        kino_values: List[int] = []

        for line in number_lines:
            line = line.strip()

            if not line:
                continue

            # -------------------------------------------------
            # FORMATO 1:
            # Números separados por guiones.
            #
            # Ejemplo:
            # 34-11-67-76-31-10-64-19-22-45-...
            # -------------------------------------------------
            if "-" in line:
                parts = line.split("-")

                for part in parts:
                    part = part.strip()

                    if not part:
                        continue

                    if not part.isdigit():
                        continue

                    value = int(part)

                    if 1 <= value <= 84:
                        kino_values.append(value)

                continue

            # -------------------------------------------------
            # FORMATO 2:
            # Números separados por espacios.
            #
            # Ejemplo:
            # 02 03 14 20 22 25 28 36 ...
            # -------------------------------------------------
            if len(line.split()) > 1:
                parts = line.split()

                valid_parts = []

                for part in parts:
                    if part.isdigit():
                        value = int(part)

                        if 1 <= value <= 84:
                            valid_parts.append(value)

                if valid_parts:
                    kino_values.extend(valid_parts)

                continue

            # -------------------------------------------------
            # FORMATO 3:
            # Un número por línea.
            #
            # Ejemplo:
            # 02
            # 03
            # 14
            # 20
            # ...
            # 83
            # -------------------------------------------------
            if line.isdigit():
                value = int(line)

                if 1 <= value <= 84:
                    kino_values.append(value)

                continue

            # -------------------------------------------------
            # FORMATO 4:
            # Números concatenados.
            #
            # Ejemplo:
            # 23142022252836384149515455586164767783
            #
            # Se segmenta respetando:
            # - exactamente 20 números
            # - rango 1-84
            # - orden ascendente
            # - sin duplicados
            # -------------------------------------------------
            compact_values = _parse_kino_compact_numbers(line)

            if compact_values is not None:
                kino_values.extend(compact_values)

        # -----------------------------------------------------
        # VALIDACIÓN FINAL
        # -----------------------------------------------------

        if len(kino_values) != 20:
            raise ValueError(
                "Kino TV debe tener exactamente 20 números válidos. "
                f"Se encontraron {len(kino_values)}."
            )

        if len(set(kino_values)) != 20:
            raise ValueError(
                "Kino TV no puede contener números repetidos."
            )

        if not all(1 <= value <= 84 for value in kino_values):
            raise ValueError(
                "Kino TV contiene números fuera del rango permitido 1-84."
            )

        kino_values.sort()

        return [
            DrawNumber(
                value=value,
                role="main",
                position=index,
            )
            for index, value in enumerate(kino_values, start=1)
        ]

    # ---------------------------------------------------------
    # RESTO DE JUEGOS
    # ---------------------------------------------------------

    compact_str = ""

    for nl in number_lines:

        cd = re.sub(r"\D", "", nl)

        if len(cd) >= 5:
            compact_str = cd
            break

    if compact_str:
        raw_digits = compact_str

    else:
        valid_parts = []

        for nl in number_lines:

            cd = re.sub(r"\D", "", nl)

            if 1 <= len(cd) <= 2:
                valid_parts.append(cd.zfill(2))

        raw_digits = "".join(valid_parts)

    if not raw_digits:
        raise ValueError(
            "No se encontraron números válidos para el sorteo."
        )

    segmented_interpretations = segment_numbers(
        raw_digits,
        game_type=game_type,
    )

    if not segmented_interpretations:
        raise ValueError(
            f"No fue posible segmentar los números '{raw_digits}'."
        )

    return segmented_interpretations[0]


def parse_yelu_text(
    raw_text: str,
) -> List[ParsedYeluRecord]:
    """Parsea texto multilínea adaptándose a las variaciones del formato Yelu."""

    records: List[ParsedYeluRecord] = []

    if not raw_text or not raw_text.strip():
        return records

    cleaned_text = raw_text.replace("\t", " ").replace("|", "")

    lines = [
        line.strip()
        for line in cleaned_text.splitlines()
        if line.strip()
    ]

    current_record: Optional[ParsedYeluRecord] = None
    number_lines: List[str] = []

    def finalize_current():
        nonlocal current_record, number_lines

        if not current_record:
            return

        if current_record.status == "parser_error":
            records.append(current_record)
            current_record = None
            number_lines = []
            return

        if (
            not current_record.game_type
            or current_record.game_type not in GAME_RULES
        ):
            current_record.status = "parser_error"

            current_record.error_message = (
                "Juego no reconocido en encabezado: "
                f"'{current_record.raw_header}'"
            )

            records.append(current_record)

            current_record = None
            number_lines = []

            return

        try:
            numbers = _parse_numbers(
                number_lines,
                current_record.game_type,
            )

            current_record.draw_data = DrawData(
                game=current_record.game_type,
                draw_date=current_record.draw_date,
                numbers=numbers,
                source="YeluHistoric",
            )

            current_record.status = "success"

        except Exception as e:

            current_record.status = "parser_error"
            current_record.error_message = str(e)

        records.append(current_record)

        current_record = None
        number_lines = []

    for line in lines:

        # -----------------------------------------------------
        # Cabeceras estáticas de la tabla.
        # -----------------------------------------------------
        if (
            "Fecha" in line
            or "Juega" in line
            or "Ganadores" in line
        ) and not parse_spanish_date(line):
            continue

        # -----------------------------------------------------
        # Detectar encabezado de un nuevo sorteo.
        # -----------------------------------------------------
        parsed_date = parse_spanish_date(line)

        if parsed_date:

            finalize_current()

            detected_game = match_game_type(line)

            if not detected_game:

                current_record = ParsedYeluRecord(
                    raw_header=line,
                    game_type=None,
                    draw_date=parsed_date,
                    status="parser_error",
                    error_message=(
                        "Juego no reconocido en encabezado: "
                        f"'{line}'"
                    ),
                )

                continue

            current_record = ParsedYeluRecord(
                raw_header=line,
                game_type=detected_game,
                draw_date=parsed_date,
                status="pending",
            )

            # Formato:
            # ejemplo: "Kino TV4"
            trailing_match = re.search(
                r"TV\s*(\d{1,2})$",
                line,
                re.IGNORECASE,
            )

            if trailing_match:
                number_lines.append(
                    trailing_match.group(1)
                )

            continue

        # -----------------------------------------------------
        # Números pertenecientes al registro actual.
        # -----------------------------------------------------
        if (
            current_record
            and current_record.status == "pending"
        ):

            if not line:
                continue

            number_lines.append(line)

    finalize_current()

    return records