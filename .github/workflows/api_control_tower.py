name: Python Package using Conda

on: [push]

jobs:
  build-linux:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 5

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.10
      uses: actions/setup-python@v3
      with:
        python-version: '3.10'
    - name: Add conda to system path
      run: |
        # $CONDA is an environment variable pointing to the root of the miniconda directory
        echo $CONDA/bin >> $GITHUB_PATH
    - name: Install dependencies
      run: |
        conda env update --file environment.yml --name base
    - name: Lint with flake8
      run: |
        conda install flake8
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    - name: Test with pytest
      run: |
        conda install pytest
        pytest
# === api_control_tower.py ===

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ---------- 你的原始核心（最小改動） ----------
class ControlTower:
    def __init__(self, config_path: str = "All-Ai-main.yml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.agents = self.config["agents"]
        self.workflows = self.config["workflows"]
        self.routing = self.config["routing"]

    def route(self, query: str) -> str:
        for wf_name, wf in self.workflows.items():
            for keyword in wf["trigger"]:
                if keyword == "*" or keyword in query:
                    return wf_name
        return self.routing["fallback"]

    def run_agent(self, agent_name: str, data: str) -> str:
        # 這裡保留你原本的模擬邏輯，實際部署時可替換為 LLM call
        print(f"[RUN] {agent_name} -> {data}")
        return f"{agent_name}:{data}"

    def run_workflow(self, workflow_name: str, query: str) -> str:
        workflow = self.workflows[workflow_name]
        result = query
        for step in workflow["steps"]:
            result = self.run_agent(step, result)
        return result

    def run(self, query: str) -> str:
        wf_name = self.route(query)
        return self.run_workflow(wf_name, query)


# ---------- FastAPI 層 ----------
app = FastAPI(title="Lightning AI Factory", version="1.0")

# 啟動時載入控制塔（全域單例）
ct: Optional[ControlTower] = None

@app.on_event("startup")
def startup_event():
    global ct
    ct = ControlTower("All-Ai-main.yml")
    print("Control Tower loaded.")

# 請求/回應模型
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    workflow: str
    result: str

@app.post("/run", response_model=QueryResponse)
def run_query(req: QueryRequest):
    if ct is None:
        raise HTTPException(status_code=500, detail="Control Tower not initialized")
    wf_name = ct.route(req.query)
    result = ct.run_workflow(wf_name, req.query)
    return QueryResponse(workflow=wf_name, result=result)

# 健康檢查
@app.get("/health")
def health():
    return {"status": "ok", "agents": list(ct.agents.keys()) if ct else []}

# ---------- 入口 ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
