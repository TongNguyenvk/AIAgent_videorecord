#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh backups/mongodb-*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/mongodb-restore-$$"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=========================================="
echo "MongoDB Restore"
echo "=========================================="
echo "Backup file: $BACKUP_FILE"
echo "WARNING: This will overwrite current database!"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Extracting backup..."
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

echo "Copying to container..."
docker cp "$RESTORE_DIR" webreel-mongodb:/data/restore

echo "Restoring database..."
docker exec webreel-mongodb mongorestore \
    -u webreel \
    -p webreel_mongo_2026 \
    --authenticationDatabase admin \
    --db webreel \
    --drop \
    /data/restore/webreel

echo "Cleaning up..."
rm -rf "$RESTORE_DIR"
docker exec webreel-mongodb rm -rf /data/restore

echo ""
echo "=========================================="
echo "✅ Restore completed successfully!"
echo "=========================================="
echo ""
echo "Restart backend to reload data:"
echo "docker-compose -f docker-compose.prod.yml restart api"
