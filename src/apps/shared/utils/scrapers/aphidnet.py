import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.http import JsonResponse
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
from concurrent.futures import ThreadPoolExecutor, as_completed


def scraper_aphidnet(url=None, wait_time=None, sobrenombre="APHIDNET"):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("APHIDNET")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    total_urls_found = 0
    total_urls_scraped = 0
    urls_not_scraped = []
    visited_urls = set()
    urls_to_scrape = []
    max_depth = 3

    def scrape_page(current_url, current_depth):
        nonlocal total_urls_found, total_urls_scraped, all_scraper
        content_text = ""
        portfolio_text = ""

        if current_url in visited_urls or current_depth > max_depth:
            return []

        if not current_url.startswith(url):
            print(f"URL fuera del dominio permitido: {current_url}")
            return []

        visited_urls.add(current_url)
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            content_section = soup.find("section", id="content")
            portfolio_section = soup.find("section", class_="portfolio")

            if content_section:
                content_text = content_section.get_text(strip=True)
            if portfolio_section:
                portfolio_text = portfolio_section.get_text(strip=True)

            if content_text or portfolio_text:
                all_scraper += f"URL: {current_url}\n\n"
                all_scraper += f"\nContenido principal':\n{content_text}\n"
                all_scraper += f"\nContenido secundario':\n{portfolio_text}\n"
                all_scraper += "-" * 80 + "\n\n"
                total_urls_scraped += 1

            links = soup.find_all("a", href=True)
            extracted_links = []
            for link in links:
                href = link["href"]

                full_url = urljoin(current_url, href)

                if href == "#" or not href or href.startswith("#"):
                    continue
                if not full_url.startswith(url):
                    continue
                if (
                    full_url.endswith(".pdf")
                    or full_url.endswith(".jpg")
                    or full_url.endswith(".png")
                    or full_url.endswith(".gif")
                    or "images.bugwood.org" in full_url
                ):
                    continue
                extracted_links.append((full_url, current_depth + 1))
                total_urls_found += len(extracted_links)

            return extracted_links

        except requests.RequestException as e:
            print(f"Error al procesar la URL: {current_url}, error: {str(e)}")
            urls_not_scraped.append(current_url)
            return []

    def scrape_pages_in_parallel(url_list):
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, url, depth): (url, depth)
                for url, depth in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    new_links = future.result()
                    if new_links:
                        urls_to_scrape.extend(new_links)
                except Exception as e:
                    logger.info(f"Error en tarea de scraping: {str(e)}")

    try:
        urls_to_scrape.append((url, 0))
        while urls_to_scrape:
            current_batch = [
                (url, depth)
                for url, depth in set(urls_to_scrape)
                if url not in visited_urls
            ]
            urls_to_scrape.clear()
            scrape_pages_in_parallel(current_batch)

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs encontradas: {total_urls_found}\n"
            f"Total de URLs scrapeadas: {total_urls_scraped}\n"
            f"Total de URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += "URLs no scrapeadas:\n\n"
            all_scraper += "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Error al realizar la solicitud: {str(e)}"}, status=400
        )
