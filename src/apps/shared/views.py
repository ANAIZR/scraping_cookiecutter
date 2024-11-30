from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import os
import hashlib

BASE_DIR = r"D:\Ramo Peru\Ramo Peru - Desarrollo"

def obtener_carpeta_asociada(url):
    """
    Encuentra la carpeta asociada a la URL en BASE_DIR basándose en su formato de nombre.
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()
    expected_folder_name = url.split("//")[-1].replace("/", "_") + "_" + url_hash[:8]

    folder_path = os.path.join(BASE_DIR, expected_folder_name)
    if os.path.exists(folder_path):
        return folder_path
    return None

def obtener_ultimos_archivos(carpeta):
    """
    Obtiene las rutas de los dos archivos más recientes en la carpeta especificada.
    """
    archivos = [os.path.join(carpeta, archivo) for archivo in os.listdir(carpeta) if os.path.isfile(os.path.join(carpeta, archivo))]
    archivos.sort(key=os.path.getmtime, reverse=True)
    return archivos[:2]

def leer_archivo(ruta_archivo):
    """
    Lee el contenido de un archivo.
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            return archivo.read()
    except FileNotFoundError:
        return None

@csrf_exempt
def compare(request):
    """
    Compara los dos archivos más recientes de una carpeta asociada a una URL enviada en la solicitud.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido. Usa POST."}, status=405)

    try:
        data = json.loads(request.body)
        url = data.get("url")

        if url is None:
            return JsonResponse({"error": "El parámetro 'url' es obligatorio."}, status=400)

        carpeta = obtener_carpeta_asociada(url)

        if not carpeta:
            return JsonResponse({"error": f"No se encontró la carpeta asociada a la URL: {url}. Asegúrate de hacer un scrapeo primero."}, status=400)

        ultimos_archivos = obtener_ultimos_archivos(carpeta)

        if len(ultimos_archivos) < 2:
            return JsonResponse({"error": f"No hay suficientes archivos para comparar en la carpeta '{carpeta}'."}, status=400)

        archivo_txt1 = leer_archivo(ultimos_archivos[0])
        archivo_txt2 = leer_archivo(ultimos_archivos[1])

        if archivo_txt1 is None or archivo_txt2 is None:
            return JsonResponse({"error": "Uno o ambos archivos no se pudieron leer."}, status=400)

        prompt = (
            f"Compara los siguientes textos:\n\nTexto 1:\n{archivo_txt1}\n\nTexto 2:\n{archivo_txt2} "
            "y dime si hay alguna diferencia entre ellos, en caso no tenga diferencia, decir en español que no hay diferencia y de qué habla los txt"
        )

        url = "http://localhost:11434/api/generate"
        datos = {
            "prompt": prompt,
            "model": "llama3.2"
        }
        headers = {
            "Content-Type": "application/json"
        }

        try:
            respuesta = requests.post(url, data=json.dumps(datos), headers=headers, stream=True)
            if respuesta.status_code == 200:
                respuesta_completa = ""
                for line in respuesta.iter_lines():
                    if line:
                        fragment = json.loads(line)
                        respuesta_completa += fragment.get("response", "")
                return JsonResponse({"resultado": respuesta_completa})
            else:
                return JsonResponse({"error": f"Error al conectar con la API de Ollama: {respuesta.status_code}"}, status=500)
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"error": "El cuerpo de la solicitud debe ser un JSON válido."}, status=400)
