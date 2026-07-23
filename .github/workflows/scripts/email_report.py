import os
import json
from datetime import datetime

OUTPUT_DIR = "output"

def generate_report(summary: dict):
    case_no = summary.get("case_number", "未知")
    need_verify = summary.get("need_verify", [])
    
    items_html = "".join(f"<li>{item}</li>" for item in need_verify) if need_verify else "<li>無</li>"
    
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>案件報告</title></head>
<body>
<h1>⚡ Lightning-Legal-AI 案件報告</h1>
<p>案號：{case_no}</p>
<p>系統狀態：{'待確認事項：' + str(len(need_verify)) + ' 項' if need_verify else '暫無待確認項目'}</p>
<h2>待確認清單</h2>
<ul>{items_html}</ul>
<p>生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>"""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "report.html"), "w", encoding="utf-8") as f:
        f.write(html)
