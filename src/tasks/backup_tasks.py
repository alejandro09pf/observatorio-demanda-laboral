"""
Database Backup Tasks
Automated PostgreSQL backups with cleanup
"""
import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from celery import Task
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def backup_database_task(self: Task):
    """
    Automated PostgreSQL database backup

    - Creates compressed backup in data/backups/
    - Filename: auto_backup_YYYYMMDD_HHMMSS.dump
    - Keeps backups for 7 days, then auto-deletes

    Returns:
        dict: Backup metadata (filename, size, timestamp)
    """
    try:
        # Create timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"auto_backup_{timestamp}.dump"

        # Ensure backup directory exists
        backup_dir = Path("/app/data/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / backup_filename

        logger.info(f"🔄 Starting database backup: {backup_filename}")

        # PostgreSQL connection info from environment
        db_host = os.getenv("DB_HOST", "postgres")
        db_name = os.getenv("DB_NAME", "labor_observatory")
        db_user = os.getenv("DB_USER", "labor_user")
        db_password = os.getenv("DB_PASSWORD", "123456")

        # Run pg_dump con conexión remota a postgres
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        cmd = [
            "pg_dump",
            "-h", db_host,
            "-U", db_user,
            "-F", "c",  # Custom compressed format
            "-f", str(backup_path),
            db_name
        ]

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )

        if result.returncode != 0:
            logger.error(f"❌ Backup failed: {result.stderr}")
            raise Exception(f"pg_dump failed: {result.stderr}")

        # Get backup file size
        backup_size = backup_path.stat().st_size
        backup_size_mb = backup_size / (1024 * 1024)

        logger.info(f"✅ Backup completed: {backup_filename} ({backup_size_mb:.2f} MB)")

        # Cleanup old backups (older than 7 days)
        cleanup_old_backups(backup_dir, days=7)

        return {
            "status": "success",
            "filename": backup_filename,
            "size_mb": round(backup_size_mb, 2),
            "timestamp": timestamp,
            "path": str(backup_path)
        }

    except subprocess.TimeoutExpired:
        logger.error("❌ Backup timeout (>10 minutes)")
        raise self.retry(countdown=300)  # Retry after 5 minutes

    except Exception as exc:
        logger.error(f"❌ Backup error: {exc}")
        raise self.retry(exc=exc, countdown=60)


def cleanup_old_backups(backup_dir: Path, days: int = 7):
    """
    Delete backup files older than specified days

    Args:
        backup_dir: Directory containing backups
        days: Number of days to keep backups
    """
    import time

    cutoff_time = time.time() - (days * 86400)  # 86400 seconds = 1 day
    deleted_count = 0

    for backup_file in backup_dir.glob("auto_backup_*.dump"):
        if backup_file.stat().st_mtime < cutoff_time:
            try:
                backup_file.unlink()
                deleted_count += 1
                logger.info(f"🗑️  Deleted old backup: {backup_file.name}")
            except Exception as exc:
                logger.warning(f"⚠️  Could not delete {backup_file.name}: {exc}")

    if deleted_count > 0:
        logger.info(f"✅ Cleanup complete: {deleted_count} old backups deleted")


@celery_app.task
def manual_backup_task(include_timestamp: bool = True):
    """
    Manual backup triggered by user (not scheduled)

    Args:
        include_timestamp: Include timestamp in filename

    Returns:
        dict: Backup metadata
    """
    return backup_database_task()
