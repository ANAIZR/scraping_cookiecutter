import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
from rest_framework.response import Response
from rest_framework import status


def scraper_flora_habitas(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    visited_urls = set()
    urls_not_scraped = []
    hrefs = set() 

    def get_page_content(current_url):
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error al obtener la URL {current_url}: {e}")
            urls_not_scraped.append(current_url)
            return None

    def extract_hrefs_from_div(html_content, base_url):
        soup = BeautifulSoup(html_content, "html.parser")
        contents_div = soup.find("div", id="contents")
        if contents_div:
            for link in contents_div.find_all("a", href=True):
                full_url = urljoin(base_url, link["href"])
                if "Family" not in full_url and full_url not in visited_urls:
                    hrefs.add(full_url)
                else:
                    logger.info(f"URL ignorada (duplicada o contiene 'Familia'): {full_url}")
        else:
            logger.info("No se encontró el div#contents en la página principal.")

    def scrape_page(link):
        nonlocal all_scraper
        visited_urls.add(link) 
        html_content = get_page_content(link)
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            contents_div = soup.find("div", id="contents")
            if contents_div:
                all_scraper += f"URL: {link}\n\n{contents_div.get_text(strip=True)}\n{'-' * 80}\n\n"
            else:
                logger.info(f"No se encontró el div#contents en {link}")

    try:
        main_html = get_page_content(url)
        if not main_html:
            raise ValueError("No se pudo obtener el contenido de la página principal.")

        extract_hrefs_from_div(main_html, url)
        logger.info(f"Total de enlaces encontrados: {len(hrefs)}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {executor.submit(scrape_page, link): link for link in hrefs}
            for future in as_completed(future_to_url):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error procesando {future_to_url[future]}: {str(e)}")

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs procesadas: {len(visited_urls)}\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += (
                "URLs no procesadas:\n\n" + "\n".join(urls_not_scraped) + "\n"
            )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)

        return response

    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
