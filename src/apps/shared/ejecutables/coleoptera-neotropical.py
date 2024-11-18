import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

client = MongoClient('mongodb://localhost:27017/')
db = client['scrapping-can']
collection = db['collection']
fs = gridfs.GridFS(db)

url = 'http://coleoptera-neotropical.org/8b-colecc-JEBC/JEBC/5-Buprestidae.htm'

try:
    response = requests.get(url)
    response.raise_for_status()  

    soup = BeautifulSoup(response.content, 'html.parser')

    tbody = soup.find('tbody')
    if tbody:
        text_content = tbody.get_text(separator='\n', strip=True)
    else:
        text_content = "No se encontró ningún <tbody> en la página."
        print(text_content)

    existing_doc = collection.find_one({"Url": url})

    if existing_doc:
        print(f"Ya existe un documento para esta URL con ObjectId: {existing_doc['Objeto']}")
    else:
        file_name = os.path.join(output_dir, 'tbody_content.txt')
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(text_content)

        with open(file_name, 'rb') as file_data:
            object_id = fs.put(file_data, filename=file_name)

        data = {
            'Objeto': object_id,
            'Tipo': 'Web',
            'Url': url,
            'Fecha_scrapper': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Etiquetas': ['tabla', 'tbody'],
        }
        collection.insert_one(data)

        print(f"Los datos se han guardado en MongoDB y el contenido se ha escrito en el archivo. ObjectId: {object_id}")

except requests.RequestException as e:
    print(f"Error al realizar la solicitud HTTP: {e}")

except Exception as e:
    print(f'Ocurrió un error: {e}')
