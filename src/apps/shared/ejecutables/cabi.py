import os
import pickle
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from bs4 import BeautifulSoup


def sanitize_filename(filename):
    sanitized = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    return sanitized[:100] 


try:
    driver = uc.Chrome()
    base_url = "https://www.cabidigitallibrary.org/product/qc"
    driver.get(base_url)

    sleep(5)

    try:
        with open("cookies.pkl", "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()
        print("Cookies cargadas correctamente.")
    except FileNotFoundError:
        print("No se encontraron cookies guardadas.")

    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-pc-btn-handler"))
        )
        cookie_button.click()
        print("Botón de 'Aceptar Cookies' clicado correctamente.")
    except Exception:
        print("El botón de 'Aceptar Cookies' no apareció o no fue clicable.")

    try:
        preferences_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#accept-recommended-btn-handler"))
        )
        preferences_button.click()
        print("Botón de 'Guardar preferencias' clicado correctamente.")
    except Exception:
        print("El botón de 'Guardar preferencias' no apareció o no fue clicable.")

    print("Empezaremos a buscar el código...")

    while True:
        try:
            search_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.page-top-banner div.container div.quick-search button.quick-search__button"))
            )
            print("Botón de búsqueda encontrado.")
            search_button.click()
            print("Botón de búsqueda clicado correctamente.")
        except Exception as e:
            print(f"Error al realizar la búsqueda: {e}")

        try:
            print("Esperando a que el contenido sea visible...")
            content = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.row > div.col-sm-8 form#frmIssueItems > ul.rlist",
                    )
                )
            )
            print("Contenido encontrado.")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("ul.rlist li")

            base_folder_name = sanitize_filename(base_url.split("//")[1].split("/")[0])
            if not os.path.exists(base_folder_name):
                os.makedirs(base_folder_name)

            for item in items:
                content_div = item.find("div", class_="issue-item__content")
                if content_div:
                    first_link = content_div.find("a")
                    if first_link:
                        href = first_link.get("href")
                        if href:
                            print(f"Enlace encontrado: {href}")
                            full_url = href if href.startswith("http") else f"https://www.cabidigitallibrary.org{href}"
                            link_folder_name = sanitize_filename(full_url)
                            link_folder_path = os.path.join(base_folder_name, link_folder_name)
                            if not os.path.exists(link_folder_path):
                                os.makedirs(link_folder_path)

                            driver.get(full_url)
                            sleep(3)

                            print(f"Entrando a la página: {full_url}")

                            try:
                                abstracts_element = WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "article div#abstracts section#abstract",
                                        )
                                    )
                                )
                                body_element = WebDriverWait(driver, 30).until(
                                    EC.presence_of_element_located(
                                        (
                                            By.CSS_SELECTOR,
                                            "article section#bodymatter div.core-container",
                                        )
                                    )
                                )
                                print("Página cargada correctamente.")
                                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                                abstracts = page_soup.select_one("article div#abstracts section#abstract")
                                body = page_soup.select_one("article section#bodymatter div.core-container")

                                abstract_text = abstracts.get_text(strip=True) if abstracts else "No abstract found"
                                body_text = body.get_text(strip=True) if body else "No body found"

                                contenido = f"{abstract_text}\n\n\n{body_text}"
                                file_path = os.path.join(link_folder_path, "contenido.txt")
                                with open(file_path, "w", encoding="utf-8") as file:
                                    file.write(contenido)
                                print(f"Contenido guardado en {file_path}")
                            except Exception as e:
                                print(f"Error al esperar el contenido de la nueva página: {e}")

            try:
                driver.get(base_url)
                sleep(3)  

                search_button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.page-top-banner div.container div.quick-search button.quick-search__button"))
                )
                print(f"Botón de búsqueda encontrado para la siguiente página.")
                search_button.click()
                print(f"Botón de búsqueda clicado para la siguiente página.")
            except Exception as e:
                print(f"Error al hacer clic en el botón de búsqueda para la siguiente página: {e}")

            try:
                next_page_button = driver.find_element(By.CSS_SELECTOR, "nav.pagination li.next a")
                next_page_link = next_page_button.get_attribute("href")
                if next_page_link:
                    print(f"Navegando a la siguiente página: {next_page_link}")
                    driver.get(next_page_link)  
                    sleep(3)
                else:
                    print("No hay más páginas disponibles.")
                    break
            except Exception:
                print("No se encontró el siguiente enlace de página.")
                break

        except Exception as e:
            print(f"Error en la navegación o extracción de contenido: {e}")
            break

finally:
    driver.quit()
