from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from datetime import datetime
import gridfs
import requests
import pdfplumber
import os
import json

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

@csrf_exempt
def scrape_pdf(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url')
            if not url:
                return JsonResponse({'error': 'No se proporcionó una URL'}, status=400)

            url_docs = list(collection.find({"Url": url}).sort("Fecha_scrapper", -1))

            if len(url_docs) >= 2:
                oldest_doc = url_docs[-1]  
                fs.delete(oldest_doc["Objeto"])  
                collection.delete_one({"_id": oldest_doc["_id"]})  

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                pdf_filename = os.path.join(output_dir, url.split("/")[-1])
                txt_filename = pdf_filename.replace('.pdf', '.txt')
                
                with open(pdf_filename, "wb") as pdf_file:
                    pdf_file.write(response.content)
                
                full_text = ""
                with pdfplumber.open(pdf_filename) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            full_text += text + "\n"

                with open(txt_filename, "w", encoding="utf-8") as txt_file:
                    txt_file.write(full_text.strip())

                with open(txt_filename, "rb") as txt_file:
                    object_id = fs.put(txt_file, filename=txt_filename)

                data = {
                    "Objeto": object_id,
                    "Tipo": "Documento",
                    "Url": url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"]
                }
                collection.insert_one(data)

                return JsonResponse({
                    "message": "Datos guardados en MongoDB",
                    "object_id": str(object_id),
                    "Fecha_scrapper": data["Fecha_scrapper"]
                })
            else:
                error_msg = f"Error al descargar el PDF: {response.status_code}"
                error_data = {
                    "Url": url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error": error_msg
                }
                collection.insert_one(error_data)
                return JsonResponse({"error": error_msg}, status=500)

        except Exception as e:
            error_msg = f"Ocurrió un error inesperado: {str(e)}"
            error_data = {
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_msg
            }
            collection.insert_one(error_data)
            return JsonResponse({"error": error_msg}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)
