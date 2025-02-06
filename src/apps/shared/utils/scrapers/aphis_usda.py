import requests
import time
import random
import PyPDF2
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)

def extract_text_from_pdf(pdf_url):
    """Extrae texto del PDF directamente sin descargarlo."""
    try:
        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()  # Asegura que la petición fue exitosa

        # Leer el contenido del PDF en memoria
        pdf_buffer = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_buffer)

        # Extraer texto de cada página
        pdf_text = "\n".join(
            [page.extract_text() for page in reader.pages if page.extract_text()]
        )
        return pdf_text if pdf_text else "No se pudo extraer texto del PDF."

    except Exception as e:
        return f"Error al extraer contenido del PDF ({pdf_url}): {e}"


def scraper_aphis_usda(url, sobrenombre):
    """Scraping de la página APHIS de USDA, extrayendo información y texto de PDFs sin descargarlos."""
    logger = get_logger("APHIS")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()
    urls_to_scrape = [(url, 1)]
    non_scraped_urls = []

    total_found_links = 0
    total_scraped_links = 0
    total_non_scraped_links = 0

    def scrape_page(url, depth):
        nonlocal total_found_links, total_scraped_links, total_non_scraped_links, all_scraper

        if url in processed_links or depth > 3:
            return []
        processed_links.add(url)


        headers = {"User-Agent": get_random_user_agent()}
        new_links = []

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            if depth >= 2:
                main_content = soup.find("main", id="main")
                if main_content:
                    page_text = main_content.get_text(strip=True)
                    all_scraper += f"URL: {url}\n{page_text}\n\n"

            for link in soup.find_all("a", href=True):
                inner_href = link.get("href")
                full_url = urljoin(url, inner_href)

                if full_url.lower().endswith(".pdf"):
                    if full_url not in processed_links:
                        logger.info(f"Extrayendo texto de PDF: {full_url}")
                        pdf_text = extract_text_from_pdf(full_url)
                        all_scraper += f"\n\nURL: {full_url}\n{pdf_text}\n"
                        processed_links.add(full_url)
                    continue  

                if "forms" in full_url or "":  
                    total_non_scraped_links += 1  
                    non_scraped_urls.append(full_url)  
                    continue

                if (
                    urlparse(full_url).netloc == "www.aphis.usda.gov"
                    and full_url not in processed_links
                ):
                    total_found_links += 1  
                    new_links.append((full_url, depth + 1))
                    total_scraped_links += 1 

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar el enlace {url}: {e}")
            total_non_scraped_links += 1  
            non_scraped_urls.append(url)  

        return new_links

    def scrape_pages_in_parallel(url_list):
        new_links = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, url, depth): (url, depth)
                for url, depth in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    result_links = future.result()
                    new_links.extend(result_links)
                except Exception as e:
                    logger.error(f"Error en tarea de scraping: {str(e)}")
                    total_non_scraped_links += 1  
        return new_links

    try:
        while urls_to_scrape:
            urls_to_scrape = scrape_pages_in_parallel(urls_to_scrape)
            time.sleep(random.uniform(1, 3))  

        all_scraper += f"\n\nTotal links encontrados: {total_found_links}\n"
        all_scraper += f"Total links scrapeados: {total_scraped_links}\n"
        all_scraper += f"Total links no scrapeados: {total_non_scraped_links}\n"
        all_scraper += "\n\nURLs no scrapeadas:\n"
        all_scraper += "\n".join(non_scraped_urls)  

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
