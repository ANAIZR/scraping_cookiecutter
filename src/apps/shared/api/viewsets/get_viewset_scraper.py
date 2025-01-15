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
            limit = int(request.GET.get("limit", 2))  # Límite por defecto: 2

            if not url:
                return JsonResponse({"error": "Debe proporcionar una URL"}, status=400)

            # Ordenar por Fecha_scraper y limitar resultados
            records = (
                collection.find({"Url": url})
                .sort("Fecha_scraper", -1)  # Ordenar por Fecha_scraper (descendente)
                .limit(limit)  # Limitar al número de registros especificados
            )

            # Convertir a lista
            records_list = []
            for record in records:
                record_data = {
                    "Objeto": str(record.get("Objeto", None)),
                    "Tipo": record.get("Tipo", "No disponible"),
                    "Url": record.get("Url", ""),
                    "Fecha_scraper": record.get("Fecha_scraper", "No disponible"),
                    "Etiquetas": record.get("Etiquetas", []),
                }
                records_list.append(record_data)

            if not records_list:
                return JsonResponse(
                    {"message": "No hay datos de scraping disponibles para esta URL."},
                    status=404,
                )

            return JsonResponse({"data": records_list}, status=200)

        except Exception as e:
            return JsonResponse(
                {"error": f"Ocurrió un error inesperado: {str(e)}"}, status=500
            )
    else:
        return JsonResponse(
            {"error": "Método no permitido. Use GET para este endpoint."}, status=405
        )
