import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import logging

OUTPUT_DIR = "output"

def send_email_backup():
    from_addr = os.environ.get("EMAIL_FROM")
    password = os.environ.get("EMAIL_PASSWORD")
    to_addr = os.environ.get("EMAIL_TO")
    
    if not all([from_addr, password, to_addr]):
        logging.warning("Email 環境變數未設定，跳過寄送。")
        print("⚠️  未設定 EMAIL_FROM / EMAIL_PASSWORD / EMAIL_TO，略過 Email 備份。")
        return
    
    # 建立郵件
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = "⚡ Lightning-Legal-AI 案件備份通知"
    
    body = "本郵件由 Lightning-Legal-AI 自動產生，僅供本人備份，請勿回覆。"
    msg.attach(MIMEText(body, "plain"))
    
    # 附加檔案
    attachments = ["appeal_draft.docx", "case_summary.json", "legal_notice.mp3"]
    for filename in attachments:
        path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(path):
            logging.warning(f"附件不存在: {path}")
            continue
        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
    
    # 寄送（使用 Gmail SMTP）
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_addr, password)
        server.sendmail(from_addr, to_addr, msg.as_string())
        server.quit()
        logging.info("Email 備份已成功寄出。")
        print("📧 Email 備份寄送成功。")
    except Exception as e:
        logging.error(f"Email 寄送失敗: {str(e)}")
        print(f"❌ Email 寄送失敗: {e}")
