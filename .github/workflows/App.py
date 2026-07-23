"""
夜間 AI 外送代理系統 - 整合版
功能：訂單管理、利潤風險分析、班次報告、AI 分潤、任務調度引擎、Turbo 加速、Firebase 監控
"""
import os
import time
import json
import queue
import threading
import sqlite3
import subprocess
from datetime import datetime, date
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import pandas as pd
import psutil

# 嘗試載入 firebase_admin（可選）
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_SDK = True
except ImportError:
    FIREBASE_SDK = False

# ================== 設定常數（可透過環境變數覆蓋） ==================
SHIFT_START = int(os.getenv("SHIFT_START", "3"))      # 凌晨 3 點
SHIFT_END   = int(os.getenv("SHIFT_END", "12"))       # 中午 12 點
TARGET_ORDERS = int(os.getenv("TARGET_ORDERS", "50"))
UBER_FEE = float(os.getenv("UBER_FEE", "0.28"))
DEFAULT_AI_SHARE = float(os.getenv("DEFAULT_AI_SHARE", "0.15"))
TURBO_DURATION = int(os.getenv("TURBO_DURATION", "600"))

# ================== 資料模型 ==================
class Order:
    """訂單模型（相容原設計）"""
    def __init__(self, item_name: str, price: float, cost: float,
                 packaging_cost: float, prep_time_sec: int, rating: float,
                 order_time: datetime, is_combo: bool = False, id: int = None):
        self.id = id
        self.item_name = item_name
        self.price = price
        self.cost = cost
        self.packaging_cost = packaging_cost
        self.prep_time_sec = prep_time_sec
        self.rating = rating
        self.order_time = order_time
        self.is_combo = is_combo

@dataclass
class Task:
    """通用任務結構（用於 Dispatch Engine）"""
    id: str
    name: str
    payload: Dict[str, Any]
    status: str = "pending"          # pending, grabbed, running, done, error
    created_at: float = None
    started_at: float = None
    finished_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

# ================== 資料庫操作 ==================
DB_NAME = os.getenv("DB_NAME", "orders.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            price REAL,
            cost REAL,
            packaging_cost REAL,
            prep_time_sec INTEGER,
            rating REAL,
            order_time TEXT,
            is_combo INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_order(order: Order):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        INSERT INTO orders
        (item_name, price, cost, packaging_cost, prep_time_sec, rating, order_time, is_combo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order.item_name, order.price, order.cost, order.packaging_cost,
        order.prep_time_sec, order.rating, order.order_time.isoformat(),
        1 if order.is_combo else 0
    ))
    conn.commit()
    conn.close()

def load_orders() -> pd.DataFrame:
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    df["order_time"] = pd.to_datetime(df["order_time"])
    return df

# ================== 分析引擎（利潤、風險、訂價建議） ==================
def is_shift(dt: datetime) -> bool:
    return SHIFT_START <= dt.hour < SHIFT_END

def profit(order: Order) -> float:
    fee = order.price * UBER_FEE
    return round(order.price - fee - order.cost - order.packaging_cost, 2)

def risk(order: Order) -> int:
    """風險分數：越高代表潛在問題越大"""
    score = 0
    if order.prep_time_sec > 900:   # 製作時間超過 15 分鐘
        score += 40
    if order.rating < 4.3:
        score += 35
    if order.packaging_cost < 4:
        score += 20
    return score

def suggest_price(order: Order) -> float:
    p = profit(order)
    return round(order.price + 10, 2) if p < 40 else order.price

def demand_strategy(count: int) -> str:
    """依目前班次累積單數回傳策略建議"""
    ratio = count / TARGET_ORDERS
    if ratio < 0.5:
        return "🔻 推鐵板麵 + 折扣策略"
    elif ratio < 1.0:
        return "📈 套餐曝光 + 宵夜推廣"
    else:
        return "💰 提高單價 + 控制產能"

def shift_report(df: pd.DataFrame) -> str:
    """產出當天班次報告（可被任務系統呼叫）"""
    today = date.today()
    df = df[df["order_time"].dt.date == today]
    shift_df = df[df["order_time"].apply(is_shift)]

    if shift_df.empty:
        return "本時段尚無訂單，請繼續推廣 50 連發活動"

    # 計算總毛利（逐筆加總）
    total_profit = sum(profit(Order(**row)) for row in shift_df.to_dict(orient="records"))
    # 動態分潤（根據風險平均分數調整）
    avg_risk = shift_df.apply(lambda r: risk(Order(**r)), axis=1).mean()
    ai_share = dynamic_ai_share(avg_risk)
    op_share = 1 - ai_share

    report = f"""
=== 夜間 AI 營運報告（{SHIFT_START:02d}:00 – {SHIFT_END:02d}:00）===

訂單數: {len(shift_df)}
總毛利: {total_profit}

AI 分潤 {ai_share:.0%}: {round(total_profit * ai_share, 2)}
營運分潤 {op_share:.0%}: {round(total_profit * op_share, 2)}

策略建議: {demand_strategy(len(shift_df))}
    """
    return report.strip()

