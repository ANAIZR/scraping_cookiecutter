from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pdfplumber
import requests
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
import json

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}

@csrf_exempt
def scrape_pdf(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pdf_urls = data.get('pdf_urls', [])

            if not pdf_urls:
                return JsonResponse({"error": "No se proporcionaron URLs de PDF"}, status=400)

            response_data = []

            for url in pdf_urls:
                existing_doc = collection.find_one({"Url": url})
                
                if existing_doc:
                    response_data.append({
                        "message": f"El documento para esta URL ya existe.",
                        "object_id": str(existing_doc['Objeto'])
                    })
                    continue
                
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    pdf_filename = os.path.join(output_dir, url.split("/")[-1])  
                    txt_filename = pdf_filename.replace('.pdf', '.txt')  

                    with open(pdf_filename, "wb") as f:
                        f.write(response.content)

                    full_text = ""
                    with pdfplumber.open(pdf_filename) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n"

                    with open(txt_filename, "w", encoding="utf-8") as txt_file:
                        txt_file.write(full_text.strip())

                    with open(txt_filename, "rb") as f:
                        object_id = fs.put(f, filename=txt_filename)

                    data = {
                        "Objeto": object_id,
                        "Tipo": "Documento",
                        "Url": url,
                        "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Etiquetas": ["planta", "plaga"],
                    }
                    collection.insert_one(data)
                    response_data.append({
                        "message": f"Texto extraído y guardado en MongoDB",
                        "object_id": str(object_id)
                    })

                    records = list(collection.find({'Url': url}).sort("Fecha_scrapper", -1))
                    if len(records) > 2:
                        for record in records[2:]:
                            collection.delete_one({'_id': record['_id']})
                            fs.delete(record['Objeto'])  
                else:
                    response_data.append({
                        "error": f"Error al descargar el PDF {url}: {response.status_code}"
                    })

            return JsonResponse({"results": response_data})

        except Exception as e:
            return JsonResponse({"error": f"Ocurrió un error: {str(e)}"}, status=500)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
