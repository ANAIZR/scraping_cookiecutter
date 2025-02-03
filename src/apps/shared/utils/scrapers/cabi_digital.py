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
    load_keywords
)
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect
logger = get_logger("scraper")

def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver()
    
    try:
        if login_cabi_scienceconnect(driver):
            print("Login completado, continuando con el scraping...")
    except:
        logger.error("No se encontro el login")
    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        object_id = None
        try:

            collection, fs = connect_to_mongo()

            main_folder = generate_directory(sobrenombre)

            keywords = load_keywords("plants.txt")
            if not keywords:
                return Response(
                    {
                        "status": "error",
                        "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            visited_urls = set()
            scraping_failed = False
            base_domain = "https://www.cabidigitallibrary.org"
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
            logger.info(
                "El botón de 'Guardar preferencias' no apareció o no fue clicable."
            )

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
                time.sleep(random.uniform(3, 6))

                search_input.submit()
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                scraping_failed = True
                continue
            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            content_accumulated = ""
            while True:
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break
                    logger.info(f"Encontrados {len(items)} resultados.")
                    for item in items:
                        href = item.find("a")["href"]
                        if href.startswith("/doi/10.1079/cabicompendium"):
                            absolut_href = f"{base_domain}{href}"
                            driver.get(absolut_href)
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
                            if abstract_text or body_text:
                                content_accumulated += f"URL:{absolut_href} \nTexto: {abstract_text}\n\n\n{body_text}"
                                content_accumulated += "-" * 100 + "\n\n"

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
                            "No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave."
                        )
                        driver.get(url)
                        break  
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break
                    
            if content_accumulated:
                with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                    keyword_file.write(content_accumulated)

                with open(keyword_file_path, "rb") as file_data:
                    object_id = fs.put(
                        file_data,
                        filename=os.path.basename(keyword_file_path),
                        metadata={
                            "keyword": keyword,
                            "scraping_date": datetime.now(),
                        },
                    )
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

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
                "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }
            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": data["Fecha_scraper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

            collection.insert_one(data)
            delete_old_documents(url, collection, fs)

            return Response(
                {
                    "data": response_data,
                },
                status=status.HTTP_200_OK,
            )
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()