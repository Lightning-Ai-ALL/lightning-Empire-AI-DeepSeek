import os
from gtts import gTTS

OUTPUT_DIR = "output"

def generate_tts(summary: dict):
    case_no = summary.get("case_number", "未知案號")
    message = (
        f"Lightning Legal AI 提醒。"
        f"案件 {case_no}。"
        f"請確認法院文件送達日期與上訴期限。"
        f"請確認案件待辦事項。"
    )
    
    # 儲存文字檔
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt_path = os.path.join(OUTPUT_DIR, "tts_message.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(message)
    
    # 產生 mp3
    tts = gTTS(text=message, lang="zh-tw")
    mp3_path = os.path.join(OUTPUT_DIR, "legal_notice.mp3")
    tts.save(mp3_path)
