#!/usr/bin/env python3
"""FinnPayments database backup script.
Backs up finnpayments.db and aml_auth.db daily with 30-day retention.

Install:
  sudo cp deploy/backup-db.py /usr/local/bin/finnpayments-backup.py
  sudo chmod +x /usr/local/bin/finnpayments-backup.py
  sudo cp deploy/finnpayments-backup.service /etc/systemd/system/
  sudo cp deploy/finnpayments-backup.timer /etc/systemd/system/
  sudo systemctl enable --now finnpayments-backup.timer
"""
import sqlite3
import gzip
import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

APP_DIR = Path("/home/administrator/finnpayments")
BACKUP_DIR = Path("/home/administrator/backups/finnpayments")
RETENTION_DAYS = 30

def backup_database(src_path: Path, dest_path: Path):
    """Create a safe online backup of a SQLite database."""
    src_conn = sqlite3.connect(str(src_path))
    dest_conn = sqlite3.connect(str(dest_path))
    src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()

def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[{datetime.now().isoformat()}] Starting FinnPayments database backup...")

    backed_up = []
    for db_name in ["finnpayments.db", "aml_auth.db"]:
        src = APP_DIR / db_name
        if src.exists():
            dest = BACKUP_DIR / f"{db_name.replace('.db', '')}_{timestamp}.db"
            backup_database(src, dest)
            # Compress
            gz_path = dest.with_suffix(".db.gz")
            with open(dest, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            dest.unlink()  # remove uncompressed
            print(f"[{datetime.now().isoformat()}] Backed up {db_name} → {gz_path.name}")
            backed_up.append(gz_path.name)
        else:
            print(f"[{datetime.now().isoformat()}] WARNING: {db_name} not found, skipping")

    # Delete backups older than retention period
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted = 0
    for f in BACKUP_DIR.glob("*.db.gz"):
        if f.stat().st_mtime < cutoff.timestamp():
            f.unlink()
            deleted += 1
    print(f"[{datetime.now().isoformat()}] Deleted {deleted} backup(s) older than {RETENTION_DAYS} days")

    # Show status
    all_backups = list(BACKUP_DIR.glob("*.db.gz"))
    total_size = sum(f.stat().st_size for f in all_backups)
    size_mb = round(total_size / (1024 * 1024), 1)
    print(f"[{datetime.now().isoformat()}] Backup complete: {len(all_backups)} files, {size_mb} MB total")

    # Write status file for monitoring
    status = {
        "last_backup": datetime.now().isoformat(),
        "files": len(all_backups),
        "size_mb": size_mb,
    }
    (BACKUP_DIR / "last_backup.json").write_text(json.dumps(status))

if __name__ == "__main__":
    main()
