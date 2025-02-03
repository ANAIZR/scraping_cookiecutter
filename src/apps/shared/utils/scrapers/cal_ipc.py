import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyPDF2 import PdfReader
from io import BytesIO
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
import time
from rest_framework.response import Response
from rest_framework import status
def scraper_cal_ipc(url, sobrenombre, max_depth=2):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    total_urls_found = 0
    total_urls_scraped = 0
    urls_not_scraped = []
    visited_urls = set()
    urls_to_scrape = []

    base_domain = "https://www.cal-ipc.org/"

    def extract_text_from_pdf(pdf_url):
 
        try:
            response = requests.get(pdf_url, headers=headers, timeout=20)
            response.raise_for_status()
            pdf_file = BytesIO(response.content)
            reader = PdfReader(pdf_file)
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
            return extracted_text.strip()
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF {pdf_url}: {str(e)}")
            return None

    def scrape_initial_page(current_url):

        logger.info(f"Scraping la página inicial: {current_url}")
        try:
            response = requests.get(current_url, headers=headers, timeout=50)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            td_with_links = soup.select("tbody td.it-latin:has(a[href])")
            logger.info(f"Se encontraron {len(td_with_links)} celdas con la clase 'it-latin'.")

            links = [a['href'] for td in td_with_links for a in td.find_all("a", href=True)]
            valid_links = [
                (urljoin(base_domain, link), 1)
                for link in links
                if urljoin(base_domain, link).startswith(base_domain)
                and not any(link.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif"])
                and "upload" not in link.lower()
            ]
            return valid_links

        except requests.RequestException as e:
            logger.error(f"Error al procesar la página inicial {current_url}: {str(e)}")
            return []

    def scrape_page(current_url, current_depth):
 
        nonlocal total_urls_found, total_urls_scraped, all_scraper

        if current_url in visited_urls or current_depth > max_depth:
            return []

        logger.info(f"Procesando URL: {current_url} (Nivel: {current_depth})")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, headers=headers, timeout=20)
            response.raise_for_status()
            time.sleep(1)
            soup = BeautifulSoup(response.text, "html.parser")

            container_div = soup.find("div", id="container")
            extracted_links = []

            if container_div:
                content = container_div.get_text(strip=True)
                all_scraper += f"URL: {current_url}\n\n"
                all_scraper += f"{content}\n"
                all_scraper += "-" * 80 + "\n\n"
                total_urls_scraped += 1

                links = container_div.find_all("a", href=True)
                for link in links:
                    href = link["href"]
                    full_url = urljoin(base_domain, href)

                    if full_url.startswith(base_domain) and "upload" not in href.lower():
                        if href.lower().endswith(".pdf"):
                            pdf_text = extract_text_from_pdf(full_url)
                            if pdf_text:
                                all_scraper += f"Texto extraído del PDF: {full_url}\n\n"
                                all_scraper += f"{pdf_text}\n"
                                all_scraper += "-" * 80 + "\n\n"
                            else:
                                all_scraper += f"Enlace PDF (no se pudo extraer texto): {full_url}\n"
                        elif not any(href.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                            extracted_links.append((full_url, current_depth + 1))

            total_urls_found += len(extracted_links)
            return extracted_links

        except requests.RequestException as e:
            logger.error(f"Error al procesar la URL: {current_url}, error: {str(e)}")
            urls_not_scraped.append(current_url)
            return []

    def scrape_pages_in_parallel(url_list):
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {
                executor.submit(scrape_page, url, depth): (url, depth)
                for url, depth in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    new_links = future.result()
                    urls_to_scrape.extend(new_links)
                except Exception as e:
                    logger.error(f"Error en tarea de scraping: {str(e)}")

    try:
        initial_links = scrape_initial_page(url)
        urls_to_scrape.extend(initial_links)

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

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

