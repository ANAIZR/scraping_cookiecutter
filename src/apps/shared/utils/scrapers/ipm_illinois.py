from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pymongo import MongoClient
from datetime import datetime
import gridfs
import os
import hashlib
import requests
import PyPDF2
from io import BytesIO
import urllib3
from ..functions import (
    generate_directory,
    get_next_versioned_filename,
    delete_old_documents,
    initialize_driver,
    connect_to_mongo
)


def extract_text_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url, stream=True, verify=False, timeout=10)
        response.raise_for_status()

        pdf_buffer = BytesIO(response.content) 
        reader = PyPDF2.PdfReader(pdf_buffer)
        
        pdf_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

        return pdf_text

    except Exception as e:
        print(f"Error al extraer contenido del PDF ({pdf_url}): {e}")
        return None


def scraper_pdf_content_and_save(pdf_url, collection, fs, sobrenombre, all_scraper):
    try:
        pdf_text = extract_text_from_pdf(pdf_url)
        if pdf_text:
            pdf_folder = generate_directory(sobrenombre)  
            file_path = os.path.join(pdf_folder, f"{sobrenombre}.txt")  

            with open(file_path, "a", encoding="utf-8") as file:  
                file.write(f"\n\nURL: {pdf_url}\n{pdf_text}\n")

            with open(file_path, "rb") as file_data:
                object_id = fs.put(file_data, filename=os.path.basename(file_path))

                data = {
                    "Objeto": object_id,
                    "Tipo": "PDF",
                    "Url": pdf_url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Etiquetas": ["planta", "plaga"],
                }
                collection.insert_one(data)

                delete_old_documents(pdf_url, collection, fs)

                all_scraper += f"\n\nURL: {pdf_url}\n{pdf_text}"

                return all_scraper

    except Exception as e:
        print(f"Error al guardar contenido PDF: {e}")
        return all_scraper + f"\n\nURL: {pdf_url}\nError: {str(e)}"



def scraper_all_pdfs_from_page(url, collection, fs):
    driver = initialize_driver()
    all_scraper = ""  

    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table:nth-child(3)"))
        )
        table_content = driver.find_element(By.CSS_SELECTOR, "table:nth-child(3)")
        pdf_links = table_content.find_elements(By.CSS_SELECTOR, "a[href$='.pdf']")

        if not pdf_links:
            return "No se encontraron archivos PDF en la página."

        for link in pdf_links:
            pdf_url = link.get_attribute("href")
            if pdf_url:
                all_scraper = scraper_pdf_content_and_save(pdf_url, collection, fs, "IPM", all_scraper)

        return all_scraper  

    except Exception as e:
        print(f"Error durante el scraping de PDFs en la página: {e}")
        return f"Error: {str(e)}"

    finally:
        driver.quit()


def scraper_ipm_illinoes(url,sobrenombre):
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        collection,fs = connect_to_mongo()

        scraper_all_pdfs_from_page(url, collection, fs)
        return {
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Mensaje": "Scraping completado exitosamente."
        }

    except Exception as e:
        return {
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Mensaje": f"Error en el scraping: {str(e)}"
        }
