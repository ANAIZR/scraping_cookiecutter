from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
import os
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time

import os

import os

def scrape_ncbi(url, sobrenombre):
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scrapped = ""

    # Ruta relativa al archivo .txt desde el archivo .py
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Directorio actual de código.py
    txt_file_path = os.path.join(base_dir, "..", "txt", "fungi.txt")  # Subir 2 niveles y llegar a txt
    txt_file_path = os.path.normpath(txt_file_path)

    # Verificar si el archivo existe
    if not os.path.exists(txt_file_path):
        return Response({"error": f"El archivo {txt_file_path} no existe."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        driver.get(url)

        # Cargar los términos desde el archivo archivo.txt
        with open(txt_file_path, 'r') as file:
            search_terms = file.readlines()

        for term in search_terms:
            term = term.strip()  # Limpiar espacios en blanco
            if not term:
                continue  # Saltar si el término está vacío

            # Buscar el término en el campo de texto
            search_box = driver.find_element(By.ID, "searchtxt")
            search_box.clear()
            search_box.send_keys(term)

            # Enviar el formulario (simular el click en el botón de submit)
            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()

            # Esperar a que la página cargue
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Verificar si existe una tabla con width="100%"
            try:
                table = driver.find_element(By.XPATH, "//table[@width='100%']")
                # Extraer los datos de la tabla
                table_data = table.text
                if table_data.strip():  # Si la tabla tiene datos
                    all_scrapped += table_data + "\n"
            except:
                # Si no se encuentra la tabla, continuar con el siguiente término
                continue

        # Si se encontraron datos para scrapear, guardarlos
        if all_scrapped.strip():
            response_data = save_scraped_data(
                all_scrapped, url, sobrenombre, collection, fs
            )
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
