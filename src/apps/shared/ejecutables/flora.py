import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Configuración de Selenium
chrome_options = Options()
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("--ignore-ssl-errors=yes")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL de la página
url = "https://www.cabidigitallibrary.org/product/qc"

# Intentar cargar cookies guardadas si existen
try:
    driver.get(url)
    with open("cookies.pkl", "rb") as file:
        cookies = pickle.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.refresh()
    print("Cookies cargadas correctamente.")
except FileNotFoundError:
    print("No se encontraron cookies guardadas.")

# Ahora realiza las interacciones que necesitas
try:
    # Si las cookies no estaban guardadas, se procede con la verificación
    try:
        cookie_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#onetrust-pc-btn-handler"))
        )
        cookie_button.click()
        print("Botón de 'Aceptar Cookies' clicado correctamente.")

        preferences_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#accept-recommended-btn-handler"))
        )
        preferences_button.click()
        print("Botón de 'Guardar preferencias' clicado correctamente.")
        
        # Guardar cookies luego de aceptar los popups
        cookies = driver.get_cookies()
        with open("cookies.pkl", "wb") as file:
            pickle.dump(cookies, file)
        print("Cookies guardadas correctamente.")

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".quick-search__form"))
        )
        
        search_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.quick-search__button"))
        )
        
        search_input = driver.find_element(By.ID, "AllFieldb117445f-c250-4d14-a8d9-7c66d5b6a4800")
        search_input.send_keys("Grapevine")  
        
        search_button.click()
        print("Botón de búsqueda clicado correctamente.")

    except Exception as e:
        print(f"Error: {e}")

except Exception as e:
    print(f"Ocurrió un error: {e}")
finally:
    driver.quit()
