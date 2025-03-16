import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status

def scraper_flora_habitas(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo()
    all_scraper = ""
    visited_urls = set()
    urls_not_scraped = []
    hrefs = set()
    total_scraped_successfully = 0

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

    def scrape_page(link_href):
        nonlocal all_scraper, total_scraped_successfully
        visited_urls.add(link_href)
        html_content = get_page_content(link_href)
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            contents_div = soup.find("div", id="contents")
            if contents_div:
                content_text = contents_div.get_text(strip=True)
                all_scraper += f"URL: {link_href}\n\n{content_text}\n{'-' * 80}\n\n"
                
                if content_text and content_text.strip():
                    object_id = save_to_mongo("urls_scraper", content_text, link_href, url)
                    total_scraped_successfully += 1
                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                    
            else:
                logger.info(f"No se encontró el div#contents en {link_href}")

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
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n"
            f"Total de archivos almacenados: {total_scraped_successfully}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += (
                "URLs no procesadas:\n\n" + "\n".join(urls_not_scraped) + "\n"
            )

        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response


    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)