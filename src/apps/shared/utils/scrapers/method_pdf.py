import requests
from pypdf import PdfReader
from io import BytesIO
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    connect_to_mongo,
    get_logger,
    save_scraper_data_pdf, 
    get_random_user_agent
)
import pdfplumber  


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
                text += page_text

        return text.strip()
    except Exception as e:
        raise Exception(f"Error al extraer texto con PyPDF: {e}")


def extract_text_with_pdfplumber(pdf_file):

    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        return text.strip()
    except Exception as e:
        raise Exception(f"Error al extraer texto con pdfplumber: {e}")


def scraper_pdf(url, sobrenombre, start_page=1, end_page=None):

    logger = get_logger("Extrayendo texto de PDF")

    try:
        collection, fs = connect_to_mongo()

        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)

        try:
            all_scraper = extract_text_with_pypdf(pdf_file, start_page, end_page)
        except Exception as e:
            logger.warning(f"PyPDF falló: {e}. Intentando con pdfplumber...")
            all_scraper = extract_text_with_pdfplumber(pdf_file)

        if not all_scraper.strip():
            return Response(
                {"error": "No se pudo extraer texto del PDF en el rango especificado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = save_scraper_data_pdf(
            all_scraper, 
            url,
            sobrenombre,
            collection,
            fs
        )

        logger.info(f"DEBUG - Respuesta de save_scraper_data_pdf: {response_data}")

        if not isinstance(response_data, dict):
            return Response(
                {"error": f"Respuesta no serializable en save_scraper_data_pdf: {type(response_data)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return response_data

    except Exception as e:
        logger.error(f"Error inesperado en el scraping de PDF: {e}")
        return Response(
            {"error": f"Error inesperado: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
