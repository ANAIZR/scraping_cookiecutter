from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
import gridfs
from .functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status
import time


def close_modal(driver):
    try:
        close_button = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a.header-action.action-close")
            )
        )
        driver.execute_script("arguments[0].click();", close_button)

    except Exception as e:
        print(f"No se pudo cerrar el modal: {e}")


def scrape_mycobank_org(url, sobrenombre):
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)

    all_scrapped = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#search-btn"))
        )

        driver.execute_script("document.querySelector('#search-btn').click();")

        time.sleep(5)

        while True:
            WebDriverWait(driver, 60).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "table.mat-table tbody tr")
                )
            )
            time.sleep(5)
            rows = driver.find_elements(By.CSS_SELECTOR, "table.mat-table tbody tr")
            print(f"Encontradas {len(rows)} filas en la página actual.")

            for index, row in enumerate(rows, start=1):
                try:
                    time.sleep(5)
                    link = row.find_element(By.CSS_SELECTOR, "td a")
                    link_name = link.text.strip()
                    driver.execute_script("arguments[0].click();", link)

                    time.sleep(5)
                    popup_title = (
                        WebDriverWait(driver, 60)
                        .until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.mat-dialog-title")
                            )
                        )
                        .text
                    )

                    popup_content = (
                        WebDriverWait(driver, 60)
                        .until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.first-column")
                            )
                        )
                        .text
                    )

                    content = (
                        f"Title: {popup_title}\nContent:\n{popup_content}\n{'-'*50}\n"
                    )
                    all_scrapped += content

                    close_modal(driver)

                except Exception as e:
                    print(f"Error al procesar la fila {index}: {e}")
                    continue
            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label='Next page']"
                )

                driver.execute_script("arguments[0].click();", next_button)
                print("Siguiente pagina")
                time.sleep(5)

            except Exception as e:
                print("Error al intentar avanzar al siguiente paginador", e)
                break
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
        print(f"Ocurrió un error: {e}")
        return Response(
            {"error": "Ocurrió un error durante el scraping."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
