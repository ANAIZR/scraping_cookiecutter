import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pickle
import random
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
from datetime import datetime
from ..functions import (
    initialize_driver_cabi,
    get_logger,
    connect_to_mongo,
    load_keywords,
    process_scraper_data
)
from rest_framework.response import Response
from rest_framework import status
from ..credentials import login_cabi_scienceconnect

logger = get_logger("scraper")

def detect_captcha(driver, context="Desconocido"):
    """
    Detecta si aparece el CAPTCHA de Cloudflare y lo registra con el contexto donde se encontró.
    """
    try:
        captcha_checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#content input[type='checkbox']"))
        )
        logger.warning(f"⚠ CAPTCHA detectado en: {context}. Intentando resolverlo...")
        
        driver.execute_script("arguments[0].click();", captcha_checkbox)
        time.sleep(5)  

        if is_captcha_present(driver):
            logger.error(f"❌ CAPTCHA persistente en {context}. Posible bloqueo.")
            return True
        else:
            logger.info(f"✅ CAPTCHA resuelto en {context}.")
            return False

    except TimeoutException:
        logger.info(f"✅ No se detectó CAPTCHA en {context}.")
        return False

def is_captcha_present(driver):
    try:
        driver.find_element(By.CSS_SELECTOR, "#content input[type='checkbox']")
        return True
    except NoSuchElementException:
        return False


