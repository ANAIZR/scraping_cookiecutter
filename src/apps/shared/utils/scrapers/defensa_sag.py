from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from ..functions import (
    initialize_driver,
    get_logger,
    connect_to_mongo,
    process_scraper_data_v2,
    extract_text_from_pdf
)
from bson import ObjectId
import time

non_scraped_urls = []
total_scraped_links = 0

def scraper_defensa_sag(url, sobrenombre):
    logger = get_logger("DEFENSA SAG")
    logger.info(f"Iniciando scraping para URL: {url}")

    driver = initialize_driver()
    collection, fs = connect_to_mongo()
    scraped_urls = set()
    visited_urls = set()

    try:
        driver.get(url)
        driver.execute_script("document.body.style.zoom='100%'")
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)

        print(f"✅ Página cargada correctamente.")

        try:
            driver.find_element(By.CSS_SELECTOR, "table tbody tr td table:nth-child(2) tr td table")
            print("✅ Se encontró las opciones del table")
            logger.info("✅ Se encontró las opciones del table")

            elemento_a = driver.find_element(By.ID, "stUI16_lnk")
            elemento_a.click()
            
            driver.execute_script("arguments[0].click();", elemento_a)


            ##urls del primer desplegable
            urls_desp1 = [f"https://defensa.sag.gob.cl/reqmercado/consulta.asp?tp={i}" for i in [6, 102, 7, 8, 9]]
            urls_desp2 = [f"https://defensa.sag.gob.cl/reqmercado/consulta.asp?tp={i}" for i in [14, 19, 15, 111, 112, 113]]

            index = 2
            while True:
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, f"tr.sttr:nth-child({index})")
                    if not rows:
                        print("✅ No hay más filas pares para procesar.")
                        break                    
                    
                    if(index == 14):
                        print("primer desplegable")
                        for option1 in urls_desp1:
                            driver.get(option1)
                            process_dropdowns(driver, logger, visited_urls, scraped_urls, fs)

                    if(index == 20):                        
                        print("segundo desplegable")
                        for option2 in urls_desp2:
                            driver.get(option2)
                            process_dropdowns(driver, logger, visited_urls, scraped_urls, fs)                            

                    else:
                        row = rows[0]
                        span_element = row.find_element(By.CSS_SELECTOR, "span")
                        span_text = span_element.text.strip()

                        row.click()
                        time.sleep(2)

                        print(f"🟢 El nombre del tr es: {span_text}")
                        logger.info(f"🟢 El nombre del tr es: {span_text}")

                        process_dropdowns(driver, logger, visited_urls, scraped_urls, fs)

                    index += 2  

                    driver.back()
                    time.sleep(3)  

                except NoSuchElementException:
                    logger.warning(f"⚠️ No se encontró el span en la fila {index}.")
                    index += 2  
                except StaleElementReferenceException:
                    logger.warning(f"🔄 Elemento obsoleto en la fila {index}, reintentando...")
                    time.sleep(1)

        except NoSuchElementException:
            logger.error("❌ No se encontró el table especificado")
            return {"error": "No se encontró el table especificado"}
        
        all_scraper = (
            f"Total enlaces scrapeados: {len(scraped_urls)}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )

        response = process_scraper_data_v2(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"⚠️ Error general durante el scraping: {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        print("🚪 Navegador cerrado.")

def process_dropdowns(driver, logger, visited_urls, scraped_urls, fs):
    """
    Procesa cada opción en los dropdowns:
    - "Buscar por" (`#buscar`)
    - "Nombre Científico" (`#nombre`)
    - "País" (`#select4`)
    Luego extrae la URL final y busca PDFs.
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "buscar"))
        )
        dropdown_buscar = Select(driver.find_element(By.ID, "buscar"))
        logger.info("📌 Dropdown 'Buscar por' encontrado.")

        for i in range(1, len(dropdown_buscar.options)):  # Saltar "Ingrese Búsqueda"
            try:
                dropdown_buscar = Select(driver.find_element(By.ID, "buscar"))
                option_text = dropdown_buscar.options[i].text.strip()
                logger.info(f"🔄 Procesando opción {i} en 'Buscar por': {option_text}")

                dropdown_buscar.select_by_index(i)
                time.sleep(2)

                if is_element_present(driver, By.ID, "nombre"):
                    process_second_dropdown(driver, logger, visited_urls, scraped_urls, fs)

            except NoSuchElementException:
                logger.warning(f"⚠️ No se encontró opción {i} en 'Buscar por'.")

    except TimeoutException:
        logger.warning("❌ No se encontraron los dropdowns principales.")

def process_second_dropdown(driver, logger, visited_urls, scraped_urls, fs):
    try:
        dropdown_nombre = Select(driver.find_element(By.ID, "nombre"))
        logger.info("📌 Dropdown 'Nombre Científico' encontrado.")

        for j in range(1, len(dropdown_nombre.options)):
            try:
                dropdown_nombre = Select(driver.find_element(By.ID, "nombre"))
                dropdown_nombre.select_by_index(j)
                time.sleep(2)

                if is_element_present(driver, By.ID, "select4"):
                    process_third_dropdown(driver, logger, visited_urls, scraped_urls, fs)

            except NoSuchElementException:
                logger.warning(f"⚠️ No se encontró opción {j} en 'Nombre Científico'.")

    except TimeoutException:
        logger.warning("❌ No se encontró el dropdown 'Nombre Científico'.")

def process_third_dropdown(driver, logger, visited_urls, scraped_urls, fs):
    global total_scraped_links
    try:
        dropdown_pais = Select(driver.find_element(By.ID, "select4"))
        logger.info("📌 Dropdown 'País' encontrado.")

        for k in range(1, len(dropdown_pais.options)):
            try:
                dropdown_pais = Select(driver.find_element(By.ID, "select4"))
                dropdown_pais.select_by_index(k)
                time.sleep(2)

                detail_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.texto_titulo"))
                )
                driver.execute_script("arguments[0].click();", detail_button)
                time.sleep(2)

                result_url = driver.current_url
                if result_url not in visited_urls:
                    visited_urls.add(result_url)
                    scraped_urls.add(result_url)
                    logger.info(f"✅ URL extraída: {result_url}")

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                pdf_links = page_soup.select("td.cssBodyListado tbody a")

                for link in pdf_links:
                    href = link.get("href")
                    if href and href.endswith(".pdf"):
                        logger.info(f"📄 Extrayendo texto de PDF: {href}")
                        content_text = extract_text_from_pdf(href)

                        if content_text:
                            object_id = fs.put(
                                content_text.encode("utf-8"),
                                source_url=href,
                                scraping_date=datetime.now(),
                                Etiquetas=["planta", "plaga"],
                                contenido=content_text,
                                url=result_url
                            )
                            total_scraped_links += 1
                            scraped_urls.append(href)
                            logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")

                            existing_versions = list(fs.find({"source_url": href}).sort("scraping_date", -1))
                            if len(existing_versions) > 1:
                                oldest_version = existing_versions[-1]
                                file_id = oldest_version._id  # Esto obtiene el ID correcto
                                fs.delete(file_id)  # Eliminar la versión más antigua
                                logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")
                        else:
                            non_scraped_urls.append(href)
 
            except NoSuchElementException:
                continue

    except TimeoutException:
        logger.warning("❌ No se encontró el dropdown 'País'.")

def is_element_present(driver, by, value):
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False
