import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.http import JsonResponse
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
import time

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

    def scrape_initial_page(current_url):
        """
        Scrapes the initial URL to extract all hrefs with class 'paf-list'.
        """
        logger.info(f"Scraping la página inicial: {current_url}")
        try:
            response = requests.get(current_url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Buscar todos los hrefs con clase 'paf-list'
            links = soup.find_all("a", class_="paf-list", href=True)
            extracted_links = []

            for link in links:
                href = link["href"]
                full_url = urljoin(base_domain, href)

                if full_url.startswith(base_domain):
                    logger.info(f"URL válida encontrada en página inicial: {full_url}")
                    extracted_links.append((full_url, 1))

            return extracted_links

        except requests.RequestException as e:
            logger.error(f"Error al procesar la página inicial {current_url}: {str(e)}")
            return []

    def scrape_page(current_url, current_depth):
        """
        Scrapes individual pages to extract the ID 'container' and additional links.
        """
        nonlocal total_urls_found, total_urls_scraped, all_scraper

        if current_url in visited_urls or current_depth > max_depth:
            return []

        logger.info(f"Procesando URL: {current_url} (Nivel: {current_depth})")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, headers=headers, timeout=20)
            response.raise_for_status()
            time.sleep(1)  # Esperar un segundo para no sobrecargar el servidor
            soup = BeautifulSoup(response.text, "html.parser")

            # Extraer contenido de ID 'container'
            container_div = soup.find("div", id="container")
            if container_div:
                content = container_div.get_text()
                all_scraper += f"URL: {current_url}\n\n"
                all_scraper += f"{content}\n"
                all_scraper += "-" * 80 + "\n\n"
                total_urls_scraped += 1

            # Extraer nuevos links de 'paftable'
            table = soup.find("table", id="paftable")
            links = table.find_all("a", href=True) if table else []
            extracted_links = []

            for link in links:
                href = link["href"]
                full_url = urljoin(base_domain, href)

                if full_url.startswith(base_domain) and not any(
                    href.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".pdf"]
                ):
                    logger.info(f"URL válida encontrada: {full_url}")
                    extracted_links.append((full_url, current_depth + 1))

            total_urls_found += len(extracted_links)
            return extracted_links

        except requests.RequestException as e:
            logger.error(f"Error al procesar la URL: {current_url}, error: {str(e)}")
            urls_not_scraped.append(current_url)
            return []

    def scrape_pages_in_parallel(url_list):
        """
        Parallel scraping of pages.
        """
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
        # Paso 1: Obtener URLs iniciales desde la página principal
        initial_links = scrape_initial_page(url)
        urls_to_scrape.extend(initial_links)

        # Paso 2: Procesar las URLs extraídas
        while urls_to_scrape:
            current_batch = [
                (url, depth)
                for url, depth in set(urls_to_scrape)
                if url not in visited_urls
            ]
            urls_to_scrape.clear()
            scrape_pages_in_parallel(current_batch)

        # Generar el resumen del scraping
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

        # Guardar los datos procesados
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Error al realizar la solicitud: {str(e)}"}, status=400
        )
