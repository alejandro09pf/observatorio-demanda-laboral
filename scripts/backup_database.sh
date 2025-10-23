#!/bin/bash
#
# Database Backup Script
# Creates a compressed SQL dump of the entire database
#

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/labor_observatory_backup_$TIMESTAMP.sql.gz"

# Database connection details
DB_HOST="127.0.0.1"
DB_PORT="5433"
DB_NAME="labor_observatory"
DB_USER="labor_user"
DB_PASSWORD="123456"

echo "=================================="
echo "DATABASE BACKUP"
echo "=================================="
echo ""
echo "Database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Export password for pg_dump
export PGPASSWORD="$DB_PASSWORD"

# Create backup
echo "Creating backup..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo ""
    echo "✅ Backup completed successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
    echo ""

    # Show table counts
    echo "Table row counts in backup:"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT
            tablename,
            n_live_tup as row_count
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY n_live_tup DESC;
    "
else
    echo "❌ Backup failed!"
    exit 1
fi

# Unset password
unset PGPASSWORD

echo ""
echo "=================================="
echo "BACKUP COMPLETE"
echo "=================================="
