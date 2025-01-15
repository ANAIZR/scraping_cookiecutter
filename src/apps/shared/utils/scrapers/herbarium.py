from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
import time
import os
import random
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename
)
from selenium.common.exceptions import StaleElementReferenceException

logger = get_logger("scraper")

def load_keywords(file_path="../txt/family.txt"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(base_path, file_path)
        with open(absolute_path, "r", encoding="utf-8") as f:
            keywords = [
                line.strip() for line in f if isinstance(line, str) and line.strip()
            ]
        # logger.info(f"Palabras clave cargadas: {keywords}")
        return keywords
    except Exception as e:
        logger.info(f"Error al cargar palabras clave desde {file_path}: {str(e)}")
        raise

def scraper_herbarium(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()

    try:
        driver.get(url)

        link_list = driver.find_elements(
            By.CSS_SELECTOR, "#nav ul li a"
        )

        main_folder = generate_directory(url)
    
        while True:
            for link in link_list:
                href = link.get_attribute("href")

                processed_links.add(href)
                
                original_window = driver.current_window_handle

                try:
                    #abriendo enlaces principales(son 2)
                    driver.get(href)

                    keywords = load_keywords()
                    cont = 1

                    for keyword in keywords:
                        print("siguiente palabra clave ",keyword)
                        if(keyword):
                            print(f"Buscando con la palabra clave {cont}: {keyword}")
                            # keyword_folder = generate_directory(keyword, main_folder)
                            try:
                                search_input =  WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='family']"))
                                    )
                                search_input.clear()
                                search_input.send_keys(keyword)
                                time.sleep(random.uniform(2, 4))

                                search_input.submit()

                                #######################PAGINA A SCRAPEAR#######################

                                driver.execute_script("window.open(arguments[0]);", href)
                                new_window = driver.window_handles[1]
                                driver.switch_to.window(new_window)

                                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                                items = page_soup.select("tbody tr")
                                print("pintando items ",len(items))
                            

                                for item in items:
                                    tds = item.find_all("td")
                                    print("pintando tds ",len(tds))
                                    for td in tds:
                                        all_scraper += f"{td.get_text(strip=True)};"
                                    all_scraper += "\n"
                                    logger.info("fila escrapeada por adrian ",all_scraper)

                                file_path = get_next_versioned_filename(
                                    main_folder, keyword
                                )

                                ##CREACION Y ESCRITURA DE ARCHIVO
                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(all_scraper)
                                
                                cont += 1
                                driver.close()
                                driver.switch_to.window(original_window)
                                print("volviendo a la pagina principal")

                                time.sleep(random.uniform(2, 4))

                                # content_div = page_soup.find("body")       
                                # content_text = content_div.text.strip()
                                # print('pintando el cuerpo de la tabla ',content_text)               
                                
                                # if(content_text == "Fairchild Tropical Botanic Garden Virtual Herbarium"):
                                #     print(f"No se encontraron resultados {cont}")
                                # else:
                                #     print("Felicidades, si se encontraron resultados")
                                #     driver.quit()

                                #################################################################

                                # time.sleep(random.uniform(3, 6))

                                # WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

                                # cont += 1
                                # driver.close()
                                
                                # driver.switch_to.window(original_window)

                                # logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
                                # time.sleep(random.uniform(10, 12))

                            except Exception as e:
                                logger.info(f"Error al realizar la búsqueda: {e}")
                                scraping_failed = True
                                continue


                except:
                    print("Error en el contenido")

    except Exception as e:
        print(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error al cerrar el navegador: {e}")