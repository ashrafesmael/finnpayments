#!/bin/bash
# FinnPayments database backup script
# Backs up finnpayments.db and aml_auth.db daily with 30-day retention
# Install: sudo cp deploy/backup-db.sh /usr/local/bin/finnpayments-backup.sh
#          sudo chmod +x /usr/local/bin/finnpayments-backup.sh
#          sudo cp deploy/finnpayments-backup.service /etc/systemd/system/
#          sudo cp deploy/finnpayments-backup.timer /etc/systemd/system/
#          sudo systemctl enable --now finnpayments-backup.timer

set -euo pipefail

APP_DIR="/home/administrator/finnpayments"
BACKUP_DIR="/home/administrator/backups/finnpayments"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting FinnPayments database backup..."

# Back up business DB
BUSINESS_DB="$APP_DIR/finnpayments.db"
if [ -f "$BUSINESS_DB" ]; then
    # Use sqlite3 .backup for a safe online snapshot
    sqlite3 "$BUSINESS_DB" ".backup '$BACKUP_DIR/finnpayments_${DATE}.db'"
    echo "[$(date)] Backed up finnpayments.db → finnpayments_${DATE}.db"
else
    echo "[$(date)] WARNING: finnpayments.db not found, skipping"
fi

# Back up auth DB
AUTH_DB="$APP_DIR/aml_auth.db"
if [ -f "$AUTH_DB" ]; then
    sqlite3 "$AUTH_DB" ".backup '$BACKUP_DIR/aml_auth_${DATE}.db'"
    echo "[$(date)] Backed up aml_auth.db → aml_auth_${DATE}.db"
else
    echo "[$(date)] WARNING: aml_auth.db not found, skipping"
fi

# Compress backups
cd "$BACKUP_DIR"
for f in *_${DATE}.db; do
    if [ -f "$f" ]; then
        gzip -f "$f"
        echo "[$(date)] Compressed $f"
    fi
done

# Delete backups older than retention period
DELETED=$(find "$BACKUP_DIR" -name "*.db.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "[$(date)] Deleted $DELETED backup(s) older than $RETENTION_DAYS days"

# Show current backup count and disk usage
COUNT=$(find "$BACKUP_DIR" -name "*.db.gz" | wc -l)
SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$(date)] Backup complete: $COUNT files, $SIZE total"

# Write status file for monitoring
echo "{\"last_backup\":\"$(date -Iseconds)\",\"files\":$COUNT,\"size\":\"$SIZE\"}" > "$BACKUP_DIR/last_backup.json"
