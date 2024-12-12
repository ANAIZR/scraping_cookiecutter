from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import gridfs
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def scrape_delta(url, sobrenombre):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Ejecuta en modo sin ventana si lo necesitas
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scrapped = []

    try:
        # Accede a la URL principal
        driver.get(url)
        time.sleep(2)  # Espera para que se cargue la página

        # Encuentra los <p> que contienen <a> con href="../"
        primary_links = driver.find_elements(
            By.XPATH, "//p/a[starts-with(@href, '../')]"
        )
        print("Se encontraron los siguientes links:")
        print(f"{len(primary_links)} links encontrados")
        for link in primary_links:
            href = link.get_attribute("href")
            if href:
                print(f"Accediendo a: {href}")
                driver.get(href)
                time.sleep(2)  # Espera para que se cargue la página

                # Dentro de esta página, encuentra <p> con <a> cuyo href inicie con "www"
                secondary_links = driver.find_elements(
                    By.XPATH, "//p/a[starts-with(@href, 'www')]"
                )

                for secondary_link in secondary_links:
                    secondary_href = secondary_link.get_attribute("href")
                    if secondary_href:
                        print(f"Scrapeando contenido de: {secondary_href}")
                        driver.get(secondary_href)
                        time.sleep(2)  # Espera para que cargue la página

                        # Extrae contenido, por ejemplo, todo el texto de la página
                        page_content = driver.find_element(By.TAG_NAME, "body").text
                        all_scrapped.append(
                            {"url": secondary_href, "content": page_content}
                        )

                        # Regresa a la página principal para continuar iterando
                        print("Regresand a la lista")
                        driver.back()
                        time.sleep(5)

                print("Termin de iterar en la lista")
                # Regresa a la página inicial para continuar iterando

                driver.back()

        # Guarda los datos en MongoDB si hay algo scrapeado
        if all_scrapped:
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
