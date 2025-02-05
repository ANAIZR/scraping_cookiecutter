from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidElementStateException
from bs4 import BeautifulSoup
import time
import random
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from ..functions import (
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    load_keywords
)

logger = get_logger("scraper")

def scraper_ecoport(url, sobrenombre):
    try:
        driver = initialize_driver()
        object_id = None

        main_folder = generate_directory(sobrenombre)
        print(f"*********** La carpeta principal es: {main_folder} ***********")

        all_urls = []
        collection, fs = connect_to_mongo("scrapping-can", "collection")
        keywords = load_keywords("plants.txt")
        scraping_failed = False
        visited_urls = set()
        urls_not_scraped = []
        total_urls_found = 0
        total_urls_scraped = 0

        driver.get(url)
        domain = "http://ecoport.org"

        for keyword in keywords:
            try:
                driver.get(url) 
                time.sleep(2)

                keyword_folder = generate_directory(keyword, main_folder)
                print(f"*********** Creando carpeta para la palabra clave: {keyword_folder} ***********")

                file_path = get_next_versioned_filename(keyword_folder, keyword)
                print(f"/////////////////////////////////////////////// Se está creando el txt para {keyword}")

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "td input"))
                )
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "td input"))
                )

                time.sleep(2) 

                search_input.clear()
                time.sleep(1)
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input:nth-child(2)"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))

                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")
                results = soup.select("tr td a")

                if not results:
                    print(f"No se encontraron resultados para la palabra clave: {keyword}")
                    scraping_failed = True
                    continue

                for link in results:
                    href = link.get("href")
                    if href:
                        full_href = domain + href if not href.startswith("http") else href
                        if full_href not in visited_urls:
                            visited_urls.add(full_href)
                            total_urls_found += 1
                            total_urls_scraped += 1
                            print(f"Procesando: {full_href}")

                            # Acceder a la URL y extraer los datos
                            driver.get(full_href)
                            time.sleep(random.uniform(3, 6))

                            soup = BeautifulSoup(driver.page_source, "html.parser")

                            title = soup.find("u")
                            title_text = title.get_text(strip=True) if title else "Título no encontrado"

                            tables = soup.select("table.ecoportBanner")
                            ecoport_info = tables[1].get_text("\n", strip=True) if len(tables) > 1 else "No se encontró ecoportBanner"

                            section_table = soup.select_one("table.sectionContainer")
                            search_table = soup.select_one("table.searchResultsTable") if not section_table else None
                            section_info = section_table.get_text("\n", strip=True) if section_table else (
                                search_table.get_text("\n", strip=True) if search_table else "No se encontró sección de contenido ni tabla de resultados"
                            )

                            images = []
                            if search_table:
                                image_tags = search_table.select("img")
                                for img in image_tags:
                                    img_src = img.get("src")
                                    if img_src:
                                        images.append(domain + img_src if not img_src.startswith("http") else img_src)

                            # Escribir en el archivo
                            with open(file_path, "a", encoding="utf-8") as file:
                                file.write(f"URL: {full_href}\n")
                                file.write(f"Título: {title_text}\n\n")
                                file.write(f"Información:\n{ecoport_info}\n\n")
                                file.write(f"Texto:\n{section_info}\n")

                                if images:
                                    file.write(f"\nImágenes encontradas:\n")
                                    for img_url in images:
                                        file.write(f"{img_url}\n")

                                file.write("-" * 100 + "\n\n")

                            driver.back()
                            time.sleep(random.uniform(3, 6))

                driver.back()
                time.sleep(random.uniform(3, 6))

                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(
                        f"Resumen del scraping:\n"
                        f"Total de URLs encontradas: {total_urls_found}\n"
                        f"Total de URLs scrapeadas: {total_urls_scraped}\n"
                        f"Total de URLs no scrapeadas: {len(urls_not_scraped)}\n\n"
                        f"{'-'*80}\n\n"
                    )

            except TimeoutException:
                print(f"Tiempo de espera agotado para la palabra clave: {keyword}")
                scraping_failed = True
            except NoSuchElementException:
                print(f"Elemento no encontrado en la búsqueda de: {keyword}")
                scraping_failed = True
            except InvalidElementStateException:
                print(f"El campo de búsqueda está en un estado inválido para la palabra clave: {keyword}")
                scraping_failed = True
            except Exception as e:
                print(f"Error inesperado al procesar {keyword}: {str(e)}")
                urls_not_scraped.append(keyword)
                scraping_failed = True

        print(f"Total de URLs encontradas: {total_urls_found}")

        if scraping_failed:
            return Response(
                {"message": "Error durante el scraping. Algunas URLs fallaron."},
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
                {"data": response_data},
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        logger.error(f"Error en el scraper: {str(e)}")
        return Response(
            {"message": "Ocurrió un error al procesar los datos."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        driver.quit()