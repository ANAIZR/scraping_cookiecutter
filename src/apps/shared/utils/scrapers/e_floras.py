from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)
from rest_framework.response import Response
from rest_framework import status

logger = get_logger("Iniciando")

def scraper_e_floras(
    url,
    sobrenombre
):
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    page_principal ="http://www.efloras.org/"
    collection, fs = connect_to_mongo()

    all_scraper = ""
    is_first_page = True
    total_td_found = 0
    total_td_scraped = 0

    try:
        driver.get(url)

        submit = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#TableMain #ucEfloraHeader_tableHeaderWrapper tbody tr td:nth-of-type(2) input[type='submit']",
                )
            )
        )
        submit.click()

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#ucFloraTaxonList_panelTaxonList span table",
                )
            )
        )

        def scraper_page():
            nonlocal all_scraper, total_td_found, total_td_scraped
            content = BeautifulSoup(driver.page_source, "html.parser")
            content_container = content.select_one(
                "#ucFloraTaxonList_panelTaxonList span table"
            )

            tr_tags = content_container.find_all("tr")

            for i, tr_tag in enumerate(tr_tags):
                if is_first_page:
                    if i < 2 or i >= len(tr_tags) - 2:
                        continue
                try:
                    td_tags = tr_tag.select("td:nth-child(2)")
                    total_td_found += len(td_tags)  
                    if td_tags:
                        for td in td_tags:
                            a_tags = td.find("a")
                            if a_tags:
                                href = a_tags.get("href")
                                page = page_principal + href
                                if href:
                                    driver.get(page)
                                    WebDriverWait(driver, 30).until(
                                        EC.presence_of_element_located(
                                            (
                                                By.CSS_SELECTOR,
                                                "#TableMain #panelTaxonTreatment #lblTaxonDesc",
                                            )
                                        )
                                    )
                                    content = BeautifulSoup(driver.page_source, "html.parser")
                                    content_container = content.select_one(
                                        "#TableMain #panelTaxonTreatment #lblTaxonDesc"
                                    )

                                    if content_container:
                                        all_scraper += f"Contenido de la página {href}:\n"
                                        cleaned_text = " ".join(content_container.text.split())
                                        all_scraper += cleaned_text + "\n\n"
                                        total_td_scraped += 1  

                                    driver.back()
                except Exception as e:
                    print(f"Error procesando la fila {i}: {e}")

        scraper_page()
        is_first_page = False
        next_page_selector = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#TableMain #ucFloraTaxonList_panelTaxonList  span a[title='Page 2']"
                        )
                    )
                )
        if next_page_selector:
            try:
                next_page_button = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "#TableMain #ucFloraTaxonList_panelTaxonList  span a[title='Page 2']",
                        )
                    )
                )
                next_page_button.click()
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#ucFloraTaxonList_panelTaxonList span table")
                    )
                )
                scraper_page()
            except Exception as e:
                print(f"Error al navegar a la siguiente página: {e}")

        logger.info(f"Total enlaces encontrados: {total_td_found}")
        logger.info(f"Total enlaces scrapeados: {total_td_scraped}")

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response
    except Exception as e:
        print(f"Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
        logger.info("Navegador cerrado")

