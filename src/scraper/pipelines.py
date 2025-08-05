import psycopg2
import hashlib
from scrapy.exceptions import DropItem
from datetime import datetime
from .settings import DB_PARAMS


class JobPostgresPipeline:
    def open_spider(self, spider):
        self.connection = psycopg2.connect(**DB_PARAMS)
        self.cursor = self.connection.cursor()

    def close_spider(self, spider):
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def process_item(self, item, spider):
        # Crear hash para evitar duplicados
        content_string = f"{item['title']}{item['description']}{item.get('requirements', '')}"
        content_hash = hashlib.sha256(content_string.encode("utf-8")).hexdigest()

        try:
            self.cursor.execute("""
                INSERT INTO raw_jobs (
                    portal, country, url, title, company, location,
                    description, requirements, salary_raw, contract_type,
                    remote_type, posted_date, content_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (content_hash) DO NOTHING
            """, (
                item.get("portal"),
                item.get("country"),
                item.get("url"),
                item.get("title"),
                item.get("company"),
                item.get("location"),
                item.get("description"),
                item.get("requirements"),
                item.get("salary_raw"),
                item.get("contract_type"),
                item.get("remote_type"),
                item.get("posted_date"),
                content_hash
            ))

            return item

        except psycopg2.Error as e:
            spider.logger.warning(f"Error al insertar en PostgreSQL: {e}")
            raise DropItem(f"Error al insertar: {e}")
