from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import gridfs
 
 
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
 
            scraped_data = collection.find({"Url": url})
 
            if not scraped_data:
                return JsonResponse(
                    {"message": "No hay datos de scraping disponibles para esta URL."},
                    status=200,
                )
 
            data_to_return = []
            for record in scraped_data:
                record_data = {
                    "Objeto": (
                        str(record.get("Objeto", None))
                        if record.get("Objeto")
                        else None
                    ),
                    "Tipo": record.get("Tipo", "No disponible"),
                    "Url": record.get("Url", ""),
                    "Fecha_scraper": record.get("Fecha_scraper", "No disponible"),
                    "Etiquetas": record.get("Etiquetas", []),
                }
                data_to_return.append(record_data)
 
            return JsonResponse({"scraper_data": data_to_return}, status=200)
 
        except Exception as e:
            error_msg = f"Ocurrió un error inesperado: {str(e)}"
            return JsonResponse({"error": error_msg}, status=500)