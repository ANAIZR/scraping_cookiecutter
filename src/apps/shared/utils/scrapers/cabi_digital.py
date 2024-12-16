from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
import os
import time
import pickle
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
)
from rest_framework.response import Response
from rest_framework import status
from selenium.webdriver.chrome.options import Options


def scraper_cabi_digital(url, sobrenombre):
    options = Options()
    options.add_argument("--headless")
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(60)
    driver.get(url)

    time.sleep(5)

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    output_dir = os.path.expanduser("~/")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_folder_path = generate_directory(output_dir, url)

    data_collected = []  # Lista para almacenar los datos recolectados

    try:
        with open("cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()
    except FileNotFoundError:
        print("No se encontraron cookies guardadas.")

    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-pc-btn-handler"))
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

    while True:
        try:
            search_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "div.page-top-banner div.container div.quick-search button.quick-search__button",
                    )
                )
            )
            search_button.click()
        except Exception as e:
            print(f"Error al realizar la búsqueda: {e}")

        try:
            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.row > div.col-sm-8 form#frmIssueItems > ul.rlist",
                    )
                )
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("ul.rlist li")

            for item in items:
                content_div = item.find("div", class_="issue-item__content")
                if content_div:
                    first_link = content_div.find("a")
                    if first_link:
                        href = first_link.get("href")
                        if href:

                            full_url = (
                                href
                                if href.startswith("http")
                                else f"https://www.cabidigitallibrary.org{href}"
                            )
                            folder_path = generate_directory(base_folder_path, href)

                            driver.get(full_url)
                            time.sleep(5)

                            try:
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "article div#abstracts section#abstract",
                                        )
                                    )
                                )
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "article section#bodymatter div.core-container",
                                        )
                                    )
                                )
                                page_soup = BeautifulSoup(
                                    driver.page_source, "html.parser"
                                )
                                abstracts = page_soup.select_one(
                                    "article div#abstracts section#abstract"
                                )
                                body = page_soup.select_one(
                                    "article section#bodymatter div.core-container"
                                )

                                abstract_text = (
                                    abstracts.get_text(strip=True)
                                    if abstracts
                                    else "No abstract found"
                                )
                                body_text = (
                                    body.get_text(strip=True)
                                    if body
                                    else "No body found"
                                )
                                if abstract_text and body_text:
                                    contenido = f"{abstract_text}\n\n\n{body_text}"
                                    file_path = get_next_versioned_filename(
                                        folder_path, base_name=sobrenombre
                                    )
                                    with open(file_path, "w", encoding="utf-8") as file:
                                        file.write(contenido)

                                    with open(file_path, "rb") as file_data:
                                        object_id = fs.put(
                                            file_data,
                                            filename=os.path.basename(file_path),
                                        )
                                    data = {
                                        "Objeto": object_id,
                                        "Tipo": "Web",
                                        "Url": full_url,
                                        "Fecha_scrapper": datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                        "Etiquetas": ["planta", "plaga"],
                                    }
                                    collection = db["collection"]
                                    collection.insert_one(data)
                                    delete_old_documents(full_url, collection, fs)

                                    data_collected.append(
                                        {
                                            "Url": full_url,
                                            "Fecha_scrapper": data["Fecha_scrapper"],
                                            "Etiquetas": data["Etiquetas"],
                                        }
                                    )

                            except Exception as e:
                                print(
                                    f"Error al esperar el contenido de la nueva página: {e}"
                                )
            try:
                driver.get(url)
                time.sleep(3)

                search_button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "div.page-top-banner div.container div.quick-search button.quick-search__button",
                        )
                    )
                )
                search_button.click()
            except Exception as e:
                print(
                    f"Error al hacer clic en el botón de búsqueda para la siguiente página: {e}"
                )
            try:
                next_page_button = driver.find_element(
                    By.CSS_SELECTOR, "nav.pagination span a"
                )
                next_page_link = next_page_button.get_attribute("href")
                if next_page_link:
                    driver.get(next_page_link)
                    time.sleep(3)
                else:
                    break
            except Exception:
                break

        except Exception as e:
            break

    driver.quit()

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
