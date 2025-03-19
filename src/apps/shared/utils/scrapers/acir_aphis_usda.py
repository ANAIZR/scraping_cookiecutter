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
    load_keywords,
    extract_text_from_pdf
)
from rest_framework.response import Response
from rest_framework import status
logger = get_logger("scraper")

def scraper_acir_aphis_usda(url, sobrenombre):
    driver = initialize_driver()
    logger = get_logger("scraper")
    
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
        except Exception as e:
            logger.error(f"Error al inicializar el scraper: {str(e)}")

        for keyword in keywords:
            print(f"Buscando con la palabra clave: {keyword}")
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    driver.switch_to.frame(iframes[0])
                    logger.info("✅ Cambiado a iframe correctamente")
 
                # 🔥 Seleccionar el input correcto basándonos en la etiqueta `<label>`
                taxon_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Approved, Common, or Synonym of Accepted Scientific Name')]/following-sibling::div//input"))
                )
               
                taxon_input.clear()
                taxon_input.send_keys(keyword)
                print(f"✅ Se ingresó la palabra clave: {keyword}")
 
                try:
                    search_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')]"))
                    )
                except TimeoutException:
                    logger.warning("No se encontró el botón de búsqueda.")
                try:
 
                    search_button.click()
 
                except:
                    driver.execute_script("arguments[0].click();", search_button)
               
                time.sleep(random.uniform(3, 6))
     
            except Exception as e:
                scraping_failed = True
                logger.info(f"Error al realizar la búsqueda: {e}")

            keyword_folder = generate_directory(keyword, main_folder)
            keyword_file_path = get_next_versioned_filename(keyword_folder, keyword)

            content_accumulated = ""
            while True:
                try:

                    try:
                        # 1. Esperar a que la tabla esté presente (con Selenium)
                        html = WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Show Entries')]/ancestor::article//table[contains(@class,'slds-table_header-fixed') and contains(@class,'slds-table_bordered')]"))
                        )

                        # Acceder al tbody desde la tabla
                        tbody = html.find_element(By.TAG_NAME, "tbody")
                        
                        print("qumadev : solo body",tbody.text)
                        # Obtener todas las filas (tr) del tbody
                        filas = tbody.find_elements(By.TAG_NAME, "tr")

                        # Extraer el valor de data-row-key-value de cada fila
                        valores_row_key = [fila.get_attribute("data-row-key-value") for fila in filas]

                        print("qumadev: Valores encontrados:", valores_row_key)


                        # # Obtener todas las filas del tbody
                        # filas = tbody.find_elements(By.TAG_NAME, "tr")

                        print("qumadev : filas",filas)

                        # texto_tabla = html.text
                        # print("qumadev : antes de pintar")
                        # print(texto_tabla)
                        # print("qumadev : despues de pintar")

                        # 2. Obtener el HTML de la página y parsear con BeautifulSoup
                        soup = BeautifulSoup(driver.page_source, "html.parser")

                        # 3. Encontrar la tercera tabla (índice 2)
                        tablas = soup.select("table.slds-table.slds-table_header-fixed.slds-table_bordered")
                        tercera_tabla = tablas[2]  # Índice 2 para la tercera tabla

                        # 4. Acceder al tbody y a las filas (tr)
                        tbody = tercera_tabla.find("tbody")
                        filas = tbody.find_all("tr")

                    except Exception as e:
                        logger.warning(f"No se encontraron resultados en la página: {e}")
                        filas = []

                    if filas:
                        # 5. Iterar sobre las filas
                        body_text = ""
                        for fila in filas:
                            tds = fila.find_all("td")
                            for td in tds:
                                body_text += f"{td.get_text(separator=' ', strip=True)};"
                            body_text += "\n"



                        if body_text:
                            content_accumulated += f"keyword:{keyword} \n\n\n{body_text}"
                            content_accumulated += "-" * 100 + "\n\n"

                            print(f"Página procesada y guardada: {keyword}")
                            print(f"info guardada: {body_text}")
                        else:
                            print("No se encontró contenido en la página.")
                        driver.back()
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table.slds-table"))
                        )
                        time.sleep(random.uniform(3, 6))
                    else:
                        logger.info(f"Item no existen {len(filas)} resultados.")
                        driver.get(url)
                        time.sleep(random.uniform(3, 6))

                    try:
                        logger.info("Buscando botón para la siguiente página.")
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            "doaj-pager-next.doaj-pager-next-bottom-pager",
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
                            "url": url,
                            "keyword": keyword,
                            "content": content_accumulated,
                            "scraping_date": datetime.now(),
                            "Etiquetas": ["planta", "plaga"],
                        },
                    )
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(
                    collection.find({
                        "metadata.keyword": keyword,
                        "metadata.url": url  
                    }).sort("metadata.scraping_date", -1)
                )

                if len(existing_versions) > 2:
                    oldest_version = existing_versions[-1]  
                    fs.delete(oldest_version["_id"])  
                    collection.delete_one({"_id": oldest_version["_id"]}) 
                    logger.info(
                        f"Se eliminó la versión más antigua de '{keyword}' con URL '{url}' y object_id: {oldest_version['_id']}"
                    )


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
        logger.info("Navegador cerrado")
