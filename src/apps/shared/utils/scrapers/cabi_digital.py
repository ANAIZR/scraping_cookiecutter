from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import pickle
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    get_logger,
    connect_to_mongo,
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
        logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.info(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise


def scraper_cabi_digital(url, sobrenombre):
    try:
        driver = initialize_driver()
        try:
            driver.get(url)
            time.sleep(random.uniform(6, 10))

            collection, fs = connect_to_mongo("scrapping-can", "collection")

            main_folder = generate_directory(url)

            keywords = load_keywords()
            visited_urls = set()
            scraping_failed = False
            base_domain = "https://www.cabidigitallibrary.org/"
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        try:
            with open("cookies.pkl", "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
        except FileNotFoundError:
            logger.info("No se encontraron cookies guardadas.")

        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#onetrust-pc-btn-handler")
                )
            )
            cookie_button.click()
        except Exception:
            logger.info("El botón de 'Aceptar Cookies' no apareció o no fue clicable.")
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
            keyword_folder = generate_directory(keyword, main_folder)
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
                time.sleep(random.uniform(3, 6))

                search_input.submit()
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                scraping_failed = True
                continue

            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    logger.info(f"Encontrados {len(items)} resultados.")
                    for item in items:
                        href = item.find("a")["href"]
                        if href.startswith("/doi/10.1079/cabicompendium"):
                            absolut_href = f"{base_domain}{href}"
                            driver.get(absolut_href)
                            try:
                                cookie_button = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable(
                                        (By.CSS_SELECTOR, "#onetrust-pc-btn-handler")
                                    )
                                )
                                cookie_button.click()
                            except Exception:
                                logger.info(
                                    "El botón de 'Aceptar Cookies' no apareció o no fue clicable."
                                )
                            try:
                                preferences_button = WebDriverWait(driver, 5).until(
                                    EC.element_to_be_clickable(
                                        (
                                            By.CSS_SELECTOR,
                                            "#accept-recommended-btn-handler",
                                        )
                                    )
                                )
                                preferences_button.click()
                            except Exception:
                                logger.info(
                                    "El botón de 'Guardar preferencias' no apareció o no fue clicable."
                                )
                            visited_urls.add(absolut_href)
                            WebDriverWait(driver, 60).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "body")
                                )
                            )

                            time.sleep(random.uniform(6, 10))
                            soup = BeautifulSoup(driver.page_source, "html.parser")
                            abstracts = soup.select_one("#abstracts")
                            body = soup.select_one("#bodymatter>.core-container")
                            abstract_text = (
                                abstracts.get_text(strip=True)
                                if abstracts
                                else "No abstract found"
                            )
                            body_text = (
                                body.get_text(strip=True) if body else "No body found"
                            )
                            if abstract_text and body_text:
                                contenido = f"{abstract_text}\n\n\n{body_text}"
                                link_folder = generate_directory(href, keyword_folder)
                                file_path = get_next_versioned_filename(
                                    link_folder, keyword
                                )
                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(contenido)

                                with open(file_path, "rb") as file_data:
                                    object_id = fs.put(
                                        file_data, filename=os.path.basename(file_path)
                                    )

                                print(f"Página procesada y guardada: {absolut_href}")
                            else:
                                print("No se encontró contenido en la página.")
                            driver.back()
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, "ul.rlist li")
                                )
                            )
                            time.sleep(random.uniform(3, 6))

                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            ".pagination__btn.pagination__btn--next.icon-arrow_r",
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(
                                f"Yendo a la siguiente página: {next_page_link}"
                            )
                            driver.get(next_page_link)
                        else:
                            logger.info(
                                "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                            )
                            break
                    except NoSuchElementException:
                        logger.info(
                            "No se encontró el botón para la siguiente página. Volviendo al inicio para la próxima palabra clave."
                        )
                        driver.get(url)  # Volver al inicio
                        time.sleep(
                            random.uniform(6, 10)
                        )  # Pausa antes de interactuar de nuevo

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
                            logger.info(
                                f"Preparado para la próxima palabra clave: {keyword}"
                            )
                        except TimeoutException:
                            logger.error(
                                f"No se pudo encontrar el campo de búsqueda al regresar al inicio."
                            )
                            break
                        except Exception as e:
                            logger.error(
                                f"Error inesperado al intentar reiniciar la búsqueda: {str(e)}"
                            )
                            break
                    except Exception as e:
                        logger.error(
                            f"Error inesperado al intentar navegar a la siguiente página: {str(e)}"
                        )
                        break

                except Exception as e:
                    logger.error(f"Error al procesar resultados: {e}")
                    scraping_failed = True
                    break

        if scraping_failed:
            return Response(
                {
                    "message": "Error durante el scraping. Algunas URLs fallaron.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            collection.insert_one(data)
            delete_old_documents(url, collection, fs)
            response = Response(data, status=status.HTTP_200_OK)
            return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {str(e)}")
        return {"status": "error", "message": f"Error durante el scraping: {str(e)}"}
    finally:
        driver.quit()
