import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
from ..functions import (
    process_scraper_data,
    get_logger,
    get_random_user_agent,
    connect_to_mongo,
)


def scraper_flora_habitas(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("FLORA_HABITAS")
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    visited_urls = set()  
    urls_not_scraped = []  
    all_scraper = "" 

    def get_page_content(current_url):
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error al obtener contenido de {current_url}: {str(e)}")
            urls_not_scraped.append(current_url)
            return None

    def extract_hrefs_from_div(html_content, base_url):
        """Extrae todos los enlaces del div#contents, excluyendo los que contienen 'family'."""
        soup = BeautifulSoup(html_content, "html.parser")
        hrefs = set()  
        contents = soup.find("div", id="contents")
        if contents:
            links = contents.find_all("a", href=True)  
            for link in links:
                href = link["href"]
                if "family" not in href.lower():  # Excluir enlaces que contienen 'family'
                    full_url = urljoin(base_url, href) if not href.startswith("http") else href
                    hrefs.add(full_url)
                else:
                    logger.info(f"Enlace excluido (contiene 'family'): {href}")
        else:
            logger.warning("No se encontró el div#contents en el HTML proporcionado.")
        return hrefs

    def scrape_page(link):
        nonlocal all_scraper
        if link in visited_urls:
            logger.info(f"URL ya procesada: {link}")
            return None

        visited_urls.add(link)  
        logger.info(f"Procesando URL: {link}")

        html_content = get_page_content(link)
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            contents_div = soup.find("div", id="contents")
            if contents_div:
                all_scraper += f"URL: {link}\n\n{contents_div.get_text(strip=True)}\n{'-' * 80}\n\n"
            else:
                logger.warning(f"No se encontró el div#contents en {link}")
        else:
            logger.error(f"No se pudo obtener el contenido de la URL: {link}")

    def process_links_in_parallel(links):
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(scrape_page, link): link for link in links}
            for future in as_completed(future_to_url):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error en tarea de scraping: {str(e)}")

    try:
        main_html = get_page_content(url)
        if not main_html:
            raise ValueError("No se pudo obtener el contenido de la página principal.")

        links = extract_hrefs_from_div(main_html, url)
        logger.info(f"Total de enlaces encontrados en la página principal: {len(links)}")

        process_links_in_parallel(links)

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs procesadas: {len(visited_urls)}\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += "URLs no procesadas:\n\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)

        return response

    except Exception as e:
        logger.error(f"Error inesperado durante el scraping: {str(e)}")
        return JsonResponse(
            {"error": f"Error durante el scraping: {str(e)}"}, status=500
        )
