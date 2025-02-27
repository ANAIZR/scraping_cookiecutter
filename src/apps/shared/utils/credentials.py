import time
import random
import logging
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger("LOGIN_CABI")

# Credenciales obtenidas del archivo .env
CREDENTIALS = {
    "email": os.getenv("EMAIL"),
    "password": os.getenv("PASSWORD")
}

def save_html_and_screenshot(driver, filename):
    """
    🚀 Guarda el HTML actual y una captura de pantalla para depuración.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot(filename.replace(".html", ".png"))
        logger.info(f"📄 Guardado: {filename}")
    except Exception as e:
        logger.error(f"❌ Error al guardar HTML y captura: {e}")

def force_rendering(driver, filename):
    """
    🚀 Forza la ejecución completa del DOM ejecutando todos los scripts
    y simulando interacción humana.
    """
    logger.info("⏳ Forzando la renderización completa del DOM...")

    try:
        # Esperar que la página cargue completamente
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)

        # **Ejecutar JavaScript en la página**
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll hasta abajo
        time.sleep(2)

        # **Simular interacción de usuario**
        actions = ActionChains(driver)
        actions.move_by_offset(5, 5).perform()  # Mover el mouse un poco
        time.sleep(1)
        actions.send_keys(Keys.TAB).perform()  # Presionar TAB para cambiar de foco
        time.sleep(1)
        actions.send_keys(Keys.ENTER).perform()  # Simular ENTER
        time.sleep(2)

        # **Ejecutar todos los scripts de la página**
        driver.execute_script("""
            var scripts = document.getElementsByTagName('script');
            for (var i = 0; i < scripts.length; i++) {
                if (!scripts[i].src) {
                    try { eval(scripts[i].innerText); } catch (e) {}
                }
            }
        """)

        time.sleep(5)  # Esperar a que los scripts terminen de ejecutarse
        logger.info("✅ Renderización forzada completada.")
        save_html_and_screenshot(driver, filename)

    except Exception as e:
        logger.error(f"❌ Error en la renderización del DOM: {e}")

def login_cabi_scienceconnect(driver):
    """
    🚀 Función mejorada para hacer login en CABI ScienceConnect.
    - Guarda el HTML **justo al entrar a /login/password**.
    - Luego intenta encontrar el campo de contraseña.
    """
    try:
        logger.info("➡ Accediendo a la página de login...")
        driver.get("https://cabi.scienceconnect.io/login")
        time.sleep(random.uniform(3, 6))

        # **Esperar que Cloudflare termine**
        logger.info("⏳ Esperando a que Cloudflare termine...")
        WebDriverWait(driver, 30).until(
            lambda d: "Verificar que usted es un ser humano" not in d.page_source
        )

        # **Guardar HTML inicial de la página de login**
        save_html_and_screenshot(driver, "html_initial_login.html")

        # **Buscar el input de email**
        try:
            logger.info("➡ Buscando el campo de email...")
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#email-input"))
            )
            logger.info("✅ Campo de email encontrado.")
        except Exception:
            logger.error("❌ No se encontró el campo de email. Verifica el HTML guardado.")
            return False

        # **Ingresar email**
        logger.info(f"✉ Ingresando email: {CREDENTIALS['email']}")
        email_input.send_keys(CREDENTIALS["email"])
        time.sleep(random.uniform(1, 3))

        # **Clic en el botón de continuar**
        try:
            continue_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            driver.execute_script("arguments[0].click();", continue_button)
            time.sleep(random.uniform(3, 6))
            logger.info("✅ Botón de 'Continuar' presionado.")
        except Exception:
            logger.warning("⚠ No se encontró el botón de 'Continuar'. Intentando enviar con Enter.")
            email_input.submit()
            time.sleep(random.uniform(3, 6))

        # **Guardar el HTML tras ingresar el email**
        save_html_and_screenshot(driver, "html_after_email.html")

        # **Esperar el cambio de URL a la página de contraseña**
        logger.info("⏳ Esperando el cambio a la página de contraseña...")
        WebDriverWait(driver, 15).until(
            lambda d: "/login/password" in d.current_url
        )

        # **Guardar el HTML justo al entrar a /login/password**
        save_html_and_screenshot(driver, "html_password_initial.html")

        # **Forzar renderización del DOM en /login/password**
        force_rendering(driver, "html_after_password.html")

        # **Intentar encontrar el campo de contraseña**
        password_input = None
        search_methods = [
            (By.CSS_SELECTOR, "#pass-input"),
            (By.ID, "pass-input"),
            (By.NAME, "password"),
            (By.XPATH, "//input[@type='password']"),
        ]

        for method, selector in search_methods:
            try:
                logger.info(f"🔎 Buscando contraseña con método: {method} - {selector}")
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((method, selector))
                )
                if password_input:
                    break
            except Exception:
                continue

        # **Si no se encontró el campo, capturar pantalla**
        if not password_input:
            save_html_and_screenshot(driver, "html_password_not_found.html")
            logger.error("❌ No se encontró el campo de contraseña. Verifica los archivos HTML guardados.")
            return False

        logger.info("✅ Campo de contraseña encontrado.")
        logger.info(f"🔑 Ingresando contraseña: {CREDENTIALS['password'][:3]}*** (oculta por seguridad)")
        password_input.send_keys(CREDENTIALS["password"])
        password_input.submit()
        time.sleep(random.uniform(3, 6))

        logger.info("✅ Inicio de sesión exitoso en CABI ScienceConnect.")
        return True

    except Exception as e:
        save_html_and_screenshot(driver, "html_error.html")
        logger.error(f"❌ Error inesperado al iniciar sesión: {e}")
        return False
