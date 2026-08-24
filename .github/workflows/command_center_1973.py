# command/command_center_1973.py
from dataclasses import dataclass, field
from enum import IntEnum
from datetime import datetime, timezone
import uuid


class PermissionLevel(IntEnum):
    L0_OBSERVE = 0
    L1_ANALYZE = 1
    L2_RECOMMEND = 2
    L3_AUTOMATION = 3
    L4_HUMAN_CONFIRM = 4


class TaskStatus:
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    WAITING_L4 = "WAITING_L4"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    risk_level: PermissionLevel

    status: str = TaskStatus.CREATED
    assigned_nodes: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)

    created_at: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )


class CommandCenter1973:

    SAFE_NODES = {"777", "888"}

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def _get_task(self, task_id: str) -> Task:
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")

        return self.tasks[task_id]

    def log(self, task: Task, message: str):
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {message}"

        task.logs.append(entry)
        print(entry)

    def create_task(
        self,
        title: str,
        description: str,
        risk_level: PermissionLevel,
    ) -> Task:

        task_id = f"1973-{uuid.uuid4().hex[:8].upper()}"

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            risk_level=risk_level,
        )

        self.tasks[task_id] = task

        self.log(
            task,
            f"CREATE | {title} | L{risk_level}",
        )

        return task

    def add_ai_analysis(
        self,
        task_id: str,
        model: str,
        result: str,
        confidence: str,
    ):

        task = self._get_task(task_id)

        task.status = TaskStatus.ANALYZING

        self.log(
            task,
            (
                f"AI | {model} | "
                f"confidence={confidence} | "
                f"{result}"
            ),
        )

    def assign_node(
        self,
        task_id: str,
        node: str,
    ) -> bool:

        task = self._get_task(task_id)

        if node not in self.SAFE_NODES:
            self.log(task, f"DENY | unknown node={node}")
            return False

        if node not in task.assigned_nodes:
            task.assigned_nodes.append(node)

        self.log(
            task,
            f"ASSIGN | node={node}",
        )

        return True

    def request_l4_confirmation(
        self,
        task_id: str,
    ):

        task = self._get_task(task_id)

        task.status = TaskStatus.WAITING_L4

        self.log(
            task,
            "L4 | WAITING HUMAN CONFIRMATION",
        )

    def human_confirm(
        self,
        task_id: str,
        approved: bool,
        operator: str = "human",
    ) -> bool:

        task = self._get_task(task_id)

        if task.status != TaskStatus.WAITING_L4:
            self.log(
                task,
                "L4 DENY | invalid task state",
            )
            return False

        if approved:
            task.status = TaskStatus.APPROVED

            self.log(
                task,
                f"L4 APPROVED | operator={operator}",
            )

            return True

        task.status = TaskStatus.REJECTED

        self.log(
            task,
            f"L4 REJECTED | operator={operator}",
        )

        return False

    def start_task(self, task_id: str) -> bool:

        task = self._get_task(task_id)

        if task.risk_level >= PermissionLevel.L4_HUMAN_CONFIRM:

            if task.status != TaskStatus.APPROVED:
                self.log(
                    task,
                    "SAFETY GATE | L4 approval required",
                )
                return False

        task.status = TaskStatus.RUNNING

        self.log(
            task,
            "RUNNING | simulation mode",
        )

        return True

    def complete_task(
        self,
        task_id: str,
        report: str,
    ):

        task = self._get_task(task_id)

        task.status = TaskStatus.COMPLETED

        self.log(
            task,
            f"COMPLETE | {report}",
        )
        
# ⚡ OPER AI · Lightning Empire
# 🏛️ 1973 Command Center
#
# 功能：
#   - 任務建立
#   - AI 分析結果登記
#   - 777 / 888 模擬節點調度
#   - L0-L4 權限管理
#   - L4 人工確認閘門
#   - 任務狀態與日誌
#
# 安全設計：
#   本程式不直接控制真實無人機、不執行攻擊、
#   不執行拘束/追捕/執法，也不繞過人工授權。

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Dict, List, Optional
import uuid


# ============================================================
# L0-L4 權限
# ============================================================

class PermissionLevel(IntEnum):
    L0_OBSERVE = 0
    L1_ANALYZE = 1
    L2_RECOMMEND = 2
    L3_AUTOMATION = 3
    L4_HUMAN_CONFIRM = 4


# ============================================================
# 任務狀態
# ============================================================

class TaskStatus:
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    WAITING_L4 = "WAITING_L4"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


# ============================================================
# 任務資料
# ============================================================

@dataclass
class Task:
    task_id: str
    title: str
    description: str
    risk_level: PermissionLevel
    status: str = TaskStatus.CREATED
    assigned_nodes: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    logs: List[str] = field(default_factory=list)


# ============================================================
# 1973 指揮中心
# ============================================================

