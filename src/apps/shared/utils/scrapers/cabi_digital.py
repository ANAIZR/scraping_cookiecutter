import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
from http.cookies import SimpleCookie
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")

def load_keywords(file_path="../txt/plants.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [
                line.strip() for line in f if isinstance(line, str) and line.strip()
            ]
        print(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        print(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver()
    driver.get(url)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    output_dir = "c:/web_scraper_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_folder_path = generate_directory(output_dir, url)

    keywords = load_keywords()
    all_hrefs = []  # Almacenar todos los hrefs recolectados

    try:
        # Manejo de cookies y preferencias
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#onetrust-pc-btn-handler")
                )
            )
            cookie_button.click()
        except Exception:
            print("El botón de 'Aceptar Cookies' no apareció o no fue clicable.")

        try:
            preferences_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#accept-recommended-btn-handler")
                )
            )
            preferences_button.click()
        except Exception:
            print("El botón de 'Guardar preferencias' no apareció o no fue clicable.")

        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            keyword_results_found = False
            try:
                try:
                    search_input = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "#AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800",
                            )
                        )
                    )
                except Exception as e:
                    print(
                        "No se encontró el primer elemento de búsqueda. Intentando con el segundo..."
                    )
                    search_input = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "#AllField357930a0-4458-47d0-9201-85b5725fa0ee0",
                            )
                        )
                    )

                search_input.clear()
                search_input.send_keys(keyword)
                search_input.submit()
                print(f"Buscando {keyword} en la página.")

            except Exception as e:
                print(
                    f"Error al realizar la búsqueda con la palabra clave {keyword}: {e}"
                )
                continue

            while True:
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "div.row > div.col-sm-8 form#frmIssueItems > ul.rlist",
                            )
                        )
                    )
                    print("Elemento encontrado en la página de resultados.")
                    keyword_results_found = True

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    for item in items:
                        try:
                            href = item.find("a")["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolut_href = (
                                    f"https://www.cabidigitallibrary.org{href}"
                                )
                                all_hrefs.append(absolut_href)

                        except (TypeError, KeyError):
                            print("No se encontró un enlace (<a>) válido.")

                    next_page_button = driver.find_element(
                        By.CSS_SELECTOR,
                        ".pagination__btn.pagination__btn--next.icon-arrow_r",
                    )
                    next_page_link = next_page_button.get_attribute("href")
                    if next_page_link:
                        print(f"Yendo a la siguiente página: {next_page_link}")
                        driver.get(next_page_link)
                    else:
                        break
                except Exception:
                    print("No se encontró más páginas de resultados.")
                    break
            if not keyword_results_found:
                print(f"No se encontraron resultados para la palabra clave: {keyword}")

    finally:
        driver.quit()

    data_collected = []
    for href in all_hrefs:
        print(f"Procesando href con requests: {href}")
        try:
            response = requests.get(href)
            if response.status_code == 403:
                print(f"Acceso bloqueado por cookies para {href}.")
                cookies = driver.get_cookies()
                session = requests.Session()
                for cookie in cookies:
                    session.cookies.set(cookie["name"], cookie["value"])

                response = session.get(href)
            if response.status_code == 200:
                page_soup = BeautifulSoup(response.text, "html.parser")
                abstracts = page_soup.select_one(
                    "article div#abstracts section#abstract"
                )
                body = page_soup.select_one(
                    "article section#bodymatter div.core-container"
                )

                abstract_text = (
                    abstracts.get_text(strip=True) if abstracts else "No abstract found"
                )
                body_text = body.get_text(strip=True) if body else "No body found"

                if abstract_text and body_text:
                    contenido = f"{abstract_text}\n\n\n{body_text}"
                    keyword_folder_path = os.path.join(base_folder_path, keyword)
                    if not os.path.exists(keyword_folder_path):
                        os.makedirs(keyword_folder_path)

                    folder_path = generate_directory(keyword_folder_path, href)
                    file_path = get_next_versioned_filename(
                        folder_path, base_name=sobrenombre
                    )
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(contenido)

                    with open(file_path, "rb") as file_data:
                        object_id = fs.put(
                            file_data, filename=os.path.basename(file_path)
                        )
                    data = {
                        "Objeto": object_id,
                        "Tipo": "Web",
                        "Url": href,
                        "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Etiquetas": ["planta", "plaga"],
                    }
                    collection.insert_one(data)
                    delete_old_documents(href, collection, fs)

                    data_collected.append(
                        {
                            "Url": href,
                            "Fecha_scrapper": data["Fecha_scrapper"],
                            "Etiquetas": data["Etiquetas"],
                        }
                    )
        except Exception as e:
            print(f"Error procesando {href}: {e}")

    if data_collected:
        return Response(
            {"message": "Escrapeo realizado con éxito", "data": data_collected},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"message": "No se generaron datos. Volver a realizar el scraping"},
            status=status.HTTP_400_BAD_REQUEST,
        )
