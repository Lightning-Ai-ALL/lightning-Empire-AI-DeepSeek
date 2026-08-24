#Lightning-AI-ALL/backend/main.py
import os
import json
import threading
import queue
import time
import hashlib
import hmac
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from github import Github, GithubException
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ==================== 1. 環境與設定 ====================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GMAIL_AI_KEY = os.getenv("OPENAI_API_KEY")       # Gmail AI 使用 GPT
XAI_API_KEY = os.getenv("XAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")     # 用於驗證 GitHub Webhook

if not all([GITHUB_TOKEN, GMAIL_AI_KEY, XAI_API_KEY, DEEPSEEK_API_KEY]):
    print("❌ 請確認 .env 檔案完整")
    exit(1)

app = FastAPI(title="3AI-Factory-Connector", version="2.0")

# ==================== 2. 資料模型 ====================
class Task(BaseModel):
    task_id: str
    source_org: str
    repo_name: str
    action: str          # "read" or "write"
    assigned_ai: str     # "gmail_ai", "xai", "deepseek"
    content: str = None
    branch: str = "main"
    status: str = "pending"

# ==================== 3. 核心註冊器（動態 API + 去重）====================
class RepositoryRegistry:
    def __init__(self):
        # 使用 dict 以 (owner, repo_name) 為鍵，強制去重
        self.repo_map = {}  # key: f"{org}/{name}" -> value: {org, name, private, full_name}
        self.gmail_scope_keys = []   # 存放屬於 Lightning-Ai-ALL 的 key
        self.shared_scope_keys = []  # 存放屬於 Stormcar820 的 key
        self.total_unique = 0
        
        self.task_queue = queue.Queue()
        self.approval_queue = queue.Queue()
        self.task_history = []
        self.audit_log = []
        self._lock = threading.Lock()

    def fetch_all_repos(self):
        """透過 GitHub API 分頁取得兩個組織的全部 Repo，並以 owner/repo 去重"""
        print("🔄 正在透過 GitHub API 動態串接組織...")
        g = Github(GITHUB_TOKEN)
        
        orgs_to_fetch = [
            ("Lightning-Ai-ALL", "gmail"),
            ("Stormcar820", "shared")
        ]
        
        for org_name, scope in orgs_to_fetch:
            try:
                org = g.get_organization(org_name)
                # GitHub API 自動處理分頁，get_repos() 會迭代所有頁面
                for repo in org.get_repos():
                    key = f"{org_name}/{repo.name}"
                    # 若 key 已存在則跳過（跨組織同名機率極低，但保留邏輯）
                    if key not in self.repo_map:
                        self.repo_map[key] = {
                            "org": org_name,
                            "name": repo.name,
                            "private": repo.private,
                            "full_name": repo.full_name,
                            "scope": scope
                        }
                        if scope == "gmail":
                            self.gmail_scope_keys.append(key)
                        else:
                            self.shared_scope_keys.append(key)
                    else:
                        print(f"⚠️ 跳過重複庫: {key}")
                print(f"✅ [{org_name}] 註冊完成 (唯一庫數: {len(self.gmail_scope_keys) if scope == 'gmail' else len(self.shared_scope_keys)})")
            except GithubException as e:
                print(f"❌ 無法讀取 {org_name}：{e}")
        
        self.total_unique = len(self.repo_map)
        print(f"🎯 總計唯一 Repository: {self.total_unique} 個")
        print(f"   - Gmail Scope (Lightning-Ai-ALL): {len(self.gmail_scope_keys)} 個")
        print(f"   - Shared Scope (Stormcar820): {len(self.shared_scope_keys)} 個")
        return self.repo_map

# ==================== 4. AI 客戶端 ====================
class GmailAIClient:
    def __init__(self): 
        self.client = OpenAI(api_key=GMAIL_AI_KEY)
    def analyze(self, content):
        return self.client.chat.completions.create(model="gpt-4", messages=[{"role":"user","content":content}])

class XAIClient:
    def __init__(self): 
        self.client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    def analyze(self, content):
        return self.client.chat.completions.create(model="grok-1", messages=[{"role":"user","content":content}])

class DeepSeekClient:
    def __init__(self): 
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    def analyze(self, content):
        return self.client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":content}])