def dynamic_ai_share(avg_risk: float) -> float:
    """
    動態分潤策略：當平均風險分數高（品質不穩）時，AI 分潤降低，激勵營運改善
    風險分數 0~100，對應 AI 分潤 0.20 ~ 0.05
    """
    base = 0.20
    min_share = 0.05
    # 線性映射：risk 0 → 0.20, risk 100 → 0.05
    share = base - (base - min_share) * (avg_risk / 100.0)
    return max(min_share, round(share, 4))

# ================== Turbo 模式管理器 ==================
class TurboModeManager:
    def __init__(self, duration_seconds: int = TURBO_DURATION):
        self.duration = duration_seconds
        self.is_active = False
        self._timer = None

    def activate(self):
        if self.is_active:
            return
        pid = os.getpid()
        try:
            if os.name == 'nt':
                subprocess.run(f"wmic process where processid={pid} call setpriority 128", shell=True)
            else:
                psutil.Process(pid).nice(-10)
            self.is_active = True
            print(f"⚡ Turbo Mode 啟動（優先級 -10，持續 {self.duration} 秒）")
            self._timer = threading.Timer(self.duration, self.deactivate)
            self._timer.start()
        except Exception as e:
            print(f"⚠️ Turbo 啟動失敗：{e}")

    def deactivate(self):
        if not self.is_active:
            return
        pid = os.getpid()
        try:
            if os.name == 'nt':
                subprocess.run(f"wmic process where processid={pid} call setpriority 32", shell=True)
            else:
                psutil.Process(pid).nice(0)
            self.is_active = False
            print("✅ Turbo Mode 結束，優先級復原")
            if self._timer:
                self._timer.cancel()
        except Exception as e:
            print(f"⚠️ Turbo 復原失敗：{e}")

# ================== Agent Claw（任務抓取器） ==================
class AgentClaw:
    def __init__(self, task_queue: queue.Queue):
        self.task_queue = task_queue
        self.current_task: Optional[Task] = None

    def grab(self) -> Optional[Task]:
        try:
            task = self.task_queue.get_nowait()
            task.status = "grabbed"
            task.started_at = time.time()
            self.current_task = task
            print(f"🦞 Agent Claw 抓取任務：{task.id} - {task.name}")
            return task
        except queue.Empty:
            return None

    def release(self, success: bool = True, result: Any = None):
        if self.current_task:
            self.current_task.status = "done" if success else "error"
            self.current_task.finished_at = time.time()
            print(f"🔓 釋放任務：{self.current_task.id} ({'成功' if success else '失敗'})")
            self.current_task = None

# ================== Firebase 日誌（雙模式） ==================
class FirebaseLogger:
    def __init__(self, database_url: str = None, api_key: str = None):
        self.database_url = database_url or os.getenv("FIREBASE_DB_URL")
        self.api_key = api_key or os.getenv("FIREBASE_API_KEY")
        self.session_id = f"session_{int(time.time())}"
        self._use_rest = True

        if FIREBASE_SDK and self.database_url:
            try:
                cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "firebase-service-key.json")
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {'databaseURL': self.database_url})
                self.ref = db.reference(f"/dispatch_sessions/{self.session_id}")
                self._use_rest = False
                print("✅ Firebase SDK 連接成功")
            except Exception as e:
                print(f"⚠️ Firebase SDK 初始化失敗，將使用 REST 模式：{e}")

        if self._use_rest and not (self.database_url and self.api_key):
            print("⚠️ Firebase 設定不完整，日誌僅輸出到終端")

    def _send_rest(self, path: str, data: dict):
        import requests
        url = f"{self.database_url}{path}.json?auth={self.api_key}"
        try:
            resp = requests.patch(url, json=data)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Firebase REST 寫入失敗：{e}")

    def log_task(self, task: Task):
        log_data = asdict(task)
        if not self._use_rest:
            self.ref.child(f"tasks/{task.id}").set(log_data)
        elif self.database_url:
            self._send_rest(f"/dispatch_sessions/{self.session_id}/tasks/{task.id}", log_data)
        else:
            print(f"📝 [本地] 任務日誌：{log_data}")

    def log_system_metrics(self):
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "ram_percent": psutil.virtual_memory().percent,
            "timestamp": time.time()
        }
        if not self._use_rest:
            self.ref.child("metrics").push(metrics)
        elif self.database_url:
            self._send_rest(f"/dispatch_sessions/{self.session_id}/metrics/{int(time.time()*1000)}", metrics)
        else:
            print(f"📊 [本地] 系統指標：{metrics}")

