import os
import hashlib
from datetime import datetime
import logging
import random
import undetected_chromedriver as uc
import time
import pypdf
from pymongo import MongoClient
import gridfs
import requests
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from pymongo.errors import PyMongoError


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/89.0.4389.114",
]

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME")
OUTPUT_DIR = os.path.expanduser(os.getenv("OUTPUT_DIR"))
LOG_DIR = os.path.expanduser(os.getenv("LOG_DIR"))
LOAD_KEYWORDS = os.path.expanduser(os.getenv("LOAD_KEYWORDS"))
load_dotenv()

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def load_keywords(file_name, base_dir=LOAD_KEYWORDS):
    logger = get_logger("CARGAR PALABRAS CLAVE")
    try:
        file_path = os.path.join(base_dir, file_name)
        if not os.path.exists(file_path):
            logger.error(f"El archivo '{file_path}' no existe.")
            raise FileNotFoundError(f"El archivo '{file_path}' no existe.")
        
        with open(file_path, "r", encoding="utf-8") as file:
            content = [line.strip() for line in file if line.strip()] 
        return content
    except FileNotFoundError as e:
        logger.error(e)
        return None
    except Exception as e:
        logger.error(f"Error leyendo el archivo '{file_name}': {e}")
        return None



def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_logger(name, level=logging.DEBUG, output_dir=LOG_DIR):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    log_file = "app.log"
    folder_path = os.path.abspath(output_dir)  
    os.makedirs(folder_path, exist_ok=True) 

    log_path = os.path.join(folder_path, log_file)

    try:
        if not os.path.exists(log_path):
            with open(log_path, "w", encoding="utf-8") as f:
                pass

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        fh.setFormatter(formatter)

        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(ch)
            logger.addHandler(fh)

    except Exception as e:
        print(f"Error al configurar el logger: {e}")
        raise

    return logger

def driver_init():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    #Nueva forma para "engañar" a la página
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.90 Safari/537.36"
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(f"user-agent={user_agent}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    return driver


def initialize_driver(retries=3):
    logger = get_logger("INICIALIZANDO EL DRIVER")

    for attempt in range(retries):
        try:
            logger.info(
                f"Intento {attempt + 1} de inicializar el navegador con Selenium."
            )
            options = uc.ChromeOptions()
            options.binary_location = "/usr/bin/google-chrome"
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--allow-insecure-localhost")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--start-maximized")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")        
            random_user_agent = get_random_user_agent()
            options.add_argument(f"user-agent={random_user_agent}")
            logger.info(f"Usando User-Agent: {random_user_agent}")

            driver = uc.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )

            driver.set_page_load_timeout(600)
            logger.info("Navegador iniciado correctamente con Selenium.")
            return driver
        except Exception as e:
            logger.error(f"Error al iniciar el navegador: {e}")

            if attempt < retries - 1:
                time.sleep(5)
            else:
                raise

def initialize_driver_cabi(retries=3):
    logger = get_logger("INICIALIZANDO EL DRIVER")

    for attempt in range(retries):
        try:
            logger.info(f"Intento {attempt + 1} de inicializar el navegador en Selenium Server Remoto.")

            options = webdriver.ChromeOptions()
            options.add_argument("--disable-gpu")
            options.add_argument("--allow-insecure-localhost")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--start-maximized")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            #options.add_argument("--headless=new")  
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-software-rasterizer")

            random_user_agent = get_random_user_agent()
            options.add_argument(f"user-agent={random_user_agent}")
            logger.info(f"Usando User-Agent: {random_user_agent}")

            driver = webdriver.Remote(
                command_executor="http://100.122.137.82:4444/wd/hub", 
                options=options
            )

            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")  # 🔥 Ocultar propiedad webdriver

            driver.set_page_load_timeout(600)
            logger.info("✅ Conexión exitosa con Selenium Server en Windows.")
            return driver
        except Exception as e:
            logger.error(f"❌ Error al conectar con Selenium Server en Windows: {e}")

            if attempt < retries - 1:
                time.sleep(5)
            else:
                raise




