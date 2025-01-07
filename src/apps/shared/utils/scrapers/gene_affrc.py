import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import random
from ..functions import get_logger, connect_to_mongo, process_scraper_data


def scraper_gene_affrc(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    all_links = []

    def fetch_url(record_id):
        """
        Función auxiliar para realizar la solicitud HTTP y validar el contenido.
        """
        base_detail_url = (
            "https://www.gene.affrc.go.jp/databases-micro_pl_diseases_detail_en.php"
        )
        detail_url = f"{base_detail_url}?id={record_id}"
        try:
            response = requests.get(detail_url, timeout=random.uniform(3, 7))
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                if soup.find("div", class_="container"):  # Verifica contenido relevante
                    logger.info(f"URL válida encontrada: {detail_url}")
                    return detail_url
                else:
                    logger.info(f"Página {detail_url} no contiene datos relevantes.")
            else:
                logger.info(
                    f"URL inválida: {detail_url} (Código: {response.status_code})"
                )
        except requests.RequestException as e:
            logger.error(f"Error al acceder a {detail_url}: {e}")
        return None

    try:
        start_id = 1
        max_attempts = 15000
        logger.info(
            f"Construyendo URLs desde {start_id} hasta {start_id + max_attempts - 1}."
        )

        # Paralelizar solicitudes con ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_record = {
                executor.submit(fetch_url, record_id): record_id
                for record_id in range(start_id, start_id + max_attempts)
            }

            for future in as_completed(future_to_record):
                record_id = future_to_record[future]
                try:
                    result = future.result()
                    if result:
                        all_links.append(result)
                except Exception as e:
                    logger.error(f"Error procesando ID {record_id}: {e}")

        logger.info(f"Total de enlaces válidos encontrados: {len(all_links)}")

        # Procesar cada enlace válido
        for link in all_links:
            try:
                response = requests.get(link)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Extraer tabla de datos
                table = soup.select_one("div.container table.table")
                if table:
                    for row in table.select("tr"):
                        cells = row.find_all("td")
                        headers = row.find_all("th")

                        if headers:
                            for header in headers:
                                all_scraper += header.text.strip() + ": "
                        for cell in cells:
                            all_scraper += cell.text.strip() + "\n"
                else:
                    logger.info(f"No se encontró tabla en {link}")
            except requests.RequestException as e:
                logger.error(f"Error al procesar enlace {link}: {e}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Ocurrió un error durante el scraping: {e}")
