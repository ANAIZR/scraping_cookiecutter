import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ..functions import (
    connect_to_mongo,
    get_logger,
    process_scraper_data,
    get_random_user_agent
)
from django.utils.timezone import make_aware
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("scraper")
naive_datetime = datetime.now()
aware_datetime = make_aware(naive_datetime)

visited_url = set()

def scrape_single_url(url):
    try:
        logger.info(f"Procesando URL: {url}")
        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, "html.parser")

        # Eliminamos etiquetas center si existen
        for center_tag in soup.find_all("center"):
            center_tag.decompose()

        body_text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
        return body_text
    except Exception as e:
        logger.error(f"Error al procesar URL {url}: {e}")
        return None

def scraper_hort_purdue(url, sobrenombre):
    all_links = set() 
    domain = "https://hort.purdue.edu/"
    urls_not_scraped = []
    urls_scraped = []  # Aquí almacenamos las URLs que se procesaron correctamente

    try:
        if url in visited_url:
            logger.info(f"URL ya visitada: {url}")
            return Response(
                {"status": "info", "message": f"La URL {url} ya fue visitada."},
                status=status.HTTP_200_OK,
            )

        visited_url.add(url)

        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        logger.info("Contenido de la página obtenido con BeautifulSoup.")

        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("/newcrop"):
                full_url = domain + href.lstrip("/") 
                if full_url not in visited_url:
                    all_links.add(full_url)

        logger.info(f"Se encontraron {len(all_links)} enlaces únicos.")

        collection, fs = connect_to_mongo()

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(scrape_single_url, link): link for link in all_links}

            for future in as_completed(future_to_url):
                link = future_to_url[future]
                try:
                    body_text = future.result()
                    if body_text:
                        object_id = fs.put(
                            body_text.encode("utf-8"),
                            source_url=link,
                            scraping_date=datetime.now(),
                            Etiquetas=["planta", "plaga"],
                            contenido=body_text,
                            url=url
                        )
                        logger.info(f"✅ Archivo almacenado en MongoDB con object_id: {object_id}")

                        existing_versions = list(
                            fs.find({"source_url": link}).sort("scraping_date", -1)
                        )
                        if len(existing_versions) > 1:
                            oldest_version = existing_versions[-1]
                            file_id = oldest_version._id  
                            fs.delete(file_id)  
                            logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")

                        urls_scraped.append(link)
                    else:
                        urls_not_scraped.append(link)
                except Exception as e:
                    logger.error(f"Error al procesar el enlace {link}: {e}")
                    urls_not_scraped.append(link)

        all_scraper = (
            "Resumen del scraping:\n"
            f"Total de URLs encontradas: {len(all_links)}\n"
            f"Total de URLs procesadas exitosamente: {len(urls_scraped)}\n"
            f"URLs procesadas exitosamente:\n{chr(10).join(urls_scraped)}\n\n"
            f"Total de URLs no procesadas: {len(urls_not_scraped)}\n"
            f"URLs no procesadas:\n{chr(10).join(urls_not_scraped)}\n"
        )

        response = process_scraper_data(all_scraper, url, sobrenombre)

        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response(
            {"status": "error", "message": f"Error durante el scraping: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
