import requests
import time
import random
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

def scraper_aphis_usda(url, sobrenombre):
    logger = get_logger("scraper")
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

            if depth >= 2:
                main_content = soup.find("main", id="main")
                if main_content:
                    nonlocal all_scraper
                    page_text = main_content.get_text(strip=True)
                    all_scraper += f"URL: {url}\n{page_text}\n\n" 

            for link in soup.find_all("a", href=True):
                inner_href = link.get("href")
                full_url = urljoin(url, inner_href)

                if full_url.lower().endswith(".pdf"):
                    total_non_scraped_links += 1  
                    non_scraped_urls.append(full_url)  
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
            logger.info(f"URLs restantes por procesar: {len(urls_to_scrape)}")
            urls_to_scrape = scrape_pages_in_parallel(urls_to_scrape)
            time.sleep(random.uniform(1, 3))  # Pause between iterations

        all_scraper += f"\n\nTotal links found: {total_found_links}\n"
        all_scraper += f"Total links scraped: {total_scraped_links}\n"
        all_scraper += f"Total links not scraped: {total_non_scraped_links}\n"
        all_scraper += "\n\nURLs no scrapeadas:\n"
        all_scraper += "\n".join(non_scraped_urls)  # List non-scraped URLs

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
