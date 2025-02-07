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
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
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
        response_data = []
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
            logger.info(f"Buscando con la palabra clave: {keyword}")
            content_accumulated = ""

            # Buscar el término
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
            except Exception as e:
                logger.warning(f"Error al realizar la búsqueda para '{keyword}': {e}")
                continue

            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            while True:
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")

                    # Procesar resultados
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para '{keyword}'."
                        )
                        break

                    for item in items:
                        anchor = item.find("a")  # Verifica si existe el enlace
                        if (
                            anchor and "href" in anchor.attrs
                        ):  # Verifica si el atributo 'href' está presente
                            href = anchor["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolute_href = (
                                    f"https://www.cabidigitallibrary.org{href}"
                                )
                                driver.get(absolute_href)
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "body")
                                    )
                                )

                                soup = BeautifulSoup(driver.page_source, "html.parser")
                                abstract = soup.select_one("#abstracts")
                                body = soup.select_one("#bodymatter>.core-container")
                                abstract_text = (
                                    abstract.get_text(strip=True)
                                    if abstract
                                    else "No abstract found"
                                )
                                body_text = (
                                    body.get_text(strip=True)
                                    if body
                                    else "No body found"
                                )

                                if abstract_text or body_text:
                                    content_accumulated += f"URL: {absolute_href}\nAbstract: {abstract_text}\n\nBody: {body_text}\n{'-' * 100}\n\n"

                                driver.back()
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "ul.rlist li")
                                    )
                                )
                        else:
                            logger.warning(
                                f"No se encontró un enlace válido en el item: {item}"
                            )

                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR, ".pagination__btn--next"
                        )
                        if next_page_button:
                            driver.execute_script(
                                "arguments[0].click();", next_page_button
                            )
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

            if content_accumulated.strip():
                with open(keyword_file_path, "w", encoding="utf-8") as keyword_file:
                    keyword_file.write(content_accumulated)

                with open(keyword_file_path, "rb") as file_data:
                    object_id = fs.put(
                        file_data,
                        filename=os.path.basename(keyword_file_path),
                        metadata={
                            "keyword": keyword,
                            "scraping_date": datetime.now(),
                            "url": url,
                        },
                    )
                logger.info(
                    f"Archivo almacenado en MongoDB para '{keyword}' con ObjectId: {object_id}"
                )

                keyword_files = list(
                    fs.find({"metadata.keyword": keyword}).sort(
                        "metadata.scraping_date", -1
                    )
                )
                if len(keyword_files) > 2:
                    for file_to_delete in keyword_files[2:]:
                        fs.delete(file_to_delete["_id"])
                        logger.info(
                            f"Registro antiguo eliminado para '{keyword}' con ObjectId: {file_to_delete['_id']}"
                        )
                response_data.append(
                    {
                        "keyword": keyword,
                        "url": url,
                        "scraping_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "object_id": str(object_id),
                    }
                )
            collection.insert_one(
                {
                    "url": url,
                    "fecha_scraping": datetime.now(),
                    "keywords_procesados": len(keywords),
                    "detalles": response_data,
                }
            )

        if scraping_failed:
            return Response(
                {
                    "status": "warning",
                    "message": "Scraping completado con algunos errores.",
                    "data": response_data,
                },
                status=status.HTTP_207_MULTI_STATUS,
            )
        else:
            return Response(
                {
                    "message": "Scraping completado con éxito.",
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
