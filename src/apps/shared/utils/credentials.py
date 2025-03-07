import time
import random
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os

load_dotenv()

CREDENTIALS = {
    "email": os.getenv("EMAIL"),
    "password": os.getenv("PASSWORD")
}

def login_cabi_scienceconnect(driver):

    logger = logging.getLogger("LOGIN_CABI")

    try:
        driver.get("https://cabi.scienceconnect.io/login")
        time.sleep(random.uniform(3, 6))

        email_input = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#email-input"))
        )

        if email_input:
            email_input.send_keys(CREDENTIALS["email"])
            time.sleep(random.uniform(1, 3))

            email_input.submit()
            time.sleep(random.uniform(1, 3))

            password_input = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#pass-input"))
            )
            time.sleep(random.uniform(1, 3))

            if password_input:
                password_input.send_keys(CREDENTIALS["password"])
                password_input.submit()
                time.sleep(random.uniform(1, 3))
                return True
            else:
                return False

    except Exception as e:
        logger.error(f"Error al iniciar sesión: {e}")
        return False
