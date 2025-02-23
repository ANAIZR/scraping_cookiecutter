import requests
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    extract_text_from_pdf,
)
from datetime import datetime
from bson import ObjectId

def scraper_aphis_usda(url, sobrenombre):
    logger = get_logger("APHIS")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo()
    all_scraper = ""
    processed_links = set()
    urls_to_scrape = [(url, 1)]  
    non_scraped_urls = []  
    scraped_urls = []

    total_found_links = 0
    total_scraped_links = 0
    total_non_scraped_links = 0
    allowed_domain = "https://www.aphis.usda.gov"

    def scrape_page(current_url, depth):
        nonlocal total_found_links, total_scraped_links, total_non_scraped_links
        content_text = ""

        if current_url in processed_links or depth > 3: 
            return []
        processed_links.add(current_url)

        logger.info(f"Accediendo a {current_url} en el nivel {depth}")

        headers = {"User-Agent": get_random_user_agent()}
        new_links = []

        try:
            if current_url.lower().endswith(".pdf"):
                content_text = extract_text_from_pdf(current_url)
            else:
                response = requests.get(current_url, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                if depth >= 2:
                    main_content = soup.find("main", id="main")
                    if main_content:
                        content_text = main_content.get_text(separator=" ", strip=True)

            if content_text and content_text.strip():
                object_id = fs.put(
                    content_text.encode("utf-8"),
                    source_url=current_url,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=content_text,
                    url=url
                )
                total_scraped_links += 1
                scraped_urls.append(current_url)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                

                existing_versions = list(fs.find({"source_url": current_url}).sort("scraping_date", -1))


                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    fs.delete(oldest_version._id)  
                    logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")

            for link in soup.find_all("a", href=True):
                inner_href = link.get("href")
                full_url = urljoin(current_url, inner_href)

                if not full_url.startswith(allowed_domain):
                    continue
                
                if any(substring in full_url.lower() for substring in ["#top", "filter", "media","forms"]):
                    continue
                
                if full_url.lower().endswith(".pdf"):
                    content_text = extract_text_from_pdf(full_url)
                    if content_text:
                        object_id = fs.put(
                            content_text.encode("utf-8"),
                            source_url=full_url,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=content_text,
                            url=url
                        )
                        total_scraped_links += 1
                        scraped_urls.append(full_url)
                        logger.info(f"Archivo PDF almacenado en MongoDB con object_id: {object_id}")

                        

                        existing_versions = list(fs.find({"source_url": full_url}).sort("scraping_date", -1))


                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")
                    else:
                        total_non_scraped_links += 1
                        non_scraped_urls.append(full_url)
                    continue

                if full_url not in processed_links:
                    new_links.append((full_url, depth + 1))
                    total_found_links += 1

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar el enlace {current_url}: {e}")
            total_non_scraped_links += 1  
            non_scraped_urls.append(current_url)  

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
        return new_links

    while urls_to_scrape:
        urls_to_scrape = scrape_pages_in_parallel(urls_to_scrape)
        time.sleep(random.uniform(1, 3))

    all_scraper += (
        f"Total links found: {total_found_links}\n"
        f"Total links scraped: {total_scraped_links}\n"
        f"Scraped URLs:\n" + "\n".join(scraped_urls) + "\n"
        f"Total links not scraped: {total_non_scraped_links}\n"
        f"Non-scraped URLs:\n" + "\n".join(non_scraped_urls) + "\n"
    )

    response = process_scraper_data(all_scraper, url, sobrenombre)
    return response
