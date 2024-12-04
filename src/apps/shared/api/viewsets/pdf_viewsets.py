from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from datetime import datetime
import requests
import pdfplumber
import os
import json
import gridfs
import urllib.parse

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

@csrf_exempt
def scrape_url(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            url = data.get("url")
            tipo = data.get("tipo")

            if tipo not in [1, 2]:
                return JsonResponse(
                    {"error": "Tipo inválido. Debe ser 1 para URL o 2 para PDF"},
                    status=400,
                )

            if not url:
                return JsonResponse({"error": "No se proporcionó una URL"}, status=400)

            url_docs = list(collection.find({"Url": url}).sort("Fecha_scrapper", -1))
            if len(url_docs) >= 2:
                oldest_doc = url_docs[-1]
                fs.delete(oldest_doc["Objeto"])
                collection.delete_one({"_id": oldest_doc["_id"]})

            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                return JsonResponse(
                    {"error": f"Error al descargar la URL: {str(e)}"}, status=500
                )

            if response.status_code == 200:
                if tipo == 2:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/pdf" not in content_type:
                        return JsonResponse(
                            {"error": "El archivo no es un PDF"}, status=400
                        )

                tipo_documento = "PDF" if tipo == 2 else "URL"

                url_folder = urllib.parse.urlparse(url).netloc.replace('.', '_')
                url_folder_path = os.path.join(output_dir, url_folder)

                if not os.path.exists(url_folder_path):
                    os.makedirs(url_folder_path)

                pdf_filename = os.path.join(url_folder_path, url.split("/")[-1])
                base_filename = pdf_filename.replace(".pdf", "")
                
                pdf_version = 0
                pdf_filename_with_version = f"{base_filename}_v{pdf_version}.pdf"
                
                while os.path.exists(pdf_filename_with_version):
                    pdf_version += 1
                    pdf_filename_with_version = f"{base_filename}_v{pdf_version}.pdf"

                with open(pdf_filename_with_version, "wb") as pdf_file:
                    pdf_file.write(response.content)

                full_text = ""
                with pdfplumber.open(pdf_filename_with_version) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            full_text += text + "\n"

                txt_filename_with_version = f"{base_filename}_v{pdf_version}.txt"
                
                while os.path.exists(txt_filename_with_version):
                    pdf_version += 1
                    txt_filename_with_version = f"{base_filename}_v{pdf_version}.txt"

                with open(txt_filename_with_version, "w", encoding="utf-8") as txt_file:
                    txt_file.write(full_text.strip())

                with open(txt_filename_with_version, "rb") as txt_file:
                    object_id = fs.put(txt_file, filename=txt_filename_with_version)

                data = {
                    "Objeto": object_id,
                    "Tipo": tipo_documento,
                    "Url": url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                }
                collection.insert_one(data)

                return JsonResponse(
                    {
                        "message": "Datos guardados en MongoDB",
                        "Fecha_scrapper": data["Fecha_scrapper"],
                    },
                    status=200,
                )

            else:
                return JsonResponse(
                    {"error": f"Error al descargar la URL: {response.status_code}"},
                    status=500,
                )

        except Exception as e:
            return JsonResponse(
                {"error": f"Ocurrió un error inesperado: {str(e)}"}, status=500
            )

@csrf_exempt
def get_scraped_url(request):
    if request.method == "GET":
        try:
            url = request.GET.get("url")

            if not url:
                return JsonResponse({"error": "Debe proporcionar una URL"}, status=400)

            scraped_data = collection.find({"Url": url})

            if not scraped_data:
                return JsonResponse(
                    {"message": "No hay datos de scraping disponibles para esta URL."},
                    status=200,
                )

            data_to_return = []
            for record in scraped_data:
                record_data = {
                    "Objeto": (
                        str(record.get("Objeto", None))
                        if record.get("Objeto")
                        else None
                    ),
                    "Tipo": record.get("Tipo", "No disponible"),
                    "Url": record.get("Url", ""),
                    "Fecha_scrapper": record.get("Fecha_scrapper", "No disponible"),
                    "Etiquetas": record.get("Etiquetas", []),
                }
                data_to_return.append(record_data)

            return JsonResponse({"scraped_data": data_to_return}, status=200)

        except Exception as e:
            error_msg = f"Ocurrió un error inesperado: {str(e)}"
            return JsonResponse({"error": error_msg}, status=500)
