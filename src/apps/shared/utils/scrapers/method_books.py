from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_text_from_image,
    save_scraper_data_adrian
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
import traceback


def scraper_method_books(url, sobrenombre):
    try:
        driver = initialize_driver()
        driver.get(
            url
        )  # acceder a la URL

        # input_busqueda = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='search_query']"))
        # )
        # input_busqueda.send_keys("sws")
        # # Esperar a que el botón esté presente en el DOM y sea clickeable
        boton = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.gbe:nth-child(5) > .gbmt"))
        )
        # # Hacer clic en el botón
        boton.click()
        # print("Se hizo clic en el botón de búsqueda.")

        # descargar_pdf_button = driver.find_element(By.CSS_SELECTOR, "a.gbmt.goog-menuitem-content")

        # descargar_pdf_button.click()
    # Esperar a que el enlace "Descargar PDF" esté presente 
        # descargar_pdf_link = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.LINK_TEXT, "Descargar PDF")) 
        # )

        # # Hacer clic en el enlace "Descargar PDF"
        # descargar_pdf_link.click()
        print("Se hizo clic en el botón 'Descargar PDF'.")
        time.sleep(10000)    
        return Response({"message": "Scraper finalizado"}, status=status.HTTP_200_OK)

        # all_scraper = get_text_from_image(url)
        # collection, fs = connect_to_mongo("scrapping-can", "collection")
        # save_scraper_data_adrian(all_scraper, url, sobrenombre, collection, fs)
        print("adrian terminado")
        
    except:
        print("Error al scrapear libros escaneados")
