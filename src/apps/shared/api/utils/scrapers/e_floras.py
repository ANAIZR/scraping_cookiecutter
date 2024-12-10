from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pymongo import MongoClient
import gridfs
import os
from ..functions import save_scraped_data
from rest_framework.response import Response
from rest_framework import status

def scrape_e_floras(
    url=None,
    page_principal=None,
    wait_time=None,
    sobrenombre=None,
    next_page_selector=None,
):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    client = MongoClient("mongodb://localhost:27017/")
    db = client["scrapping-can"]
    collection = db["collection"]
    fs = gridfs.GridFS(db)
    all_scrapped = ""
    is_first_page = True
    try:
        driver.get(url)
        
        submit = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#TableMain #ucEfloraHeader_tableHeaderWrapper tbody tr td:nth-of-type(2) input[type='submit']",
                )
            )
        )
        submit.click()

        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "#ucFloraTaxonList_panelTaxonList span table",
                )
            )
        )

        def scrape_page():
            nonlocal all_scrapped
            content = BeautifulSoup(driver.page_source, "html.parser")
            content_container = content.select_one("#ucFloraTaxonList_panelTaxonList span table")

            tr_tags = content_container.find_all("tr")

            for i, tr_tag in enumerate(tr_tags):
                if is_first_page:
                    if i < 2 or i >= len(tr_tags) - 2:
                        continue
                try:
                    td_tags = tr_tag.select("td:nth-child(2)")
                    if td_tags:
                        a_tags = td_tags[0].find("a")
                        if a_tags:
                            href = a_tags.get("href")
                            page = page_principal + href
                            if href:
                                driver.get(page)
                                WebDriverWait(driver, wait_time).until(
                                    EC.presence_of_element_located(
                                        (By.CSS_SELECTOR, "#TableMain #panelTaxonTreatment #lblTaxonDesc")
                                    )
                                )
                                content = BeautifulSoup(driver.page_source, "html.parser")
                                content_container = content.select_one("#TableMain #panelTaxonTreatment #lblTaxonDesc")

                                if content_container:
                                    all_scrapped += f"Contenido de la página {href}:\n"
                                    cleaned_text = " ".join(content_container.text.split()) 
                                    all_scrapped += cleaned_text + "\n\n"
                                
                                driver.back()
                except Exception as e:
                    print(f"Error procesando la fila {i}: {e}")

        scrape_page()
        is_first_page = False

        if next_page_selector:
            try:
                next_page_button = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#TableMain #ucFloraTaxonList_panelTaxonList  span a[title='Page 2']")
                    )
                )
                next_page_button.click()
                WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#ucFloraTaxonList_panelTaxonList span table"))
                )
                scrape_page()
            except Exception as e:
                print(f"Error al navegar a la siguiente página: {e}")

        if all_scrapped.strip():
            response_data = save_scraped_data(
                all_scrapped, url, sobrenombre, collection, fs
            )

            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
    except Exception as e:
        print(f"Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
