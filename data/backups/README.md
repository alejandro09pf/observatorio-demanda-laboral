# Database Backups

This directory contains database backup and restore utilities for the Labor Observatory project.

## Overview

The database backup files (*.sql.gz) are **NOT committed to git** due to their large size (100+ MB). However, the backup and restore scripts ARE committed, allowing you to create and restore backups on any computer.

## Creating a Backup

Run the backup script from the project root:

```bash
bash scripts/backup_database.sh
```

This will:
- Create a timestamped compressed SQL dump in `data/backups/`
- File format: `labor_observatory_backup_YYYYMMDD_HHMMSS.sql.gz`
- Include all tables: raw_jobs, cleaned_jobs, extracted_skills, esco_skills, skill_embeddings, etc.
- Show table row counts after backup

**Example output:**
```
==================================
DATABASE BACKUP
==================================

Database: labor_observatory
Backup file: data/backups/labor_observatory_backup_20251023_123806.sql.gz

Creating backup...
✅ Backup completed successfully!
   File: data/backups/labor_observatory_backup_20251023_123806.sql.gz
   Size: 112M
```

## Restoring a Backup

To restore a backup on another computer:

```bash
bash scripts/restore_database.sh data/backups/labor_observatory_backup_YYYYMMDD_HHMMSS.sql.gz
```

**⚠️ WARNING**: This will **DROP and recreate** the entire database!

The script will:
1. Ask for confirmation before proceeding
2. Drop the existing labor_observatory database
3. Create a new empty database
4. Create the pgvector extension
5. Restore all data from the backup file
6. Show table row counts after restore

**Example:**
```bash
# List available backups
bash scripts/restore_database.sh

# Restore a specific backup
bash scripts/restore_database.sh data/backups/labor_observatory_backup_20251023_123806.sql.gz
```

## Transferring Backups Between Computers

Since backup files are not in git, you need to transfer them manually:

**Option 1: Cloud Storage**
- Upload the .sql.gz file to Google Drive, Dropbox, etc.
- Download on the target computer

**Option 2: Direct Transfer**
- Use `scp`, `rsync`, or USB drive to copy the file

**Option 3: Fresh Scraping**
- Instead of transferring data, run the scraping and extraction pipeline on the new computer

## Database Connection Details

The scripts use these connection parameters (from .env):
- Host: 127.0.0.1
- Port: 5433
- Database: labor_observatory
- User: labor_user
- Password: 123456

Make sure PostgreSQL is running and accessible before running the scripts.

## Typical Database Sizes

As of October 2025:
- **Compressed backup**: ~112 MB (.sql.gz)
- **Uncompressed SQL**: ~550 MB
- **Database on disk**: ~650 MB

**Table sizes** (uncompressed):
- cleaned_jobs: 301 MB
- skill_embeddings: 120 MB
- raw_jobs: 105 MB
- esco_skills: 17 MB
- extracted_skills: ~15 MB
- Other tables: <5 MB each

## Automation

You can automate backups using cron:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/project && bash scripts/backup_database.sh

# Weekly backup on Sundays at 3 AM
0 3 * * 0 cd /path/to/project && bash scripts/backup_database.sh
```

## Troubleshooting

**"Database connection failed"**
- Verify PostgreSQL is running: `docker-compose ps` or `pg_ctl status`
- Check .env has correct DATABASE_URL
- Test connection: `psql -h 127.0.0.1 -p 5433 -U labor_user -d labor_observatory`

**"pg_dump: command not found"**
- Install PostgreSQL client tools
- On macOS: `brew install postgresql`
- On Ubuntu: `sudo apt install postgresql-client`

**"gunzip: command not found"**
- Install gzip (usually pre-installed on Unix systems)
- On Windows: Use Git Bash or WSL

**Backup file too large for transfer**
- Consider splitting: `split -b 50M backup.sql.gz backup_part_`
- Rejoin: `cat backup_part_* > backup.sql.gz`
