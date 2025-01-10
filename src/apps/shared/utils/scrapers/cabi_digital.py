from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
import os
import time
import pickle
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status


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


data_collected = []


def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver()
    try:
        driver.get(url)
        time.sleep(5)

        # Configuración de MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["scrapping-can"]
        collection = db["collection"]
        fs = gridfs.GridFS(db)

        # Directorio base
        output_dir = "c:/web_scraper_files"
        os.makedirs(output_dir, exist_ok=True)
        base_folder_path = generate_directory(output_dir, url)

        # Cargar palabras clave
        keywords = load_keywords()

        # Cargar cookies si existen
        try:
            with open("cookies.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
        except FileNotFoundError:
            print("No se encontraron cookies guardadas.")

        # Aceptar cookies
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

        # Procesar palabras clave
        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            try:
                search_input = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800",
                        )
                    )
                )
                search_input.clear()
                search_input.send_keys(keyword)
                search_input.submit()
                print(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                print(f"Error al realizar la búsqueda: {e}")
                continue

            # Iterar sobre páginas de resultados
            while True:
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    print("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    print(f"Encontrados {len(items)} resultados.")
                    for item in items:
                        href = item.find("a")["href"]
                        if href.startswith("/doi/10.1079/cabicompendium"):
                            absolut_href = f"https://www.cabidigitallibrary.org{href}"
                            process_page(
                                driver,
                                absolut_href,
                                base_folder_path,
                                sobrenombre,
                                fs,
                                collection,
                            )

                    try:
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
                        print("No se encontró el botón para la siguiente página.")
                        break
                except Exception as e:
                    print(f"Error al procesar resultados: {e}")
                    break
    finally:
        driver.quit()  # Aquí se asegura cerrar el navegador


def process_page(driver, url, base_folder_path, sobrenombre, fs, collection):
    try:
        driver.get(url)
        folder_path = generate_directory(base_folder_path, url)
        time.sleep(5)

        # Esperar que carguen los contenidos
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#abstracts"))
        )
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#bodymatter>.core-container")
            )
        )

        # Extraer contenido
        soup = BeautifulSoup(driver.page_source, "html.parser")
        abstracts = soup.select_one("#abstracts")
        body = soup.select_one("#bodymatter>.core-container")

        abstract_text = (
            abstracts.get_text(strip=True) if abstracts else "No abstract found"
        )
        body_text = body.get_text(strip=True) if body else "No body found"

        if abstract_text and body_text:
            contenido = f"{abstract_text}\n\n\n{body_text}"
            file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(contenido)

            with open(file_path, "rb") as file_data:
                object_id = fs.put(file_data, filename=os.path.basename(file_path))

            # Guardar en MongoDB
            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
            print(f"Página procesada y guardada: {url}")
            data_collected.append(
                {
                    "Url": url,
                    "Fecha_scrapper": data["Fecha_scrapper"],
                    "Etiquetas": data["Etiquetas"],
                }
            )
        driver.back()
    except Exception as e:
        print(f"Error al procesar la página {url}: {e}")

    if data_collected:
        return Response(
            {
                "message": "Escrapeo realizado con éxito",
                "data": data_collected,
            },
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"message": "No se generaron datos. Volver a realizar el scraping"},
            status=status.HTTP_400_BAD_REQUEST,
        )
