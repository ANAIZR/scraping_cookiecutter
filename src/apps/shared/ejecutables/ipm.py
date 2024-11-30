from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = "http://pnwhandbooks.org/plantdisease/"

try:
    driver.get(url)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table:nth-child(3)"))
    )
    
    table_content = driver.find_element(By.CSS_SELECTOR, "table:nth-child(3)")
    
    paragraphs = table_content.find_elements(By.CSS_SELECTOR, "p")
    
    for paragraph in paragraphs:
        text = paragraph.text
        print(f"Texto: {text}")
        
        links = paragraph.find_elements(By.CSS_SELECTOR, "a")
        for link in links:
            href = link.get_attribute("href")
            print(f"  Enlace: {href}")
    
    time.sleep(5)

except Exception as e:
    print(f"Error al cargar la página principal: {e}")

finally:
    driver.quit()
