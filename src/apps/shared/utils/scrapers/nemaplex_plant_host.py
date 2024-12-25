from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
)

def scraper_nemaplex_plant_host(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    driver = initialize_driver()
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""

    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "DropDownList1"))
        )

        dropdown = Select(driver.find_element(By.ID, "DropDownList1"))

        for index in range(len(dropdown.options)):

            dropdown.select_by_index(index)

            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "GridView1"))
                )

                page_soup = BeautifulSoup(driver.page_source, "html.parser")
                table = page_soup.find("table", {"id": "GridView1"})
                if table:
                    
                    rows = table.find_all("tr")
                    for row in rows:
                        columns = row.find_all("td")
                        row_data = [col.get_text(strip=True) for col in columns]
                        all_scraper += (
                            " ".join(row_data) + "\n"
                        ) 
                
            except:
                print(f"Error inesperado para la opción {index + 1}. Excepción: {str(e)}")

            driver.back()

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "DropDownList1"))
            )

        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        logger.info("Scraping completado exitosamente.")
        return response


    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        driver.quit()
