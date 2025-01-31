from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
from ..functions import process_scraper_data, initialize_driver, get_logger, load_keywords,connect_to_mongo

def scraper_sciencedirect(url, sobrenombre):
    logger = get_logger("scraper")
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    def scrape_pages(driver, keywords):
        all_scraper = ""
        
        cont_keyword = 0
        for keyword in keywords:
            cont_keyword += 1
            try:
                # Ingresar la palabra clave en el input con id 'qs'
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "qs"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                search_input.submit()
                time.sleep(random.uniform(3, 6))
                
                # Esperar a que aparezcan los resultados y obtener los hrefs
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "srp-results-list"))
                )
                results_list = driver.find_elements(By.CSS_SELECTOR, "#srp-results-list a")

                # Filtrar URLs 
                urls = [
                    result.get_attribute("href")
                    for result in results_list
                    if result.get_attribute("href") 
                        and result.get_attribute("href").lower().startswith("https://www.sciencedirect.com/science/article/pii")
                        and not result.get_attribute("href").lower().endswith(".pdf")
                ]

                print(f"cantidad de urls con la palabra clave {keyword} {cont_keyword}:  ", len(urls))
                print(f"urls encontradas:",urls)
                
                cont_url = 0
                for url in urls:
                    cont_url += 1
                    if cont_url > 2: break
                    print(f"URL {url}: {cont_url}")
                    driver.get(url)
                    time.sleep(random.uniform(3, 6))
                    
                    # Extraer el texto del div con id 'abstracts'
                    try:
                        abstract_text = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "abstracts"))
                        ).text
                        
                        all_scraper += f"{abstract_text}\n"
                    except Exception as e:
                        logger.error(f"Error extrayendo abstracts de {url}: {e}")
                        continue
                    
                    # Volver a la segunda página
                    driver.back()
                    print("volviendo a la segunda pagina")
                    time.sleep(random.uniform(3, 6))

                # print("all scrapper",all_scraper)
                
                # Volver a la primera página
                driver.back()
                print("volviendo a la primera pagina")
                time.sleep(random.uniform(3, 6))
            
            except Exception as e:
                logger.error(f"Error procesando la palabra clave {keyword} {cont_keyword}: {e}")
                continue
        
        # Procesar los datos extraídos
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response


    logger.info(f"Iniciando scraping en {url} con sobrenombre {sobrenombre}")
    
    driver = initialize_driver()
    keywords = load_keywords()  # Función para cargar palabras clave desde un archivo

    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        scrape_pages(driver, keywords)
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {e}")
    finally:
        driver.quit()
