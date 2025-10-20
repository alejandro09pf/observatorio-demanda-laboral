import psycopg2
import hashlib
from scrapy.exceptions import DropItem
from datetime import datetime
from .settings import DB_PARAMS
import logging
import threading

logger = logging.getLogger(__name__)


class JobPostgresPipeline:
    """Optimized PostgreSQL pipeline with batch inserts for high throughput."""

    def __init__(self, batch_size=100):
        """Initialize pipeline with configurable batch size."""
        self.batch_size = batch_size
        self.batch = []
        self.batch_lock = threading.Lock()
        self.stats = {
            'total_items_received': 0,
            'total_items_inserted': 0,
            'total_duplicates_skipped': 0,
            'batches_flushed': 0
        }
        self.stats_lock = threading.Lock()

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline instance from crawler settings."""
        batch_size = crawler.settings.getint('BATCH_INSERT_SIZE', 100)
        return cls(batch_size=batch_size)

    def open_spider(self, spider):
        """Open database connection when spider starts."""
        try:
            self.connection = psycopg2.connect(**DB_PARAMS)
            self.cursor = self.connection.cursor()
            self.db_connected = True
            logger.info(f"✅ Connected to PostgreSQL: {DB_PARAMS['database']}")
            logger.info(f"📦 Batch insert size: {self.batch_size} jobs/batch")
        except Exception as e:
            logger.warning(f"Failed to connect to database: {e}")
            logger.warning("Spider will run without database storage")
            self.db_connected = False

    def close_spider(self, spider):
        """Flush remaining items and close database connection when spider finishes."""
        if hasattr(self, 'connection') and getattr(self, 'db_connected', False):
            # Flush any remaining items in the batch
            self._flush_batch()

            self.connection.commit()
            self.cursor.close()
            self.connection.close()

            # Log final statistics
            logger.info("=" * 60)
            logger.info("📊 PIPELINE STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Items received:      {self.stats['total_items_received']:,}")
            logger.info(f"Items inserted:      {self.stats['total_items_inserted']:,}")
            logger.info(f"Duplicates skipped:  {self.stats['total_duplicates_skipped']:,}")
            logger.info(f"Batches flushed:     {self.stats['batches_flushed']:,}")
            if self.stats['total_items_received'] > 0:
                dup_rate = (self.stats['total_duplicates_skipped'] / self.stats['total_items_received']) * 100
                logger.info(f"Duplicate rate:      {dup_rate:.1f}%")
            logger.info("=" * 60)
            logger.info("Database connection closed")

    def process_item(self, item, spider):
        """Process job item and add to batch for insertion."""
        if not getattr(self, 'db_connected', False):
            logger.debug(f"Database not connected, skipping storage for: {item.get('title', 'Unknown')}")
            return item

        with self.stats_lock:
            self.stats['total_items_received'] += 1

        # Create content hash for deduplication
        content_string = f"{item.get('title', '')}{item.get('description', '')}{item.get('requirements', '')}"
        content_hash = hashlib.sha256(content_string.encode("utf-8")).hexdigest()

        # Prepare item data
        item_data = {
            'portal': item.get('portal'),
            'country': item.get('country'),
            'url': item.get('url'),
            'title': item.get('title'),
            'company': item.get('company'),
            'location': item.get('location'),
            'description': item.get('description'),
            'requirements': item.get('requirements'),
            'salary_raw': item.get('salary_raw'),
            'contract_type': item.get('contract_type'),
            'remote_type': item.get('remote_type'),
            'posted_date': item.get('posted_date'),
            'content_hash': content_hash
        }

        # Add to batch (thread-safe)
        with self.batch_lock:
            self.batch.append(item_data)

            # Flush batch if it reaches the configured size
            if len(self.batch) >= self.batch_size:
                self._flush_batch()

        return item

    def _flush_batch(self):
        """Flush the current batch to database (must be called with batch_lock held or at close)."""
        if not self.batch:
            return

        try:
            # Prepare batch insert values
            values = []
            for job in self.batch:
                values.append((
                    job['portal'],
                    job['country'],
                    job['url'],
                    job['title'],
                    job['company'],
                    job['location'],
                    job['description'],
                    job['requirements'],
                    job['salary_raw'],
                    job['contract_type'],
                    job['remote_type'],
                    job['posted_date'],
                    job['content_hash']
                ))

            # Execute batch insert with ON CONFLICT DO NOTHING for deduplication
            self.cursor.executemany("""
                INSERT INTO raw_jobs (
                    portal, country, url, title, company, location,
                    description, requirements, salary_raw, contract_type,
                    remote_type, posted_date, content_hash, scraped_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (content_hash) DO NOTHING
            """, values)

            self.connection.commit()

            # Calculate statistics
            inserted = self.cursor.rowcount
            duplicates = len(self.batch) - inserted

            with self.stats_lock:
                self.stats['total_items_inserted'] += inserted
                self.stats['total_duplicates_skipped'] += duplicates
                self.stats['batches_flushed'] += 1

            if inserted > 0 or duplicates > 10:
                logger.info(f"📦 Batch #{self.stats['batches_flushed']}: ✅ {inserted} inserted, ⏭️ {duplicates} duplicates")

            # Clear batch
            self.batch = []

        except psycopg2.Error as e:
            logger.error(f"❌ Batch insert error: {e}")
            self.connection.rollback()
            self.batch = []
        except Exception as e:
            logger.error(f"❌ Unexpected error during batch flush: {e}")
            self.connection.rollback()
            self.batch = []
