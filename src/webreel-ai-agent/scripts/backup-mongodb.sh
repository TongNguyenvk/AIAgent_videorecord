#!/bin/bash
set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_ROOT="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/mongodb-$DATE"
RETENTION_DAYS=7
LOG_FILE="$BACKUP_ROOT/backup.log"

# Ensure backup directory exists with correct permissions
mkdir -p "$BACKUP_ROOT"
chmod 755 "$BACKUP_ROOT"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting MongoDB backup..."

# Check if MongoDB container is running
if ! docker ps | grep -q webreel-mongodb; then
    log "ERROR: MongoDB container is not running"
    exit 1
fi

# Create backup inside container
log "Creating backup in container..."
docker exec webreel-mongodb mongodump \
    -u webreel \
    -p webreel_mongo_2026 \
    --authenticationDatabase admin \
    --db webreel \
    --out /data/backup/$DATE \
    2>&1 | tee -a "$LOG_FILE"

# Copy backup to host
log "Copying backup to host..."
if docker cp webreel-mongodb:/data/backup/$DATE "$BACKUP_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    log "Backup copied successfully to $BACKUP_DIR"
else
    log "ERROR: Failed to copy backup"
    exit 1
fi

# Fix permissions (make readable by current user)
chmod -R 755 "$BACKUP_DIR"

# Compress backup
log "Compressing backup..."
cd "$BACKUP_ROOT"
tar -czf "mongodb-$DATE.tar.gz" "mongodb-$DATE"
rm -rf "mongodb-$DATE"
log "Backup compressed: mongodb-$DATE.tar.gz"

# Calculate backup size
BACKUP_SIZE=$(du -h "mongodb-$DATE.tar.gz" | cut -f1)
log "Backup size: $BACKUP_SIZE"

# Clean up old backups (keep last N days)
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_ROOT" -name "mongodb-*.tar.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_ROOT" -name "mongodb-*.tar.gz" | wc -l)
log "Remaining backups: $REMAINING"

# Clean up backup inside container
docker exec webreel-mongodb rm -rf /data/backup/$DATE

log "Backup completed successfully!"

# Optional: Send notification (uncomment and configure)
# curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
#   -H 'Content-Type: application/json' \
#   -d "{\"text\":\"MongoDB backup completed: $BACKUP_SIZE\"}"

exit 0
