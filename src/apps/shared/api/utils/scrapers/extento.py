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


def scrape_extento(url, sobrenombre):
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")  # Ejecutar en segundo plano (sin interfaz gráfica)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scrapped = ""  # Variable para almacenar los enlaces que se vayan a scrapear

    try:
        # Cargar la página inicial
        driver.get(url)

        # Esperar a que se carguen las tablas
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))

        # Acceder al segundo <table> y luego al segundo <tr>
        tables = driver.find_elements(By.TAG_NAME, "table")
        if len(tables) >= 2:
            second_table = tables[1]  # Acceder al segundo <table>
            rows = second_table.find_elements(By.TAG_NAME, "tr")

            if len(rows) >= 2:
                second_row = rows[1]  # Acceder al segundo <tr>
                tds = second_row.find_elements(By.TAG_NAME, "td")

                # Buscar todos los enlaces <a> dentro de los <td>
                for td in tds:
                    links = td.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href:
                            print(f"Enlace encontrado: {href}")
                            driver.get(href)

                            # Esperar a que se carguen las tablas en la nueva página
                            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))

                            # Acceder al tercer <table> de la nueva página
                            new_tables = driver.find_elements(By.TAG_NAME, "table")
                            if len(new_tables) >= 3:
                                third_table = new_tables[2]
                                new_rows = third_table.find_elements(By.TAG_NAME, "tr")

                                # Buscar <td> que contengan enlaces <a href>
                                for new_row in new_rows:
                                    new_tds = new_row.find_elements(By.TAG_NAME, "td")

                                    for new_td in new_tds:
                                        new_links = new_td.find_elements(By.TAG_NAME, "a")
                                        for new_link in new_links:
                                            new_href = new_link.get_attribute("href")
                                            if new_href:
                                                print(f"Enlace encontrado en tercera tabla: {new_href}")
                                                driver.get(new_href)

                                                # Esperar a que cargue el contenido del body
                                                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

                                                # Extraer el contenido del body
                                                body_content = driver.find_element(By.TAG_NAME, "body").text
                                                all_scrapped += f"{new_href}\n{body_content[:500]}\n"  # Guardamos el enlace y el inicio del contenido
                                            driver.back()
                                            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))
                            driver.back()
                            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))


        # Si encontramos enlaces, guardamos los datos
        if all_scrapped.strip():
            response_data = save_scraped_data(all_scrapped, url, sobrenombre, collection, fs)
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
