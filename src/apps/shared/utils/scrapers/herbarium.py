from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
import os
import random
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException
)
from datetime import datetime
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    load_keywords,
    delete_old_documents,
)

logger = get_logger("scraper")

def scraper_herbarium(url, sobrenombre):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)

        link_list = driver.find_elements(By.CSS_SELECTOR, "#nav ul li a")
        logger.info(f"Cantidad de links encontrados: {len(link_list)}")

        main_folder = generate_directory(sobrenombre)
        index = 1

        for link in link_list:
            try:
                if index == 3:
                    break

                logger.info(f"Procesando página # {index}")
                href = link.get_attribute("href")
                secondary_window = driver.current_window_handle

                sub_folder = os.path.join(main_folder, str(href.split("/")[-1]))
                os.makedirs(sub_folder, exist_ok=True)

                driver.get(href)

                keywords = load_keywords("family.txt")
                cont = 1

                if index == 1:
                    for keyword in keywords:
                        if keyword:
                            logger.info(f"Buscando con la palabra clave {cont}: {keyword}")
                            try:
                                search_input = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='family']"))
                                )
                                search_input.clear()
                                search_input.send_keys(keyword)
                                time.sleep(random.uniform(2, 4))

                                search_input.submit()

                                driver.execute_script("window.open(arguments[0]);", href)
                                new_window = driver.window_handles[1]
                                driver.switch_to.window(new_window)
                                time.sleep(random.uniform(2, 4))

                                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                                items = page_soup.select("tbody tr")
                                logger.info(f"Items encontrados: {len(items)}")

                                keyword_folder = os.path.join(main_folder, "main.php", keyword)
                                os.makedirs(keyword_folder, exist_ok=True)

                                all_scraper = ""

                                for item in items:
                                    tds = item.find_all("td")
                                    for td in tds:
                                        all_scraper += f"{td.get_text(strip=True)};"
                                    all_scraper += "\n"

                                file_path = get_next_versioned_filename(keyword_folder, keyword)

                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(all_scraper)

                                cont += 1
                                driver.close()
                                driver.switch_to.window(secondary_window)
                                time.sleep(random.uniform(2, 4))

                            except Exception as e:
                                logger.info(f"Error al realizar la búsqueda: {e}")
                                continue

                    driver.back()
                    time.sleep(random.uniform(2, 4))

                elif index == 2:
                    logger.info("Procesando el segundo enlace")
                    sub_directory = "islands"

                    search_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='B1']"))
                    )
                    search_input.click()

                    page_soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = page_soup.select("tbody tr")
                    logger.info(f"Items encontrados: {len(items)}")

                    for item in items:
                        tds = item.find_all("td")
                        for td in tds:
                            all_scraper += f"{td.get_text(strip=True)};"
                        all_scraper += "\n"

                    file_path = get_next_versioned_filename(sub_folder, sub_directory)

                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(all_scraper)

                    time.sleep(random.uniform(2, 4))
                    driver.quit()

                index += 1

            except Exception as e:
                logger.error(f"Error al procesar el contenido: {e}")

        object_id = fs.put(all_scraper.encode("utf-8"), filename=sobrenombre)

        existing_versions = list(
            collection.find({
                "metadata.keyword": keyword,
                "metadata.url": url  
            }).sort("metadata.scraping_date", -1)
        )
        logger.info(f"Versiones encontradas para '{keyword}': {existing_versions}")

        if len(existing_versions) > 2:
            oldest_version = existing_versions[-1]  
            fs.delete(oldest_version["_id"])  
            collection.delete_one({"_id": oldest_version["_id"]}) 
            logger.info(
                f"Se eliminó la versión más antigua de '{keyword}' con URL '{url}' y object_id: {oldest_version['_id']}"
            )

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
        logger.info(f"DEBUG - Tipo de respuesta de save_scraper_data_pdf: {type(response_data)}")

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
        if driver:
            driver.quit()
            logger.info("Navegador cerrado")