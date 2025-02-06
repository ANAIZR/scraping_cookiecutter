from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
from bson import ObjectId
import random
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
import os
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

def scraper_pestnet(url, sobrenombre):
    try:
        driver = initialize_driver()
        object_id = None

        main_folder = generate_directory(sobrenombre)
        print(f"*********** La carpeta principal es: {main_folder} ***********")

        all_urls = set()  
        extracted_articles = []  
        failed_urls = []  

        collection, fs = connect_to_mongo("scrapping-can", "collection")
        keywords = load_keywords("plants.txt")
        scraping_failed = False

        driver.get(url)

        for keyword in keywords:
            try:
                driver.get(url)
                time.sleep(2)

                keyword_folder = generate_directory(keyword, main_folder)
                print(f"*********** La carpeta para {keyword} es: {keyword_folder} ********")

                file_path = get_next_versioned_filename(keyword_folder, keyword)
                print(f"/////////////////////////////////////////////// Se está creando el txt para {keyword}")

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

                while True:
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    results = soup.select("article.entry-article h2.entry-title a")  
                    print(f"🔹 Encontrados {len(results)} posts para '{keyword}'.")

                    if not results:
                        print(f"⚠️ No se encontraron resultados para '{keyword}', pasando al siguiente keyword.")
                        break

                    for link in results:
                        href = link.get("href")
                        if href and href not in all_urls:  
                            print(f"✅ Nueva URL almacenada: {href}")  
                            all_urls.add(href)

                    try:
                        button_load_more = WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "li a.load"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", button_load_more)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", button_load_more)
                        time.sleep(random.uniform(2, 4))

                        click_count += 1  
                        print(f"🔹 Click en 'Load More' número {click_count}")

                        if click_count >= 3:  
                            print("🔹 Se ha alcanzado el límite de 3 clics en 'Load More'. Deteniendo scraping.")
                            break

                    except TimeoutException:
                        print("No se encontró el botón 'Load More', deteniendo el scraping.")
                        break
                
                print(f"✅ Finalizado el scraping para '{keyword}'. Total URLs extraídas hasta ahora: {len(all_urls)}")

                for article_url in all_urls:
                    try:
                        driver.get(article_url)
                        time.sleep(2)  

                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, "html.parser")

                        article_content = soup.select_one("article.entry-article")
                        if article_content:
                            extracted_text = article_content.get_text(separator="\n").strip()
                            print(f"Extraído artículo de: {article_url}")

                            extracted_articles.append({"url": article_url, "content": extracted_text})  
                        else:
                            print(f"No se encontró `article.entry-article` en: {article_url}")
                            failed_urls.append(article_url)

                    except Exception as e:
                        print(f"❌ Error al extraer el artículo de {article_url}: {e}")
                        failed_urls.append(article_url)


                print("\n Finalizado el scraping de artículos.")
                print(f"Total de artículos extraídos: {len(extracted_articles)}")
                print(f"Total de URLs fallidas: {len(failed_urls)}")

                if extracted_articles:
                    with open(file_path, "w", encoding="utf-8") as file:

                        for article in extracted_articles:
                            url = article["url"]
                            content = article["content"].strip().replace("\n", " ")

                            file.write(f"URL: {url}\n{content}\n{'-'*80}\n\n")


            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"Error al buscar '{keyword}': {e}")
                scraping_failed = True
                continue

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
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()