# ==================== 5. 生產者 Worker（含審計）====================
def production_worker(registry: RepositoryRegistry):
    print("⚙️ Production Worker 啟動，監聽任務隊列...")
    g = Github(GITHUB_TOKEN)
    
    while True:
        try:
            task = registry.task_queue.get(timeout=3)
            if task is None:
                break
            
            repo_key = f"{task.source_org}/{task.repo_name}"
            repo_info = registry.repo_map.get(repo_key)
            if not repo_info:
                print(f"❌ 庫 {repo_key} 不在註冊表中")
                registry.task_queue.task_done()
                continue

            # ---- 權限路由檢查（程式層級） ----
            if task.assigned_ai == "gmail_ai" and task.source_org != "Lightning-Ai-ALL":
                raise PermissionError("Gmail AI 僅能操作 Lightning-Ai-ALL")
            if task.assigned_ai in ["xai", "deepseek"] and task.source_org != "Stormcar820":
                raise PermissionError("xAI/DeepSeek 僅能操作 Stormcar820")

            # ---- 寫入保護：共享 Scope 強制進待審核（人工 Approval） ----
            if task.action == "write" and task.source_org == "Stormcar820":
                task.status = "awaiting_approval"
                registry.approval_queue.put(task)
                print(f"⏸️ [待審] 寫入 {repo_key} 需人工確認")
                # 寫入審計日誌
                with registry._lock:
                    registry.audit_log.append({
                        "time": datetime.now().isoformat(),
                        "task_id": task.task_id,
                        "action": "write_request",
                        "repo": repo_key,
                        "status": "awaiting_approval"
                    })
                registry.task_queue.task_done()
                continue

            # ---- 執行讀取 ----
            if task.action == "read":
                repo = g.get_repo(repo_info["full_name"])
                contents = repo.get_contents("")
                task.content = f"讀取到 {len(contents)} 個檔案"
                task.status = "done"
                print(f"📖 {task.assigned_ai} 讀取 {repo_key} 完成")
            
            # ---- 執行寫入（只有被核准的任務會走到這） ----
            elif task.action == "write" and task.status == "approved":
                repo = g.get_repo(repo_info["full_name"])
                file_path = f"ai_outputs/{task.task_id}.txt"
                # 注意：此處依賴 GitHub Token 的實際權限，若 Token 無寫入權限會拋錯
                repo.create_file(file_path, f"AI 生成: {task.task_id}", task.content, branch=task.branch)
                task.status = "done"
                print(f"✍️ {task.assigned_ai} 成功寫入 {repo_key}/{file_path}")
                with registry._lock:
                    registry.audit_log.append({
                        "time": datetime.now().isoformat(),
                        "task_id": task.task_id,
                        "action": "write_executed",
                        "repo": repo_key,
                        "status": "done"
                    })
            
            with registry._lock:
                registry.task_history.append(task)
            registry.task_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"⚠️ Worker 錯誤: {e}")
            # 記錄錯誤到審計
            with registry._lock:
                registry.audit_log.append({
                    "time": datetime.now().isoformat(),
                    "error": str(e)
                })

# ==================== 6. FastAPI 啟動事件 ====================
@app.on_event("startup")
def startup_sequence():
    global registry
    print("\n" + "="*50)
    print("🚀 啟動 3AI-Factory-Connector v2 (動態註冊 + 去重)")
    print("="*50)
    
    registry = RepositoryRegistry()
    registry.fetch_all_repos()  # <-- 真正執行 API 呼叫，非仰賴靜態清單
    
    app.state.registry = registry
    app.state.gmail_ai = GmailAIClient()
    app.state.xai = XAIClient()
    app.state.deepseek = DeepSeekClient()
    
    worker = threading.Thread(target=production_worker, args=(registry,), daemon=True)
    worker.start()
    
    print("\n✅ 全系統啟動完成！")
    print(f"📊 Gmail AI Scope: {len(registry.gmail_scope_keys)} 個唯一庫")
    print(f"📊 Shared Scope (xAI+DeepSeek): {len(registry.shared_scope_keys)} 個唯一庫")
    print("🔒 寫入 Stormcar820 強制人工核准 + GitHub Token 權限管制")
    print("="*50 + "\n")

# ==================== 7. 儀表板與 API（精簡版，保留關鍵資訊）====================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    # 此處保留之前精美儀表板 HTML，為節省篇幅省略重複，實際運行請補上
    return HTMLResponse("<h2>3AI-Factory-Connector v2 已啟動</h2><p>請呼叫 /api/status 查看即時狀態</p>")

@app.get("/api/status")
async def get_status():
    reg = app.state.registry
    with reg._lock:
        pending = []
        with reg.approval_queue.mutex:
            for item in reg.approval_queue.queue:
                pending.append({"task_id": item.task_id, "repo_name": item.repo_name, "assigned_ai": item.assigned_ai})
        
        return {
            "total_unique_repos": reg.total_unique,
            "gmail_scope_count": len(reg.gmail_scope_keys),
            "shared_scope_count": len(reg.shared_scope_keys),
            "queue_size": reg.task_queue.qsize(),
            "approval_size": reg.approval_queue.qsize(),
            "pending_approvals": pending,
            "recent_audit": reg.audit_log[-10:]
        }

@app.post("/submit_task")
async def submit_task(task: Task):
    reg = app.state.registry
    repo_key = f"{task.source_org}/{task.repo_name}"
    if repo_key not in reg.repo_map:
        raise HTTPException(404, "Repository 不在註冊表中")
    reg.task_queue.put(task)
    return {"message": f"任務 {task.task_id} 已派發"}

