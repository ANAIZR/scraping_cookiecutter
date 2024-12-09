import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

start_url = "https://www.eppo.int/ACTIVITIES/plant_quarantine/A1_list"

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

def is_valid_link(href):
    invalid_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".zip", ".rar", ".tar", ".gz")
    return not href.endswith(invalid_extensions)

def scrape_main_and_links_sequentially(url, output_file):
    try:
        # Obtener contenido del sitio principal
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Guardar contenido del sitio principal
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"# SITIO PRINCIPAL: {url}\n")
            f.write(soup.get_text(separator="\n", strip=True))
            f.write("\n************************************\n")

        # Obtener todos los enlaces en la página principal
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link["href"]
            full_url = urljoin(url, href)

            if is_valid_link(full_url):
                print(f"Procesando enlace: {full_url}")
                try:
                    # Acceder al enlace
                    link_response = requests.get(full_url, headers=HEADERS, timeout=10)
                    link_response.raise_for_status()
                    link_soup = BeautifulSoup(link_response.text, "html.parser")

                    # Guardar contenido del enlace
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(f"# ENLACE: {full_url}\n")
                        f.write(link_soup.get_text(separator="\n", strip=True))
                        f.write("\n************************************\n")

                except requests.exceptions.RequestException as e:
                    print(f"Error al procesar el enlace {full_url}: {e}")

    except requests.exceptions.RequestException as e:
        print(f"Error al procesar el sitio principal {url}: {e}")

# Configuración del archivo de salida
folder_path = generate_directory(output_dir, start_url)
file_path = get_next_versioned_filename(folder_path, base_name="eppo_A1")

if os.path.exists(file_path):
    os.remove(file_path)

# Ejecutar el scraping
scrape_main_and_links_sequentially(start_url, file_path)

print(f"Scraping completo. El contenido está en '{file_path}'.")