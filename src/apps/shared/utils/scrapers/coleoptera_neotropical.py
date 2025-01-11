from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import gridfs
import os
from rest_framework.response import Response
from rest_framework import status

from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    connect_to_mongo
)

def scraper_coleoptera_neotropical(url, sobrenombre):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
        
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    collection, fs = connect_to_mongo()

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "body tbody"))
        )
        content = driver.find_element(By.CSS_SELECTOR, "body tbody")

        rows = content.find_elements(By.TAG_NAME, "tr")
        total_rows = len(rows)

        all_scraper_data = []
        scrape_count = 0

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            row_data = [col.text.strip() for col in cols]  
            all_scraper_data.append(row_data) 
            scrape_count += 1  

        scrape_info = f"Total de filas encontradas: {total_rows}\nFilas scrapeadas: {scrape_count}\n\n"

        scraped_text = scrape_info + "\n".join([", ".join(row) for row in all_scraper_data])

        folder_path = generate_directory(url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(scraped_text)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }

            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": data["Fecha_scrapper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)

            delete_old_documents(url, collection, fs)
        
        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
