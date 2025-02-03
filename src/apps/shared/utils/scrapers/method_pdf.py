import requests
import os
import PyPDF2
from io import BytesIO
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    connect_to_mongo,
    get_logger,
    save_scraper_data_pdf, 
    get_random_user_agent
)


import PyPDF2

def extract_text_with_pypdf2(pdf_file, start_page=1, end_page=None):
    try:
        text = ""
        reader = PyPDF2.PdfReader(pdf_file)  

        total_pages = len(reader.pages)

        start = max(0, start_page - 1)  
        end = min(total_pages, end_page) if end_page else total_pages

        if start >= total_pages:
            raise ValueError(f"El número de página inicial ({start_page}) excede el total de páginas ({total_pages}).")

        for i in range(start, end):
            text += reader.pages[i].extract_text() or "" 
        return text.strip()
    except Exception as e:
        raise Exception(f"Error al extraer texto con PyPDF2: {e}")


def scraper_pdf(url, sobrenombre, start_page=1, end_page=None):
    logger = get_logger("Extrayendo texto de PDF")

    try:
        collection, fs = connect_to_mongo("scrapping-can", "collection")

        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)

        all_scraper = extract_text_with_pypdf2(pdf_file, start_page, end_page)

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

        return Response({"data": response_data}, status=status.HTTP_200_OK)
    except requests.Timeout:
        return Response(
            {"error": "El servidor tardó demasiado en responder."},
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except requests.ConnectionError:
        return Response(
            {"error": "No se pudo establecer conexión con el servidor."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except requests.HTTPError as e:
        return Response(
            {"error": f"Error HTTP al descargar el PDF: {e}"},
            status=e.response.status_code if e.response else 500,
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error inesperado en el scraping de PDF: {e}")
        return Response(
            {"error": f"Error inesperado: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )