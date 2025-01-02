import os
import hashlib
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status
import logging
from pymongo import MongoClient
import gridfs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import random
from selenium.common.exceptions import TimeoutException

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/89.0.4389.114",
]

# Configuración de directorio de salida
OUTPUT_DIR = "c:/web_scraper_files"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    logger.addHandler(ch)
    return logger


def initialize_driver():
    logger = get_logger("scraper")
    try:
        logger.info("Inicializando el navegador.")
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        random_user_agent = random.choice(USER_AGENTS)
        options.add_argument(f"user-agent={random_user_agent}")
        logger.info(f"Usando User-Agent: {random_user_agent}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        logger.info("Navegador iniciado correctamente.")
        return driver
    except Exception as e:
        logger.error(f"Error al inicializar el navegador: {str(e)}")
        raise


def connect_to_mongo(db_name="scrapping-can", collection_name="collection"):
    logger = get_logger("mongo_connection")
    try:
        logger.info(f"Conectando a la base de datos MongoDB: {db_name}")
        client = MongoClient("mongodb://localhost:27017/")
        db = client[db_name]
        fs = gridfs.GridFS(db)
        logger.info(f"Conexión a MongoDB establecida con éxito: {db_name}")
        return db[collection_name], fs
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        raise


def generate_directory(output_dir, url):
    logger = get_logger("generar directorio")

    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        folder_name = (
            url.split("//")[-1].replace("/", "_").replace("?", "_").replace("=", "_")
            + "_"
            + url_hash[:8]
        )
        folder_path = os.path.join(output_dir, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        logger.info(f"Directorio generado: {folder_path}")
        return folder_path
    except Exception as e:
        logger.error(f"Error al generar el directorio: {str(e)}")
        raise


def get_next_versioned_filename(folder_path, base_name="archivo"):
    logger = get_logger("generar siguiente versión de archivo")

    try:
        version = 0
        while True:
            file_name = f"{base_name}_v{version}.txt"
            file_path = os.path.join(folder_path, file_name)
            if not os.path.exists(file_path):
                return file_path
            version += 1
    except Exception as e:
        logger.error(f"Error al generar el nombre del archivo: {str(e)}")
        raise


def delete_old_documents(url, collection, fs, limit=2):
    logger = get_logger("eliminar documentos antiguos")
    try:
        docs_for_url = collection.find({"Url": url}).sort("Fecha_scraper", -1)
        docs_count = collection.count_documents({"Url": url})

        if docs_count > limit:
            docs_to_delete = list(docs_for_url)[limit:]
            for doc in docs_to_delete:
                collection.delete_one({"_id": doc["_id"]})
                fs.delete(doc["Objeto"])

            logger.info(
                f"Se han eliminado {docs_count - limit} documentos antiguos para la URL {url}."
            )
        else:
            logger.info(
                f"No se encontraron documentos para eliminar. Se mantienen {docs_count} documentos para la URL {url}."
            )

        return docs_count > limit
    except Exception as e:
        logger.error(f"Error al eliminar documentos antiguos: {str(e)}")
        raise


def save_scraper_data(all_scraper, url, sobrenombre, collection, fs):
    logger = get_logger("guardar datos del scraper")
    try:
        folder_path = generate_directory(OUTPUT_DIR, url)
        file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(all_scraper)

        with open(file_path, "rb") as file_data:
            object_id = fs.put(file_data, filename=os.path.basename(file_path))

            data = {
                "Objeto": object_id,
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Etiquetas": ["planta", "plaga"],
            }

            collection.insert_one(data)
            logger.info(f"Datos guardados en MongoDB para la URL: {url}")

            delete_old_documents(url, collection, fs)

            response_data = {
                "Tipo": "Web",
                "Url": url,
                "Fecha_scraper": data["Fecha_scraper"],
                "Etiquetas": data["Etiquetas"],
                "Mensaje": "Los datos han sido scrapeados correctamente.",
            }

        return response_data
    except Exception as e:
        logger.error(f"Error al guardar datos del scraper: {str(e)}")
        raise


def process_scraper_data(all_scraper, url, sobrenombre, collection, fs):
    logger = get_logger("procesar datos del scraper")
    try:
        if all_scraper.strip():
            response_data = save_scraper_data(
                all_scraper, url, sobrenombre, collection, fs
            )
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            logger.warning(f"No se encontraron datos para scrapear en la URL: {url}")
            return Response(
                {
                    "Tipo": "Web",
                    "Url": url,
                    "Mensaje": "No se encontraron datos para scrapear.",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
            },
            status=status.HTTP_408_REQUEST_TIMEOUT,
        )
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "Ocurrió un error al procesar los datos.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return Response(
            {
                "Tipo": "Web",
                "Url": url,
                "Mensaje": "No se pudo conectar a la página web.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
