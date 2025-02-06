import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from rest_framework.response import Response
from rest_framework import status

from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    extract_text_from_pdf
)

ALLOWED_DOMAINS = ["flora.huh.harvard.edu", "www.efloras.org"]
PDF_BASE_URL = "http://flora.huh.harvard.edu/china/mss/"

def scraper_flora_harvard(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo()
    all_scraper = ""
    visited_urls = set()
    urls_not_scraped = []

    def get_page_content(current_url):
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error al obtener {current_url}: {e}")
            urls_not_scraped.append(current_url)
            return None

    def extract_hrefs_from_ul(html_content, base_url):
        soup = BeautifulSoup(html_content, "html.parser")
        hrefs = []
        for ul in soup.find_all("ul"):
            for link in ul.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/"):
                    href = urljoin(base_url, href)
                elif href.endswith(".pdf"):
                    href = urljoin(PDF_BASE_URL, href)

                parsed_url = urlparse(href)
                if parsed_url.netloc in ALLOWED_DOMAINS or href.startswith(PDF_BASE_URL):
                    hrefs.append(href)
                else:
                    logger.warning(f"URL bloqueada por dominio no permitido: {href}")
        return hrefs

    def process_link(current_url):
        nonlocal all_scraper

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
                content = panel_treatment.get_text(separator="\n", strip=True)
                all_scraper += f"URL: {current_url}\n\n{content}\n{'-' * 80}\n\n"

            links = extract_hrefs_from_ul(html_content, url)
            for link in links:
                if link.endswith(".pdf"):
                    pdf_text = extract_text_from_pdf(link)
                    if pdf_text:
                        all_scraper += f"URL: {link}\n\n{pdf_text}\n{'-' * 80}\n\n"
                else:
                    process_link(link)  

        except Exception as e:
            logger.error(f"Error al procesar la URL {current_url}: {e}")
            urls_not_scraped.append(current_url)

    try:
        main_html = get_page_content(url)
        if not main_html:
            return Response(
                {"message": "No se pudo acceder a la URL principal."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        links = extract_hrefs_from_ul(main_html, url)
        logger.info(f"Total de enlaces encontrados: {len(links)}")

        for link in links:
            process_link(link)

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs procesadas: {len(visited_urls)}\n"
            f"Total de PDFs procesados: {sum(1 for l in links if l.endswith('.pdf'))}\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += "URLs no procesadas:\n\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
