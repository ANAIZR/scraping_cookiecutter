import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import hashlib

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

output_dir = r"C:\web_scraping_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

url = "https://www.aphis.usda.gov/plant-pests-diseases"

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

def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def is_valid_link(href):
    invalid_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".zip", ".rar", ".tar", ".gz")
    return not href.endswith(invalid_extensions)

def scrape_page(url, visited, start_url, file, site_count):
    normalized_url = normalize_url(url)
    if normalized_url in visited:
        return site_count

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text_content = soup.get_text(separator="\n", strip=True)

        if not text_content:
            print(f"No se encontró texto en: {url}")
            return site_count

        site_count += 1
        with open(file, "a", encoding="utf-8") as f:
            f.write(f"# {site_count} - SITIO: {url}\n")
            f.write(f"Contenido:\n{text_content}\n")
            f.write("************************************\n")
        print(f"Contenido del sitio {site_count} guardado: {url}")

        visited.add(normalized_url)

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(url, href)
            if full_url.startswith(start_url) and is_valid_link(full_url):
                site_count = scrape_page(full_url, visited, start_url, file, site_count)

    except requests.exceptions.RequestException as e:
        print(f"Error al procesar {url}: {e}")

    return site_count

folder_path = generate_directory(output_dir, url)
file_path = get_next_versioned_filename(folder_path, base_name="aphis")

if os.path.exists(file_path):
    os.remove(file_path)

visited_links = set()
site_counter = scrape_page(url, visited_links, url, file_path, 0)

print(f"Scraping completo. {site_counter} sitios procesados. El contenido está en '{file_path}'.")
