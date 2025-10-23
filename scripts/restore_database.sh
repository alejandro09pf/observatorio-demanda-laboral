#!/bin/bash
#
# Database Restore Script
# Restores database from a compressed SQL dump
#

set -e  # Exit on error

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    BACKUP_DIR="$PROJECT_ROOT/data/backups"

    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"
    fi
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Database connection details
DB_HOST="127.0.0.1"
DB_PORT="5433"
DB_NAME="labor_observatory"
DB_USER="labor_user"
DB_PASSWORD="123456"

echo "=================================="
echo "DATABASE RESTORE"
echo "=================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
echo ""
echo "⚠️  WARNING: This will DROP and recreate the database!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Export password
export PGPASSWORD="$DB_PASSWORD"

echo ""
echo "Dropping existing database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "Creating new database..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "Creating pgvector extension..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Restoring backup..."
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

# Unset password
unset PGPASSWORD

echo ""
echo "✅ Restore completed successfully!"
echo ""

# Show table counts
export PGPASSWORD="$DB_PASSWORD"
echo "Table row counts after restore:"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT
        tablename,
        n_live_tup as row_count
    FROM pg_stat_user_tables
    WHERE schemaname = 'public'
    ORDER BY n_live_tup DESC;
"
unset PGPASSWORD

echo ""
echo "=================================="
echo "RESTORE COMPLETE"
echo "=================================="
