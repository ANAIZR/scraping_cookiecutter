import requests
from bs4 import BeautifulSoup
import pypdf
import io
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
)

def scraper_ipm_illinois(url,sobrenombre):
    all_scraper = ""
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    response = requests.get(url)
    collection,fs = connect_to_mongo()

    if response.status_code != 200:
        print(f"Error al acceder a la URL: {url}")
        return None
    soup = BeautifulSoup(response.content, 'html.parser')

    tables = soup.find_all("table")
    if len(tables) < 3:
        print("No se encontraron al menos 3 tablas en el cuerpo de la página")
        return None
    
    third_table = tables[2]  

    links = third_table.find_all("p")

    for p in links:
        a_tag = p.find("a", href=True)
        if a_tag and a_tag["href"].endswith(".pdf"):
            pdf_url = a_tag["href"]
            if not pdf_url.startswith("http"):
                pdf_url = url.rstrip("/") + "/" + pdf_url  
            
            print(f"Extrayendo texto de: {pdf_url}")
            try:
                pdf_response = requests.get(pdf_url)
                if pdf_response.status_code == 200:
                    pdf_bytes = io.BytesIO(pdf_response.content)
                    pdf_reader = pypdf.PdfReader(pdf_bytes)

                    pdf_text = ""
                    for page in pdf_reader.pages:
                        pdf_text += page.extract_text() + " "

                    all_scraper += f"URL: {pdf_url} \n\n {pdf_text.strip()}  \n"
                    all_scraper +="*"*100+"\n"
            except Exception as e:
                print(f"Error al procesar el PDF {pdf_url}: {e}")

    response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
    return response
