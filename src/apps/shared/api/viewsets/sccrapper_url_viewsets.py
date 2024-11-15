from django.http import JsonResponse
from rest_framework.decorators import api_view
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
from ...models.scraper import ScraperURL
@api_view(['POST'])
def run_scraper(request):
    # Recuperar la URL y los parámetros de configuración desde el modelo ScraperURL
    scraper_url = ScraperURL.objects.get(pk=request.data['pk'])  # Usamos la 'pk' enviada
    url = scraper_url.url
    parameters = scraper_url.parameters  # Aquí están los parámetros de configuración

    # Extraer parámetros del JSON almacenado
    search_button_selector = parameters.get('search_button_selector', '#go')
    content_selector = parameters.get('content_selector', 'ul.content.spec')
    wait_time = parameters.get('wait_time', 10)

    # Resto del código de scraping igual que antes
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    output_dir = r"C:\web_scraping_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Conexión a MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['scrapping-can']
    collection = db['collection']
    fs = gridfs.GridFS(db)

    try:
        driver.get(url)

        # Esperar y hacer clic en el botón según el selector pasado
        search_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
        )
        search_button.click()

        # Esperar a que el contenido se cargue
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, content_selector))
        )

        # Hacer scraping
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        text_content = soup.get_text(separator='\n', strip=True)

        # Guardar contenido en MongoDB si no existe
        existing_doc = collection.find_one({"Url": url})
        if not existing_doc:
            file_name = os.path.join(output_dir, 'scraped_content.txt')
            with open(file_name, 'w', encoding='utf-8') as file:
                file.write(text_content)

            with open(file_name, 'rb') as file_data:
                object_id = fs.put(file_data, filename=file_name)

            # Insertar información en la base de datos
            data = {
                'Objeto': object_id,
                'Tipo': 'Web',
                'Url': url,
                'Fecha_scrapper': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Etiquetas': ['planta', 'plaga'],
            }
            collection.insert_one(data)

            response_data = {'message': f"Scraping exitoso. Datos guardados en MongoDB. ObjectId: {object_id}"}
        else:
            response_data = {'message': f"Ya existe un documento para esta URL con ObjectId: {existing_doc['Objeto']}"}

    except Exception as e:
        response_data = {'error': str(e)}

    finally:
        driver.quit()

    return JsonResponse(response_data)
