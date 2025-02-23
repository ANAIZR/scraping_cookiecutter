from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
import random
from datetime import datetime
from bson import ObjectId
from urllib.parse import urljoin

def scraper_ala_org(url, sobrenombre):
    logger = get_logger("ALA_ORG")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    total_links_found = 0
    total_scraped_successfully = 0
    total_failed_scrapes = 0
    all_scraper = ""
    scraped_urls = []

    try:
        driver.get(url)
        logger.info("Página cargada correctamente.")

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
        
        object_ids = []
        failed_urls = []

        while True:
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#search-results-list li.search-result"))
                )

                lis = driver.find_elements(By.CSS_SELECTOR, "#search-results-list li.search-result")
                
                if not lis:
                    logger.warning("No se encontraron resultados en la búsqueda.")
                    break  
                total_links_found += len(lis)

                for li in lis:
                    try:
                        a_tag = li.find_element(By.CSS_SELECTOR, "a")
                        href = a_tag.get_attribute("href")
                        
                        if href:
                            href = urljoin(url, href)  
                            scraped_urls.append(href)
                            logger.info(f"Accediendo a {href}")

                            try:
                                driver.execute_script("arguments[0].click();", a_tag) 
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "section.container-fluid"))
                                )
                                time.sleep(random.randint(2, 4))
                            except Exception as e:
                                logger.warning(f"No se pudo hacer clic en {href}: {e}")
                                total_failed_scrapes += 1
                                failed_urls.append(href)
                                continue  

                            try:
                                content = driver.find_element(By.CSS_SELECTOR, "section.container-fluid")
                                if content:
                                    content_text = content.text.strip()
                                    
                                    object_id = fs.put(
                                        content_text.encode("utf-8"),
                                        source_url=href,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["planta", "plaga"],
                                        contenido=content_text,
                                        url=url
                                    )
                                    object_ids.append(object_id)
                                    total_scraped_successfully += 1

                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                    existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(oldest_version._id)  
                                        logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")

                                    
                            except Exception as e:
                                logger.warning(f"No se pudo extraer contenido de {href}: {e}")
                                total_failed_scrapes += 1
                                failed_urls.append(href)

                            try:
                                driver.back()
                                time.sleep(random.randint(2, 4))
                            except Exception as e:
                                logger.warning(f"No se pudo regresar a la página de resultados, recargando URL: {url}")
                                driver.get(url)
                                time.sleep(random.randint(2, 4))

                    except Exception as e:
                        logger.warning(f"Error al procesar un resultado de búsqueda: {e}")
                        total_failed_scrapes += 1

                """try:
                    next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                    next_page_url = next_page_btn.get_attribute("href")
                    if next_page_url:
                        logger.info(f"Navegando a la siguiente página: {next_page_url}")
                        driver.get(next_page_url)
                        time.sleep(3)
                    else:
                        logger.info("No hay más páginas de resultados.")
                        break
                except Exception as e:
                    logger.warning("No se encontró el botón de siguiente página, terminando el scraping.")
                    break"""
                
                max_pages = 3  # Número máximo de páginas a navegar
                page_count = 0  # Contador de páginas navegadas

                while page_count < max_pages:
                    try:
                        next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                        next_page_url = next_page_btn.get_attribute("href")

                        if next_page_url:
                            logger.info(f"Navegando a la página {page_count + 1}/{max_pages}: {next_page_url}")
                            driver.get(next_page_url)
                            time.sleep(3)  # Espera para que la página cargue completamente
                            page_count += 1  # Incrementa el contador
                        else:
                            logger.info("No hay más páginas de resultados.")
                            break
                    except Exception as e:
                        logger.warning("No se encontró el botón de siguiente página, terminando el scraping.")
                        break

                logger.info("Se alcanzó el límite de navegación o no hay más páginas.")


            except Exception as e:
                logger.error(f"Error al cargar los resultados: {e}")
                break
        
        if total_scraped_successfully == 0:
            return {"error": "No se pudieron scrapeear datos correctamente."}
        
        all_scraper += f"Total enlaces encontrados: {total_links_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_scraped_successfully}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {total_failed_scrapes}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        logger.info("Navegador cerrado.")