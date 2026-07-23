# sentinel_v3.py - Lightning-ALL 專用 v3（CSV Schema Guard + Auto Rollback + Energy Pipeline）
import os
import json
import hashlib
import shutil
import logging
from datetime import datetime
from pathlib import Path

# ================== 配置 ==================
TARGET_CSV = r"D:\Lightning-AI-ALL\data\emotion×reasoning.Ai.csv"   # 主 CSV
SNAPSHOT_DIR = r"D:\Lightning-AI-ALL\sentinel_snapshots"
BACKUP_DIR = r"D:\Lightning-AI-ALL\sentinel_backups"
LOG_FILE = r"D:\Lightning-AI-ALL\sentinel_v3.log"

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

EXPECTED_COLUMNS = 12  # emotion×reasoning.Ai.csv 欄位數

def get_file_hash(file_path):
    return hashlib.md5(Path(file_path).read_bytes()).hexdigest()

def create_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(BACKUP_DIR) / f"energy_backup_{ts}.csv"
    shutil.copy2(TARGET_CSV, backup_path)
    logging.info(f"Backup created: {backup_path.name}")
    return str(backup_path)

def get_csv_schema():
    if not Path(TARGET_CSV).exists():
        return {"error": "CSV not found"}
    with open(TARGET_CSV, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split(',')
    return {
        "column_count": len(header),
        "columns": [h.strip() for h in header],
        "hash": get_file_hash(TARGET_CSV)
    }

def validate_and_snapshot():
    schema = get_csv_schema()
    if "error" in schema:
        logging.error(schema["error"])
        return {"status": "error", "msg": schema["error"]}

    if schema["column_count"] != EXPECTED_COLUMNS:
        logging.warning(f"Schema mismatch! Expected {EXPECTED_COLUMNS}, got {schema['column_count']}")
        # Auto rollback
        latest_backup = max(Path(BACKUP_DIR).glob("*.csv"), default=None)
        if latest_backup:
            shutil.copy2(latest_backup, TARGET_CSV)
            logging.info(f"Auto rollback executed from {latest_backup.name}")
            return {"status": "rollback", "restored_from": str(latest_backup)}
        return {"status": "mismatch"}

    # Create snapshot
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = {
        "version": ts,
        "timestamp": datetime.now().isoformat(),
        "schema": schema,
        "backup": create_backup()
    }
    snap_file = Path(SNAPSHOT_DIR) / f"snapshot_{ts}.json"
    snap_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    
    logging.info(f"✅ Sentinel v3 SUCCESS - Version {ts} | Columns: {schema['column_count']}")
    return {"status": "ok", "version": ts}

if __name__ == "__main__":
    result = validate_and_snapshot()
    print(json.dumps(result, indent=2, ensure_ascii=False))
