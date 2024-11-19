import requests
from bs4 import BeautifulSoup

base_url = "https://books.google.com.bo/books?id=_wxn-mJcTX0C&pg=PA182&lpg=PA182&dq=carpophilus+hemipterus+en+sesamo#v=onepage&q&f=false"

ebook_text = ""


for page_num in range(1, 194): 
    url = f"{base_url}{page_num}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extraer contenido de cada página
    content = soup.find("div", class_="ebook-page-content")
    if content:
        ebook_text += content.get_text(strip=True) + "\n"
    else:
        print(f"Fin del ebook en la página {page_num}")
        break

# Guardar el contenido
with open("ebook_paginas.txt", "w", encoding="utf-8") as file:
    file.write(ebook_text)

print("Ebook completo guardado.")
