import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

start_url = "https://hort.purdue.edu/newcrop/Indices/index_ab.html"

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

# URL base principal
#BASE_URL = "https://hort.purdue.edu/newcrop/Indices/index_ab.html"
#OUTPUT_DIR = "scraped_data"
#os.makedirs(OUTPUT_DIR, exist_ok=True)
# Configuración del archivo de salida
folder_path = generate_directory(output_dir, start_url)
file_path = get_next_versioned_filename(folder_path, base_name="hort")
# Función para obtener el contenido HTML de una página
def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a {url}: {e}")
        return None

# Función para extraer los enlaces alfabéticos de la página principal
def get_alphabet_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    alphabet_links = []
    center_p = soup.find("p", align="center")
    if center_p:
        for link in center_p.find_all("a", href=True):
            full_url = urljoin(base_url, link['href'])
            alphabet_links.append(full_url)
    return alphabet_links

# Función para extraer los enlaces de una sección específica
def get_section_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    section_links = []
    for p in soup.find_all("p"):
        for link in p.find_all("a", href=True):
            full_url = urljoin(base_url, link['href'])
            section_links.append(full_url)
    return section_links



# Función principal
if __name__ == "__main__":
    # Obtener contenido de la página principal
    main_html = get_html(start_url)
    if not main_html:
        print("No se pudo acceder a la página principal.")
        exit()

    # Obtener enlaces alfabéticos
    alphabet_links = get_alphabet_links(main_html, start_url)
    print(f"Enlaces alfabéticos encontrados: {len(alphabet_links)}")

    # Preparar el archivo de salida
    #output_file = get_next_versioned_filename(start_url)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"Contenido extraído del sitio: {start_url}\n\n")

    # Recorrer cada enlace alfabético
    for alpha_link in alphabet_links:
        print(f"Procesando sección: {alpha_link}")
        alpha_html = get_html(alpha_link)
        if not alpha_html:
            continue

        # Obtener los enlaces dentro de la sección
        section_links = get_section_links(alpha_html, alpha_link)
        print(f"  Enlaces encontrados en la sección: {len(section_links)}")

        # Procesar cada enlace de la sección
        for link in section_links:
            print(f"    Extrayendo contenido de: {link}")
            link_html = get_html(link)
            if not link_html:
                continue

            # Guardar contenido en el archivo de texto
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"# URL: {link}\n")
                soup = BeautifulSoup(link_html, "html.parser")
                f.write(soup.get_text(separator="\n", strip=True))
                f.write("\n\n" + ("=" * 80) + "\n\n")

    print(f"Proceso completado. El contenido está en '{file_path}'.")