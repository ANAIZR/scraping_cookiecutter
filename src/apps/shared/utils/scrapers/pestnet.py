from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
import random
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    connect_to_mongo,
    get_logger,
    driver_init,
    process_scraper_data,
    load_keywords,
    save_to_mongo
)

logger = get_logger("scraper")

def scraper_pestnet(url, sobrenombre):
    try:
        driver = driver_init()
        object_ids = []
        total_urls_scraped = 0
        scraped_urls = []
        failed_urls = []
        total_urls_found = 0

        collection, fs = connect_to_mongo()
        keywords = load_keywords("pruebas.txt")

        driver.get(url)
        time.sleep(2)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        load_more_button = soup.select_one("li a.load")

        if load_more_button:
            print("✅ Botón 'Load More' encontrado antes de interactuar.")
        else:
            print("❌ Botón 'Load More' no encontrado antes de interactuar.")

        for keyword in keywords:
            try:
                driver.get(url)
                time.sleep(2)

                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input.orig"))
                )
                
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input.orig"))
                )
                time.sleep(2)

                search_input.clear()
                time.sleep(1)
                search_input.send_keys(keyword)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.promagnifier"))
                )
                search_button.click()
                time.sleep(random.uniform(3, 6))

                click_count = 0
                all_urls = set()
                
                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results = soup.select("article.entry-article h2.entry-title a")
                    
                    if not results:
                        break
                    
                    for link in results:
                        href = link.get("href")
                        if href and href not in all_urls:
                            all_urls.add(href)
                            total_urls_found += 1
                    
                    try:
                        button_load_more = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "li a.load"))
                        )
                        print("✅ Botón 'Load More' encontrado, haciendo clic.")
                        driver.execute_script("arguments[0].click();", button_load_more)
                        time.sleep(random.uniform(2, 4))
                        
                        click_count += 1
                        if click_count >= 3:
                            break
                    except TimeoutException:
                        print("❌ Botón 'Load More' no encontrado en esta iteración.")
                        break
                
                for article_url in all_urls:
                    try:
                        driver.get(article_url)
                        time.sleep(2)
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, "html.parser")
                        article_content = soup.select_one("article.entry-article")

                        if article_content:
                            content_text = article_content.get_text(separator="\n").strip()
                            
                            if content_text:
                                object_id = save_to_mongo("urls_scraper", content_text, article_url, url)  # 📌 Guardar en `urls_scraper`
                                total_urls_scraped += 1
                                scraped_urls.append(article_url)
                                logger.info(f"📂 Contenido guardado en `urls_scraper` con object_id: {object_id}")
                                
                            
                    except Exception as e:
                        logger.error(f"❌ Error al extraer el artículo de {article_url}: {e}")
                        failed_urls.append(article_url)

            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"Error al buscar '{keyword}': {e}")
                continue

        all_scraper = f"Total enlaces encontrados: {total_urls_found}\n"
        all_scraper += f"Total scrapeados con éxito: {total_urls_scraped}\n"
        all_scraper += "URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n"
        all_scraper += f"Total fallidos: {len(failed_urls)}\n"
        all_scraper += "URLs fallidas:\n" + "\n".join(failed_urls) + "\n"
        
        response = process_scraper_data(all_scraper, url, sobrenombre)        
        return response
     


    except Exception as e:
        logger.error(f"Error en el scraper: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        driver.quit()
