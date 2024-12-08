import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import hashlib

# Configurar headers para simular un navegador
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

url = "https://www.delta-intkey.com/www/data.htm"
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


# Crear carpeta y archivo para almacenar el contenido
folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="delta")

def is_valid_link(href):
    """
    Filtra los enlaces que no sean de texto (por ejemplo, .pdf, .jpg, etc.).
    """
    invalid_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".zip", ".rar", ".tar", ".gz")
    return not href.endswith(invalid_extensions)

def scrape_page(url, visited, allowed_domain, file, site_count):
    """
    Extrae el contenido de una página, lo guarda en un archivo único y sigue los enlaces internos recursivamente
    dentro del dominio permitido.
    """
    if url in visited:  # Evitar visitar la misma página dos veces
        return site_count
    
    try:
        # Descargar la página
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extraer el texto visible de la página
        text_content = soup.get_text(separator="\n", strip=True)

        if not text_content:  # Si no hay texto en la página, no guardar
            print(f"No se encontró texto en: {url}")
            return site_count

        # Incrementar contador de sitios
        site_count += 1

        # Escribir contenido en el archivo único
        with open(file, "a", encoding="utf-8") as f:
            f.write(f"# {site_count} - SITIO: {url}\n")
            f.write(f"Contenido:\n{text_content}\n")
            f.write("************************************\n")
        print(f"Contenido del sitio {site_count} guardado: {url}")

        visited.add(url)  # Marcar como visitado

        # Encontrar y seguir enlaces internos
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(url, href)  # Convertir en URL absoluta

            # Filtrar enlaces que pertenezcan al dominio permitido y sean válidos
            if urlparse(full_url).netloc == allowed_domain and is_valid_link(full_url):
                site_count = scrape_page(full_url, visited, allowed_domain, file, site_count)

    except Exception as e:
        print(f"Error al procesar {url}: {e}")
    
    return site_count

# URL inicial
start_url = "https://www.delta-intkey.com/www/data.htm"
allowed_domain = "www.delta-intkey.com"  # Dominio permitido
visited_links = set()

# Eliminar archivo de salida si ya existe
if os.path.exists(file_path):
    os.remove(file_path)

# Iniciar scraping
site_counter = scrape_page(start_url, visited_links, allowed_domain, file_path, 0)

print(f"Scraping completo. {site_counter} sitios procesados. El contenido está en '{file_path}'.")
