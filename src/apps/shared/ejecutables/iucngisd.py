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

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

client = MongoClient('mongodb://localhost:27017/')
db = client['scrapping-can']  
collection = db['collection']
fs = gridfs.GridFS(db)  

driver.get('https://www.iucngisd.org/gisd/search.php')

try:
    search_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'go'))  
    )

    search_button.click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.content.spec"))  
    )

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)

    existing_doc = collection.find_one({"Url": 'http://www.iucngisd.org/gisd/'})

    if existing_doc:
        print(f"Ya existe un documento para esta URL con ObjectId: {existing_doc['Objeto']}")
    else:
        file_name = os.path.join(output_dir, 'iucngisd.txt')
        
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(text_content)
        
        with open(file_name, 'rb') as file_data:
            object_id = fs.put(file_data, filename=file_name)  

        data = {
            'Objeto': object_id,  
            'Tipo': 'Web', 
            'Url': 'http://www.iucngisd.org/gisd/', 
            'Fecha_scrapper': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  
            'Etiquetas': ['planta', 'plaga'], 
        }

        collection.insert_one(data)

        print(f"Los datos se han guardado en MongoDB y el contenido se ha escrito en el archivo. ObjectId: {object_id}")

except Exception as e:
    print(f'Ocurrió un error: {e}')

finally:
    # Cerrar el navegador
    driver.quit()