from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time


from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_text_from_image
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
import traceback
import requests


def scraper_method_books(url, sobrenombre):
    try:
        driver = initialize_driver()
        driver.get(
            url
        )  # acceder a la URL

        boton = WebDriverWait(driver, 20).until( EC.presence_of_element_located((By.CSS_SELECTOR, "li.gbe:nth-child(5) > .gbmt")) )
        driver.execute_script("arguments[0].click();", boton)
        
        

        # href = WebDriverWait(driver, 20).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, "li.gbe.gbmtc:nth-child(5) a"))
        # )
        # link= href.get_attribute("href")
        # print("Pantalla de descarga: ", link)


        # response = requests.get(link)
        # print("Response: ", response)

        # nombre_archivo = "descarga.pdf"
        # ruta_directorio = "C:/Users/Usuario/Downloads"
        # ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
        # with open(ruta_completa, "wb") as file:
        #     file.write(response.content)
        # print(f"PDF descargado y guardado como '{nombre_archivo}'.")
        

        # descargar_pdf_button = driver.find_element(By.CSS_SELECTOR, "a.gbmt.goog-menuitem-content")

        # descargar_pdf_button.click()
    # Esperar a que el enlace "Descargar PDF" esté presente 
        # descargar_pdf_link = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.LINK_TEXT, "Descargar PDF")) 
        # )

        # # Hacer clic en el enlace "Descargar PDF"
        # descargar_pdf_link.click()
        # print("Se hizo clic en el botón 'Descargar PDF'.")
        

        # all_scraper = get_text_from_image(url)
        # collection, fs = connect_to_mongo("scrapping-can", "collection")
        # save_scraper_data_adrian(all_scraper, url, sobrenombre, collection, fs)
        # document.querySelector("pdf-viewer#viewer").shadowRoot.querySelector('viewer-toolbar#toolbar').shadowRoot.querySelector("viewer-download-controls#downloads").shadowRoot.querySelector('cr-icon-button#download');

        
        # Llama a la función
        # click_download_button_with_coordinates("URL_del_visor_PDF")

        return Response({"message": "Scraper finalizado y archivo descargado"}, status=status.HTTP_200_OK)
        
    except:
        print("Error al scrapear libros escaneados")
        print(traceback.format_exc())

        return Response({"message": "Scraper finalizado"}, status=status.HTTP_400_BAD_REQUEST)

