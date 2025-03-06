from src.apps.shared.models.scraperURL import ScraperURL
from src.apps.shared.models.scraperURL import ReportComparison
import logging
from django.conf import settings
from pymongo import MongoClient

import json


logger = logging.getLogger(__name__)


class ScraperComparisonService:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB_NAME]
        self.collection = self.db["collection"]

    def get_comparison_for_url(self, url):

        documents = list(self.collection.find({"url": url}).sort("scraping_date", -1))

        if len(documents) < 2:
            logger.info(f"No hay suficientes versiones de la URL {url} para comparar.")
            return {
                "status": "no_comparison",
                "message": "Menos de dos registros encontrados.",
            }

        doc1, doc2 = documents[:2]
        object_id1, object_id2 = str(doc1["_id"]), str(doc2["_id"])

        existing_report = ReportComparison.objects.filter(
            scraper_source__url=url
        ).first()

        if (
            existing_report
            and existing_report.object_id1 == object_id1
            and existing_report.object_id2 == object_id2
        ):
            logger.info(f"La comparación entre {object_id1} y {object_id2} ya existe.")
            return {
                "status": "duplicate",
                "message": "La comparación ya fue realizada anteriormente.",
            }

        return self.compare_and_save(url, doc1, doc2)

    def compare_and_save(self, url, doc1, doc2):

        object_id1, object_id2 = str(doc1["_id"]), str(doc2["_id"])
        content1, content2 = doc1.get("contenido", ""), doc2.get("contenido", "")

        if not content1 or not content2:
            logger.warning(
                f"Uno de los documentos ({object_id1}, {object_id2}) no tiene contenido."
            )
            return {
                "status": "missing_content",
                "message": "Uno de los registros no tiene contenido.",
            }

        comparison_result = self.generate_comparison(content1, content2)

        if comparison_result and comparison_result.get("has_changes", False):
            self.save_or_update_comparison_to_postgres(
                url, object_id1, object_id2, comparison_result
            )
            return {
                "status": "changed",
                "message": "Se detectaron cambios en la comparación.",
            }

        return {
            "status": "no_changes",
            "message": "No se detectaron cambios en la comparación.",
        }

    def generate_comparison(self, content1, content2):

        urls1 = self.extract_urls(content1)
        urls2 = self.extract_urls(content2)

        new_urls = list(set(urls2) - set(urls1))
        removed_urls = list(set(urls1) - set(urls2))

        has_changes = bool(new_urls or removed_urls)

        return {
            "info_agregada": new_urls,
            "info_eliminada": removed_urls,
            "estructura_cambio": has_changes,
        }

    def extract_urls(self, content):

        scraped_urls = []
        lines = content.split("\n")
        scraping_section = False

        for line in lines:
            line = line.strip()
            if "Enlaces scrapeados:" in line:
                scraping_section = True
                continue
            elif "Enlaces no procesados:" in line:
                break

            if scraping_section and line:
                scraped_urls.append(line)

        return scraped_urls

    def save_or_update_comparison_to_postgres(
        self, url, object_id1, object_id2, comparison_result
    ):

        scraper_source, _ = ScraperURL.objects.get_or_create(url=url)

        ReportComparison.objects.update_or_create(
            scraper_source=scraper_source,
            object_id1=object_id1,
            object_id2=object_id2,
            defaults={
                "info_agregada": json.dumps(comparison_result["info_agregada"]),
                "info_eliminada": json.dumps(comparison_result["info_eliminada"]),
                "estructura_cambio": comparison_result["estructura_cambio"],
            },
        )
        logger.info(f"Comparación guardada para la URL {url}.")
