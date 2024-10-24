import gridfs
from pymongo import MongoClient

# Conexión a MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
fs = gridfs.GridFS(db)

try:
    files = fs.find()

    for file in files:
        print(
            f"ID: {file._id}, Nombre: {file.filename}"
        )  

        try:
            file_data = fs.get(file._id)
            with open(f"{file.filename}.txt", "wb") as output_file:
                output_file.write(file_data.read())
            print(
                f"Archivo {file.filename} recuperado exitosamente y guardado como {file.filename}.txt."
            )
        except gridfs.errors.NoFile:
            print(f"El archivo con ID {file._id} no se encontró en GridFS.")
except Exception as e:
    print(f"Ocurrió un error: {e}")