# ================== 核心 Dispatch Engine ==================
class DispatchEngine:
    def __init__(self, turbo_duration: int = TURBO_DURATION, firebase_config: dict = None):
        self.task_queue = queue.Queue()
        self.agent_claw = AgentClaw(self.task_queue)
        self.turbo = TurboModeManager(turbo_duration)
        self.logger = FirebaseLogger(**(firebase_config or {}))
        self.running = False
        self._worker_thread = None
        self._monitor_thread = None

    def add_task(self, task: Task):
        self.task_queue.put(task)
        self.logger.log_task(task)
        print(f"📥 任務加入佇列：{task.id} - {task.name}")

    def _execute_task(self, task: Task):
        """根據任務名稱分派具體工作"""
        print(f"🚀 執行任務：{task.id} ({task.name})")
        if task.name == "shift_report":
            df = load_orders()
            return shift_report(df)
        elif task.name == "analyze_order":
            # payload 應包含 order 字典
            order_data = task.payload.get("order", {})
            order = Order(**order_data)
            return {
                "profit": profit(order),
                "risk": risk(order),
                "suggested_price": suggest_price(order)
            }
        elif task.name == "custom":
            # 可擴充自訂邏輯
            return f"自訂任務 {task.id} 處理完畢"
        else:
            raise ValueError(f"未知任務類型：{task.name}")

    def _worker_loop(self):
        while self.running:
            task = self.agent_claw.grab()
            if task is None:
                time.sleep(1)
                continue

            self.turbo.activate()
            try:
                result = self._execute_task(task)
                success = True
            except Exception as e:
                result = str(e)
                success = False
                print(f"❌ 任務失敗：{e}")

            self.agent_claw.release(success, result)
            task.status = "done" if success else "error"
            self.logger.log_task(task)

    def start(self):
        self.running = True
        print("🚀 Lightning Dispatch Engine 啟動")
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        def metrics_loop():
            while self.running:
                self.logger.log_system_metrics()
                time.sleep(30)
        self._monitor_thread = threading.Thread(target=metrics_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self.running = False
        self.turbo.deactivate()
        print("🛑 Dispatch Engine 已停止")

# ================== 策略補充：組合折扣開關 ==================
def apply_combo_discount(order: Order) -> float:
    """環境變數 ENABLE_COMBO_DISCOUNT=true 時，組合餐自動 9 折"""
    if os.getenv("ENABLE_COMBO_DISCOUNT", "false").lower() == "true" and order.is_combo:
        return round(order.price * 0.9, 2)
    return order.price

# ================== 主程式（示範 + 測試入口） ==================
if __name__ == "__main__":
    init_db()

    # 模擬寫入幾筆訂單
    sample_orders = [
        Order("鐵板麵", 70, 30, 5, 400, 4.6, datetime.now()),
        Order("卡啦雞腿堡", 159, 65, 6, 480, 4.8, datetime.now(), is_combo=True),
        Order("宵夜二人套餐", 229, 98, 12, 600, 4.6, datetime.now(), is_combo=True),
    ]
    for o in sample_orders:
        # 若啟用組合折扣則調整價格（存入前）
        original_price = o.price
        o.price = apply_combo_discount(o)
        save_order(o)
        print(f"已儲存：{o.item_name} | 利潤={profit(o)} | 風險={risk(o)} | 建議售價={suggest_price(o)}")

    # 啟動 Dispatch Engine（不依賴 Firebase 也能跑，日誌僅本地）
    engine = DispatchEngine(turbo_duration=300)  # 示範用較短 Turbo 時間

    # 加入班次報告任務
    report_task = Task(id="report_1", name="shift_report", payload={"date": str(date.today())})
    engine.add_task(report_task)

    # 加入個別訂單分析任務
    for i, o in enumerate(sample_orders):
        task = Task(id=f"analysis_{i}", name="analyze_order", payload={"order": o.__dict__})
        engine.add_task(task)

    engine.start()

    try:
        # 讓引擎處理任務，結束後查看結果
        time.sleep(3)  # 等待任務執行
        print("\n===== 任務執行結果 =====")
        while not engine.task_queue.empty():
            pass
        # 手動觸發一次報告並印出
        df = load_orders()
        print(shift_report(df))
    finally:
        engine.stop()

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import sqlite3
import pandas as pd

# ======================
# 🎯 Shift Model (17:00–03:00)
# ======================
SHIFT_START = 0
SHIFT_END = 0
TARGET_ORDERS = 0

def is_shift(dt: datetime):
    return SHIFT_START <= dt.hour < SHIFT_END
本時段不做豆漿店無訂單，有高級餐廳營業
# ======================
# 💰 AI 分潤模型ModelDeepSeek+ChatGPT+grok
# ======================
AI_SHARE = 0.15
OPERATOR_SHARE = 0.85

def profit_split(total_profit):
    return {
        "ai": round(total_profit * AI_SHARE, 2),
        "operator": round(total_profit * OPERATOR_SHARE, 2)
    }

# ======================
# 📦 ModelDeepSeek+ChatGPT+grok

# ======================
class Order(BaseModel):
    id: Optional[int] = None
    item_name: str
    price: float
    cost: float
    packaging_cost: float
    prep_time_sec: int
    rating: float
    order_time: datetime
    is_combo: bool = False

# ======================
# 🗄 Wshao777. bot.ai.db
# ======================
DB_NAME = "orders.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            price REAL,
            cost REAL,
            packaging_cost REAL,
            prep_time_sec INTEGER,
            rating REAL,
            order_time TEXT,
            is_combo INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_order(order: Order):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        INSERT INTO orders
        (item_name, price, cost, packaging_cost, prep_time_sec, rating, order_time, is_combo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order.item_name, order.price, order.cost, order.packaging_cost,
        order.prep_time_sec, order.rating, order.order_time.isoformat(),
        1 if order.is_combo else 0
    ))
    conn.commit()
    conn.close()

