import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.http import JsonResponse
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data_v2,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    extract_text_from_pdf
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import chardet

def scraper_aphidnet(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("APHIDNET")
    collection, fs = connect_to_mongo()
    
    total_urls_found = 0
    total_urls_scraped = 0
    total_failed_scrapes = 0
    urls_not_scraped = []
    urls_scraped = []
    visited_urls = set()
    urls_to_scrape = []
    max_depth = 3

    def scrape_page(current_url, current_depth):
        nonlocal total_urls_found, total_urls_scraped, total_failed_scrapes
        content_text = ""
        portfolio_text = ""

        if current_url in visited_urls or current_depth > max_depth:
            return []

        if not current_url.startswith(url):
            return []

        visited_urls.add(current_url)
        try:
            response = requests.get(current_url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type:
                content_text = extract_text_from_pdf(current_url)
            else:
                detected_encoding = chardet.detect(response.content)["encoding"]
                if detected_encoding:
                    response.encoding = detected_encoding
                
                soup = BeautifulSoup(response.text, "html.parser")
                content_section = soup.find("section", id="content")
                portfolio_section = soup.find("section", class_="portfolio")

                if content_section:
                    content_text = content_section.get_text(strip=True)
                if portfolio_section:
                    portfolio_text = portfolio_section.get_text(strip=True)

            full_content = f"{content_text}\n{portfolio_text}".strip()
            
            if full_content:
                object_id = fs.put(
                    full_content.encode("utf-8"),
                    source_url=current_url,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=full_content,
                    url=url
                )
                total_urls_scraped += 1
                urls_scraped.append(current_url)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                collection.insert_one(
                    {
                        "_id": object_id,
                        "source_url": current_url,
                        "scraping_date": datetime.now(),
                        "Etiquetas": ["planta", "plaga"],
                        "url": url,
                    }
                )

                existing_versions = list(
                    collection.find({"source_url": current_url}).sort(
                        "scraping_date", -1
                    )
                )

                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    fs.delete(ObjectId(oldest_version["_id"]))
                    collection.delete_one(
                        {"_id": ObjectId(oldest_version["_id"])}
                    )
                    logger.info(
                        f"Se eliminó la versión más antigua con este enlace: '{current_url}' y object_id: {oldest_version['_id']}"
                    )
            else:
                urls_not_scraped.append(current_url)
                total_failed_scrapes += 1

            links = soup.find_all("a", href=True) if "html" in content_type else []
            extracted_links = []
            for link in links:
                href = link["href"]
                full_url = urljoin(current_url, href)

                if href == "#" or not href or href.startswith("#"):
                    continue
                if not full_url.startswith(url):
                    continue
                if full_url.endswith(".jpg") or "credits" in full_url or "glossary" in full_url:
                    continue
                extracted_links.append((full_url, current_depth + 1))
                total_urls_found += 1

            return extracted_links

        except requests.RequestException as e:
            urls_not_scraped.append(current_url)
            total_failed_scrapes += 1
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
            f"Total de URLs fallidas: {total_failed_scrapes}\n\n"
        )

        if urls_scraped:
            all_scraper += "URLs scrapeadas:\n" + "\n".join(urls_scraped) + "\n\n"
        
        if urls_not_scraped:
            all_scraper += "URLs fallidas:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response
    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Error al realizar la solicitud: {str(e)}"}, status=400
        )
