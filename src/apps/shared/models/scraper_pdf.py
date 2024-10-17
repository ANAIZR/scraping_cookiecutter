import pdfplumber
import requests
from pymongo import MongoClient
from datetime import datetime
import gridfs

client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)  #

pdf_urls = [
    "https://www.iucngisd.org/gisd/pdf/100Spanish.pdf",
    "https://www.sag.gob.cl/sites/default/files/MANUAL_INSECTOS_MADERA.pdf",
]

# Configura el encabezado User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
}

for url in pdf_urls:
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        pdf_filename = url.split("/")[-1] 
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
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }

        collection.insert_one(data)

        print(f"Texto extraído y guardado en MongoDB desde {txt_filename}. ObjectId: {object_id}")
    else:
        print(f"Error al descargar el PDF {url}: {response.status_code}")
