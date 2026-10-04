# Pruebas unitarias para el scraper web (yelu_scraper.py).

from unittest.mock import patch
from pathlib import Path

import pytest

from app.database.connection import init_db
from app.database.repository import DrawRepository
from app.importers.yelu_importer import YeluImporter
from app.rules.game_rules import GameType
from app.scrapers.yelu_scraper import YeluWebScraper


@pytest.fixture
def temp_scraper_env(tmp_path):
    db_file = str(tmp_path / "scraper_test.db")
    init_db(db_file)
    repo = DrawRepository(db_path=db_file)
    importer = YeluImporter(repository=repo)
    scraper = YeluWebScraper(importer=importer)
    return scraper, repo


def test_html_cleaning_from_yelu_table(temp_scraper_env):
    scraper, _ = temp_scraper_env

    mock_html = """
    | **" '** | **31 de Julio 2021 - Sábado** | **' '** | **Kino TV** | **' '** | **0309** | **' "** | **4400** | **" "** |
    | ------- | ----------------------------- | ------- | ----------- | ------- | -------- | ------- | -------- | ------- |
    """

    cleaned_text = scraper.clean_html_to_text(mock_html)

    assert "31 de Julio 2021 - Sábado" in cleaned_text
    assert "Kino TV" in cleaned_text
    assert "0309" in cleaned_text
    assert "4400" in cleaned_text


@patch("app.scrapers.yelu_scraper.YeluWebScraper.fetch_month_html")
def test_sync_latest_draws_with_mock(mock_fetch, temp_scraper_env):
    scraper, repo = temp_scraper_env

    mock_fetch.return_value = """
    | **" "** | **30 de Agosto 2026 - Domingo** | **" "** | **Kino TV** | **" "** | **1216222325323436374043475356596770727778** | **" "** | **4500** | **" "** |
    | ------- | ------------------------------- | ------- | ----------- | ------- | -------------------------------------------- | ------- | -------- | ------- |
    """

    summary = scraper.sync_latest_draws()

    assert summary.total == 1
    assert summary.saved == 1

    draws = repo.get_draws_by_game(GameType.KINO_TV)

    assert len(draws) == 1


def test_clean_real_yelu_all_games(temp_scraper_env):
    scraper, _ = temp_scraper_env

    mock_html = """
    <table>
        <tr>
            <th>Fecha del Sorteo</th>
            <th>Juega</th>
            <th>Números Ganadores</th>
            <th>Sorteo</th>
        </tr>

        <tr>
            <td title="Fecha del Sorteo">29 de Septiembre 2026 - Martes</td>
            <td nowrap title="Quiniela Palé">
                <a href="/leidsa/results/quiniela-pale">Quiniela Palé</a>
            </td>
            <td nowrap title="Números Ganadores">
                <span title="83-33-64">
                    <div>83</div><div>33</div><div>64</div>
                </span>
            </td>
            <td></td>
        </tr>

        <tr>
            <td title="Fecha del Sorteo">29 de Septiembre 2026 - Martes</td>
            <td nowrap title="Super Kino TV">
                <a href="/leidsa/results/super-kino-tv">Kino TV</a>
            </td>
            <td nowrap title="Números Ganadores">
                <span title="2-15-16-17-18-22-24-25-27-41-43-46-56-59-63-64-68-70-75-83">
                </span>
            </td>
            <td></td>
        </tr>

        <tr>
            <td title="Fecha del Sorteo">29 de Septiembre 2026 - Martes</td>
            <td nowrap title="Loto Pool">
                <a href="/leidsa/results/loto-pool">Loto Pool</a>
            </td>
            <td nowrap title="Números Ganadores">
                <span title="6-13-17-28-29"></span>
            </td>
            <td></td>
        </tr>

        <tr>
            <td title="Fecha del Sorteo">29 de Septiembre 2026 - Martes</td>
            <td nowrap title="Pega 3 Más">
                <a href="/leidsa/results/pega-3-mas">Pega 3 Más</a>
            </td>
            <td nowrap title="Números Ganadores">
                <span title="10-36-24"></span>
            </td>
            <td></td>
        </tr>

        <tr>
            <td title="Fecha del Sorteo">27 de Septiembre 2026 - Domingo</td>
            <td nowrap title="Loto Más">
                <a href="/leidsa/results/loto-mas">Loto Más Domingo</a>
            </td>
            <td nowrap title="Números Ganadores">
                <span title="11-26-27-31-33-39+7-3"></span>
            </td>
            <td></td>
        </tr>
    </table>
    """

    cleaned = scraper.clean_html_to_text(mock_html)

    assert "29 de Septiembre 2026 - Martes Quiniela Palé" in cleaned
    assert "83-33-64" in cleaned

    assert "Kino TV" in cleaned
    assert "2-15-16-17-18-22-24-25-27-41-43-46-56-59-63-64-68-70-75-83" in cleaned

    assert "Loto Pool" in cleaned
    assert "6-13-17-28-29" in cleaned

    assert "Pega 3 Más" in cleaned
    assert "10-36-24" in cleaned

    assert "Loto Más Domingo" in cleaned
    assert "11-26-27-31-33-39+7-3" in cleaned

