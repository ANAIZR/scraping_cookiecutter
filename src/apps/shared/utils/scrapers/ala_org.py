from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    get_random_user_agent
)
from bs4 import BeautifulSoup

def scraper_ala_org(url, sobrenombre):
    logger = get_logger("ALA_ORG")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")

    all_hrefs = []  
    try:
        driver.get(url)
        
        btn = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[type='submit']"))
        )
        btn.click()
        time.sleep(2)

        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol"))
            )

            lis = driver.find_elements(By.CSS_SELECTOR, "ol li.search-result")
            
            for li in lis:
                try:
                    a_tag = li.find_element(By.CSS_SELECTOR, "a")
                    href = a_tag.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = url + href[1:] 
                        all_hrefs.append(href)  
                except Exception as e:
                    logger.warning(f"Error obteniendo href: {e}")

            try:
                next_page_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")
                next_page_url = next_page_btn.get_attribute("href")
                if next_page_url:
                    driver.get(next_page_url)
                    time.sleep(3)
                else:
                    break
            except Exception:
                break  

    finally:
        driver.quit() 

    total_encontrados = len(all_hrefs)
    total_scrapeados = 0
    total_fallidos = 0
    fallidos = [] 

    all_scraper = ""
    headers = {"User-Agent": get_random_user_agent()}

    for href in all_hrefs:
        try:
            response = requests.get(href, headers=headers, timeout=40)  
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                main_content = soup.select_one("#main")  
                
                if main_content:
                    extracted_text = main_content.get_text(separator=" ", strip=True) 
                    all_scraper += extracted_text  
                    all_scraper += "\n\n"
                    total_scrapeados += 1 
                else:
                    logger.warning(f"No se encontró el ID 'main' en {href}")
                    fallidos.append(href)
                    total_fallidos += 1
            else:
                logger.warning(f"No se pudo obtener {href}, código {response.status_code}")
                fallidos.append(href)
                total_fallidos += 1
        except requests.RequestException as e:
            logger.error(f"Error en la solicitud a {href}: {e}")
            fallidos.append(href)
            total_fallidos += 1

    resumen_scraping = f"""
    === RESUMEN DEL SCRAPING ===
    Total de enlaces encontrados: {total_encontrados}
    Total de enlaces scrapeados con éxito: {total_scrapeados}
    Total de enlaces fallidos: {total_fallidos}
    
    Enlaces no scrapeados:
    {', '.join(fallidos) if fallidos else 'Ninguno'}
    ============================
    """

    all_scraper += resumen_scraping

    return process_scraper_data(all_scraper, sobrenombre, sobrenombre, collection, fs)