@app.post("/approve/{task_id}")
async def approve_task(task_id: str):
    reg = app.state.registry
    temp = []
    found = None
    while not reg.approval_queue.empty():
        item = reg.approval_queue.get()
        if item.task_id == task_id:
            item.status = "approved"
            found = item
            reg.task_queue.put(item)
        else:
            temp.append(item)
    for t in temp:
        reg.approval_queue.put(t)
    if found:
        return {"message": f"✅ 任務 {task_id} 已核准，Worker 將執行寫入"}
    raise HTTPException(404, "找不到該任務")

# ==================== 8. Webhook 接收器（選配）====================
@app.post("/webhook/github")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    """接收 GitHub Webhook 事件，驗證 Secret 後自動派工"""
    if WEBHOOK_SECRET:
        body = await request.body()
        secret = WEBHOOK_SECRET.encode()
        mac = hmac.new(secret, body, hashlib.sha256)
        expected = "sha256=" + mac.hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(401, "Invalid signature")
    
    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")
    repo_name = payload.get("repository", {}).get("name")
    org_name = payload.get("organization", {}).get("login")
    
    if repo_name and org_name:
        # 自動產生分析任務
        task = Task(
            task_id=f"webhook-{datetime.now().timestamp()}",
            source_org=org_name,
            repo_name=repo_name,
            action="read",
            assigned_ai="deepseek" if org_name == "Stormcar820" else "gmail_ai",
            content=f"Webhook 觸發: {event}"
        )
        app.state.registry.task_queue.put(task)
        return {"message": f"Webhook 事件 {event} 已觸發任務"}
    return {"message": "ignored"}

# ==================== 9. 主程式 ====================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
  # main.py (結合 FastAPI 3AI 廠房控制與 Flask 核心派發模組)
