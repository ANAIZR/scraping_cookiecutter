import requests
from requests.auth import HTTPProxyAuth

# Credenciales del proxy de Oxylabs
proxy_user = "customer-USERNAME-sessid-0159477921-sesstime-10"
proxy_pass = "PASSWORD"
proxy_host = "pr.oxylabs.io"
proxy_port = "7777"

proxies = {
    "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
    "https": f"https://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
}

# Configurar autenticación
proxy_auth = HTTPProxyAuth(proxy_user, proxy_pass)

try:
    response = requests.get("http://httpbin.org/ip", proxies=proxies, auth=proxy_auth, timeout=10)
    print("🔹 Respuesta con proxy en requests:", response.text)
except requests.exceptions.RequestException as e:
    print(f"❌ Error en la solicitud con proxy: {e}")
