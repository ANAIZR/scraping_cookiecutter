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
from bson import ObjectId
from datetime import datetime


def scraper_bugwood(url, sobrenombre, max_depth=3):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo()

    all_scraper = ""
    total_urls_found = 0
    total_urls_scraped = 0
    total_non_scraped_links = 0
    urls_not_scraped = []
    visited_urls = set()
    urls_to_scrape = []

    base_domain = "https://wiki.bugwood.org"

    def scrape_page(current_url, current_depth):
        nonlocal total_urls_found, total_urls_scraped, all_scraper, total_non_scraped_links

        if current_url in visited_urls or current_depth > max_depth:
            return []

        if not current_url.startswith(base_domain):
            logger.info(f"URL fuera del dominio permitido: {current_url}")
            return []

        if any(
            exclude in current_url
            for exclude in [
                "&action=edit", "&action=history", "&action=info",
                "User", "&action=credits", "&printable=",
                "&oldid=", "Copyright", "Special",
                "Bugwoodwiki", "Glosary", "&redirect=no",
            ]
        ):
            logger.info(f"URL filtrada por parámetros no válidos: {current_url}")
            return []

        logger.info(f"Procesando URL: {current_url} (Nivel: {current_depth})")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            links = soup.find_all("a", href=True)
            extracted_links = []

            for link in links:
                href = link["href"]
                if href == "#" or not href or href.startswith("#"):
                    continue
                if href.startswith("/"):
                    href = urljoin(base_domain, href)

                if not href.startswith(base_domain):
                    continue

                if any(
                    exclude in href
                    for exclude in [
                        "&action=edit", "&action=history", "&action=info",
                        "User", "&action=credits", "&printable=",
                        "&oldid=", "Copyright", "Special",
                        "Bugwoodwiki", "&redirect=no",
                    ]
                ):
                    continue

                logger.info(f"✅ URL válida encontrada: {href}")
                extracted_links.append((href, current_depth + 1))

            total_urls_found += len(extracted_links)

            container_div = soup.find("div", class_="container")
            if container_div:
                content_text = container_div.get_text(strip=True)

                if content_text:
                    object_id = fs.put(
                        content_text.encode("utf-8"),
                        source_url=current_url,
                        scraping_date=datetime.now(),
                        Etiquetas=["planta", "plaga"],
                        contenido=content_text,
                        url=url
                    )
                    total_urls_scraped += 1
                    logger.info(f"✅ Archivo almacenado en MongoDB con object_id: {object_id}")

                    existing_versions = list(fs.find({"source_url": current_url}).sort("scraping_date", -1))

                    if len(existing_versions) > 1:
                        oldest_version = existing_versions[-1]
                        file_id = oldest_version._id  
                        fs.delete(file_id)  
                        logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                else:
                    total_non_scraped_links += 1
                    urls_not_scraped.append(current_url)
                    logger.warning(f"⚠️ No se almacenó contenido vacío para: {current_url}")

            return extracted_links

        except requests.RequestException as e:
            logger.error(f"❌ Error al procesar la URL: {current_url}, error: {str(e)}")
            total_non_scraped_links += 1
            urls_not_scraped.append(current_url)
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
                    urls_to_scrape.extend(new_links)
                except Exception as e:
                    logger.error(f"❌ Error en tarea de scraping: {str(e)}")

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
            f"📌 **Resumen del scraping:**\n"
            f"🔗 Total de URLs encontradas: {total_urls_found}\n"
            f"✅ Total de URLs scrapeadas: {total_urls_scraped}\n"
            f"⚠️ Total de URLs no scrapeadas: {total_non_scraped_links}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += "⚠️ URLs no scrapeadas:\n\n"
            all_scraper += "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        logger.info("🚀 Scraping completado exitosamente.")
        return response

    except requests.RequestException as e:
        return JsonResponse(
            {"error": f"Error al realizar la solicitud: {str(e)}"}, status=400
        )
