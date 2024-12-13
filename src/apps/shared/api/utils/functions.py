import os
import hashlib
from datetime import datetime
OUTPUT_DIR = r"~/"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_").replace("?","_").replace("=","_") + "_" + url_hash[:8]
    folder_path = os.path.join(output_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path


def get_next_versioned_filename(folder_path, base_name="archivo"):
    version = 0
    while True:
        file_name = f"{base_name}_v{version}.txt"
        file_path = os.path.join(folder_path, file_name)
        if not os.path.exists(file_path):
            return file_path
        version += 1




def delete_old_documents(url, collection, fs, limit=2):
    docs_for_url = collection.find({"Url": url}).sort("Fecha_scrapper", -1)

    docs_count = collection.count_documents({"Url": url})
    
    if docs_count > limit:
        docs_to_delete = list(docs_for_url)[limit:]  

        for doc in docs_to_delete:
            collection.delete_one({"_id": doc["_id"]})
            fs.delete(doc["Objeto"])

        print(f"Se han eliminado {docs_count - limit} documentos antiguos para la URL {url}.")
    else:
        print(f"No se encontraron documentos para eliminar. Se mantienen {docs_count} documentos para la URL {url}.")
    
    return docs_count > limit


def save_scraped_data(all_scrapped, url, sobrenombre, collection, fs):
    folder_path = generate_directory(OUTPUT_DIR, url)
    file_path = get_next_versioned_filename(folder_path, base_name=sobrenombre)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(all_scrapped)

    with open(file_path, "rb") as file_data:
        object_id = fs.put(file_data, filename=os.path.basename(file_path))

        data = {
            "Objeto": object_id,
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Etiquetas": ["planta", "plaga"],
        }

        collection.insert_one(data)

        delete_old_documents(url, collection, fs)

        response_data = {
            "Tipo": "Web",
            "Url": url,
            "Fecha_scrapper": data["Fecha_scrapper"],
            "Etiquetas": data["Etiquetas"],
            "Mensaje": "Los datos han sido scrapeados correctamente.",
        }

    return response_data
