from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
import traceback
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_ala_org(url, sobrenombre):
    logger = get_logger("ALA_ORG")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""

    try:
        start_time = time.time() 

        driver.get(url)
        logger.info(" Página cargada correctamente.")

        page_number = 1 
        total_links = 0  

        try:
            button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            driver.execute_script("arguments[0].click();", button)
            time.sleep(random.randint(1, 3))
            logger.info("Clic en el botón de búsqueda exitoso.")
        except Exception as e:
            logger.error(f"No se pudo hacer clic en el botón de búsqueda: {e}")
            return {"error": "No se encontró el botón de búsqueda"}

        while True:
            logger.info(f" Procesando página {page_number} de resultados...")

            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ol li.search-result"))
                )

                lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")

                if not lis:
                    logger.warning("No se encontraron resultados en la búsqueda.")
                    break 

                logger.info(f"Se encontraron {len(lis)} resultados en la página {page_number}.")

                for index, li in enumerate(lis, start=1):
                    try:
                        a_tag = li.find_element(By.CSS_SELECTOR, "a")
                        href = a_tag.get_attribute("href")

                        if not href:
                            logger.warning(f"El resultado {index} no tiene enlace. Omitiendo...")
                            continue

                        if href.startswith("/"):
                            href = url + href[1:]

                        logger.info(f"Accediendo a {href}")

                        total_links += 1  

                        try:
                            ActionChains(driver).move_to_element(a_tag).click().perform()
                            WebDriverWait(driver, 30).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "section.container-fluid"))
                            )
                            logger.info(f"Página de detalles cargada: {href}")
                        except Exception as e:
                            logger.warning(f"No se pudo hacer clic en {href}: {e}")
                            continue  

                        try:
                            content = driver.find_element(By.CSS_SELECTOR, "section.container-fluid")
                            if content.text.strip():
                                all_scraper += f"URL: {href}\n{content.text.strip()}\n\n"
                                logger.info(f"Contenido extraído de {href}.")
                            else:
                                logger.warning(f"Página {href} no tiene contenido útil.")
                        except Exception as e:
                            logger.warning(f"No se pudo extraer contenido de {href}: {e}")

                        try:
                            driver.back()
                            time.sleep(random.randint(2, 4))
                            logger.info(f"Regresando a la página {page_number} de resultados.")
                        except Exception as e:
                            logger.warning(f"No se pudo regresar a la página de resultados, recargando URL: {url}")
                            driver.get(url)
                            time.sleep(random.randint(2, 4))

                    except Exception as e:
                        logger.warning(f"Error al procesar un resultado de búsqueda: {e}")
                        logger.error(traceback.format_exc())
                        continue

                try:
                    next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                    next_page_url = next_page_btn.get_attribute("href")

                    if next_page_url:
                        logger.info(f"➡ Navegando a la siguiente página: {next_page_url}")
                        driver.get(next_page_url)
                        time.sleep(3)
                        page_number += 1  # Incrementar contador de páginas procesadas
                    else:
                        logger.info("No hay más páginas de resultados.")
                        break
                except Exception as e:
                    logger.warning("No se encontró el botón de siguiente página, terminando el scraping.")
                    break

            except Exception as e:
                logger.error(f"Error al cargar los resultados: {e}")
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.info("Se guardó el HTML de la página con error como 'error_page.html'.")
                break

        if not all_scraper.strip():
            logger.warning(f"No se encontraron datos para scrapear en la URL: {url}")
            return {"status": "no_content", "url": url, "message": "No se encontraron datos para scrapear."}

        end_time = time.time()  
        elapsed_time = round(end_time - start_time, 2)
        logger.info(f"Scraping completado en {elapsed_time} segundos.")
        logger.info(f"Total de páginas procesadas: {page_number}")
        logger.info(f"Total de enlaces procesados: {total_links}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
