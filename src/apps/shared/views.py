from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import os
import hashlib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'files', 'scrapers'))

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
    Obtiene las rutas de los dos archivos .txt más recientes en la carpeta especificada.
    """
    archivos_txt = [os.path.join(carpeta, archivo) for archivo in os.listdir(carpeta) if archivo.endswith('.txt') and os.path.isfile(os.path.join(carpeta, archivo))]
    if not archivos_txt:
        return None
    archivos_txt.sort(key=os.path.getmtime, reverse=True)
    return archivos_txt[:2]

def leer_archivo(ruta_archivo):
    """
    Lee el contenido de un archivo y lo retorna como string.
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

        if ultimos_archivos is None:
            return JsonResponse({"error": f"No hay archivos txt para este scrapeo en la carpeta '{carpeta}'."}, status=400)

        if len(ultimos_archivos) < 2:
            return JsonResponse({"error": f"No hay suficientes archivos para comparar en la carpeta '{carpeta}'."}, status=400)

        archivo_txt1 = leer_archivo(ultimos_archivos[0])
        archivo_txt2 = leer_archivo(ultimos_archivos[1])

        if archivo_txt1 is None or archivo_txt2 is None:
            return JsonResponse({"error": "Uno o ambos archivos no se pudieron leer."}, status=400)

        contenido_txt = f"Texto 2:\n{archivo_txt2}"

        prompt = (
            f"Eres un experto en fitosanidad y tu tarea es analizar el siguiente texto extraído de una web fitosanitaria. "
            f"A partir de esta información, genera un registro estructurado en formato JSON que contenga datos válidos. "
            f"Un registro debe incluir al menos información de una plaga, un hospedante, o una interacción entre ambos para ser considerado válido. "
            f"Completa tantos campos como sea posible y deja vacíos (`null`) aquellos que no puedan ser llenados. La respuesta debe ser exclusivamente del JSON y no me des ninguna observación del archivo. Usa el siguiente formato:\n\n"
            
            f"**Campos Comunes:**\n"
            f"- `tipo_registro`: Indica si el texto se refiere a una \"plaga\", \"hospedante\", o \"interacción\".\n"
            f"- `fuente`: URL o nombre de la fuente de donde proviene el texto.\n"
            f"- `tipo_fuente`: Tipo de fuente (Informe, Boletín, Noticia, Investigación, Libro).\n"
            f"- `idioma`: Idioma del texto analizado.\n"
            f"- `fecha_extraccion`: Fecha en la que se obtuvo el texto.\n\n"

            f"**Plagas:**\n"
            f"- `id_plaga`: Identificador único de la plaga (si no hay, usa null).\n"
            f"- `nombre_comun_plaga`: Nombre común de la plaga (si no hay, usa null).\n"
            f"- `nombre_cientifico_plaga`: Nombre científico de la plaga (si no hay, usa null).\n"
            f"- `clasificacion`: Clasificación de la plaga (e.g., Artropodo, Nematodo, Virus) (si no hay, usa null).\n"
            f"- `descripcion_plaga`: Descripción breve de la plaga (si no hay, usa null).\n"
            f"- `impacto`: Nivel de impacto (e.g., bajo, medio, alto) (si no hay, usa null).\n\n"

            f"**Hospedantes:**\n"
            f"- `id_hospedante`: Identificador único del hospedante (si no hay, usa null).\n"
            f"- `nombre_comun_hospedante`: Nombre común del hospedante (si no hay, usa null).\n"
            f"- `nombre_cientifico_hospedante`: Nombre científico del hospedante (si no hay, usa null).\n"
            f"- `tipo_hospedante`: Tipo de hospedante (e.g., agrícola, forestal, ornamental) (si no hay, usa null).\n"
            f"- `familia_taxonomica`: Familia taxonómica del hospedante (si no hay, usa null).\n"
            f"- `zona_geografica`: Zonas geográficas relevantes para el hospedante (si no hay, usa null).\n"
            f"- `descripcion_hospedante`: Descripción breve del hospedante (si no hay, usa null).\n\n"

            f"**Interacciones (Plaga-Hospedante):**\n"
            f"- `organos_afectados`: Órganos del hospedante afectados por la plaga (si no hay, usa null).\n"
            f"- `organos_no_afectados`: Órganos no afectados por la plaga (si no hay, usa null).\n"
            f"- `descripcion_afectacion`: Descripción del daño causado (si no hay, usa null).\n"
            f"- `id_zona`: Relación con zona geográfica (si no hay, usa null).\n"
            f"- `temperatura_minima`: Temperatura mínima registrada en la interacción (°C) (si no hay, usa null).\n"
            f"- `temperatura_maxima`: Temperatura máxima registrada en la interacción (°C) (si no hay, usa null).\n"
            f"- `humedad_porcentaje`: Porcentaje de humedad relativo (%) (si no hay, usa null).\n"
            f"- `precipitacion_minima`: Precipitación mínima registrada (mm) (si no hay, usa null).\n"
            f"- `precipitacion_maxima`: Precipitación máxima registrada (mm) (si no hay, usa null).\n"
            f"- `probabilidad_riesgo`: Probabilidad de ocurrencia (en porcentaje) (si no hay, usa null).\n\n"

            f"Ahora, por favor analiza el siguiente texto y genera el registro estructurado correspondiente:\n\n{contenido_txt}"
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