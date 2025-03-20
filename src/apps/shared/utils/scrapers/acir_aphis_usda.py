from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data
)
from rest_framework.response import Response
from rest_framework import status



def scraper_acir_aphis_usda(url, sobrenombre):
    logger = get_logger("scraper")
    non_scraped_urls = []
    scraped_urls = []    
    driver = initialize_driver()
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection") 
    urls_to_scrape = []


    def scrape_page(href):
        print("qumadev url a scrapear inicio")
        new_links = []

        try: # O el driver que estés utilizando
            driver.get(href)
            time.sleep(random.uniform(1, 3))
            # Esperar a que el contenido principal esté presente
            main_content = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.slds-col--padded.contentRegion.comm-layout-column"))
            )

            time.sleep(random.uniform(1, 3))
            if main_content:
                page_text = main_content.text
                print("contenido by qumadev", href, page_text)

            if page_text:
                object_id = fs.put(
                    page_text.encode("utf-8"),
                    source_url=href,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=page_text,
                    url=url
                )
                scraped_urls.append(href)
                logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    file_id = oldest_version._id  # Esto obtiene el ID correcto
                    fs.delete(file_id)  # Eliminar la versión más antigua
                    logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
            else:
                non_scraped_urls.append(href)

        except Exception as e:
            logger.error(f"Error al procesar el enlace {href}: {e}")
            non_scraped_urls.append(href)
        # finally:
        #     # Cerrar el navegador
        #     driver.quit()

        return new_links

    try:
        driver.get(url)
        time.sleep(random.uniform(6, 10))
        try:
            keywords = load_keywords("plants.txt")

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
                logger.info(f"Error al realizar la búsqueda: {e}")

            while True:
                try:

                    # 1. Esperar a que la tabla esté presente (con Selenium)
                    html = WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Show Entries')]/ancestor::article//table[contains(@class,'slds-table_header-fixed') and contains(@class,'slds-table_bordered')]"))
                    )

                    # Acceder al tbody desde la tabla
                    tbody = html.find_element(By.TAG_NAME, "tbody")
                    
                    # Obtener todas las filas (tr) del tbody
                    filas = tbody.find_elements(By.TAG_NAME, "tr")

                    # Extraer ambos valores
                    datos = []
                    for fila in filas:
                        row_key = fila.get_attribute("data-row-key-value")
                        th_text = fila.find_element(By.TAG_NAME, "th").text  # Texto del th
                        datos.append({
                            "data-row-key-value": row_key,
                            "th_text": th_text
                        })

                    for item in datos:
                        # Limpiar y formatear el th_text
                        slug = item['th_text'].lower().replace(' ', '-').replace('(', '').replace(')', '').strip()
                        
                        # Construir la URL
                        url = f"https://acir.aphis.usda.gov/s/cird-taxon/{item['data-row-key-value']}/{slug}"
                        print("qumadev URL generada:", url)
                        urls_to_scrape.append(url)

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

        if urls_to_scrape:
            logger.info(f"URLs restantes por procesar: {len(urls_to_scrape)}")

            for url in urls_to_scrape:
                time.sleep(random.uniform(1, 3))
                scrape_page(url)
                time.sleep(random.uniform(1, 3))

        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
    
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
