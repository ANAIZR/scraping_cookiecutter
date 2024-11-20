import os
import hashlib
def generate_directory(output_dir, url):
    url_hash = hashlib.md5(url.encode()).hexdigest()
    folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]
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
