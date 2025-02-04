import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PyPDF2 import PdfReader
from io import BytesIO
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
from rest_framework.response import Response
from rest_framework import status


def scraper_flora_harvard(url, sobrenombre):
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    visited_urls = set()
    urls_not_scraped = []
    
    def get_page_content(current_url):
        response = requests.get(current_url, headers=headers)
        response.raise_for_status()
        return response.text

    def extract_hrefs_from_ul(html_content, base_url):
        soup = BeautifulSoup(html_content, "html.parser")
        hrefs = []
        for ul in soup.find_all("ul"):
            links = ul.find_all("a", href=True)
            for link in links:
                href = link["href"]
                # Convertir enlaces relativos a absolutos
                if href.startswith("/"):
                    href = urljoin(base_url, href)
                elif href.endswith(".pdf"):
                    href = urljoin("http://flora.huh.harvard.edu/china/mss/", href)
                hrefs.append(href)
        return hrefs

    def extract_text_from_pdf(pdf_url):
        try:
            response = requests.get(pdf_url, headers=headers, stream=True)
            response.raise_for_status()

            pdf_reader = PdfReader(BytesIO(response.content))
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"

            logger.info(f"Texto extraído del PDF: {pdf_url}")
            return pdf_text
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF {pdf_url}: {str(e)}")
            urls_not_scraped.append(pdf_url)
            return None

    def process_link(current_url):
        nonlocal all_scraper

        if current_url in visited_urls:
            return

        visited_urls.add(current_url)
        logger.info(f"Procesando URL: {current_url}")

        try:
            html_content = get_page_content(current_url)
            soup = BeautifulSoup(html_content, "html.parser")

            panel_treatment = soup.find("div", id="panelTaxonTreatment")
            if panel_treatment:
                content = panel_treatment.get_text(strip=True)
                all_scraper += f"URL: {current_url}\n\n{content}\n{'-' * 80}\n\n"

            links = extract_hrefs_from_ul(html_content, url)
            for link in links:
                if link.endswith(".pdf"):
                    pdf_text = extract_text_from_pdf(link)
                    if pdf_text:
                        all_scraper += f"URL: {link}\n\n{pdf_text}\n{'-' * 80}\n\n"
                else:
                    process_link(link)  # Procesa enlaces internos no PDF

        except Exception as e:
            logger.error(f"Error al procesar la URL {current_url}: {str(e)}")
            urls_not_scraped.append(current_url)

    try:
        main_html = get_page_content(url)
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
        logger.error(f"Error durante el scraping: {str(e)}")
        return Response(
            {"message": f"Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
