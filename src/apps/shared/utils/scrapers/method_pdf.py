import requests
import os
import pdfplumber
from io import BytesIO
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    connect_to_mongo,
)


def extract_text_with_pdfminer(pdf_file):
    try:
        return extract_text(pdf_file)
    except Exception as e:
        raise Exception(f"Error al extraer texto con pdfminer: {e}")


def scraper_pdf(url, sobrenombre, start_page=1, end_page=None):
    try:
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }
        response = requests.get(url, verify=False, headers=headers)
        response.raise_for_status()

        folder_path = generate_directory(url)
        txt_filepath = get_next_versioned_filename(folder_path, base_name=sobrenombre)
        os.makedirs(os.path.dirname(txt_filepath), exist_ok=True)
        start_page = start_page or 1
        if start_page < 1:
            return Response(
                {"error": "El número de página inicial debe ser mayor o igual a 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "text/html" in response.headers["Content-Type"]:
            soup = BeautifulSoup(response.text, "html.parser")
            pages = soup.find_all("div#viewer div.page")
            extracted_pages = [
                int(page["data-page-number"])
                for page in pages
                if start_page <= int(page["data-page-number"]) <= end_page
            ]
            return Response({"pages": extracted_pages}, status=status.HTTP_200_OK)

        pdf_file = BytesIO(response.content)
        full_text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                start = max(0, start_page - 1)
                end = min(total_pages, end_page) if end_page else total_pages
                if start >= total_pages:
                    return Response(
                        {
                            "error": "El número de página inicial excede el total de páginas del PDF."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                for i in range(start, end):
                    text = pdf.pages[i].extract_text()
                    if text:
                        full_text += text + "\n"

        except Exception as e:
            print(f"pdfplumber falló: {e}")
            pdf_file.seek(0)
            full_text = extract_text_with_pdfminer(pdf_file)

        if not full_text.strip():
            raise Exception("No se pudo extraer texto del PDF.")

        with open(txt_filepath, "w", encoding="utf-8") as txt_file:
            txt_file.write(full_text.strip())

        # Generar los datos para guardar en MongoDB
        data = {
            "Objeto": sobrenombre,
            "Tipo": "PDF",
            "Url": url,
            "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }

        collection.insert_one(data)
        delete_old_documents(url, collection, fs)

        # Respuesta de éxito
        response_data = {
            "Tipo": "PDF",
            "Url": url,
            "Fecha_scraper": data["Fecha_scraper"],
            "Etiquetas": data["Etiquetas"],
            "Mensaje": "Los datos han sido scrapeados correctamente y guardados.",
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except requests.exceptions.RequestException as e:
        return Response(
            {"error": f"Error al descargar el PDF: {e}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": f"Error al procesar el PDF o extraer el texto: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
