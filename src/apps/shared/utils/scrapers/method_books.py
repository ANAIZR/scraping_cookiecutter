from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    initialize_driver,
    generate_directory,
)
from rest_framework.response import Response
from rest_framework import status
import os
import random
import json
import time
from bs4 import BeautifulSoup
import traceback


def scraper_method_books(url, sobrenombre):
    try:
        driver = initialize_driver()
        driver.get(
            url
        )  # acceder a la URL . (La url lo estas mandando desde el fixture)
        print("Intentado")
        
    except:
        print("Error")
