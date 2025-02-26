import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    extract_text_from_pdf
)
from datetime import datetime
from bson import ObjectId

def scraper_fao_org_home(url, sobrenombre):
    url_padre = url
    logger = get_logger("FAO_ORG_HOME")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()
    urls_to_scrape = [(url, 1)]  
    non_scraped_urls = []  
    scraped_urls = []


    total_found_links = 0
    total_scraped_links = 0
    total_non_scraped_links = 0

    def scrape_page(url, depth):
        nonlocal total_found_links, total_scraped_links, total_non_scraped_links

        if url in processed_links or depth > 3: 
            return []
        processed_links.add(url)

        logger.info(f"Accediendo a {url} en el nivel {depth}")

        headers = {"User-Agent": get_random_user_agent()}
        new_links = []

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            if url.endswith(".pdf"):
                logger.info(f"Extrayendo texto de PDF: {url}")
                pdf_text = extract_text_from_pdf(url)

                if pdf_text:
                    object_id = fs.put(
                        pdf_text.encode("utf-8"),
                        source_url=url,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "plaga"],
                        contenido=pdf_text,
                        url=url_padre
                    )
                    total_scraped_links += 1
                    scraped_urls.append(url)
                    logger.info(f"Texto de PDF almacenado en MongoDB con object_id: {object_id}")

                    existing_versions = list(fs.find({"source_url": url}).sort("scraping_date", -1))
                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        fs.delete(ObjectId(oldest_version._id))
                        logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version._id}")
                else:
                    non_scraped_urls.append(url)
                    total_non_scraped_links += 1
                return []            

            if depth >= 2:
                # Extraer solo el contenido principal
                # main_content = soup.find("body", id="main-content")
                main_content = soup.find("body")
                
                if main_content:
                    # Eliminar header y footer dentro del main content si existen
                    for element in main_content.find_all(['header', 'footer']):
                        element.decompose()
                    
                    # Extraer texto limpio
                    page_text = main_content.get_text(separator=' ', strip=True)
                    if page_text:
                        object_id = fs.put(
                            page_text.encode("utf-8"),
                            source_url=url,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=page_text,
                            url=url_padre
                        )
                        total_scraped_links += 1
                        scraped_urls.append(url)
                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                        existing_versions = list(fs.find({"source_url": url}).sort("scraping_date", -1))
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            file_id = oldest_version._id  # Esto obtiene el ID correcto
                            fs.delete(file_id)  # Eliminar la versión más antigua
                            logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                    else:
                        non_scraped_urls.append(url)

            # ... (resto del código original de procesamiento de links)
            for link in soup.find_all("a", href=True):
                inner_href = link.get("href")
                full_url = urljoin(url, inner_href)

                if full_url.startswith("http://www.fao.org/countryprofiles/index/en/?"):
                    total_non_scraped_links += 1
                    non_scraped_urls.append(full_url)
                    continue

                if "forms" in full_url or "":  
                    total_non_scraped_links += 1  
                    non_scraped_urls.append(full_url)  
                    continue

                if (
                    urlparse(full_url).netloc == "www.fao.org"
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
        nonlocal total_non_scraped_links
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
            logger.info(f"URLs restantes por procesar: {len(urls_to_scrape)}")
            urls_to_scrape = scrape_pages_in_parallel(urls_to_scrape)
            time.sleep(random.uniform(1, 3))  


        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
