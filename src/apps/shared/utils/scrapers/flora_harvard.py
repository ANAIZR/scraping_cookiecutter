import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from bson import ObjectId
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    extract_text_from_pdf,
    save_to_mongo
)
from rest_framework.response import Response
from rest_framework import status

def scraper_flora_harvard(url, sobrenombre):

    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo()

    all_scraper = "" 
    visited_urls = set()
    urls_not_scraped = []
    scraped_urls = []
    total_scraped_links = 0

    def get_page_content(current_url):

        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error al obtener el contenido de {current_url}: {e}")
            urls_not_scraped.append(current_url)
            return None

    def extract_hrefs_from_ul(html_content, base_url):
 
        soup = BeautifulSoup(html_content, "html.parser")
        hrefs = []
        for ul in soup.find_all("ul"):
            links = ul.find_all("a", href=True)
            for link in links:
                href = link["href"]
                if href.startswith("/"):
                    href = urljoin(base_url, href)
                elif href.endswith(".pdf"):
                    href = urljoin("http://flora.huh.harvard.edu/china/mss/", href)
                hrefs.append(href)
        return hrefs

    def process_link(current_url):
 
        nonlocal total_scraped_links, all_scraper

        if current_url in visited_urls:
            return

        visited_urls.add(current_url)
        logger.info(f"Procesando URL: {current_url}")

        try:
            html_content = get_page_content(current_url)
            if not html_content:
                return

            soup = BeautifulSoup(html_content, "html.parser")

            panel_treatment = soup.find("div", id="panelTaxonTreatment")
            if panel_treatment:
                content_text = panel_treatment.get_text(strip=True)
                object_id = save_to_mongo("urls_scraper", content_text, current_url, url)
                total_scraped_links += 1
                scraped_urls.append(current_url)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                

                

            links = extract_hrefs_from_ul(html_content, url)

            for link in links:
                if link.endswith(".pdf"):
                    pdf_content = extract_text_from_pdf(link)

                    if pdf_content:
                        object_id = fs.put(
                            pdf_content.encode("utf-8"),
                            source_url=link,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=pdf_content,
                            url=url
                        )

                        

                        scraped_urls.append(link)
                        total_scraped_links += 1

                        existing_versions = list(fs.find({"source_url": link}).sort("scraping_date", -1))

                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            fs.delete(ObjectId(oldest_version["_id"]))
                            logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

        except Exception as e:
            logger.error(f"Error al procesar la URL {current_url}: {str(e)}")
            urls_not_scraped.append(current_url)

    try:
        main_html = get_page_content(url)
        if not main_html:
            return Response({"error": "No se pudo acceder a la página principal"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        links = extract_hrefs_from_ul(main_html, url)
        logger.info(f"Total de enlaces encontrados: {len(links)}")

        for link in links:
            process_link(link)

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs procesadas: {len(scraped_urls)}\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n"
            f"Total de archivos almacenados en MongoDB: {total_scraped_links}\n\n"
            f"{'-'*80}\n\n"
        )

        if scraped_urls:
            all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"

        if urls_not_scraped:
            all_scraper += "URLs no procesadas:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre,collection)
        return response

    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
