from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.response import Response
from rest_framework import status
from selenium.common.exceptions import StaleElementReferenceException
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)


def scraper_delta(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()
    base_url = "https://www.delta-intkey.com/"

    # Contadores
    total_enlaces_encontrados = 0
    total_enlaces_scrapeados = 0

    try:
        driver.get(url)

        while True:
            body = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            if body:
                print("Elemento body encontrado")
                elementos_p = body.find_elements(By.CSS_SELECTOR, "p")
                enlaces_disponibles = False  # Bandera para detener el bucle

                for p in elementos_p:
                    try:
                        enlace = p.find_element(By.CSS_SELECTOR, "a")
                        if enlace:
                            href = enlace.get_attribute("href")
                            if (
                                href
                                and href.startswith(f"{base_url}")
                                and href not in processed_links
                            ):
                                enlaces_disponibles = True
                                processed_links.add(href)
                                total_enlaces_encontrados += 1
                                print(f"Enlace encontrado en la URL principal: {href}")
                                driver.get(href)

                                body_url = WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "body")
                                    )
                                )
                                if body_url:
                                    elementos_p_url = body_url.find_elements(
                                        By.CSS_SELECTOR, "p"
                                    )
                                    for p_url in elementos_p_url:
                                        try:
                                            enlace_url = p_url.find_element(
                                                By.CSS_SELECTOR, "a"
                                            )
                                            if enlace_url:
                                                href_url = enlace_url.get_attribute(
                                                    "href"
                                                )
                                                if (
                                                    href_url
                                                    and href_url.startswith(
                                                        f"{base_url}"
                                                    )
                                                    and href_url.endswith(".htm")
                                                    and href_url not in processed_links
                                                ):
                                                    processed_links.add(href_url)
                                                    total_enlaces_encontrados += 1
                                                    driver.get(href_url)

                                                    body = WebDriverWait(
                                                        driver, 30
                                                    ).until(
                                                        EC.presence_of_element_located(
                                                            (By.CSS_SELECTOR, "body")
                                                        )
                                                    )
                                                    if body:
                                                        total_enlaces_scrapeados += 1
                                                        all_scraper += f"{href_url}\n"
                                                        all_scraper += (
                                                            f"{body.text}\n\n"
                                                        )
                                                        all_scraper += f"{'='*50}\n\n"
                                                    driver.back()
                                        except Exception as e:
                                            print(f"Error al procesar sub enlace: {e}")
                                            continue

                                total_enlaces_scrapeados += 1
                                driver.back()

                                body = WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "body")
                                    )
                                )
                                break
                    except StaleElementReferenceException:
                        print("Referencia obsoleta al elemento <p>, saltando...")
                        continue
                    except Exception as e:
                        print(f"Error al procesar enlace en <p>: {e}")
                        continue

                if not enlaces_disponibles:
                    break

            else:
                print("Elemento body no encontrado")
                break

        logger.info(f"Total de enlaces encontrados: {total_enlaces_encontrados}")
        logger.info(f"Total de enlaces scrapeados: {total_enlaces_scrapeados}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        print(f"Error general en el proceso de scraping: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error al cerrar el navegador: {e}")
