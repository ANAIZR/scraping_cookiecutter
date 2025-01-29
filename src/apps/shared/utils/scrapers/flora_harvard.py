import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.http import JsonResponse
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
from rest_framework.response import Response
from rest_framework import status

def scraper_flora_harvard(url, sobrenombre):
    """
    Scraper que extrae enlaces dentro de <ul>, descarga PDFs y extrae texto de 'panelTaxonTreatment'.
    """
    headers = {"User-Agent": get_random_user_agent()}
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    visited_urls = set()
    urls_not_scraped = []
    pdf_folder = "pdfs"  # Carpeta única para todos los PDFs

    # Crear carpeta para PDFs
    os.makedirs(pdf_folder, exist_ok=True)

    def get_page_content(current_url):
        """
        Realiza una solicitud GET y devuelve el contenido HTML.
        """
        response = requests.get(current_url, headers=headers)
        response.raise_for_status()
        return response.text

    def extract_hrefs_from_ul(html_content, base_url):
        """
        Extrae todos los enlaces de las etiquetas <ul>.
        """
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

    def download_pdf(pdf_url):
        """
        Descarga un archivo PDF en la carpeta única correspondiente.
        """
        try:
            response = requests.get(pdf_url, headers=headers, stream=True)
            response.raise_for_status()

            pdf_name = os.path.basename(pdf_url)
            pdf_path = os.path.join(pdf_folder, pdf_name)

            with open(pdf_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    pdf_file.write(chunk)

            logger.info(f"PDF descargado: {pdf_path}")
        except Exception as e:
            logger.error(f"Error al descargar el PDF {pdf_url}: {str(e)}")
            urls_not_scraped.append(pdf_url)

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
                    download_pdf(link)

        except Exception as e:
            logger.error(f"Error al procesar la URL {current_url}: {str(e)}")
            urls_not_scraped.append(current_url)

    try:
        main_html = get_page_content(url)
        links = extract_hrefs_from_ul(main_html, url)
        logger.info(f"Total de enlaces encontrados: {len(links)}")

        # Procesar cada enlace
        for link in links:
            process_link(link)

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de URLs procesadas: {len(visited_urls)}\n"
            f"Total de PDFs descargados: {len(os.listdir(pdf_folder))}\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        ) + all_scraper

        if urls_not_scraped:
            all_scraper += "URLs no procesadas:\n\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

