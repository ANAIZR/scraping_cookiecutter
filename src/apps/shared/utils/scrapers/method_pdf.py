import requests
from pypdf import PdfReader
from io import BytesIO
import pdfplumber  
from ..functions import (
    connect_to_mongo,
    get_logger,
    save_scraper_data_pdf, 
    get_random_user_agent
)


def extract_text_with_pypdf(pdf_file, start_page=1, end_page=None):

    try:
        text = ""
        reader = PdfReader(pdf_file)

        if reader.is_encrypted:
            raise ValueError("El PDF está cifrado y no se puede extraer texto.")

        total_pages = len(reader.pages)

        start = max(0, start_page - 1)  
        end = min(total_pages, end_page) if end_page else total_pages

        if start >= total_pages:
            raise ValueError(f"El número de página inicial ({start_page}) excede el total de páginas ({total_pages}).")

        for i in range(start, end):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text += page_text + "\n\n"

        return text.strip()
    except Exception as e:
        raise Exception(f"Error al extraer texto con PyPDF: {e}")


def extract_text_with_pdfplumber(pdf_file, start_page=1, end_page=None):

    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)

            start = max(0, start_page - 1)  
            end = min(total_pages, end_page) if end_page else total_pages

            if start >= total_pages:
                raise ValueError(f"El número de página inicial ({start_page}) excede el total de páginas ({total_pages}).")

            for i in range(start, end):
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n\n"

        return text.strip()
    except Exception as e:
        raise Exception(f"Error al extraer texto con pdfplumber: {e}")


def scraper_pdf(url, sobrenombre, start_page=1, end_page=None):

    logger = get_logger("Extrayendo texto de PDF")

    try:
        collection, fs = connect_to_mongo()
        headers = {"User-Agent": get_random_user_agent()}

        logger.info(f"Descargando PDF desde: {url}")
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)

        try:
            all_scraper = extract_text_with_pypdf(pdf_file, start_page, end_page)
        except Exception as e:
            logger.warning(f"PyPDF falló: {e}. Intentando con pdfplumber...")
            all_scraper = extract_text_with_pdfplumber(pdf_file, start_page, end_page)

        if not all_scraper.strip():
            return {"error": "No se pudo extraer texto del PDF en el rango especificado."}

        response_data = save_scraper_data_pdf(
            all_scraper, 
            url,
            sobrenombre,
            collection,
            fs
        )

        logger.info(f"DEBUG - Respuesta de save_scraper_data_pdf: {response_data}")

        if not isinstance(response_data, dict):
            return {"error": f"Respuesta no serializable en save_scraper_data_pdf: {type(response_data)}"}

        return response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Error al descargar el PDF: {e}")
        return {"error": f"Error al descargar el PDF: {e}"}
    except Exception as e:
        logger.error(f"Error inesperado en el scraping de PDF: {e}")
        return {"error": f"Error inesperado: {e}"}