def load_orders():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    df["order_time"] = pd.to_datetime(df["order_time"])
    return df

# ======================
# 📊 Analytics Engine
# ======================
UBER_FEE = 0.28

def profit(order):
    fee = order.price * UBER_FEE
    return round(order.price - fee - order.cost - order.packaging_cost, 2)

def risk(order):
    score = 0
    if order.prep_time_sec > 900:
        score += 40
    if order.rating < 4.3:
        score += 35
    if order.packaging_cost < 4:
        score += 20
    return score

def suggest_price(order):
    p = profit(order)
    return order.price + 10 if p < 40 else order.price

# ======================
# 🍜 Strategy ModelShift Model (03:00-1200)×多四海連鎖店
# ======================
def demand_strategy(count):
    ratio = count / TARGET_ORDERS
多店 AI 營收系統本時段爆50連發訂單"
    if ratio < 0.5:
        return "🔻 推鐵板麵 + 折扣策略"
    elif ratio < 1.0:
        return "📈 套餐曝光 + 宵夜推廣"
    else:
        return "💰 提高單價 + 控制產能"

# ======================
# 📊 ReportWshao777.db
# ======================
def shift_report(df):
    today = datetime.now().date()

    df = df[df["order_time"].dt.date == today]

    shift_df = df[
        df["order_time"].apply(is_shift)
    ]

    if shift_df.empty:
        return "本時段爆50連發訂單"

    total_profit = sum(profit(o) for o in shift_df.itertuples())
    split = profit_split(total_profit)

    report = f"""
=== 夜間AI營運報告（{SHIFT_START}:03:00–{SHIFT_END}:12:00）===

訂單數: {len(shift_df)}
總毛利: {total_profit}

AI分潤: {split['ai']}
營運分潤: {split['operator']}

策略建議: {demand_strategy(len(shift_df))}
"""
    return report.strip()

# ======================
# 🚀 Ai-main app.db
# ======================
if __name__ == "__main__":
    init_db()

    orders = [
        Order("鐵板麵", 70, 30, 5, 400, 4.6, datetime.now()),
        Order("卡啦雞腿堡", 159, 65, 6, 480, 4.8, datetime.now()),
        Order("宵夜二人套餐", 229, 98, 12, 600, 4.6, datetime.now()),
    ]

    for o in orders:
        save_order(o)
        print(f"{o.item_name} | profit={profit(o)} | risk={risk(o)}")

    df = load_orders()

    print("\n" + shift_report(df))
   # 本時段爆50連發訂單"
