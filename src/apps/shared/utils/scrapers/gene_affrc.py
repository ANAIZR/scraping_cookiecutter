import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from datetime import datetime
from bson import ObjectId
from ..functions import get_logger, connect_to_mongo, process_scraper_data


def scraper_gene_affrc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo()

    all_scraper = ""
    scraped_urls = []
    total_scraped_links = 0

    def fetch_url(record_id):
        base_detail_url = (
            "https://www.gene.affrc.go.jp/databases-micro_pl_diseases_detail_en.php"
        )
        detail_url = f"{base_detail_url}?id={record_id}"
        try:
            response = requests.get(detail_url, timeout=random.uniform(3, 7))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.find("div", class_="container"):
                logger.info(f"URL válida encontrada: {detail_url}")
                return detail_url
            else:
                logger.info(f"Página {detail_url} no contiene datos relevantes.")
        except requests.RequestException as e:
            logger.error(f"Error al acceder a {detail_url}: {e}")
        return None

    def process_link(link):
        try:
            response = requests.get(link, timeout=random.uniform(3, 7))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            extracted_data = ""
            table = soup.select_one("div.container table.table")
            if table:
                for row in table.select("tr"):
                    headers = row.find_all("th")
                    cells = row.find_all("td")
                    if headers:
                        extracted_data += " ".join(header.text.strip() for header in headers) + ": "
                    extracted_data += " ".join(cell.text.strip() for cell in cells) + "\n"
            else:
                logger.info(f"No se encontró tabla en {link}")

            extracted_data += f"URL: {link}\n"

            if extracted_data.strip():
                object_id = fs.put(
                    extracted_data.encode("utf-8"),
                    source_url=link,
                    scraping_date=datetime.now(),
                    Etiquetas=["planta", "plaga"],
                    contenido=extracted_data,
                    url=url
                )

                

                scraped_urls.append(link)
                global total_scraped_links
                total_scraped_links += 1
                existing_versions = list(fs.find({"source_url": link}).sort("scraping_date", -1))

                if len(existing_versions) > 1:
                    oldest_version = existing_versions[-1]
                    file_id = oldest_version._id  
                    fs.delete(file_id)  
                    logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")

                
            return extracted_data

        except requests.RequestException as e:
            logger.error(f"Error al procesar enlace {link}: {e}")
            return ""

    try:
        start_id = 1
        max_attempts = 15000
        logger.info(f"Generando URLs desde {start_id} hasta {start_id + max_attempts - 1}.")

        all_links = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch_url, record_id) for record_id in range(start_id, start_id + max_attempts)]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_links.append(result)

        logger.info(f"Total de enlaces válidos encontrados: {len(all_links)}")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_link, link) for link in all_links]
            for future in as_completed(futures):
                future.result()

        all_scraper = (
            f"Total URLs generadas: {max_attempts}\n"
            f"Total URLs válidas encontradas: {len(all_links)}\n"
            f"Total URLs scrapeadas y almacenadas: {total_scraped_links}\n\n"
            "Lista de URLs scrapeadas:\n"
            + "\n".join(scraped_urls)
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Ocurrió un error durante el scraping: {e}")
        return None
