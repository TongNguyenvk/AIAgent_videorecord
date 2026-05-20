# MongoDB Backup Scripts

## Scripts

### 1. `backup-mongodb.sh`

Backup MongoDB database to compressed tar.gz file.

**Features**:

- Automatic compression
- Retention policy (7 days)
- Logging
- Permission handling
- Size reporting

**Usage**:

```bash
./scripts/backup-mongodb.sh
```

**Output**:

```
backups/
├── mongodb-20260501_020000.tar.gz
├── mongodb-20260502_020000.tar.gz
├── backup.log
```

**Crontab** (daily at 2 AM):

```bash
0 2 * * * /path/to/webreel-ai-agent/scripts/backup-mongodb.sh >> /path/to/webreel-ai-agent/backups/cron.log 2>&1
```

### 2. `restore-mongodb.sh`

Restore MongoDB database from backup file.

**Usage**:

```bash
./scripts/restore-mongodb.sh backups/mongodb-20260501_020000.tar.gz
```

**Interactive confirmation**:

```
WARNING: This will overwrite current database!
Continue? (yes/no):
```

**After restore**:

```bash
docker-compose -f docker-compose.prod.yml restart api
```

### 3. `check-backup-health.sh`

Check if backups are running correctly.

**Usage**:

```bash
./scripts/check-backup-health.sh
```

**Output**:

```
✅ Latest backup found:
-rw-r--r-- 1 user user 2.5M May  1 02:00 mongodb-20260501_020000.tar.gz

Total backups: 7
Total backup size: 17M

✅ Backup health check passed
```

**Crontab** (every 6 hours):

```bash
0 */6 * * * /path/to/webreel-ai-agent/scripts/check-backup-health.sh
```

## Setup

### 1. Make scripts executable

```bash
chmod +x scripts/*.sh
```

### 2. Create backup directory

```bash
mkdir -p backups
chmod 755 backups
```

### 3. Test backup

```bash
./scripts/backup-mongodb.sh
```

### 4. Test restore

```bash
./scripts/restore-mongodb.sh backups/mongodb-*.tar.gz
```

### 5. Setup crontab

```bash
crontab -e
```

Add lines:

```bash
# MongoDB backup (daily at 2 AM)
0 2 * * * /home/deploy/webreel-ai-agent/scripts/backup-mongodb.sh >> /home/deploy/webreel-ai-agent/backups/cron.log 2>&1

# Backup health check (every 6 hours)
0 */6 * * * /home/deploy/webreel-ai-agent/scripts/check-backup-health.sh
```

Verify:

```bash
crontab -l
```

## Troubleshooting

### Permission Denied

```bash
# Fix script permissions
chmod +x scripts/*.sh

# Fix backup directory permissions
chmod 755 backups

# Check Docker permissions
docker ps | grep mongodb
```

### Backup file too small

```bash
# Check MongoDB is running
docker ps | grep mongodb

# Check MongoDB logs
docker logs webreel-mongodb

# Test manual backup
docker exec webreel-mongodb mongodump --help
```

### Cron not running

```bash
# Check cron service
sudo service cron status

# Check cron logs
grep CRON /var/log/syslog

# Test script manually
./scripts/backup-mongodb.sh
```

## Backup Strategy

### Retention Policy

- **Daily backups**: Keep 7 days
- **Weekly backups**: Keep 4 weeks (manual)
- **Monthly backups**: Keep 12 months (manual)

### Offsite Backup (Optional)

Sync to Cloudflare R2:

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure R2
rclone config

# Sync backups
rclone sync backups/ r2:webreel-backups/mongodb/
```

Add to crontab:

```bash
0 3 * * * rclone sync /path/to/backups/ r2:webreel-backups/mongodb/
```

## Monitoring

### Slack Notifications

Edit `backup-mongodb.sh`:

```bash
# At the end of script
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"MongoDB backup completed: $BACKUP_SIZE\"}"
```

### Email Notifications

```bash
# Install mailutils
sudo apt-get install mailutils

# Add to backup script
echo "MongoDB backup completed: $BACKUP_SIZE" | mail -s "Backup Success" admin@example.com
```

## Recovery Procedures

### Full Database Recovery

```bash
# 1. Stop backend
docker-compose -f docker-compose.prod.yml stop api

# 2. Restore database
./scripts/restore-mongodb.sh backups/mongodb-YYYYMMDD_HHMMSS.tar.gz

# 3. Start backend
docker-compose -f docker-compose.prod.yml start api

# 4. Verify
curl http://localhost:8000/health
```

### Partial Recovery (Single Collection)

```bash
# Extract backup
tar -xzf backups/mongodb-20260501_020000.tar.gz

# Restore single collection
docker exec -i webreel-mongodb mongorestore \
  -u webreel -p webreel_mongo_2026 \
  --authenticationDatabase admin \
  --db webreel \
  --collection jobs \
  mongodb-20260501_020000/webreel/jobs.bson
```

## Best Practices

1. **Test restores regularly** - Monthly restore test
2. **Monitor backup size** - Should grow over time
3. **Check logs** - Review `backup.log` weekly
4. **Offsite backup** - Sync to R2/S3 for disaster recovery
5. **Document procedures** - Keep this README updated
6. **Alert on failures** - Setup Slack/email notifications
7. **Encrypt backups** - For sensitive data (optional)

## Security

### Encrypt Backups

```bash
# Encrypt
gpg --symmetric --cipher-algo AES256 mongodb-20260501_020000.tar.gz

# Decrypt
gpg --decrypt mongodb-20260501_020000.tar.gz.gpg > mongodb-20260501_020000.tar.gz
```

### Secure Credentials

Store MongoDB password in environment variable:

```bash
# In .env
MONGO_PASSWORD=webreel_mongo_2026

# In backup script
MONGO_PASSWORD=${MONGO_PASSWORD:-webreel_mongo_2026}
```

## Cost Analysis

### Local Backup

- **Storage**: ~100MB per backup × 7 days = 700MB
- **Cost**: Free (local disk)

### Offsite Backup (R2)

- **Storage**: 700MB × $0.015/GB = $0.01/month
- **Upload**: 7 uploads/month × $0.0000045 = $0.00003/month
- **Total**: ~$0.01/month (negligible)

**Recommendation**: Enable offsite backup for disaster recovery.