def connect_to_mongo():

    logger = get_logger("MONGO_CONNECTION")

    try:
        if not all([MONGO_URI, MONGO_DB_NAME]):
            raise ValueError("⚠️ Faltan variables de entorno en el archivo .env")

        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        fs = gridfs.GridFS(db)

        logger.info(f"✅ Conexión a MongoDB establecida correctamente: {MONGO_DB_NAME}")
        return db, fs  

    except Exception as e:
        logger.error(f"❌ Error al conectar a MongoDB: {str(e)}")
        raise

def save_to_mongo(collection_name, content_text, href, url):


    logger = get_logger("GUARDAR EN MONGO")

    if not content_text:
        logger.warning("⚠️ No hay contenido para guardar en MongoDB.")
        return None

    try:
        db, fs = connect_to_mongo()  
        collection = db[collection_name]  

        document = {
            "source_url": href,
            "scraping_date": datetime.now(),
            "etiquetas": ["planta", "plaga"],
            "contenido": content_text,
            "url": url
        }

        result = collection.insert_one(document)
        object_id = result.inserted_id
        logger.info(f"📂 Documento guardado en `{collection_name}` con object_id: {object_id}")

        existing_versions = list(
            collection.find({"source_url": href}).sort("scraping_date", -1)
        )
        old_records = collection.find({"source_url": href}).sort("scraping_date", -1)
        if collection.count_documents({"source_url": href}) > 1:
            for record in list(old_records)[1:]:  
                collection.delete_one({"_id": record["_id"]})
                logger.info(f"🗑 Eliminado documento antiguo con ObjectId: {record['_id']}")

        logger.info(f"📂 Nuevo documento insertado en `{collection_name}` con ObjectId: {object_id}")

        

        return object_id

    except PyMongoError as e:
        logger.error(f"❌ Error al guardar en MongoDB: {str(e)}")
        return None


