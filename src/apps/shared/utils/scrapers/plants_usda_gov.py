from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
import time
from datetime import datetime
from bson import ObjectId
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_plants_usda_gov(url, sobrenombre):

    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()

    all_scraper = ""  
    total_scraped_links = 0
    scraped_urls = []
    urls_not_scraped = []

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#main-content"))
        )

        characteristic = driver.find_element(
            By.CSS_SELECTOR, "div.sidebar-desktop li:first-child a"
        )
        driver.execute_script("arguments[0].click();", characteristic)

        time.sleep(2)

        while True:
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "section.content table tbody tr")
                    )
                )

                soup = BeautifulSoup(driver.page_source, "html.parser")
                tr_tags = soup.select("section.content table tbody tr")
                time.sleep(2)

                for index, tr in enumerate(tr_tags[1:], start=1):
                    try:
                        if tr.select("td"):
                            link_tag = tr.select_one("td:nth-child(2) a")
                            if link_tag:
                                href = link_tag.get("href")
                                if href.startswith("/"):
                                    href = f"https://plants.usda.gov{href}"
                                
                                driver.get(href)

                                WebDriverWait(driver, 60).until(
                                    EC.visibility_of_element_located(
                                        (By.CSS_SELECTOR, "table.usa-table.width-full.classification-table")
                                    )
                                )

                                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                                select_element = page_soup.find(
                                    "table", class_="usa-table width-full classification-table"
                                )

                                if select_element:
                                    content_text = select_element.text.strip()

                                    object_id = fs.put(
                                        content_text.encode("utf-8"),
                                        source_url=href,
                                        scraping_date=datetime.now(),
                                        Etiquetas=["plant", "usda"],
                                        contenido=content_text,
                                        url=url
                                    )

                                    

                                    scraped_urls.append(href)
                                    total_scraped_links += 1
                                    existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                                    logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                                    if len(existing_versions) > 1:
                                        oldest_version = existing_versions[-1]
                                        fs.delete(oldest_version._id) 
                                        logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version.id}")


                                    

                                else:
                                    logger.warning(f"No se encontró contenido en {href}")
                                    urls_not_scraped.append(href)

                                driver.back()
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_all_elements_located(
                                        (By.CSS_SELECTOR, "section.content table tbody tr")
                                    )
                                )

                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        urls_not_scraped.append(href)
                max_pages = 3  # Número máximo de veces que se puede hacer clic en "Next"
                page_count = 0  # Contador de páginas navegadas

                while page_count < max_pages:  # Se detiene después de 3 páginas
                    try:
                        next_page_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, "li.usa-pagination__item.usa-pagination__arrow a.usa-pagination__next-page")
                            )
                        )
                        driver.execute_script("arguments[0].click();", next_page_button)
                        time.sleep(3)
                        
                        page_count += 1  # Incrementa el contador
                        print(f"Navegación {page_count}: Se hizo clic en 'Next'.")
                    except Exception as e:
                        print("No se encontró el botón 'Next' o no es clickeable.")
                        break  # Detiene el bucle si el botón no aparece

                print("Se alcanzó el límite de navegación (3 páginas) o no hay más páginas.")

                """try:
                    next_page_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "li.usa-pagination__item.usa-pagination__arrow a.usa-pagination__next-page")
                        )
                    )
                    driver.execute_script("arguments[0].click();", next_page_button)
                    time.sleep(3)
                except Exception as e:
                    break """

            except Exception as e:
                break 

        all_scraper = (
            f"Resumen del scraping:\n"
            f"Total de enlaces procesados: {len(scraped_urls)}\n"
            f"Total de enlaces no procesados: {len(urls_not_scraped)}\n\n"
            f"{'-'*80}\n\n"
        )

        if scraped_urls:
            all_scraper += "Enlaces scrapeados:\n" + "\n".join(scraped_urls) + "\n\n"

        if urls_not_scraped:
            all_scraper += "Enlaces no procesados:\n" + "\n".join(urls_not_scraped) + "\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()