from app.scrapers.yelu_scraper import YeluWebScraper
from app.database.repository import DrawRepository
from app.importers.yelu_importer import YeluImporter


repo = DrawRepository("data/leidsa.db")
importer = YeluImporter(repo)
scraper = YeluWebScraper(importer)


html = scraper.fetch_month_html(
    game_name="",
    date_month="2026-09",
)


if html:
    with open("yelu_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTML guardado en yelu_debug.html")
    print(f"📏 Tamaño: {len(html)} caracteres")

    texto = scraper.clean_html_to_text(html)

    print("\n========== TEXTO EXTRAÍDO ==========")
    print(texto)

else:
    print("❌ No se recibió HTML")