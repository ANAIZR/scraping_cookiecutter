import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

start_url = "http://www.extento.hawaii.edu/kbase/crop/crop.htm"

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

def is_valid_link(href, base_domain):
    """
    Verifica si un enlace es válido:
    - No tiene extensiones de archivo no deseadas.
    - Pertenece al mismo dominio que el URL base.
    """
    invalid_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".zip", ".rar", ".tar", ".gz")
    if href and not href.endswith(invalid_extensions):
        # Comparar dominios
        href_domain = urlparse(href).netloc
        return base_domain in href_domain or not href_domain
    return False

def scrape_all_links_recursively(base_url, current_url, output_file, visited_links, base_domain):
    try:
        # Obtener contenido del sitio actual
        response = requests.get(current_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Guardar contenido de la página actual
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"# SITIO: {current_url}\n")
            f.write(soup.get_text(separator="\n", strip=True))
            f.write("\n************************************\n")

        # Buscar todos los enlaces
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link["href"]
            full_url = urljoin(current_url, href)  # Corregir URLs relativos
            normalized_url = urlparse(full_url).geturl()

            if (
                normalized_url not in visited_links 
                and is_valid_link(full_url, base_domain)
            ):
                visited_links.add(normalized_url)  # Registrar enlace como visitado
                print(f"Procesando enlace: {normalized_url}")
                scrape_all_links_recursively(base_url, normalized_url, output_file, visited_links, base_domain)

    except requests.exceptions.RequestException as e:
        # Registrar errores en el archivo de salida
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"# ERROR ENLACE: {current_url}\n")
            f.write(f"Error: {str(e)}\n")
            f.write("\n************************************\n")
        print(f"Error al procesar el enlace {current_url}: {e}")

# Configuración del archivo de salida
folder_path = generate_directory(output_dir, start_url)
file_path = get_next_versioned_filename(folder_path, base_name="extento")

if os.path.exists(file_path):
    os.remove(file_path)

# Determinar el dominio base
base_domain = urlparse(start_url).netloc

# Ejecutar el scraping
visited_links = set()
scrape_all_links_recursively(start_url, start_url, file_path, visited_links, base_domain)

print(f"Scraping completo. El contenido está en '{file_path}'.")
