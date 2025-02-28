import time
import random
import logging
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configurar logging
logger = logging.getLogger("LOGIN_CABI")

# Credenciales obtenidas del archivo .env
CREDENTIALS = {
    "email": os.getenv("EMAIL"),
    "password": os.getenv("PASSWORD")
}

def login_cabi_scienceconnect(driver):
    """
    🚀 Función para hacer login en CABI ScienceConnect.
    Guarda capturas y HTML antes de encontrar los campos de email y contraseña.
    """
    try:
        logger.info("➡ Accediendo a la página de login...")
        driver.get("https://cabi.scienceconnect.io/login")
        time.sleep(random.uniform(3, 6))

        # **Esperar que Cloudflare termine**
        logger.info("⏳ Esperando a que Cloudflare termine...")
        WebDriverWait(driver, 60).until(
            lambda d: "Verificar que usted es un ser humano" not in d.page_source
        )

        # **Guardar el HTML y la captura antes de buscar el campo de email**
        with open("email.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("email.png")
        logger.info("📄 Guardado 'email.html' y 'email.png'.")

        # **Buscar el input de email**
        try:
            logger.info("➡ Buscando el campo de email...")
            email_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#email-input"))
            )
        except Exception:
            logger.error("❌ No se encontró el campo de email. Verifica si la página cambió.")
            return False

        if email_input:
            logger.info("✅ Campo de email encontrado.")
            email_input.send_keys(CREDENTIALS["email"])
            time.sleep(random.uniform(1, 3))
            email_input.submit()
            time.sleep(random.uniform(3, 6))

        # **Guardar el HTML y la captura antes de buscar el campo de contraseña**
        with open("password.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("password.png")
        logger.info("📄 Guardado 'password.html' y 'password.png'.")

        # **Buscar el input de contraseña**
        try:
            logger.info("➡ Buscando el campo de contraseña...")
            password_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#pass-input"))
            )
        except Exception:
            logger.error("❌ No se encontró el campo de contraseña. Es posible que el email sea incorrecto.")
            return False

        if password_input:
            logger.info("✅ Campo de contraseña encontrado.")
            password_input.send_keys(CREDENTIALS["password"])
            password_input.submit()
            time.sleep(random.uniform(3, 6))

        # **Verificar si el login fue exitoso**
        if "incorrect" in driver.page_source.lower() or "error" in driver.page_source.lower():
            logger.error("❌ Error al iniciar sesión: La contraseña podría ser incorrecta.")
            return False

        logger.info("✅ Inicio de sesión exitoso en CABI ScienceConnect.")
        return True

    except Exception as e:
        logger.error(f"❌ Error inesperado al iniciar sesión: {e}")
        return False