def test_debug_yelu_agosto(temp_scraper_env):
    scraper, _ = temp_scraper_env

    html = scraper.fetch_month_html("", "2026-08")
    raw_text = scraper.clean_html_to_text(html)

    print("\n===== PRIMERAS FECHAS =====")
    lines = raw_text.splitlines()

    for line in lines[:40]:
        print(repr(line))

    print("\n===== TOTAL DE LINEAS =====")
    print(len(lines))

def test_sync_history_agosto(temp_scraper_env):
    state_file = Path("data/yelu_sync_state.json")

    print("\n========== CHECKPOINT ==========")

    if state_file.exists():
        print(state_file.read_text(encoding="utf-8"))
    else:
        print("NO EXISTE CHECKPOINT")

    print("================================")
    scraper, _ = temp_scraper_env

    summary = scraper.sync_all_history(
        start_year=2021,
        start_month=7,
    )

    print("\n===== RESUMEN =====")
    print(summary)

def test_compare_yelu_months(temp_scraper_env):
    scraper, _ = temp_scraper_env

    for month in ["2021-07", "2021-08", "2026-08", "2026-09"]:
        print(f"\n========== {month} ==========")

        html = scraper.fetch_month_html("", month)

        assert html is not None

        raw_text = scraper.clean_html_to_text(html)

        lines = raw_text.splitlines()

        print(f"Caracteres HTML: {len(html)}")
        print(f"Líneas procesadas: {len(lines)}")

        for line in lines[:10]:
            print(repr(line))


def test_inspect_kino_2023_raw_text(temp_scraper_env):
    scraper, _ = temp_scraper_env

    month = "2023-10"

    print(f"\n{'=' * 70}")
    print(f"KINO TV — RAW TEXT — {month}")
    print(f"{'=' * 70}")

    html = scraper.fetch_month_html(
        game_name="",
        date_month=month,
    )

    assert html is not None, f"No se pudo obtener HTML para {month}"

    raw_text = scraper.clean_html_to_text(html)

    lines = raw_text.splitlines()

    kino_found = False
    collecting = False

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Detectar encabezado de Kino
        if "Kino TV" in line:
            kino_found = True
            collecting = True

            print("\n--- KINO ---")
            print(repr(line))
            continue

        # Cuando encontramos otro sorteo, dejamos de imprimir
        # el bloque anterior.
        if collecting and (
            "de " in line
            and any(
                month_name in line.lower()
                for month_name in [
                    "enero", "febrero", "marzo", "abril",
                    "mayo", "junio", "julio", "agosto",
                    "septiembre", "octubre", "noviembre", "diciembre",
                ]
            )
        ):
            collecting = False

        if collecting:
            print(repr(line))

    assert kino_found, f"No se encontró ningún Kino TV en {month}"


def test_parse_kino_yelu():
    from app.parsers.yelu_parser import parse_yelu_text

    raw_text = """
    31 de Octubre 2023 - Martes Kino TV
    34-11-67-76-31-10-64-19-22-45-27-46-32-59-39-26-38-13-21-14
    """

    records = parse_yelu_text(raw_text)

    assert len(records) == 1

    record = records[0]

    print("\n========== KINO PARSER ==========")
    print("Estado:", record.status)
    print("Error:", record.error_message)
    print("Fecha:", record.draw_date)

    assert record.status == "success"
    assert record.draw_data is not None

    numbers = record.draw_data.numbers

    print("Cantidad:", len(numbers))
    print("Números:", [n.value for n in numbers])
    print("Posiciones:", [n.position for n in numbers])

    assert len(numbers) == 20

    values = [n.value for n in numbers]

    assert values == sorted(values)

    assert all(1 <= value <= 80 for value in values)

    assert len(set(values)) == 20