def generate_directory(url, output_dir=OUTPUT_DIR):
    logger = get_logger("GENERANDO DIRECTORIO")
    try:
        folder_name = (
            url.split("//")[-1].replace("/", "_").replace("?", "_").replace("=", "_")
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

def get_next_versioned_pdf_filename(folder_path, base_name="archivo"):
    logger = get_logger("generar siguiente versión de archivo PDF")
    try:
        if len(base_name) > 50:
            base_name = hashlib.md5(base_name.encode()).hexdigest()[:10]  
        version = 0
        while True:
            file_name = f"{base_name}_v{version}.pdf"
            file_path = os.path.join(folder_path, file_name)
            if not os.path.exists(file_path): 
                return file_path 
            version += 1
    except Exception as e:
        logger.error(f"Error al generar el nombre del archivo PDF: {str(e)}")
        raise
def delete_old_documents(url, collection, fs, limit=2):

    logger = get_logger("ELIMINAR DE LA BD DOCUMENTOS ANTIGUOS")
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


def save_scraper_data(all_scraper, url, sobrenombre):
    logger = get_logger("GUARDAR DATOS DEL SCRAPER")
    try:
        response_data = {
            "Tipo": "WEB",
            "Url": url,
            "Fecha_scraper": datetime.now(),
            "Etiquetas": ["planta", "plaga"],
            "Mensaje": "Los datos han sido scrapeados correctamente.",
        }
        logger.info(f"DEBUG - Tipo de respuesta de save_scraper_data: {type(response_data)}")
        return response_data
    except Exception as e:
        logger.error(f"Error al guardar datos del scraper: {str(e)}")
        raise

def save_scraper_data_pdf(all_scraper, url, sobrenombre, collection):
    logger = get_logger("GUARDAR DATOS DEL SCRAPER")

    try:
        content_text = all_scraper.strip()
        if not content_text:
            logger.warning("⚠️ El contenido está vacío, no se guardará en MongoDB.")
            return {"error": "El contenido del scraper está vacío."}

        urls_scraper_collection = collection["urls_scraper"]
        record = {
            "source_url": url,
            "scraping_date": datetime.now(),
            "contenido": content_text,
            "Etiquetas": ["planta", "plaga"],
            "url": url
        }
        object_id = urls_scraper_collection.insert_one(record).inserted_id
        logger.info(f"✅ Contenido guardado en `urls_scraper` con ObjectId: {object_id}")

        existing_records = list(urls_scraper_collection.find({"source_url": url}).sort("scraping_date", -1))
        if len(existing_records) > 1:  
            oldest_record = existing_records[-1]
            urls_scraper_collection.delete_one({"_id": oldest_record["_id"]})
            logger.info(f"🗑 Se eliminó la versión más antigua en `urls_scraper` con ObjectId: {oldest_record['_id']}")

        collection_db = collection["collection"]
        collection_db.insert_one({
            "_id": object_id,
            "source_url": url,
            "scraping_date": datetime.now(),
            "contenido": f"Se scrapeó 1 URL: {url}",
            "Etiquetas": ["planta", "plaga"],
            "url": url,
        })
        logger.info(f"📄 Se registró la acción en `collection` con ObjectId: {object_id}")

        existing_records_collection = list(collection_db.find({"source_url": url}).sort("scraping_date", -1))
        if len(existing_records_collection) > 2:  
            oldest_record_collection = existing_records_collection[-1]
            collection_db.delete_one({"_id": oldest_record_collection["_id"]})
            logger.info(f"🗑 Se eliminó la versión más antigua en `collection` con ObjectId: {oldest_record_collection['_id']}")

        response_data = {
            "Tipo": "Documento",
            "Url": url,
            "Fecha_scraper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
            "Mensaje": "Los datos han sido scrapeados y guardados correctamente en MongoDB.",
        }

        logger.info(f"📂 Datos guardados correctamente en `collection` y `urls_scraper` para la URL: {url}")
        return response_data

    except Exception as e:
        logger.error(f"❌ Error al guardar datos del scraper: {str(e)}")
        return {"error": f"Error al guardar datos del scraper: {str(e)}"}


def process_scraper_data(all_scraper, url, sobrenombre, collection_name=MONGO_COLLECTION_NAME):
    logger = get_logger("PROCESANDO DATOS DE ALL SCRAPER")

    try:
        db, _ = connect_to_mongo()  
        collection = db[collection_name]  
        logger.info(f"✅ Conectado a MongoDB en la base de datos: '{MONGO_DB_NAME}', colección: '{collection_name}'")

        if all_scraper.strip():
            response_data = save_scraper_data(all_scraper, url, sobrenombre)
            
            collection.insert_one({
                "scraping_date": datetime.now(),
                "Etiquetas": ["planta", "plaga"],
                "contenido": all_scraper,
                "url": url,
            })

            # Mantener solo las 2 versiones más recientes en `collection`
            existing_versions = list(collection.find({"url": url}).sort("scraping_date", -1))
            if len(existing_versions) > 2:
                oldest_version = existing_versions[-1]
                collection.delete_one({"_id": oldest_version["_id"]})
                logger.info(f"🗑 Se eliminó la versión más antigua con ObjectId: {oldest_version['_id']}")

            return response_data

        else:
            logger.warning(f"No se encontraron datos para scrapear en la URL: {url}")
            return {
                "status": "no_content",
                "url": url,
                "message": "No se encontraron datos para scrapear.",
            }

    except TimeoutException:
        logger.error(f"Error: la página {url} está tardando demasiado en responder.")
        return {
            "status": "timeout",
            "url": url,
            "message": "La página está tardando demasiado en responder. Verifique si la URL es correcta o intente nuevamente más tarde.",
        }
    except ConnectionError:
        logger.error("Error de conexión a la URL.")
        return {
            "status": "connection_error",
            "url": url,
            "message": "No se pudo conectar a la página web.",
        }
    except Exception as e:
        logger.error(f"Error al procesar datos del scraper: {str(e)}")
        return {
            "status": "error",
            "url": url,
            "message": "Ocurrió un error al procesar los datos.",
            "error": str(e),
        }





def extract_text_from_pdf(pdf_url):
    try:
        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=50)
        response.raise_for_status() 

        pdf_buffer = BytesIO(response.content)
        reader = pypdf.PdfReader(pdf_buffer)

        pdf_text = "\n".join(
            [page.extract_text() for page in reader.pages if page.extract_text()]
        )
        return pdf_text if pdf_text else "No se pudo extraer texto del PDF."

    except Exception as e:
        return f"Error al extraer contenido del PDF ({pdf_url}): {e}"
