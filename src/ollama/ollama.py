import requests

url = "http://127.0.0.1:8000/api/compare"  # Cambiamos al puerto de Django

# Aquí debes cambiar la URL por la real que estás usando para el scrapeo
scrape_url = input("Introduce la URL para el scrapeo: ")

datos = {
    "url": scrape_url
}

respuesta = requests.post(url, json=datos)

if respuesta.status_code == 200:
    resultado = respuesta.json().get("resultado")
    print("Resultado de la comparación:")
    print(resultado)
    
    with open("resultado_comparacion.txt", "w", encoding="utf-8") as file:
        file.write("Resultado de la comparación:\n")
        file.write(resultado)
    
    print("\nEl resultado se ha guardado en 'resultado_comparacion.txt'.")
else:
    print("Error al conectar con el endpoint /api/compare")
	