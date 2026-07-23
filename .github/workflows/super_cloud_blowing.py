"""
Lightning AI Factory - 統一入口主控程式
整合：吹雲 + 結冰 + 極地波 + 三重威脅 + AI 決策 + Bit 控制
使用方法：python super_cloud_blowing.py [模式]
模式：menu / ai / bit / blow / ice / pole / triple / tower
"""

import sys
import os
import time
import random
import math
from datetime import datetime, timedelta

# ------------------------------
# Bit 控制層：用 bitmask 管理核心狀態
# ------------------------------
class BitCoreController:
    """用位元管理四大核心與 AI 狀態"""
    def __init__(self):
        self.state = 0b000000  # bit0: AI, bit1: 吹雲, bit2: 結冰, bit3: 極地波, bit4: 三重威脅

    def set_bit(self, index, value):
        if value:
            self.state |= (1 << index)
        else:
            self.state &= ~(1 << index)

    def get_bit(self, index):
        return (self.state >> index) & 1

    def toggle_bit(self, index):
        self.state ^= (1 << index)

    def __str__(self):
        bits = [self.get_bit(i) for i in range(5)]
        return f"AI:{bits[0]} 吹雲:{bits[1]} 結冰:{bits[2]} 極地波:{bits[3]} 三重:{bits[4]} [0b{self.state:06b}]"

bit_ctrl = BitCoreController()

# ------------------------------
# AI 降雨預測引擎（簡化版，可替換真實 API）
# ------------------------------
class AIRainPredictor:
    """AI 降雨強度預測"""
    def predict(self, base=60):
        # 模擬對流+移流+隨機
        t = time.time() / 60
        convection = math.sin(t / 2.5) * 20
        advection = math.sin(t / 10) * 15
        burst = random.choice([0,10,20,-10,25,0])
        raw = base + convection + advection + burst
        return max(0, min(100, int(raw)))

    def safe_window(self, threshold=40):
        # 模擬未來30分鐘預測，找出安全窗口
        future = [self.predict() for _ in range(30)]
        windows = []
        start = None
        for i, val in enumerate(future):
            if val < threshold:
                if start is None:
                    start = i
            else:
                if start is not None and (i - start) >= 3:
                    windows.append((start, i-1))
                start = None
        return windows

ai_rain = AIRainPredictor()

# ------------------------------
# 核心模組執行器（模擬，實際可替換為 subprocess 呼叫原本的 .py）
# ------------------------------
def run_cloud_blower():
    print("🌬️ 啟動吹雲模組... 水平風力移除雨滴")
    for i in range(10):
        rain = max(0, 80 - i*8)
        print(f"\r吹雲進度: [{'#'*i}{' '*(9-i)}] {rain}%", end='', flush=True)
        time.sleep(0.3)
    print("\n✅ 吹雲完成")

def run_iceberg():
    print("🧊 啟動結冰模組... 分子冷凍至 -60°C")
    for temp in range(0, -61, -6):
        print(f"\r結冰中: {temp}°C", end='', flush=True)
        time.sleep(0.3)
    print("\n✅ 結冰完成")

def run_polar_wave():
    print("🌍 啟動極地波... 南北極冷凍波交匯")
    print("北極波: -60°C → 逢甲 | 南極波: -70°C → 逢甲")
    time.sleep(2)
    print("✅ 極地波交匯，溫度驟降")

def run_triple_threat():
    print("💥 啟動三重威脅... 吹雲+結冰+極地波同步壓制")
    run_cloud_blower()
    run_iceberg()
    run_polar_wave()
    print("🏆 三重壓制完成，暴雨歸零")

def run_ai_decision():
    current = ai_rain.predict()
    print(f"🧠 AI 降雨預測: 目前 {current}%")
    windows = ai_rain.safe_window()
    if windows:
        for s,e in windows:
            print(f"   安全窗口: 未來 {s}-{e} 分鐘 (降雨 < 40%)")
    else:
        print("   無連續安全窗口，建議暫不外出")

def run_bit_control_menu():
    while True:
        print("\n" + str(bit_ctrl))
        print("1: 切換 AI   2: 切換吹雲  3: 切換結冰  4: 切換極地波  5: 切換三重  0: 返回")
        cmd = input("選擇: ")
        if cmd == '0':
            break
        elif cmd in '12345':
            idx = int(cmd)-1
            bit_ctrl.toggle_bit(idx)
            print(f"已切換，新狀態: {bit_ctrl}")
        else:
            print("無效輸入")

# ------------------------------
# 主選單
# ------------------------------
def main_menu():
    while True:
        print("\n" + "="*50)
        print("  Lightning AI Factory - 主控台")
        print("="*50)
        print("1. 🌬️ 吹雲 (Blow)")
        print("2. 🧊 結冰 (Iceberg)")
        print("3. 🌍 極地波 (Polar Wave)")
        print("4. 💥 三重威脅 (Triple Threat)")
        print("5. 🧠 AI 降雨預測與安全窗口")
        print("6. 🔢 Bit 控制面板")
        print("7. 🏰 啟動 Control Tower (Web)")
        print("0. 離開")
        choice = input("請選擇: ")

        if choice == '1':
            run_cloud_blower()
        elif choice == '2':
            run_iceberg()
        elif choice == '3':
            run_polar_wave()
        elif choice == '4':
            run_triple_threat()
        elif choice == '5':
            run_ai_decision()
        elif choice == '6':
            run_bit_control_menu()
        elif choice == '7':
            print("啟動 Control Tower... (請在另一個終端機執行 control_tower.py)")
        elif choice == '0':
            print("系統關閉")
            break
        else:
            print("無效選項")

# ------------------------------
# 快速指令模式 (python super_cloud_blowing.py blow)
# ------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "blow":
            run_cloud_blower()
        elif mode == "ice":
            run_iceberg()
        elif mode == "pole":
            run_polar_wave()
        elif mode == "triple":
            run_triple_threat()
        elif mode == "ai":
            run_ai_decision()
        elif mode == "bit":
            run_bit_control_menu()
        elif mode == "menu":
            main_menu()
        else:
            print(f"未知模式: {mode}")
    else:
        main_menu()
