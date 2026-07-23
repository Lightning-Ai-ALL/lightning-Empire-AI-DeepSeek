import os
import json
import re

OUTPUT_DIR = "output"

def parse_case(txt_path: str) -> dict:
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"原始案件檔案不存在: {txt_path}")
    
    # 從檔名提取案號，例如 "115簡238_raw.txt" → "115年度簡字第238號"
    basename = os.path.basename(txt_path)
    raw_name = basename.replace("_raw.txt", "")  # "115簡238"
    # 簡單轉換：假設格式為 年度+簡/易/訴+編號
    match = re.match(r"(\d+)(\D+)(\d+)", raw_name)
    if match:
        year = match.group(1)
        case_type = match.group(2)
        number = match.group(3)
        case_number = f"{year}年度{case_type}字第{number}號"
    else:
        case_number = raw_name  # fallback

    # 讀取全文
    with open(txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 嘗試從內文找出法院名稱
    court = ""
    court_match = re.search(r"臺灣\w+地方法院", full_text)
    if court_match:
        court = court_match.group(0)

    # 組成 summary（user_claim / need_verify 保留為空，由使用者事後手動編輯）
    summary = {
        "case_number": case_number,
        "court": court,
        "source": "裁判書原文",
        "court_finding": [],   # 可手動加入法院認定的要點
        "user_claim": [],      # 手動填入你的主張
        "need_verify": [],     # 手動填入待確認事項（如：送達日期、監視器原始檔）
        "service_date": None,
        "appeal_deadline": None
    }

    # 寫入 output/case_summary.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "case_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary
