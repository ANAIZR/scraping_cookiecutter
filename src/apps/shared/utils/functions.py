import os
import hashlib
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status
import logging
from pymongo import MongoClient
import gridfs

# Configuración de directorio de salida
OUTPUT_DIR = "c:/web_scraper_files"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Configuración del logger
def get_logger(name):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler("scraper_log.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

logger = get_logger("scraper")


def connect_to_mongo(db_name="scrapping-can", collection_name="collection"):
    try:
        logger.info(f"Conectando a la base de datos MongoDB: {db_name}")
        client = MongoClient("mongodb://localhost:27017/")
        db = client[db_name]
        fs = gridfs.GridFS(db)
        logger.info(f"Conexión a MongoDB establecida: {db_name}")
        return db[collection_name], fs
    except Exception as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        raise


def generate_directory(output_dir, url):
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
    try:
        if all_scraper.strip():
            response_data = save_scraper_data(all_scraper, url, sobrenombre, collection, fs)
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
