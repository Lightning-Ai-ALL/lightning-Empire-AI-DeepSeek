# Lightning-Legal-AI v0.1

私人法律文件輔助系統（非公開、非商用）

## 功能
- 保存法院文件原文（不可修改）
- 解析案號、法院
- 分離法院認定、當事人主張、待確認事項
- 生成 AI 輔助 Word 上訴草稿
- 語音提醒（TTS）
- Email 備份給自己

## 限制
❌ 不自動提交法院、不簽名、不代理送件、不判定有罪無罪

## 使用方式（本機）
1. 將裁判書全文存為 `cases/XXX_raw.txt`
2. 設定環境變數（可選，用於寄信）：
   - `EMAIL_FROM`
   - `EMAIL_PASSWORD`（Gmail 應用程式密碼）
   - `EMAIL_TO`
3. 執行：
   ```bash
   pip install -r requirements.txt
   python run_pipeline.py cases/115簡238_raw.txt
