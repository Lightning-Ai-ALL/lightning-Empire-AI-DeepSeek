# sentinel_v3.py - 完整版ai_capital_flow.py（Schema Guard + Rollback + Alert + GitHub Action ready）
import os, json, hashlib, shutil, logging
from datetime import datetime
from pathlib import Path

TARGET_CSV = r"D:\Lightning-AI-ALL\data\emotion×reasoning.Ai.csv"
SNAPSHOT_DIR = r"D:\Lightning-AI-ALL\sentinel_snapshots"
BACKUP_DIR = r"D:\Lightning-AI-ALL\sentinel_backups"
LOG_FILE = r"D:\Lightning-AI-ALL\sentinel.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, encoding='utf-8')

def get_hash(path): 
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

def create_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = Path(BACKUP_DIR) / f"energy_{ts}.csv"
    shutil.copy2(TARGET_CSV, backup)
    return str(backup)

def validate_schema():
    if not Path(TARGET_CSV).exists():
        logging.error("CSV missing")
        return False
    with open(TARGET_CSV, encoding='utf-8') as f:
        cols = len(f.readline().strip().split(','))
    return cols == 12  # 你的 emotion×reasoning 標準欄位數

def run_v3():
    if not validate_schema():
        latest_backup = max(Path(BACKUP_DIR).glob("*.csv"), default=None)
        if latest_backup:
            shutil.copy2(latest_backup, TARGET_CSV)
            logging.warning(f"⚠️ Schema mismatch → Auto rollback to {latest_backup.name}")
        return {"status": "rollback"}
    
    snapshot = {
        "version": datetime.now().isoformat(),
        "hash": get_hash(TARGET_CSV),
        "columns": 12,
        "backup": create_backup()
    }
    snap_file = Path(SNAPSHOT_DIR) / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    snap_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    
    logging.info(f"✅ Sentinel v3 OK - Version {snapshot['version']}")
    return {"status": "ok", "version": snapshot["version"]}

if __name__ == "__main__":
    run_v3()
# ai_capital_flow.py - AI 概念股資金流監控 (Taiwan Focus)
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging

logging.basicConfig(filename=r'D:\Lightning-AI-ALL\ai_monitor.log', level=logging.INFO, encoding='utf-8')

# TWSE 公開資料來源（三大法人買賣超）
TWSE_INSTITUTION_URL = "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date}&_={ts}"

AI_CONCEPT_KEYWORDS = ["台積電", "鴻海", "奇鋐", "台達電", "金像電", "緯創", "廣達", "技嘉"]  # 可擴充

def fetch_institutional_flow(date_str=None):
    if not date_str:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    url = TWSE_INSTITUTION_URL.format(date=date_str, ts=int(datetime.now().timestamp()))
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        df = pd.DataFrame(data.get('data9', []), columns=data.get('fields9', []))
        return df
    except Exception as e:
        logging.error(f"Fetch failed: {e}")
        return pd.DataFrame()

def monitor_ai_flow():
    df = fetch_institutional_flow()
    if df.empty:
        print("⚠️ 今日無資料")
        return
    
    # 篩選 AI 概念股
    df_ai = df[df['證券名稱'].str.contains('|'.join(AI_CONCEPT_KEYWORDS), na=False)]
    
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_ai_net_buy": df_ai['外資買賣超'].astype(float).sum() if '外資買賣超' in df_ai.columns else 0,
        "top_stocks": df_ai.nlargest(5, '外資買賣超')[['證券名稱', '外資買賣超', '投信買賣超']].to_dict('records')
    }
    
    # 存檔 + Sentinel 整合
    output_dir = Path(r"D:\Lightning-AI-ALL\ai_capital_data")
    output_dir.mkdir(exist_ok=True)
    json_path = output_dir / f"ai_flow_{datetime.now().strftime('%Y%m%d')}.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    
    print("✅ AI 資金流監控完成")
    print(f"外資淨買 AI 概念: {summary['total_ai_net_buy']:,.0f}")
    print("Top 買超:", summary['top_stocks'])
    
    # 可串 Sentinel v3
    # from sentinel_v3 import validate_and_snapshot
    # validate_and_snapshot()  # 版本追蹤 CSV/JSON

if __name__ == "__main__":
    monitor_ai_flow()
