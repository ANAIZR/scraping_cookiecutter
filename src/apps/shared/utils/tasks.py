from celery import shared_task
import requests


@shared_task
def add(x, y):
    return x + y

@shared_task
def send_post_to_api(url):
    # api_url = "https://apiwebscraper.sgcan.dev/api/v1/scraper-url/"
    api_url = "http://127.0.0.1:8000/api/v1/scraper-url/"
    payload = {"url": url}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar POST: {e}")
        return str(e)

    return response.status_code
