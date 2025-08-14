import psycopg2
import hashlib
from scrapy.exceptions import DropItem
from datetime import datetime
from .settings import DB_PARAMS
import logging

logger = logging.getLogger(__name__)


class JobPostgresPipeline:
    def open_spider(self, spider):
        """Open database connection when spider starts."""
        try:
            self.connection = psycopg2.connect(**DB_PARAMS)
            self.cursor = self.connection.cursor()
            logger.info(f"Connected to PostgreSQL database: {DB_PARAMS['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close_spider(self, spider):
        """Close database connection when spider finishes."""
        if hasattr(self, 'connection'):
            self.connection.commit()
            self.cursor.close()
            self.connection.close()
            logger.info("Database connection closed")

    def process_item(self, item, spider):
        """Process job item and insert into database."""
        # Create content hash for deduplication
        content_string = f"{item.get('title', '')}{item.get('description', '')}{item.get('requirements', '')}"
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

            # Check if row was actually inserted
            if self.cursor.rowcount > 0:
                logger.info(f"Inserted new job: {item.get('title', 'Unknown')} from {item.get('portal')}")
            else:
                logger.debug(f"Duplicate job skipped: {item.get('title', 'Unknown')} from {item.get('portal')}")

            return item

        except psycopg2.Error as e:
            logger.error(f"Database error while inserting job: {e}")
            raise DropItem(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while processing job: {e}")
            raise DropItem(f"Processing error: {e}")
