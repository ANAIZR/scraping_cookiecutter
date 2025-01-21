import requests
import time
import os
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from rest_framework.response import Response
from rest_framework import status
from ..functions import (
    process_scraper_data,
    connect_to_mongo,
    get_logger,
    get_random_user_agent,
    generate_directory
)
from selenium.common.exceptions import StaleElementReferenceException

logger = get_logger("scraper")

def scraper_agriculture(url, sobrenombre):
    logger = get_logger("scraper")
    logger.info(f"Iniciando scraping para URL: {url}")
    collection, fs = connect_to_mongo("scrapping-can", "collection")
    all_scraper = ""
    processed_links = set()
    urls_to_scrape = [(url, 1)]  
    non_scraped_urls = []  

    total_found_links = 0
    total_scraped_links = 0
    total_non_scraped_links = 0

    main_folder = ""

    def scrape_page_agriculture(url, sobrenombre):
        try:
            scrapper =""
            print("depth 1")
            main_folder = generate_directory(url)
            headers = {"User-Agent": get_random_user_agent()}
            new_links = []
            response = requests.get(url, headers=headers)
            response.raise_for_status()  
            soup = BeautifulSoup(response.content, "html.parser")
 
            #depth = 0 : nivel de profundidad, primera pagina
            div = soup.find("td", class_="newsroom_2cols")
            links = div.find_all("a", href=True, target="_blank")
            print("depth after 1, links: ",len(links))

            for link in links:
                # scrape_page_block()
                # if link in processed_links :
                #     return 0
                #obtencion del href
                print("depth 2")

                link_href = link.get("href")
                response_page2 = requests.get(link_href, headers=headers)
                response_page2.raise_for_status()
                soup_page2 = BeautifulSoup(response_page2.content, "html.parser")
                div_page2 = soup_page2.find("td", class_="newsroom_2cols")
                links_page2 = div_page2.find_all("a", href=True, target="_blank")
                for link_page in links_page2:                    
                    print("depth 3")
                    inner_href = link_page.get("href")
                    if inner_href in processed_links :
                        return 0
                    response_page3 = requests.get(inner_href, headers=headers)
                    response_page3.raise_for_status()
                    soup_page3 = BeautifulSoup(response_page3.content, "html.parser")
                    container_div = soup_page3.find("td", class_="newsroom_2cols")
                    page_text = container_div.get_text(strip=True)
                    scrapper += f"URL: {page_text} \n"

                    processed_links.add(inner_href)
            return scrapper
        except Exception as e:
            logger.error(f"Error en tarea de scraping por href: {str(e)}")

    def scrape_page_block():
        ## div que contiene la info para scrapeo
        soup = BeautifulSoup(response.content, "html.parser")
        container_div = soup.find("div", class_="newsroom_2cols")
        page_text = container_div.get_text(strip=True)
        return page_text
    
    def scrape_page(url, depth):
        nonlocal total_found_links, total_scraped_links, total_non_scraped_links

        if url in processed_links or depth > 3: 
            return []
        processed_links.add(url)

        logger.info(f"Accediendo a {url} en el nivel {depth}")

        headers = {"User-Agent": get_random_user_agent()}
        new_links = []

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            if depth >= 2:
                main_content = soup.find("main", id="main")
                if main_content:
                    nonlocal all_scraper
                    page_text = main_content.get_text(strip=True)
                    all_scraper += f"URL: {url}\n{page_text}\n\n" 

            for link in soup.find_all("a", href=True):
                inner_href = link.get("href")
                full_url = urljoin(url, inner_href)

                if full_url.lower().endswith(".pdf"):
                    total_non_scraped_links += 1  
                    non_scraped_urls.append(full_url)  
                    continue

                if "forms" in full_url or "":  
                    total_non_scraped_links += 1  
                    non_scraped_urls.append(full_url)  
                    continue

                if (
                    urlparse(full_url).netloc == "www.aphis.usda.gov"
                    and full_url not in processed_links
                ):
                    total_found_links += 1  
                    new_links.append((full_url, depth + 1))
                    total_scraped_links += 1 

        except requests.exceptions.RequestException as e:
            logger.error(f"Error al procesar el enlace {url}: {e}")
            total_non_scraped_links += 1  
            non_scraped_urls.append(url)  

        return new_links

    def scrape_pages_in_parallel(url_list):
        new_links = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {
                executor.submit(scrape_page, url, depth): (url, depth)
                for url, depth in url_list
            }
            for future in as_completed(future_to_url):
                try:
                    result_links = future.result()
                    new_links.extend(result_links)
                except Exception as e:
                    logger.error(f"Error en tarea de scraping: {str(e)}")
                    total_non_scraped_links += 1  
        return new_links

    try:
        # while urls_to_scrape:
        #     logger.info(f"URLs restantes por procesar: {len(urls_to_scrape)}")
        #     urls_to_scrape = scrape_pages_in_parallel(urls_to_scrape)
        #     time.sleep(random.uniform(1, 3)) 
        
        res = scrape_page_agriculture(url,sobrenombre) 
        file_path = os.path.join(main_folder, "scraped.txt")
        ##CREACION Y ESCRITURA DE ARCHIVO
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(res)

        print("despues de las funciones")

        all_scraper += f"\n\nTotal links found: {total_found_links}\n"
        all_scraper += f"Total links scraped: {total_scraped_links}\n"
        all_scraper += f"Total links not scraped: {total_non_scraped_links}\n"
        all_scraper += "\n\nURLs no scrapeadas:\n"
        all_scraper += "\n".join(non_scraped_urls)  
        response = process_scraper_data(all_scraper, url, sobrenombre, collection, fs)
        return response

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
