#!/bin/bash
#
# Rejoin Backup Script
# Rejoins split backup files into a single compressed SQL dump
#

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/data/backups"

echo "=================================="
echo "REJOIN BACKUP FILES"
echo "=================================="
echo ""

# Check if split files exist
if [ ! -f "$BACKUP_DIR/backup_part_aa" ]; then
    echo "❌ Error: Split backup files not found in $BACKUP_DIR"
    echo ""
    echo "Expected files:"
    echo "  - backup_part_aa"
    echo "  - backup_part_ab"
    echo "  - backup_part_ac"
    exit 1
fi

# Create timestamp for rejoined file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="$BACKUP_DIR/labor_observatory_backup_${TIMESTAMP}.sql.gz"

echo "Rejoining split backup files..."
echo "Output: $OUTPUT_FILE"
echo ""

# Rejoin the files
cat "$BACKUP_DIR"/backup_part_* > "$OUTPUT_FILE"

# Verify the file
if [ -f "$OUTPUT_FILE" ]; then
    SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo "✅ Backup rejoined successfully!"
    echo "   File: $OUTPUT_FILE"
    echo "   Size: $SIZE"
    echo ""

    # Test if it's a valid gzip file
    if gunzip -t "$OUTPUT_FILE" 2>/dev/null; then
        echo "✅ Backup file integrity verified (valid gzip)"
    else
        echo "⚠️  Warning: Backup file may be corrupted"
    fi
else
    echo "❌ Failed to rejoin backup files"
    exit 1
fi

echo ""
echo "=================================="
echo "REJOIN COMPLETE"
echo "=================================="
echo ""
echo "You can now restore the database using:"
echo "bash scripts/restore_database.sh $OUTPUT_FILE"