class CommandCenter1973:

    SAFE_NODES = {
        "777": {
            "name": "Drone 777",
            "role": "長程監測／通訊中繼",
        },
        "888": {
            "name": "Drone 888 AI",
            "role": "邊緣辨識／安全避障",
        },
    }

    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    # --------------------------------------------------------
    # 日誌
    # --------------------------------------------------------

    def log(self, task: Task, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {message}"
        task.logs.append(entry)
        print(entry)

    # --------------------------------------------------------
    # 建立任務
    # --------------------------------------------------------

    def create_task(
        self,
        title: str,
        description: str,
        risk_level: PermissionLevel,
    ) -> Task:

        task_id = f"1973-{uuid.uuid4().hex[:8].upper()}"

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            risk_level=risk_level,
        )

        self.tasks[task_id] = task

        self.log(
            task,
            f"任務建立：{title} | 權限 L{risk_level}",
        )

        return task

    # --------------------------------------------------------
    # AI 分析結果
    # --------------------------------------------------------

    def add_ai_analysis(
        self,
        task_id: str,
        model: str,
        result: str,
        confidence: str,
    ) -> None:

        task = self._get_task(task_id)

        task.status = TaskStatus.ANALYZING

        self.log(
            task,
            (
                f"AI 分析 | model={model} "
                f"| confidence={confidence} "
                f"| result={result}"
            ),
        )

    # --------------------------------------------------------
    # 多模型驗證
    # --------------------------------------------------------

    def validate_models(
        self,
        task_id: str,
        results: List[str],
    ) -> bool:

        task = self._get_task(task_id)

        if not results:
            self.log(task, "驗證失敗：沒有模型結果")
            return False

        # 這裡只做最基本的「結果存在性」檢查。
        # 真正的模型交叉驗證應另外建立 validator。
        unique_results = set(results)

        if len(unique_results) == 1:
            self.log(task, "多模型結果一致")
            return True

        self.log(task, "多模型結果存在差異，標記 CONFLICT")
        return False

    # --------------------------------------------------------
    # 指派 777 / 888
    # --------------------------------------------------------

    def assign_node(
        self,
        task_id: str,
        node: str,
    ) -> bool:

        task = self._get_task(task_id)

        if node not in self.SAFE_NODES:
            self.log(task, f"拒絕未知節點：{node}")
            return False

        if node not in task.assigned_nodes:
            task.assigned_nodes.append(node)

        self.log(
            task,
            (
                f"節點加入：{node} "
                f"({self.SAFE_NODES[node]['role']})"
            ),
        )

        return True

    # --------------------------------------------------------
    # L4 人工確認
    # --------------------------------------------------------

    def request_l4_confirmation(
        self,
        task_id: str,
    ) -> None:

        task = self._get_task(task_id)

        task.status = TaskStatus.WAITING_L4

        self.log(
            task,
            "L4：等待人類最終確認",
        )

    def human_confirm(
        self,
        task_id: str,
        approved: bool,
        operator: str = "human",
    ) -> bool:

        task = self._get_task(task_id)

        if task.status != TaskStatus.WAITING_L4:
            self.log(
                task,
                "L4 拒絕：任務目前不是等待人工確認狀態",
            )
            return False

        if approved:
            task.status = TaskStatus.APPROVED

            self.log(
                task,
                f"L4 人工確認通過 | operator={operator}",
            )

            return True

        task.status = TaskStatus.REJECTED

        self.log(
            task,
            f"L4 人工拒絕 | operator={operator}",
        )

        return False

    # --------------------------------------------------------
    # 執行任務
    # --------------------------------------------------------

    def start_task(self, task_id: str) -> bool:

        task = self._get_task(task_id)

        # L4 任務沒有人工確認，不得執行
        if task.risk_level >= PermissionLevel.L4_HUMAN_CONFIRM:
            if task.status != TaskStatus.APPROVED:
                self.log(
                    task,
                    "安全閘門：L4 任務尚未取得人工確認",
                )
                return False

        task.status = TaskStatus.RUNNING

        self.log(
            task,
            "任務進入 RUNNING（安全模擬模式）",
        )

        return True

    # --------------------------------------------------------
    # 完成任務
    # --------------------------------------------------------

    def complete_task(
        self,
        task_id: str,
        report: str,
    ) -> None:

        task = self._get_task(task_id)

        task.status = TaskStatus.COMPLETED

        self.log(
            task,
            f"任務完成 | report={report}",
        )

    # --------------------------------------------------------
    # 查詢任務
    # --------------------------------------------------------

    def status(self, task_id: str) -> Task:

        return self._get_task(task_id)

    # --------------------------------------------------------
    # 內部安全檢查
    # --------------------------------------------------------

    def _get_task(self, task_id: str) -> Task:

        if task_id not in self.tasks:
            raise KeyError(f"找不到任務：{task_id}")

        return self.tasks[task_id]


# ============================================================
# Demo
# ============================================================

def demo():

    center = CommandCenter1973()

    print()
    print("=" * 60)
    print("⚡ OPER AI · Lightning Empire")
    print("🏛️ 1973 Command Center")
    print("=" * 60)

    # 建立一個防災資訊模擬任務
    task = center.create_task(
        title="災害環境資訊模擬",
        description="分析公開環境資料並建立風險摘要",
        risk_level=PermissionLevel.L2_RECOMMEND,
    )

    # 多模型分析
    center.add_ai_analysis(
        task.task_id,
        model="ChatGPT",
        result="需要進一步確認環境資料",
        confidence="MEDIUM",
    )

    center.add_ai_analysis(
        task.task_id,
        model="DeepSeek",
        result="需要進一步確認環境資料",
        confidence="MEDIUM",
    )

    # 交叉驗證
    center.validate_models(
        task.task_id,
        [
            "需要進一步確認環境資料",
            "需要進一步確認環境資料",
        ],
    )

    # 模擬節點
    center.assign_node(task.task_id, "777")
    center.assign_node(task.task_id, "888")

    # L2 可以進入建議流程
    center.start_task(task.task_id)

    center.complete_task(
        task.task_id,
        "完成資訊分析與節點狀態模擬",
    )

    print()
    print("📋 任務 ID :", task.task_id)
    print("📌 狀態    :", task.status)
    print("📡 節點    :", ", ".join(task.assigned_nodes))


if __name__ == "__main__":
    demo()
