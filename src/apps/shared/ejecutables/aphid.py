from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import time
import threading

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

url = 'http://aphid.aphidnet.org/'

driver.get(url)
def scraped_data():
    try:
        nav = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'nav.main #nav li:nth-child(4) a[href="species_list.php"]'))
        )
        nav.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'content'))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        faq_div = soup.find('div', class_='grid_8').find('div', id='faq')

        h3_tags = faq_div.find_all('h3')

        for h3 in h3_tags:
            h3_id = h3.get('id')

            ul_tag = h3.find_next('ul')
            
            if ul_tag:
                li_tags = ul_tag.find_all('li')
                
                for li in li_tags:
                    a_tag = li.find('a', href=True)
                    if a_tag:
                        href = a_tag['href']
                        text = a_tag.get_text(strip=True)
                        
                        print(f"Letra: {h3_id}, Enlace: {href}, Texto: {text}")

                        driver.get(url+'/'+href)
                        
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, 'content'))
                        )

                        page_soup = BeautifulSoup(driver.page_source, 'html.parser')

                        content = page_soup.find(id='content')

                        if content:
                            print(f"Contenido de la página {href}:")
                            print(content.get_text(strip=True))

    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        driver.quit()
scraping_thread = threading.Thread(target=scraped_data)

scraping_thread.start()