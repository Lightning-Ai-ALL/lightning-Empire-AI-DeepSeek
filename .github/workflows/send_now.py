import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime

OUTPUT_DIR = "output"

# 找最新產生的 docx
files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".docx")]
if not files:
    print("❌ 找不到任何 docx 檔案")
    exit(1)

latest_file = sorted(files)[-1]  # 依檔名排序取最後
filepath = os.path.join(OUTPUT_DIR, latest_file)

from_addr = os.environ.get("EMAIL_FROM")
password = os.environ.get("EMAIL_PASSWORD")
to_addr = os.environ.get("EMAIL_TO")

if not all([from_addr, password, to_addr]):
    print("❌ 請先設定 EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO 環境變數")
    exit(1)

msg = MIMEMultipart()
msg["From"] = from_addr
msg["To"] = to_addr
msg["Subject"] = f"⚡ Lightning-Legal-AI 上訴理由狀 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

body = f"本郵件由 Lightning-Legal-AI 自動產生，附件為今日產出之{latest_file}，僅供本人備份，請勿回覆。"
msg.attach(MIMEText(body, "plain"))

with open(filepath, "rb") as f:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={latest_file}")
    msg.attach(part)

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(from_addr, password)
    server.sendmail(from_addr, to_addr, msg.as_string())
    server.quit()
    print(f"📧 已寄出 {latest_file} 至 {to_addr}")
except Exception as e:
    print(f"❌ 寄送失敗: {e}")
