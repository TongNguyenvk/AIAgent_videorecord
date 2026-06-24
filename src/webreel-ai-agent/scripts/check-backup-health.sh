#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

echo "=========================================="
echo "MongoDB Backup Health Check"
echo "=========================================="

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Find latest backup (within last 24 hours)
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "mongodb-*.tar.gz" -mtime -1 | sort | tail -n 1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ No backup found in last 24 hours!"
    echo ""
    echo "Last 5 backups:"
    ls -lht "$BACKUP_DIR"/mongodb-*.tar.gz 2>/dev/null | head -n 5 || echo "No backups found"
    echo ""
    echo "Action required: Check backup cron job"
    
    # Optional: Send alert
    # curl -X POST https://hooks.slack.com/... -d '{"text":"MongoDB backup missing!"}'
    
    exit 1
else
    echo "✅ Latest backup found:"
    ls -lh "$LATEST_BACKUP"
    echo ""
    
    # Check backup size (should be > 1KB)
    BACKUP_SIZE=$(stat -f%z "$LATEST_BACKUP" 2>/dev/null || stat -c%s "$LATEST_BACKUP" 2>/dev/null)
    if [ "$BACKUP_SIZE" -lt 1024 ]; then
        echo "⚠️  WARNING: Backup file is suspiciously small (< 1KB)"
        echo "   This might indicate a failed backup"
        exit 1
    fi
    
    # Count total backups
    TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "mongodb-*.tar.gz" | wc -l)
    echo "Total backups: $TOTAL_BACKUPS"
    
    # Calculate total backup size
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo "Total backup size: $TOTAL_SIZE"
    
    echo ""
    echo "✅ Backup health check passed"
    exit 0
fi
