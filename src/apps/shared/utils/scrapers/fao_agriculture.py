import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
)
from datetime import datetime
from selenium.common.exceptions import TimeoutException
from requests.exceptions import ConnectionError

def scraper_agriculture(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo()
    all_scraper = ""
    nivel_1_links = []
    nivel_2_links = []
    processed_links = {}  
    headers = {"User-Agent": get_random_user_agent()}

    def extract_links(current_url):
        if processed_links.get(current_url, 0) >= 2:
            logger.warning(f"Saltando URL (ya procesada más de 2 veces): {current_url}")
            return []  

        try:
            logger.info(f"Conectando a la URL: {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10) 

            if not (200 <= response.status_code < 300):
                logger.warning(f"HTTP {response.status_code} recibido para {current_url}. Saltando URL.")
                return []  

            processed_links[current_url] = processed_links.get(current_url, 0) + 1  
            soup = BeautifulSoup(response.content, "html.parser")

            td_element = soup.find("td", class_="newsroom_2cols")
            if not td_element:
                logger.warning(f"No se encontró el td con la clase 'newsroom_2cols' en {current_url}")
                return []  

            links = [
                urljoin(current_url, link.get("href"))
                for link in td_element.find_all("a", href=True, target="_blank")
            ]

            logger.info(f"Se encontraron {len(links)} enlaces en {current_url}")
            return links  

        except TimeoutException:
            logger.error(f"Error: la página {current_url} está tardando demasiado en responder.")
            return []  
        except ConnectionError:
            logger.error("Error de conexión a la URL.")
            return []
        except Exception as e:
            logger.error(f"Error al procesar datos del scraper: {str(e)}")
            return []



    def extract_text(current_url):
        if processed_links.get(current_url, 0) >= 1:
            logger.warning(f"Saltando URL (ya procesada 1 vez): {current_url}")
            return ""

        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()

            processed_links[current_url] = processed_links.get(current_url, 0) + 1 
            soup = BeautifulSoup(response.content, "html.parser")
            td_element = soup.find("td", class_="newsroom_2cols")
            if not td_element:
                logger.warning(f"No se encontró el td con la clase 'newsroom_2cols' en {current_url}")
                return ""

            return td_element.get_text(separator=" ", strip=True)
        except Exception as e:
            logger.error(f"Error al procesar datos del scraper: {str(e)}")
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

                    "Mensaje": "Ocurrió un error al procesar los datos.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



    try:
        nivel_1_links = extract_links(url)

        for link in nivel_1_links:
            nivel_2_links.extend(extract_links(link))


        for link in nivel_2_links:
            text = extract_text(link)
            if text:
                all_scraper += f"URL: {link}\n{text}\n\n"

        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
