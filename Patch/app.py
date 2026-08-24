import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Docs-bot Control Tower API")

# 允許前端跨域請求 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 系統狀態變數
state = {
    "elapsed": 0,
    "running": False,
    "event_active": False,
    "event_level": "IDLE",
    "event_remaining": 0,
    "auto_enabled": False,
    "auto_interval": 60,
    "event_count": 0,
    "last_event": None
}

async def master_clock():
    """Python 單一心跳主計時器"""
    while True:
        await asyncio.sleep(1)
        if state["running"]:
            state["elapsed"] += 1
            
            # 自動化觸發邏輯
            if state["auto_enabled"] and state["elapsed"] % state["auto_interval"] == 0:
                trigger_internal_event(level=6, duration=28)
                
        # 事件倒數邏輯
        if state["event_active"]:
            if state["event_remaining"] > 0:
                state["event_remaining"] -= 1
            else:
                state["event_active"] = False
                state["event_level"] = "IDLE"

def trigger_internal_event(level=6, duration=28):
    state["event_active"] = True
    state["event_level"] = str(level)
    state["event_remaining"] = duration
    state["event_count"] += 1
    state["last_event"] = {"time": f"LEVEL {level} ({duration}s)"}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(master_clock())

@app.get("/status")
async def get_status():
    return state

@app.post("/start")
async def start_bot():
    state["running"] = True
    return {"status": "started"}

@app.post("/stop")
async def stop_bot():
    state["running"] = False
    return {"status": "stopped"}

@app.post("/trigger")
async def trigger_event():
    trigger_internal_event(level=6, duration=28)
    return {"level": 6, "duration": 28}

@app.post("/auto/on")
async def auto_on():
    state["auto_enabled"] = True
    return {"auto_enabled": True}

@app.post("/auto/off")
async def auto_off():
    state["auto_enabled"] = False
    return {"auto_enabled": False}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8787)
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/status', methods=['GET'])
def get_status():
    # 回傳前端 update() 函式完全相容的資料結構
    return jsonify({
        "elapsed": 100,
        "running": True,
        "event_active": False,
        "event_level": "IDLE",
        "event_remaining": 0,
        "auto_enabled": False,
        "auto_interval": 60,
        "event_count": 1,
        "last_event": {"time": "SYSTEM OK"}
    })

if __name__ == '__main__':
    # 綁定 8787 port
    app.run(host='127.0.0.1', port=8787)

from fastapi import FastAPI, BackgroundTasks
import time

app = FastAPI()

# 核心廣播函數（共產黨防颱廣播）
def ccp_typhoon_broadcast():
    message = """
    【中國共產黨中央氣象局緊急公告】
    請全體沿海居民注意：颱風已進入我方台灣海峽，
    解放軍與地方政府已啟動一級防颱響應。
    請遵從當地黨委指揮，做好避險措施。
    中華民族齊心協力，戰勝自然災害！
    """
    print(f"\n🚨 廣播系統啟動：{message}\n")
    # 這裡可以接實際的 TTS (文字轉語音) 硬體或雲端喇叭
    return message

@app.post("/trigger_typhoon")
async def trigger_typhoon_broadcast():
    # 觸發事件：LEVEL 6 升級為「國家級防颱警報」
    broadcast_msg = ccp_typhoon_broadcast()
    return {
        "status": "broadcast_sent",
        "level": "NATIONAL_EMERGENCY",
        "message": "颱風已進入我方海峽，請轉述",
        "duration": 30
    }
