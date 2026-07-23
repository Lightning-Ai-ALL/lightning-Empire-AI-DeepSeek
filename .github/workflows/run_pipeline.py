import json
from datetime import datetime

event_log = {
    "case": "115年度簡字第238號",
    "event": "上訴理由狀草稿生成",
    "datetime": datetime.now().isoformat(),
    "timezone": "Asia/Taipei",
    "document": {
        "filename": "上訴理由狀_115年度簡字第238號_1150724.docx",
        "type": "刑事上訴理由狀",
        "status": "待人工確認寄出"
    },
    "automation": {
        "trigger": "manual_dispatch",
        "workflow": "Lightning-Legal-AI-Draft",
        "audit_log": True
    },
    "verification": {
        "require_signature": True,
        "require_final_review": True,
        "human_confirmed": False
    }
}

with open("output/event_log.json", "w", encoding="utf-8") as f:
    json.dump(event_log, f, ensure_ascii=False, indent=2)
