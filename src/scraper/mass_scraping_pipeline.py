import psycopg2
import hashlib
from scrapy.exceptions import DropItem
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Database connection parameters for mass scraping
DB_PARAMS = {
    'host': '127.0.0.1',  # Use IPv4 explicitly instead of localhost
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456',
}


class MassScrapingPostgresPipeline:
    """Pipeline optimized for mass scraping that allows more data collection."""
    
    def open_spider(self, spider):
        """Open database connection when spider starts."""
        try:
            self.connection = psycopg2.connect(**DB_PARAMS)
            self.cursor = self.connection.cursor()
            self.db_connected = True
            self.inserted_count = 0
            self.duplicate_count = 0
            self.error_count = 0
            logger.info(f"Connected to PostgreSQL database: {DB_PARAMS['database']}")
        except Exception as e:
            logger.warning(f"Failed to connect to database: {e}")
            logger.warning("Spider will run without database storage")
            self.db_connected = False

    def close_spider(self, spider):
        """Close database connection when spider finishes."""
        if hasattr(self, 'connection') and getattr(self, 'db_connected', False):
            self.connection.commit()
            self.cursor.close()
            self.connection.close()
            logger.info("Database connection closed")
            
        # Log final statistics
        logger.info(f"=== MASS SCRAPING PIPELINE STATISTICS ===")
        logger.info(f"✅ Jobs inserted: {self.inserted_count}")
        logger.info(f"⏭️ Duplicates skipped: {self.duplicate_count}")
        logger.info(f"❌ Errors: {self.error_count}")
        logger.info(f"📊 Total processed: {self.inserted_count + self.duplicate_count + self.error_count}")

    def process_item(self, item, spider):
        """Process job item and insert into database with intelligent duplicate handling."""
        if not getattr(self, 'db_connected', False):
            logger.debug(f"Database not connected, skipping storage for: {item.get('title', 'Unknown')}")
            return item
            
        # Create content hash for deduplication
        content_string = f"{item.get('title', '')}{item.get('description', '')}{item.get('requirements', '')}"
        content_hash = hashlib.sha256(content_string.encode("utf-8")).hexdigest()

        try:
            # Simple INSERT approach - let the database handle duplicates
            self.cursor.execute("""
                INSERT INTO raw_jobs (
                    portal, country, url, title, company, location,
                    description, requirements, salary_raw, contract_type,
                    remote_type, posted_date, content_hash, scraped_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
            
            # Commit the transaction
            self.connection.commit()
            
            # Check if row was actually inserted
            if self.cursor.rowcount > 0:
                self.inserted_count += 1
                logger.info(f"✅ INSERTED: {item.get('title', 'Unknown')} from {item.get('portal')}")
            else:
                self.duplicate_count += 1
                logger.debug(f"⏭️ DUPLICATE: {item.get('title', 'Unknown')} from {item.get('portal')}")

            return item

        except psycopg2.Error as e:
            self.error_count += 1
            logger.error(f"Database error while inserting job: {e}")
            # Rollback the transaction and continue
            try:
                self.connection.rollback()
            except:
                pass
            return item
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error while processing job: {e}")
            # Rollback the transaction and continue
            try:
                self.connection.rollback()
            except:
                pass
            return item