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
    generate_directory,
)


def scraper_agriculture(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    nivel_1_links = []
    nivel_2_links = []
    processed_links = {}  # Diccionario para rastrear URLs procesadas
    headers = {"User-Agent": get_random_user_agent()}

    def extract_links(current_url):
        """Extrae los href con target="__blank" desde la URL actual y maneja errores HTTP específicos."""
        if processed_links.get(current_url, 0) >= 2:
            logger.warning(f"Saltando URL (ya procesada más de 2 veces): {current_url}")
            return []

        try:
            logger.info(f"Conectando a la URL: {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10)  # Agregamos un timeout
            
            # Validar rango de códigos HTTP manualmente
            if not (200 <= response.status_code < 300):
                logger.warning(f"HTTP {response.status_code} recibido para {current_url}. Saltando URL.")
                return []

            logger.info(f"Conexión exitosa. Procesando contenido de {current_url}")
            processed_links[current_url] = processed_links.get(current_url, 0) + 1  # Incrementar contador
            soup = BeautifulSoup(response.content, "html.parser")

            # Verificar si el td con la clase específica existe
            td_element = soup.find("td", class_="newsroom_2cols")
            if not td_element:
                logger.warning(f"No se encontró el td con la clase 'newsroom_2cols' en {current_url}")
                return []

            # Extraer enlaces con target="_blank"
            links = [
                urljoin(current_url, link.get("href"))
                for link in td_element.find_all("a", href=True, target="_blank")
            ]
            logger.info(f"Se encontraron {len(links)} enlaces en {current_url}")
            return links

        except requests.exceptions.Timeout:
            logger.error(f"Tiempo de espera agotado para {current_url}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar la URL {current_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al procesar {current_url}: {e}")
            return []


    def extract_text(current_url):
        """Extrae el texto del td con la clase 'newsroom_2cols' y maneja espacios correctamente."""
        if processed_links.get(current_url, 0) >= 1:
            logger.warning(f"Saltando URL (ya procesada 1 vez): {current_url}")
            return ""

        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()

            processed_links[current_url] = processed_links.get(current_url, 0) + 1  # Incrementar contador
            soup = BeautifulSoup(response.content, "html.parser")
            td_element = soup.find("td", class_="newsroom_2cols")
            if not td_element:
                logger.warning(f"No se encontró el td con la clase 'newsroom_2cols' en {current_url}")
                return ""

            # Asegúrate de que el texto dentro de las etiquetas <i> no se una con los textos circundantes
            return td_element.get_text(separator=" ", strip=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar la URL {current_url}: {e}")
            return ""



    try:
        # Nivel 1: Extraer enlaces de la URL principal
        logger.info("Extrayendo enlaces del nivel 1")
        nivel_1_links = extract_links(url)
        logger.info(f"Enlaces nivel 1: {len(nivel_1_links)} encontrados.")

        # Nivel 2: Extraer enlaces de cada enlace del nivel 1
        for link in nivel_1_links:
            logger.info(f"Procesando enlaces del nivel 2 desde {link}")
            nivel_2_links.extend(extract_links(link))

        logger.info(f"Enlaces nivel 2: {len(nivel_2_links)} encontrados.")

        # Nivel 3: Extraer texto de cada enlace del nivel 2
        for link in nivel_2_links:
            logger.info(f"Extrayendo texto del nivel 3 desde {link}")
            text = extract_text(link)
            if text:
                all_scraper += f"URL: {link}\n{text}\n\n"

        # Procesar y almacenar el resultado
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
