from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import gridfs
from bson.json_util import dumps, loads

# Configuración de la conexión con MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["scrapping-can"]
collection = db["collection"]
fs = gridfs.GridFS(db)


@csrf_exempt
def get_scraper_url(request):
    if request.method == "GET":
        try:
            url = request.GET.get("url")
            if not url:
                return JsonResponse({"error": "Debe proporcionar una URL"}, status=400)

            record = collection.find_one({"Url": url})
            if not record:
                return JsonResponse(
                    {"message": "No hay datos de scraping disponibles para esta URL."},
                    status=404,
                )

            data_to_return = {
                "Objeto": str(record.get("Objeto", None)),
                "Tipo": record.get("Tipo", "No disponible"),
                "Url": record.get("Url", ""),
                "Fecha_scraper": record.get("Fecha_scraper", "No disponible"),
                "Etiquetas": record.get("Etiquetas", []),
            }

            return JsonResponse(data_to_return, status=200)

        except Exception as e:
            error_msg = f"Ocurrió un error inesperado: {str(e)}"
            return JsonResponse({"error": error_msg}, status=500)
    else:
        return JsonResponse(
            {"error": "Método no permitido. Use GET para este endpoint."}, status=405
        )