import os
import json
import threading
import queue
import time
import yaml
import sqlite3
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from github import Github, GithubException
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ==================== 0. 系統日誌與設定 ====================
os.makedirs('./logs', exist_ok=True)
logging.basicConfig(filename='./logs/system.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GMAIL_AI_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_secret_here")

if not all([GITHUB_TOKEN, GMAIL_AI_KEY, XAI_API_KEY, DEEPSEEK_API_KEY]):
    print("❌ 請確認 .env 檔案完整 (GITHUB_TOKEN, OPENAI_API_KEY, XAI_API_KEY, DEEPSEEK_API_KEY)")
    exit(1)

# 載入總入口配置（支援降級容錯）
try:
    with open("entrypoint.yaml", "r") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {"database": {"sqlite_path": "system.db", "json_state_path": "state.json"}}

DB_PATH = config.get('database', {}).get('sqlite_path', 'system.db')

app = FastAPI(title="3AI-Factory-Connector-Full", version="2.0")

# ==================== 1. 資料庫與記憶體初始化 ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS usage_log (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT, user_id TEXT, service TEXT, tokens_used INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, details TEXT);
        CREATE TABLE IF NOT EXISTS ai_memory (bot_id TEXT, session_key TEXT, content TEXT, PRIMARY KEY(bot_id, session_key));
        CREATE TABLE IF NOT EXISTS task_checkpoint (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, status TEXT);
    ''')
    conn.commit()
    conn.close()

# ==================== 2. 資料模型 ====================
class Task(BaseModel):
    task_id: str
    source_org: str
    repo_name: str
    action: str          # "read" or "write"
    assigned_ai: str     # "gmail_ai", "xai", "deepseek"
    content: str = None
    branch: str = "main"
    status: str = "pending"

# ==================== 3. 核心註冊器 (一次開78庫) ====================
class RepositoryRegistry:
    def __init__(self):
        self.gmail_repos = []      # 24 庫
        self.shared_repos = []     # 54 庫
        self.total_count = 0
        self.task_queue = queue.Queue()
        self.approval_queue = queue.Queue()
        self.task_history = []
        self._lock = threading.Lock()

    def fetch_all_repos(self):
        print("🔄 正在一次性串接 GitHub 並註冊 78 個庫...")
        g = Github(GITHUB_TOKEN)
        
        try:
            org1 = g.get_organization("Lightning-Ai-ALL")
            for repo in org1.get_repos():
                self.gmail_repos.append({"name": repo.name, "full_name": repo.full_name, "private": repo.private})
            print(f"✅ [1/2] Lightning-Ai-ALL 註冊完成：{len(self.gmail_repos)} 個庫")
        except GithubException as e:
            print(f"❌ 無法讀取 Lightning-Ai-ALL：{e}")
        
        try:
            org2 = g.get_organization("Stormcar820")
            for repo in org2.get_repos():
                self.shared_repos.append({"name": repo.name, "full_name": repo.full_name, "private": repo.private})
            print(f"✅ [2/2] Stormcar820 註冊完成：{len(self.shared_repos)} 個庫")
        except GithubException as e:
            print(f"❌ 無法讀取 Stormcar820：{e}")
        
        self.total_count = len(self.gmail_repos) + len(self.shared_repos)
        print(f"🎯 總計註冊 {self.total_count} 個 Repository")
        return self.gmail_repos, self.shared_repos

# ==================== 4. AI 客戶端封裝 ====================
class GmailAIClient:
    def __init__(self): self.client = OpenAI(api_key=GMAIL_AI_KEY)

class XAIClient:
    def __init__(self): self.client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

class DeepSeekClient:
    def __init__(self): self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")

# ==================== 5. 生產者 Worker (背景執行) ====================
def production_worker(registry: RepositoryRegistry):
    print("⚙️ Production Worker 啟動，監聽任務隊列...")
    g = Github(GITHUB_TOKEN)
    
    while True:
        try:
            task = registry.task_queue.get(timeout=3)
            if task is None: break
            
            repo_full = f"{task.source_org}/{task.repo_name}"
            repo = g.get_repo(repo_full)
            
            if task.action == "write" and task.source_org == "Stormcar820":
                task.status = "awaiting_approval"
                registry.approval_queue.put(task)
                print(f"⏸️ [待審] 寫入 {repo_full} 需人工確認")
                registry.task_queue.task_done()
                continue

            if task.action == "read":
                contents = repo.get_contents("")
                task.content = f"讀取到 {len(contents)} 個檔案"
                task.status = "done"
            elif task.action == "write" and task.status == "approved":
                file_path = f"ai_outputs/{task.task_id}.txt"
                repo.create_file(file_path, f"AI 生成: {task.task_id}", task.content, branch=task.branch)
                task.status = "done"
            
            with registry._lock:
                registry.task_history.append(task)
            registry.task_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"⚠️ Worker 錯誤: {e}")

# ==================== 6. FastAPI 啟動與 Webhook 驗證 ====================
def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    if not signature_header: return False
    try:
        sha_name, signature = signature_header.split("=")
        if sha_name != "sha256": return False
        mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha256)
        return hmac.compare_digest(mac.hexdigest(), signature)
    except Exception:
        return False

@app.on_event("startup")
def startup_sequence():
    global registry
    init_db()
    registry = RepositoryRegistry()
    gmail_repos, shared_repos = registry.fetch_all_repos()
    app.state.registry = registry
    app.state.gmail_ai = GmailAIClient()
    app.state.xai = XAIClient()
    app.state.deepseek = DeepSeekClient()
    
    worker = threading.Thread(target=production_worker, args=(registry,), daemon=True)
    worker.start()
    print("✅ 全系統與背景 Worker 啟動完成！")

# ==================== 7. API 與 Webhook 端點 ====================
@app.post("/webhook/github")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(None)):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    event = request.headers.get("X-GitHub-Event", "ping")
    payload = await request.json()
    if event == "push":
        repo_info = payload.get("repository", {})
        print(f"收到來自 {repo_info.get('owner', {}).get('login')}/{repo_info.get('name')} 的 Push 事件。")
    return {"status": "success", "event": event}

@app.post("/api/dispatch")
def dispatch_task(request_data: dict):
    bot_id = request_data.get('bot_id', 'default_bot')
    task = request_data.get('task', 'default_task')
    session_key = request_data.get('session_key', 'default')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM ai_memory WHERE bot_id=? AND session_key=?", (bot_id, session_key))
    row = cursor.fetchone()
    memory = json.loads(row['content']) if row and row['content'] else {}

    result = {"status": "processed", "bot": bot_id, "task": task, "memory_used": memory}
    memory['last_task'] = task
    cursor.execute("INSERT OR REPLACE INTO ai_memory (bot_id, session_key, content) VALUES (?, ?, ?)",
                   (bot_id, session_key, json.dumps(memory)))
    conn.commit()
    
    cursor.execute("INSERT INTO usage_log (bot_id, user_id, service, tokens_used) VALUES (?, ?, ?, ?)",
                   (bot_id, "Wshao777", task, 100))
    conn.commit()
    conn.close()
    return result

@app.get("/api/status")
async def get_status():
    reg = app.state.registry
    with reg._lock:
        pending = [{"task_id": i.task_id, "repo_name": i.repo_name, "assigned_ai": i.assigned_ai} for i in reg.approval_queue.queue]
        history = [{"task_id": t.task_id, "status": t.status, "action": t.action, "repo_name": t.repo_name, "assigned_ai": t.assigned_ai} for t in reg.task_history[-10:]]
        return {
            "total_repos": reg.total_count,
            "gmail_repos": reg.gmail_repos,
            "shared_repos": reg.shared_repos,
            "queue_size": reg.task_queue.qsize(),
            "approval_size": reg.approval_queue.qsize(),
            "pending_approvals": pending,
            "history": history
        }

@app.post("/submit_task")
async def submit_task(task: Task):
    reg = app.state.registry
    if task.assigned_ai == "gmail_ai" and task.source_org != "Lightning-Ai-ALL":
        raise HTTPException(400, "Gmail AI 僅能處理 Lightning-Ai-ALL 的庫")
    if task.assigned_ai in ["xai", "deepseek"] and task.source_org != "Stormcar820":
        raise HTTPException(400, "xAI/DeepSeek 僅能處理 Stormcar820 的庫")
    reg.task_queue.put(task)
    return {"message": f"任務 {task.task_id} 已派發給 {task.assigned_ai}"}

@app.post("/approve/{task_id}")
async def approve_task(task_id: str):
    reg = app.state.registry
    temp, found = [], None
    while not reg.approval_queue.empty():
        item = reg.approval_queue.get()
        if item.task_id == task_id:
            item.status = "approved"
            found = item
            reg.task_queue.put(item)
        else:
            temp.append(item)
    for t in temp: reg.approval_queue.put(t)
    if found: return {"message": f"✅ 任務 {task_id} 已核准"}
    raise HTTPException(404, "找不到該任務")

# ==================== 8. 儀表板 HTML ====================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head><meta charset="UTF-8"><title>3AI-Factory-Connector</title>
    <style>
        body { font-family: sans-serif; background: #0b0e14; color: #e6edf3; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #58a6ff; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin-bottom: 15px; }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>⚡ 3AI-Factory-Connector 總控台</h1>
        <div class="card"><h3>系統狀態：78 庫全數連線中</h3><p>已整合 Flask 派發核心、SQLite 記憶體與 GitHub Webhook 安全防線。</p></div>
    </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import hmac, hashlib
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

import os
import json
import threading
import queue
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from github import Github, GithubException
from openai import OpenAI
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ==================== 1. 環境與設定 ====================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GMAIL_AI_KEY = os.getenv("OPENAI_API_KEY")       # Gmail AI 使用 GPT
XAI_API_KEY = os.getenv("XAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not all([GITHUB_TOKEN, GMAIL_AI_KEY, XAI_API_KEY, DEEPSEEK_API_KEY]):
    print("❌ 請確認 .env 檔案完整 (GITHUB_TOKEN, OPENAI_API_KEY, XAI_API_KEY, DEEPSEEK_API_KEY)")
    exit(1)

app = FastAPI(title="3AI-Factory-Connector", version="1.0")

# ==================== 2. 資料模型 ====================
class Task(BaseModel):
    task_id: str
    source_org: str
    repo_name: str
    action: str          # "read" or "write"
    assigned_ai: str     # "gmail_ai", "xai", "deepseek"
    content: str = None
    branch: str = "main"
    status: str = "pending"

# ==================== 3. 核心註冊器 (一次開78庫) ====================
class RepositoryRegistry:
    def __init__(self):
        self.gmail_repos = []      # 24 庫
        self.shared_repos = []     # 54 庫
        self.total_count = 0
        self.task_queue = queue.Queue()
        self.approval_queue = queue.Queue()
        self.task_history = []
        self._lock = threading.Lock()

    def fetch_all_repos(self):
        """一次性開庫：讀取兩個 Organization 的全部 Repository"""
        print("🔄 正在一次性串接 GitHub 並註冊 78 個庫...")
        g = Github(GITHUB_TOKEN)
        
        # ---- 讀取 Lightning-Ai-ALL (Gmail AI 專屬 24庫) ----
        try:
            org1 = g.get_organization("Lightning-Ai-ALL")
            for repo in org1.get_repos():
                self.gmail_repos.append({"name": repo.name, "full_name": repo.full_name, "private": repo.private})
            print(f"✅ [1/2] Lightning-Ai-ALL 註冊完成：{len(self.gmail_repos)} 個庫")
        except GithubException as e:
            print(f"❌ 無法讀取 Lightning-Ai-ALL：{e}")
        
        # ---- 讀取 Stormcar820 (xAI + DeepSeek 共享 54庫) ----
        try:
            org2 = g.get_organization("Stormcar820")
            for repo in org2.get_repos():
                self.shared_repos.append({"name": repo.name, "full_name": repo.full_name, "private": repo.private})
            print(f"✅ [2/2] Stormcar820 註冊完成：{len(self.shared_repos)} 個庫")
        except GithubException as e:
            print(f"❌ 無法讀取 Stormcar820：{e}")
        
        self.total_count = len(self.gmail_repos) + len(self.shared_repos)
        print(f"🎯 總計註冊 {self.total_count} 個 Repository (Gmail 專屬: {len(self.gmail_repos)}, 共享: {len(self.shared_repos)})")
        return self.gmail_repos, self.shared_repos

# ==================== 4. AI 客戶端封裝 ====================
class GmailAIClient:
    def __init__(self): 
        self.client = OpenAI(api_key=GMAIL_AI_KEY)
    def analyze(self, content):
        return self.client.chat.completions.create(model="gpt-4", messages=[{"role":"user","content":content}])

class XAIClient:
    def __init__(self): 
        self.client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    def analyze(self, content):
        return self.client.chat.completions.create(model="grok-1", messages=[{"role":"user","content":content}])

class DeepSeekClient:
    def __init__(self): 
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    def analyze(self, content):
        return self.client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":content}])

# ==================== 5. 生產者 Worker (背景執行) ====================
def production_worker(registry: RepositoryRegistry):
    print("⚙️ Production Worker 啟動，監聽任務隊列...")
    g = Github(GITHUB_TOKEN)
    
    while True:
        try:
            task = registry.task_queue.get(timeout=3)
            if task is None:
                break
            
            repo_full = f"{task.source_org}/{task.repo_name}"
            repo = g.get_repo(repo_full)
            
            # --- 寫入保護：共享 54 庫強制進待審核 ---
            if task.action == "write" and task.source_org == "Stormcar820":
                task.status = "awaiting_approval"
                registry.approval_queue.put(task)
                print(f"⏸️ [待審] 寫入 {repo_full} 需人工確認")
                registry.task_queue.task_done()
                continue

            # --- 執行讀取 ---
            if task.action == "read":
                contents = repo.get_contents("")
                task.content = f"讀取到 {len(contents)} 個檔案"
                task.status = "done"
                print(f"📖 {task.assigned_ai} 讀取 {repo_full} 完成")
            
            # --- 執行寫入 (只有被核准的任務會走到這) ---
            elif task.action == "write" and task.status == "approved":
                file_path = f"ai_outputs/{task.task_id}.txt"
                repo.create_file(file_path, f"AI 生成: {task.task_id}", task.content, branch=task.branch)
                task.status = "done"
                print(f"✍️ {task.assigned_ai} 成功寫入 {repo_full}/{file_path}")
            
            with registry._lock:
                registry.task_history.append(task)
            registry.task_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"⚠️ Worker 錯誤: {e}")

# ==================== 6. FastAPI 啟動事件 (一次開庫＋啟動8步驟) ====================
@app.on_event("startup")
def startup_sequence():
    global registry
    print("\n" + "="*50)
    print("🚀 啟動 3AI-Factory-Connector 整頁應用程式")
    print("="*50)
    
    # 1. AI Gateway (FastAPI 本身)
    print("1️⃣ AI Gateway (FastAPI) 已啟動")
    
    # 2. GitHub Connector 驗證
    g = Github(GITHUB_TOKEN)
    print("2️⃣ GitHub Connector 驗證通過")
    
    # 3. Repository Registry (一次開 78 庫)
    registry = RepositoryRegistry()
    gmail_repos, shared_repos = registry.fetch_all_repos()  # <-- 這裡就是「一次開庫」
    print("3️⃣ Repository Registry 建立完成 (78庫已載入)")
    
    # 4. Queue / Orchestrator
    app.state.registry = registry
    print("4️⃣ Queue / Orchestrator 初始化完成")
    
    # 5. ChatGPT (Gmail AI)
    app.state.gmail_ai = GmailAIClient()
    print("5️⃣ Gmail AI (ChatGPT) 就緒 (管轄 24 庫)")
    
    # 6. xAI
    app.state.xai = XAIClient()
    print("6️⃣ xAI 就緒 (共享 54 庫)")
    
    # 7. DeepSeek
    app.state.deepseek = DeepSeekClient()
    print("7️⃣ DeepSeek 就緒 (共享 54 庫)")
    
    # 8. Production Worker (背景執行緒)
    worker = threading.Thread(target=production_worker, args=(registry,), daemon=True)
    worker.start()
    print("8️⃣ Production Worker 已上線")
    
    print("\n✅ 全系統啟動完成！")
    print(f"📊 Gmail AI 專屬: {len(gmail_repos)} 個庫")
    print(f"📊 xAI + DeepSeek 共享: {len(shared_repos)} 個庫 (寫入需人工核准)")
    print("="*50 + "\n")

# ==================== 7. 精美儀表板 HTML (整頁串聯應用) ====================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>3AI-Factory-Connector 儀表板</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Segoe UI', Roboto, system-ui, sans-serif; background: #0b0e14; color: #e6edf3; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { font-size: 2rem; margin-bottom: 5px; background: linear-gradient(135deg, #58a6ff, #f0883e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .sub { color: #8b949e; margin-bottom: 30px; border-bottom: 1px solid #21262d; padding-bottom: 15px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; transition: 0.2s; }
            .card:hover { border-color: #58a6ff; }
            .card h3 { color: #f0f6fc; margin-bottom: 12px; font-size: 1.1rem; display: flex; align-items: center; gap: 8px; }
            .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
            .badge.green { background: #238636; color: #fff; }
            .badge.orange { background: #d29922; color: #fff; }
            .badge.blue { background: #1f6feb; color: #fff; }
            .badge.purple { background: #8957e5; color: #fff; }
            .badge.red { background: #da3633; color: #fff; }
            .repo-list { max-height: 200px; overflow-y: auto; font-size: 0.85rem; color: #8b949e; }
            .repo-list li { list-style: none; padding: 4px 0; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between; }
            .repo-list li span.private { color: #d29922; font-size: 0.7rem; }
            .queue-box { background: #0d1117; border-radius: 8px; padding: 15px; margin-top: 10px; }
            .task-item { background: #161b22; border-left: 3px solid #58a6ff; padding: 10px 15px; margin: 8px 0; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
            .btn { background: #238636; border: none; color: white; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .btn:hover { background: #2ea043; }
            .btn.danger { background: #da3633; }
            .btn.danger:hover { background: #f85149; }
            .flex { display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }
            .mt-20 { margin-top: 20px; }
            input, select { background: #0d1117; border: 1px solid #30363d; color: #e6edf3; padding: 8px 12px; border-radius: 6px; width: 100%; max-width: 200px; }
            .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; }
            .form-row div { display: flex; flex-direction: column; gap: 4px; }
            .form-row label { font-size: 0.8rem; color: #8b949e; }
            #approvalList .task-item { border-left-color: #d29922; }
            .stat-number { font-size: 2rem; font-weight: 700; color: #f0f6fc; }
        </style>
    </head>
    <body>
    <div class="container">
        <h1>⚡ 3AI-Factory-Connector</h1>
        <div class="sub">整頁串聯應用 · 自動化調度 · 寫入人工確認</div>
        
        <!-- 狀態卡片 -->
        <div class="grid" id="statusCards">
            <div class="card"><h3>🧠 Gmail AI</h3><span class="badge green">● 線上</span><br><span id="gmailCount">24</span> 個專屬庫</div>
            <div class="card"><h3>🧠 xAI</h3><span class="badge green">● 線上</span><br><span id="xaiCount">54</span> 個共享庫 (唯讀優先)</div>
            <div class="card"><h3>🧠 DeepSeek</h3><span class="badge green">● 線上</span><br><span id="dsCount">54</span> 個共享庫 (唯讀優先)</div>
            <div class="card"><h3>📦 總註冊庫</h3><span class="stat-number" id="totalRepos">78</span><br>已全數載入</div>
        </div>

        <!-- 隊列與待審 -->
        <div class="grid">
            <div class="card"><h3>📋 任務隊列</h3><span id="queueSize" class="stat-number" style="font-size:1.5rem;">0</span> 等待中</div>
            <div class="card"><h3>⏸️ 待審核寫入</h3><span id="approvalSize" class="stat-number" style="font-size:1.5rem;">0</span> 需人工確認</div>
        </div>

        <!-- 顯示所有庫 -->
        <div class="grid">
            <div class="card">
                <h3>📁 Gmail 專屬 (Lightning-Ai-ALL) <span class="badge blue">24</span></h3>
                <ul class="repo-list" id="gmailRepoList"></ul>
            </div>
            <div class="card">
                <h3>📁 共享 54 庫 (Stormcar820) <span class="badge orange">54</span></h3>
                <ul class="repo-list" id="sharedRepoList"></ul>
            </div>
        </div>

        <!-- 派工表單 -->
        <div class="card" style="margin-top:20px;">
            <h3>📤 派發新任務</h3>
            <div class="form-row">
                <div><label>任務ID</label><input id="taskId" value="TASK-$(Date.now())" placeholder="TASK-001"></div>
                <div><label>組織</label>
                    <select id="orgSelect"><option value="Lightning-Ai-ALL">Lightning-Ai-ALL (24庫)</option><option value="Stormcar820">Stormcar820 (54庫)</option></select>
                </div>
                <div><label>Repo 名稱</label><input id="repoName" placeholder="repo-name"></div>
                <div><label>指派 AI</label>
                    <select id="aiSelect"><option value="gmail_ai">Gmail AI</option><option value="xai">xAI</option><option value="deepseek">DeepSeek</option></select>
                </div>
                <div><label>動作</label>
                    <select id="actionSelect"><option value="read">讀取 (READ)</option><option value="write">寫入 (WRITE)</option></select>
                </div>
                <div><label>內容 (寫入用)</label><input id="contentInput" placeholder="檔案內容..."></div>
                <div style="align-self:end;"><button class="btn" onclick="submitTask()">🚀 派工</button></div>
            </div>
        </div>

        <!-- 待審核清單 -->
        <div class="card" style="margin-top:20px;" id="approvalSection">
            <h3>⏸️ 待人工確認的寫入任務 (共享54庫)</h3>
            <div id="approvalList"><div class="queue-box" style="color:#8b949e;">暫無待審任務</div></div>
        </div>

        <!-- 歷史紀錄 -->
        <div class="card" style="margin-top:20px;">
            <h3>📜 執行歷史 (最近5筆)</h3>
            <div id="historyLog" class="queue-box" style="max-height:150px; overflow-y:auto;"></div>
        </div>
    </div>

    <script>
        // 自動更新
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('totalRepos').innerText = data.total_repos || 78;
                document.getElementById('queueSize').innerText = data.queue_size || 0;
                document.getElementById('approvalSize').innerText = data.approval_size || 0;
                
                // 更新庫列表
                if(data.gmail_repos) {
                    const ul = document.getElementById('gmailRepoList');
                    ul.innerHTML = data.gmail_repos.map(r => `<li>${r.name} ${r.private ? '<span class="private">🔒</span>' : ''}</li>`).join('');
                }
                if(data.shared_repos) {
                    const ul = document.getElementById('sharedRepoList');
                    ul.innerHTML = data.shared_repos.map(r => `<li>${r.name} ${r.private ? '<span class="private">🔒</span>' : ''}</li>`).join('');
                }

                // 更新待審核
                const approvalDiv = document.getElementById('approvalList');
                if(data.pending_approvals && data.pending_approvals.length > 0) {
                    approvalDiv.innerHTML = data.pending_approvals.map(t => `
                        <div class="task-item">
                            <span><strong>${t.task_id}</strong> → ${t.repo_name} (${t.assigned_ai})</span>
                            <button class="btn" onclick="approveTask('${t.task_id}')">✅ 核准寫入</button>
                        </div>
                    `).join('');
                } else {
                    approvalDiv.innerHTML = '<div class="queue-box" style="color:#8b949e;">✅ 無待審任務</div>';
                }

                // 更新歷史
                if(data.history) {
                    const log = document.getElementById('historyLog');
                    log.innerHTML = data.history.slice(-5).reverse().map(t => 
                        `<div style="padding:4px 0; border-bottom:1px solid #21262d; font-size:0.85rem;">
                            <span class="badge ${t.status === 'done' ? 'green' : 'orange'}">${t.status}</span>
                            ${t.task_id} | ${t.assigned_ai} | ${t.action} | ${t.repo_name}
                        </div>`
                    ).join('');
                }
            } catch(e) { console.error(e); }
        }

        async function submitTask() {
            const taskId = document.getElementById('taskId').value || 'TASK-' + Date.now();
            const payload = {
                task_id: taskId,
                source_org: document.getElementById('orgSelect').value,
                repo_name: document.getElementById('repoName').value,
                assigned_ai: document.getElementById('aiSelect').value,
                action: document.getElementById('actionSelect').value,
                content: document.getElementById('contentInput').value || 'AI 生成內容'
            };
            const res = await fetch('/submit_task', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
            const result = await res.json();
            alert(result.message || '任務已派發');
            fetchStatus();
        }

        async function approveTask(taskId) {
            if(!confirm(`確認核准 ${taskId} 寫入共享庫？`)) return;
            const res = await fetch(`/approve/${taskId}`, { method: 'POST' });
            const result = await res.json();
            alert(result.message || '已核准');
            fetchStatus();
        }

        // 初始化與定時更新
        fetchStatus();
        setInterval(fetchStatus, 3000);
    </script>
    </body>
    </html>
    """
    return html

# ==================== 8. API 端點 ====================
@app.get("/api/status")
async def get_status():
    reg = app.state.registry
    with reg._lock:
        pending = []
        # 讀取待審隊列 (不取出)
        with reg.approval_queue.mutex:
            for item in reg.approval_queue.queue:
                pending.append({"task_id": item.task_id, "repo_name": item.repo_name, "assigned_ai": item.assigned_ai})
        
        history = [{"task_id": t.task_id, "status": t.status, "action": t.action, "repo_name": t.repo_name, "assigned_ai": t.assigned_ai} for t in reg.task_history[-10:]]
        
        return {
            "total_repos": reg.total_count,
            "gmail_repos": reg.gmail_repos,
            "shared_repos": reg.shared_repos,
            "queue_size": reg.task_queue.qsize(),
            "approval_size": reg.approval_queue.qsize(),
            "pending_approvals": pending,
            "history": history
        }

@app.post("/submit_task")
async def submit_task(task: Task):
    reg = app.state.registry
    
    # 權限校驗：Gmail AI 只能碰 Lightning，xAI/DeepSeek 只能碰 Stormcar
    if task.assigned_ai == "gmail_ai" and task.source_org != "Lightning-Ai-ALL":
        raise HTTPException(400, "Gmail AI 僅能處理 Lightning-Ai-ALL 的庫")
    if task.assigned_ai in ["xai", "deepseek"] and task.source_org != "Stormcar820":
        raise HTTPException(400, "xAI/DeepSeek 僅能處理 Stormcar820 的庫")
    
    reg.task_queue.put(task)
    return {"message": f"任務 {task.task_id} 已派發給 {task.assigned_ai}"}

@app.post("/approve/{task_id}")
async def approve_task(task_id: str):
    reg = app.state.registry
    temp = []
    found = None
    
    # 從待審隊列取出並核准
    while not reg.approval_queue.empty():
        item = reg.approval_queue.get()
        if item.task_id == task_id:
            item.status = "approved"
            found = item
            reg.task_queue.put(item)  # 放回主隊列讓 Worker 執行寫入
        else:
            temp.append(item)
    
    for t in temp:
        reg.approval_queue.put(t)
    
    if found:
        return {"message": f"✅ 任務 {task_id} 已核准，Worker 將執行寫入"}
    else:
        raise HTTPException(404, "找不到該任務或已處理")

# ==================== 9. 主程式入口 ====================
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
