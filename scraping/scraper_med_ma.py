import argparse
import asyncio
import string
import time
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "https://medicament.ma/listing-des-medicaments"
DEFAULT_OUT = Path("data/raw/all_drugs_med_ma.csv")
CONCURRENCY = 4
NAV_TIMEOUT = 30_000
DETAIL_WAIT = 2_000


# Récupère le numéro de la dernière page pour une lettre donnée
async def get_last_page_number(page, letter: str) -> int:
    url = f"{BASE_URL}/?lettre={letter}"
    await page.goto(url, timeout=NAV_TIMEOUT)
    await page.wait_for_load_state("domcontentloaded")

    links = await page.query_selector_all("ul.pagination li.page-item a.page-link")
    if not links:
        return 1

    last_href = await links[-1].get_attribute("href")
    if not last_href:
        return 1

    parts = [p for p in last_href.split("/") if p.isdigit()]
    return int(parts[-1]) if parts else 1


# Récupère les URLs des fiches médicaments sur une page de listing
async def get_drug_urls_on_page(page, letter: str, page_num: int) -> list[str]:
    if page_num == 1:
        url = f"{BASE_URL}/?lettre={letter}"
    else:
        url = f"{BASE_URL}/page/{page_num}/?lettre={letter}"

    await page.goto(url, timeout=NAV_TIMEOUT)
    await page.wait_for_load_state("domcontentloaded")

    anchors = await page.query_selector_all("ul.listing li.listing-item a")
    urls = []
    for a in anchors:
        href = await a.get_attribute("href")
        if href:
            urls.append(href)
    return urls


# Récupère les détails d'un médicament à partir de sa fiche
async def scrape_drug_detail(context, url: str) -> dict | None:
    page = await context.new_page()
    try:
        await page.goto(url, timeout=NAV_TIMEOUT)
        await page.wait_for_timeout(DETAIL_WAIT)

        name_el = await page.query_selector(".main-title")
        if not name_el:
            return None
        drug_name = (await name_el.inner_text()).strip()

        headers = await page.query_selector_all(".detail-header")
        contents = await page.query_selector_all(".detail-content")

        record = {"drug_name": drug_name}
        for header, content in zip(headers, contents):
            key = (await header.inner_text()).strip()
            value = (await content.inner_text()).strip()
            if key:
                record[key] = value

        return record

    except PlaywrightTimeout:
        print(f"Timeout : {url}")
        return None
    except Exception as exc:
        print(f"Erreur ({url}) : {exc}")
        return None
    finally:
        await page.close()


# Scrape tous les médicaments pour une lettre donnée, en gérant la pagination et en récupérant les détails de chaque fiche
async def scrape_letter(context, letter: str) -> list[dict]:
    print(f"\n{'═' * 52}")
    print(f"  Lettre {letter}")
    print(f"{'═' * 52}")

    nav_page = await context.new_page()

    try:
        max_page = await get_last_page_number(nav_page, letter)
        print(f"  → {max_page} page(s) de listing")

        all_urls: list[str] = []
        for page_num in range(1, max_page + 1):
            urls = await get_drug_urls_on_page(nav_page, letter, page_num)
            all_urls.extend(urls)
            print(f"  ├─ Page {page_num}/{max_page} — {len(urls)} médicaments")

    finally:
        await nav_page.close()

    print(f"  └─ Total URLs : {len(all_urls)} — Scraping des fiches…")

    records: list[dict] = []

    for i in range(0, len(all_urls), CONCURRENCY):
        batch = all_urls[i : i + CONCURRENCY]
        results = await asyncio.gather(
            *[scrape_drug_detail(context, url) for url in batch]
        )
        for r in results:
            if r:
                records.append(r)

    print(f"{len(records)} fiches récupérées pour la lettre {letter}")
    return records


# Enregistre les données dans un CSV
def save_csv(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"\nCSV enregistré : {output_path}  ({len(df)} lignes, {len(df.columns)} colonnes)"
    )


# Point d'entrée principal : gère la navigation, le scraping et l'enregistrement des données
async def main(letters: list[str], output_path: Path) -> None:
    all_records: list[dict] = []
    start = time.time()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )

        for letter in letters:
            records = await scrape_letter(context, letter)
            all_records.extend(records)

        await browser.close()

    elapsed = time.time() - start
    print(f"\nDurée totale : {elapsed:.0f}s")

    save_csv(all_records, output_path)


if __name__ == "__main__":
    all_letters = list(string.ascii_uppercase)

    parser = argparse.ArgumentParser(description="Scraper médicament.ma to CSV")
    parser.add_argument(
        "--letters",
        nargs="+",
        default=all_letters,
        help="Lettres à scraper (ex: A B C). Défaut : A-Z",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Chemin du CSV de sortie. Défaut : {DEFAULT_OUT}",
    )
    args = parser.parse_args()

    letters = [l.upper() for l in args.letters]
    asyncio.run(main(letters, args.output))