def scraper_cabi_digital(url, sobrenombre):
    driver = initialize_driver_cabi()

    
    total_scraped_links = 0
    scraped_urls = []
    non_scraped_urls = []
    all_scraper=""

    """try:
        driver.get(url)
        detect_captcha(driver)
        time.sleep(random.uniform(3, 6))
        detect_captcha(driver)
         if login_cabi_scienceconnect(driver):
            print("Login completado, continuando con el scraping...") 
    except:
        logger.error("No se encontro el login")"""
    try:
        driver.get(url)
        detect_captcha(driver, "Carga de la página principal")

        time.sleep(random.uniform(1, 3))

        
        logger.info(f"Iniciando scraping para URL: {url}")
        detect_captcha(driver, "Inicio del scraping")

        collection, fs = connect_to_mongo()
        detect_captcha(driver)

        keywords = load_keywords("plants.txt")
        detect_captcha(driver, "Carga de palabras clave")

        if not keywords:
            return Response(
                {
                    "status": "error",
                    "message": "El archivo de palabras clave está vacío o no se pudo cargar.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Página de CABI cargada exitosamente.")
        scraping_exitoso = False
        base_domain = "https://www.cabidigitallibrary.org"
        visited_urls = set()
        detect_captcha(driver, f"Búsqueda con la palabra clave: {keyword}")

        try:
            if os.path.exists("cookies.pkl"):
                try:
                    with open("cookies.pkl", "rb") as file:
                        cookies = pickle.load(file)
                        for cookie in cookies:
                            driver.add_cookie(cookie)
                    driver.refresh()
                    logger.info("✅ Cookies cargadas correctamente.")
                except Exception as e:
                    logger.error(f"⚠ Error al cargar cookies: {e}")
            else:
                logger.info("⚠ No se encontraron cookies guardadas.")
        except FileNotFoundError:
            logger.info("No se encontraron cookies guardadas.")

        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-pc-btn-handler"))
            )
            driver.execute_script("arguments[0].click();", cookie_button)
            logger.info("✅ Ventana de cookies cerrada.")
            detect_captcha(driver)
        except Exception:
            logger.info("⚠ No se encontró la ventana de cookies, continuando...")
        detect_captcha(driver)
        try:
            preferences_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#accept-recommended-btn-handler")
                )
            )
            driver.execute_script("arguments[0].click();", preferences_button)

        except Exception:
            logger.info(
                "El botón de 'Guardar preferencias' no apareció o no fue clicable."
            )
        detect_captcha(driver)
        for keyword in keywords:
            detect_captcha(driver, f"Recarga de página para {keyword}")
            logger.info(f"Buscando la palabra clave: {keyword}")
            detect_captcha(driver, f"Ejecución de búsqueda para {keyword}")
            try:
                driver.get(url)
                detect_captcha(driver)
                time.sleep(random.uniform(6, 10))

                search_input = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800",
                        )
                    )
                )
                search_input.clear()
                search_input.send_keys(keyword)
                time.sleep(random.uniform(3, 6))

                search_input.submit()
                detect_captcha(driver)
                logger.info(f"Realizando búsqueda con la palabra clave: {keyword}")
            except Exception as e:
                logger.info(f"Error al realizar la búsqueda: {e}")
                continue
            visited_counts =0
            max_visits = 5

            while True:
                detect_captcha(driver, f"Resultados de búsqueda para {keyword}")
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.rlist li"))
                    )
                    logger.info("Resultados encontrados en la página.")
                    time.sleep(random.uniform(1, 3))

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    items = soup.select("ul.rlist li")
                    if not items:
                        logger.warning(
                            f"No se encontraron resultados para la palabra clave: {keyword}"
                        )
                        break
                    
                    for item in items:
                        if visited_counts>=max_visits:
                            break
                        link = item.find("a")
                        if link and "href" in link.attrs:
                            href = link["href"]
                            if href.startswith("/doi/10.1079/cabicompendium"):
                                absolut_href = f"{base_domain}{href}"
                                driver.get(absolut_href)
                                visited_urls.add(absolut_href)
                                
                                WebDriverWait(driver, 60).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                                )
                                time.sleep(random.uniform(6, 10))
                                soup = BeautifulSoup(driver.page_source, "html.parser")

                                abstracts = soup.select_one("#abstracts")
                                body = soup.select_one("#bodymatter>.core-container")
                                abstract_text = abstracts.get_text(strip=True) if abstracts else "No abstract found"
                                body_text = body.get_text(strip=True) if body else "No body found"

                                if abstract_text or body_text:
                                    content_accumulated = f"{abstract_text}\n\n\n{body_text}"
                                    content_accumulated += "-" * 100 + "\n\n"

                                    print(f"Página procesada y guardada: {absolut_href}")
                                    if content_accumulated:
                                        object_id = fs.put(
                                            content_accumulated.encode("utf-8"),
                                            source_url=absolut_href,
                                            scraping_date=datetime.now(),
                                            Etiquetas=["planta", "plaga"],
                                            contenido=content_accumulated,
                                            url=url
                                        )
                                        total_scraped_links += 1
                                        logger.info(f"Archivo almacenado en MongoDB con object_id: {object_id}")
                                        existing_versions = list(fs.find({"source_url": absolut_href}).sort("scraping_date", -1))
                                        if len(existing_versions) > 1:
                                            oldest_version = existing_versions[-1]
                                            file_id = oldest_version._id  
                                            fs.delete(file_id)  
                                            logger.info(f"Se eliminó la versión más antigua con object_id: {file_id}")

                                        scraping_exitoso = True
                                visited_counts+=1
                                driver.back()
                                WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "ul.rlist li")
                                    )
                                )
                                time.sleep(random.uniform(3, 6))
                            else:
                                non_scraped_urls.append(href)
                    if visited_counts >= max_visits:
                        logger.info("🔴 Se alcanzó el límite de 5 enlaces visitados. No se paginará más.")
                        break
                    try:
                        next_page_button = driver.find_element(
                            By.CSS_SELECTOR,
                            ".pagination__btn.pagination__btn--next.icon-arrow_r",
                        )
                        next_page_link = next_page_button.get_attribute("href")

                        if next_page_link:
                            logger.info(
                                f"Yendo a la siguiente página: {next_page_link}"
                            )
                            driver.get(next_page_link)
                        else:
                            logger.info(
                                "No hay más páginas disponibles. Finalizando búsqueda para esta palabra clave."
                            )
                            break
                    except NoSuchElementException:
                        logger.info(
                            "No se encontró el botón para la siguiente página. Finalizando búsqueda para esta palabra clave."
                        )
                        driver.get(url)
                        break
                except TimeoutException:
                    logger.warning(
                        f"No se encontraron resultados para '{keyword}' después de esperar."
                    )
                    break

        if scraping_exitoso:

            all_scraper = (
            f"Total enlaces scrapeados: {total_scraped_links}\n"
            f"URLs scrapeadas:\n" + "\n".join(scraped_urls) + "\n\n"
            f"Total enlaces no scrapeados: {len(non_scraped_urls)}\n"
            f"URLs no scrapeadas:\n" + "\n".join(non_scraped_urls) + "\n"
        )
        response = process_scraper_data(all_scraper, url, sobrenombre)
        return response
        
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        driver.quit()
        logger.info("Navegador cerrado")
