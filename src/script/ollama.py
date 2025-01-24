import requests

url_scrapeada = input("Ingresa la URL scrapeada: ")
prompt_usuario = input("Ingresa el prompt que deseas usar: ")

datos = {
    "url": url_scrapeada.strip(),
    "prompt": prompt_usuario.strip()
}

url = "http://127.0.0.1:8000/api/compare"
respuesta = requests.post(url, json=datos)

if respuesta.status_code == 200:
    resultado = respuesta.json().get("resultado")
    print("Resultado de la comparación:")
    print(resultado)

    """ with open("resultado_comparacion.txt", "w", encoding="utf-8") as file:
        file.write("Resultado de la comparación:\n")
        file.write(resultado)

    print("\nEl resultado se ha guardado en 'resultado_comparacion.txt'.") """
else:
    print(f"Error al conectar con el endpoint /api/compare: {respuesta.status_code}")
