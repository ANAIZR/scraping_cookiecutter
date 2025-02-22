from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from bson.objectid import ObjectId
from datetime import datetime
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_nematode(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    all_scraper = ""
    total_scraped_successfully = 0

    try:
        driver.get(url)
        all_scraper += f"{url}\n\n"
        
        while True:
            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.view"))
            )
            
            rows = driver.find_elements(By.CSS_SELECTOR, "div.views-row")
            
            for row in rows:
                fields = row.find_elements(By.CSS_SELECTOR, "div.content div.field--label-inline")
                for field in fields:
                    label = field.find_element(By.CSS_SELECTOR, "div.field--label").text.strip()
                    
                    field_items = []
                    spans = field.find_elements(By.CSS_SELECTOR, "span")
                    for span in spans:
                        text = span.text.strip()
                        if text and text not in field_items:
                            field_items.append(text)
                    
                    divs = field.find_elements(By.CSS_SELECTOR, "div.field--item")
                    for div in divs:
                        text = div.text.strip()
                        if text and text not in field_items:
                            field_items.append(text)
                    
                    field_text = " ".join(field_items).strip()
                    all_scraper += f"{label}: {field_text}\n"
                all_scraper += "\n"
            
                links = row.find_elements(By.CSS_SELECTOR, "a")
                for link in links:
                    link_href = link.get_attribute("href")
                    if link_href:
                        driver.get(link_href)
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        content_text = driver.find_element(By.TAG_NAME, "body").text.strip()
                        
                        if content_text:
                            object_id = fs.put(
                                content_text.encode("utf-8"),
                                source_url=link_href,
                                scraping_date=datetime.now(),
                                Etiquetas=["planta", "plaga"],
                                contenido=content_text,
                                url=url
                            )
                            total_scraped_successfully += 1
                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                            
                            existing_versions = list(fs.find({"source_url": link_href}).sort("scraping_date", -1))
                            
                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                fs.delete(ObjectId(oldest_version["_id"]))
                                logger.info(f"Se eliminó la versión más antigua con object_id: {oldest_version['_id']}")
                
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Go to next page']"))
                )
                next_button_class = next_button.get_attribute("class")
                if "disabled" in next_button_class or "is-active" in next_button_class:
                    break
                else:
                    next_button.click()
                    WebDriverWait(driver, 10).until(EC.staleness_of(content))
            except Exception:
                break
        
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        driver.quit()
        logger.info("Navegador cerrado.")
