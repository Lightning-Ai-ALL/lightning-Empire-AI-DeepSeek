#!/usr/bin/env python3
"""
WindAI 地震與海嘯預警系統 v2.0 (獨立地震頁面)
- 即時監測 CWA / OpenWeather 地震資料 (模擬)
- 地震強度分級警報 (4級以上觸發)
- 海嘯風險評估與自動通報
- 防禦資金與捐款紀錄 (聯邦銀行主帳戶)
- AI 災損分析 (選用)
"""

import random
import time
from datetime import datetime

# ========== 聯邦銀行主帳戶 (環境設定 - 與無人機系統共用) ==========
BANK_NAME = "聯邦銀行"
BANK_NUMBER = "061507123481"
UNION_BANK_CODE = "803"
UNION_SWIFT = "UBOTTWTP"

# ========== 金流串接設定 (用於緊急捐款或資金調度) ==========
PAYMENT_PROVIDER = "ecpay"
ECPAY_MERCHANT_ID = "2000132"
ECPAY_HASH_KEY = "5294y06JbISpM5x9"
ECPAY_HASH_IV = "v77hoKGq4kWxNNZS"
ECPAY_DEBUG = 1

LINE_PAY_CHANNEL_ID = "YOUR_CHANNEL_ID"
LINE_PAY_CHANNEL_SECRET = "YOUR_CHANNEL_SECRET"
LINE_PAY_SANDBOX = 1

# ========== 地震 API 金鑰 (與無人機系統相同的 API 環境) ==========
CWA_API_KEY = "CWA-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
OPENWEATHER_API_KEY = "your_openweather_key"

# ========== AI 分析金鑰 ==========
OPENAI_API_KEY = "your_openai_key"
GEMINI_API_KEY = "your_gemini_key"

# ========== 地震警報閾值 ==========
EARTHQUAKE_INTENSITY_THRESHOLD = 4      # 中央氣象局震度分級 4 級以上
TSUNAMI_ALERT_ENABLED = True
TSUNAMI_MAGNITUDE_THRESHOLD = 7.0       # 規模 7.0 以上可能引發海嘯

# ========== 模擬監測參數 ==========
CHECK_INTERVAL = 2.0                    # 每 2 秒檢測一次
SIMULATION_CYCLES = 25                  # 總監測次數

# 模擬地震事件池 (震央, 規模, 深度, 最大震度)
POSSIBLE_EVENTS = [
    ("花蓮近海", 6.2, 15.0, 5),
    ("宜蘭外海", 5.8, 20.0, 4),
    ("台東成功", 4.5, 8.0, 3),
    ("南投山區", 5.0, 12.0, 4),
    ("基隆外海", 7.1, 30.0, 5),   # 可能引發海嘯
    ("嘉義中埔", 3.9, 5.0, 2),
    ("屏東恆春", 6.8, 25.0, 5),
    ("日本琉球海溝", 7.5, 40.0, 4), # 遠地海嘯風險
]

print("🌍 WindAI 地震與海嘯預警系統 v2.0 啟動")
print(f"銀行主帳戶: {BANK_NAME} {BANK_NUMBER}")
print(f"警報閾值: 震度 {EARTHQUAKE_INTENSITY_THRESHOLD} 級 | 海嘯警報: {'啟用' if TSUNAMI_ALERT_ENABLED else '關閉'}\n")

alert_count = 0
tsunami_alert_count = 0
total_donation = 0  # 模擬自動捐款至聯邦銀行主帳戶（緊急基金）

for cycle in range(1, SIMULATION_CYCLES + 1):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 隨機觸發地震事件 (10% 機率)
    if random.random() < 0.10:
        event = random.choice(POSSIBLE_EVENTS)
        epicenter, magnitude, depth, max_intensity = event
        
        # 顯示地震資訊
        print(f"[{current_time}] ⚠️ 地震事件偵測!")
        print(f"   震央: {epicenter} | 規模: {magnitude} | 深度: {depth} km | 最大震度: {max_intensity} 級")
        
        # 檢查震度是否超過閾值
        if max_intensity >= EARTHQUAKE_INTENSITY_THRESHOLD:
            alert_count += 1
            print(f"   🚨 強震警報! 震度 {max_intensity} 級 ≥ 閾值 {EARTHQUAKE_INTENSITY_THRESHOLD} 級")
            print(f"   → 發送緊急通報 (CWA API / SMS)")
            
            # 模擬自動捐贈或防災資金調度 (存入聯邦銀行主帳戶)
            donation_amount = round(magnitude * 50000, 2)
            total_donation += donation_amount
            print(f"   💰 防災基金自動調撥: {donation_amount:,.2f} 元 → {BANK_NAME} {BANK_NUMBER}")
            
            # 若開啟海嘯警報且規模夠大
            if TSUNAMI_ALERT_ENABLED and magnitude >= TSUNAMI_MAGNITUDE_THRESHOLD:
                tsunami_alert_count += 1
                print(f"   🌊 海嘯警報! 規模 {magnitude} ≥ {TSUNAMI_MAGNITUDE_THRESHOLD}，沿岸警戒!")
                # 模擬 AI 分析
                print(f"   🤖 AI 海嘯模擬啟動 (OpenAI/Gemini) | 預估影響範圍計算中...")
        else:
            print(f"   ℹ️ 有感地震，但未達警報門檻 (震度 {max_intensity} < {EARTHQUAKE_INTENSITY_THRESHOLD})")
    else:
        # 無地震，顯示正常監測狀態
        print(f"[{current_time}] 地震監測正常 | 最近無顯著有感地震")
    
    time.sleep(CHECK_INTERVAL)

# 最終報告
print(f"\n✅ 地震預警監測結束")
print(f"總監測週期: {SIMULATION_CYCLES}")
print(f"觸發強震警報次數: {alert_count}")
print(f"海嘯警報次數: {tsunami_alert_count}")
print(f"累積防災基金: {total_donation:,.2f} 元（已撥入 {BANK_NAME}）")
print("系統持續低耗能監測中，位置深度隱藏。")